"""
routes_agent.py — chat endpoint with server-side confidence and reasoning.

Confidence and reasoning are derived from the agent's tool call trace rather
than asking the LLM to generate them. This avoids the tool_use_failed error
that occurs when the model tries to emit CONFIDENCE/REASONING inside a
function call generation.
"""
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.agent import get_agent, AgentNotConfiguredError
from app.utils.logger import get_logger

router = APIRouter(prefix="/agent", tags=["agent"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


# ── confidence rules ───────────────────────────────────────────────────────────
# Maps tool names to a base confidence score. Tools that return direct counts
# from the database are high confidence; tools that return lists the agent
# interprets are slightly lower.
_TOOL_CONFIDENCE = {
    "tool_db_summary":          100,
    "tool_site_counts":         100,
    "tool_undecided_zone_count":100,
    "tool_pile_refusal_count":  100,
    "tool_pile_test_summary":   100,
    "tool_list_sites":           95,
    "tool_list_zones":           95,
    "tool_zones_by_decision":    95,
    "tool_zones_no_decision":    95,
    "tool_zone_detail":          95,
    "tool_pile_tests":           90,
    "tool_pile_refusals":        90,
    "tool_dpsh_refusals":        90,
    "tool_ground_profile":       85,
}
_DEFAULT_CONFIDENCE = 70   # agent answered without a tool (from context only)
_NO_TOOL_CONFIDENCE  = 50  # question couldn't be answered with available tools


def _extract_tool_calls(response) -> list[dict]:
    """
    Pull tool call records from the agent response.
    Tries every known attribute that agent-framework versions use.
    """
    calls = []

    def _tc(name, args, result):
        if name:
            calls.append({
                "name":   str(name),
                "args":   args if isinstance(args, dict) else {},
                "result": result,
            })

    # response.tool_calls
    if hasattr(response, "tool_calls") and response.tool_calls:
        for tc in response.tool_calls:
            _tc(
                getattr(tc, "name", None) or getattr(tc, "function_name", None),
                getattr(tc, "arguments", None) or getattr(tc, "input", {}),
                getattr(tc, "result", None) or getattr(tc, "output", None),
            )

    # response.steps  (list of dicts or objects)
    if not calls and hasattr(response, "steps") and response.steps:
        for step in response.steps:
            if isinstance(step, dict):
                if step.get("type") in ("tool_call", "tool_use", "function_call"):
                    _tc(step.get("name") or step.get("function"),
                        step.get("input") or step.get("arguments") or {},
                        step.get("output") or step.get("result"))
            else:
                # object-style step
                stype = getattr(step, "type", "") or ""
                if "tool" in stype.lower() or "function" in stype.lower():
                    _tc(getattr(step, "name", None) or getattr(step, "function", None),
                        getattr(step, "input", {}) or getattr(step, "arguments", {}),
                        getattr(step, "output", None) or getattr(step, "result", None))

    # response.messages  (some versions expose the full message list)
    if not calls and hasattr(response, "messages") and response.messages:
        for msg in response.messages:
            role = getattr(msg, "role", "") or (msg.get("role","") if isinstance(msg,dict) else "")
            if role in ("tool", "function"):
                name = (getattr(msg, "name", None) or
                        (msg.get("name") if isinstance(msg,dict) else None))
                content = (getattr(msg, "content", None) or
                           (msg.get("content") if isinstance(msg,dict) else None))
                _tc(name, {}, content)

    # Log what we found to help debug
    import logging
    logging.getLogger(__name__).debug(
        "tool_calls extracted: %s", [c["name"] for c in calls]
    )
    return calls


def _build_confidence_and_reasoning(tool_calls: list[dict], reply: str) -> tuple[int, str]:
    """
    Derive confidence (0-100) and a reasoning string from the tool call trace.
    """
    if not tool_calls:
        # No tools called — check whether the reply looks factual or not
        refusal_words = ["cannot", "can't", "don't have", "not supported",
                         "unable", "unsupported", "not available"]
        factual_words = ["there are", "there is", "the count", "in total",
                         "pile", "zone", "borehole", "dpsh", "test"]
        is_refusal = any(w in reply.lower() for w in refusal_words)
        looks_factual = any(w in reply.lower() for w in factual_words)

        if is_refusal:
            confidence = _NO_TOOL_CONFIDENCE   # 50% — acknowledged it can't answer
            reasoning  = "This question could not be answered with the available tools."
        elif looks_factual:
            # Claims to give a factual answer but used no tools — likely hallucination
            confidence = 20
            reasoning  = ("WARNING: No database tools were called but the answer appears "
                          "factual. This answer may be incorrect — it was generated from "
                          "model memory rather than live database data.")
        else:
            confidence = _DEFAULT_CONFIDENCE   # 70% — general/explanatory answer
            reasoning  = "No database query was needed for this question."
        return confidence, reasoning

    # Base confidence = minimum of all tools used
    # (weakest link — if one tool is uncertain, the whole answer is)
    confidence = min(
        _TOOL_CONFIDENCE.get(tc["name"], _DEFAULT_CONFIDENCE)
        for tc in tool_calls
    )

    # Build reasoning from the tool trace
    parts = []
    for tc in tool_calls:
        name   = tc["name"]
        args   = tc.get("args", {})
        result = tc.get("result")

        # Summarise args as "for X" clause
        site   = args.get("site_id", "")
        zone   = args.get("zone_id", "")
        ctx    = f" for {site}" if site else ""
        ctx   += f" zone {zone}" if zone else ""

        # Summarise result — extract the most useful scalar
        summary = ""
        if isinstance(result, dict):
            # Pick the most meaningful scalar key from the result
            priority_keys = [
                "zones", "pile_locations", "pile_tests", "dpsh_probes",
                "boreholes", "test_pits", "n_refusals", "total_tests",
                "passed", "failed", "n_zones", "n", "total_sites",
                "undecided_zones", "n_undecided",
            ]
            for k in priority_keys:
                if k in result and result[k] is not None:
                    summary = f" → {k}={result[k]}"
                    break
            if not summary:
                # Fall back to showing all scalar values
                scalars = {k: v for k, v in result.items()
                           if isinstance(v, (int, float, str)) and v is not None}
                if scalars:
                    summary = " → " + ", ".join(f"{k}={v}" for k, v in list(scalars.items())[:3])
        elif isinstance(result, list):
            summary = f" → {len(result)} rows returned"
        elif result is not None:
            summary = f" → {result}"

        parts.append(f"Called {name}{ctx}{summary}.")

    reasoning = " ".join(parts)
    return confidence, reasoning


@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        agent = get_agent()
    except AgentNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        response   = await agent.run(request.message)
        # Debug: inspect contents items inside each message
        if hasattr(response, "messages") and response.messages:
            for i, msg in enumerate(response.messages[:6]):
                role = getattr(msg, "role", "?")
                contents = getattr(msg, "contents", []) or []
                logger.info("message[%d] role=%s contents_count=%d", i, role, len(contents))
                for j, item in enumerate(contents):
                    item_attrs = {k: type(v).__name__ for k, v in vars(item).items()
                                  if not k.startswith("__")}
                    logger.info("  contents[%d] attrs: %s", j, item_attrs)
                    for attr in ("type", "name", "text", "content", "id",
                                 "function_name", "function_arguments",
                                 "tool_call_id", "result", "input", "output"):
                        val = getattr(item, attr, "MISSING")
                        if val != "MISSING" and val is not None:
                            logger.info("    contents[%d].%s = %r", j, attr, str(val)[:120])
        tool_calls = _extract_tool_calls(response)
        reply      = response.text.strip()
        logger.info("chat: tools_called=%s reply_preview=%r",
                    [t["name"] for t in tool_calls], reply[:80])

        confidence, reasoning = _build_confidence_and_reasoning(tool_calls, reply)

        return {
            "reply":      reply,
            "confidence": confidence,
            "reasoning":  reasoning,
        }

    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}")