"""
routes_agent.py — chat endpoint with two-level algorithmic confidence scoring.

Level 1: plain-language sentence summarising what happened and why.
Level 2: detailed scoring breakdown across four weighted factors.

Tool call trace is read from response.messages:
  assistant messages: contents[i].type == "function_call"  → .name, .arguments
  tool messages:      contents[i].type == "function_result" → .result
"""
import json, re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.agent import get_agent, AgentNotConfiguredError
from app.utils.logger import get_logger

router = APIRouter(prefix="/agent", tags=["agent"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


# ── tool descriptions for semantic match scoring ───────────────────────────────
TOOL_DESCRIPTIONS = {
    "tool_list_sites":           "list every site graph name id status zone count call first whenever user mentions site name get correct site_id",
    "tool_db_summary":           "total counts entire database sites zones pile locations dpsh probes boreholes test pits how many sites total",
    "tool_site_counts":          "counts single site zones pile locations pile tests dpsh probes boreholes test pits how many zones piles maryvale site",
    "tool_list_zones":           "list all zones site pre-drill driven decision content counts discover zone ids before querying specific zone",
    "tool_zones_by_decision":    "all zones given pre-drill driven decision undecided zones which zones pre-drill driven decision",
    "tool_zones_no_decision":    "zones no pre-drill driven decision set yet undecided zones list ids",
    "tool_undecided_zone_count": "count zones no pre-drill driven decision site how many zones no decision yet undecided",
    "tool_zone_detail":          "full detail single zone decision tracker counts pile locations pile tests dpsh probes boreholes test pits how many boreholes zone",
    "tool_zone_pile_ids":        "list pile ids all piles specified zone pile test location ids give pile names zone",
    "tool_db_soil_types":        "all soil type nodes database unit_no name description what soil types exist",
    "tool_pile_test_summary":    "summary count pile load tests site zone total passed failed undecided how many pile tests passed failed",
    "tool_pile_tests":           "individual pile load test rows pass fail load proportions tension lateral compression percentage Ed which tests failed",
    "tool_pile_refusal_count":   "count piles did not reach target embedment depth shortfall metres average maximum how many piles short",
    "tool_pile_refusals":        "list piles did not reach target embedment depth shortfall which piles fell short embedment driven refusal",
    "tool_dpsh_refusals":        "dpsh probe refusal depths metres site zone shallow refusals pre-drill decisions probe depth",
    "tool_ground_profile":       "layered ground profile soil units depth borehole test pit ground profile bh tp soil layers",
    "tool_zone_pile_count":      "Return the count of the piles / pile test location in the specified zone",
    "tool_zone_borehole_count":  "Return the count of boreholes in the specified zone.",
    "tool_zone_testpit_count":   "Return the count of test pits in the specified zone.",
    "tool_zone_dpsh_count":      "Return the count of DPSH probes in the specified zone.",
    "tool_zone_dpsh_coordinates": "Return the ids and coordinates of all DPSH probes in the specified zone.",
    "tool_avg_embedment":         "average achieved pile embedment depth site zone min max target how deep piles go average depth driven"
}

NAVIGATION_TOOLS = {"tool_list_sites", "tool_list_zones"}

_DEFAULT_CONFIDENCE = 70
_NO_TOOL_CONFIDENCE  = 50


# ── tool call extraction ───────────────────────────────────────────────────────

def _extract_tool_calls(response) -> list[dict]:
    calls, pending = [], []
    for msg in (getattr(response, "messages", None) or []):
        for item in (getattr(msg, "contents", None) or []):
            itype = getattr(item, "type", None)
            if itype == "function_call":
                name     = getattr(item, "name", "") or ""
                args_raw = getattr(item, "arguments", "{}") or "{}"
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                except Exception:
                    args = {}
                pending.append({"name": name, "args": args, "result": None})
            elif itype == "function_result":
                result_raw = getattr(item, "result", None)
                try:
                    result = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
                except Exception:
                    result = result_raw
                if pending:
                    pending[-1]["result"] = result
                    calls.append(pending.pop())
    calls.extend(pending)
    logger.info("tool_calls extracted: %s", [c["name"] for c in calls])
    return calls


# ── confidence factors ────────────────────────────────────────────────────────

def _factor_question_match(question: str, tool_calls: list[dict]) -> tuple[float, str]:
    answering = [tc for tc in tool_calls if tc["name"] not in NAVIGATION_TOOLS]
    if not answering:
        return 0.9, "Navigation tools called correctly to resolve identifiers."
    stops = {"the","a","an","in","of","for","to","how","many","all","give",
             "what","is","are","at","and","or","with","their","its"}
    q_words = set(re.findall(r'\b\w+\b', question.lower())) - stops
    scores, details = [], []
    for tc in answering:
        desc_words = set(re.findall(r'\b\w+\b', TOOL_DESCRIPTIONS.get(tc["name"], tc["name"])))
        if not q_words:
            scores.append(0.8); details.append(f"{tc['name']}: no keywords to match"); continue
        overlap = len(q_words & desc_words)
        score   = min(1.0, (overlap / len(q_words)) * 2.5)
        scores.append(score)
        matched = sorted(q_words & desc_words)
        details.append(
            f"{tc['name']} matched {overlap}/{len(q_words)} question keywords"
            + (f" ({', '.join(matched[:4])})" if matched else "")
        )
    avg = sum(scores) / len(scores)
    return avg, "; ".join(details) + f" → match score {avg:.0%}"


def _factor_chain_length(tool_calls: list[dict]) -> tuple[float, str]:
    n_nav = sum(1 for tc in tool_calls if tc["name"] in NAVIGATION_TOOLS)
    n_ans = len(tool_calls) - n_nav
    if n_ans == 0:   return 0.85, f"{n_nav} navigation call(s), answer inferred from nav data."
    if n_ans == 1:   return 1.00, f"Direct: 1 answer tool{f' after {n_nav} nav call(s)' if n_nav else ''}."
    if n_ans == 2:   return 0.92, f"2 answer tools — minor chain, small assumption risk."
    if n_ans == 3:   return 0.80, f"3 answer tools — agent searched for answer."
    return 0.65, f"{n_ans} answer tools — long chain, higher assumption risk."


def _factor_completeness(tool_calls: list[dict]) -> tuple[float, str]:
    answering = [tc for tc in tool_calls if tc["name"] not in NAVIGATION_TOOLS]
    if not answering:
        return 0.85, "No answer tool results to evaluate."
    scores, parts = [], []
    for tc in answering:
        result = tc.get("result")
        if result is None:
            scores.append(0.5); parts.append(f"{tc['name']}: no result"); continue
        if isinstance(result, dict):
            has_data = (any(isinstance(v,(int,float)) and not isinstance(v,bool) and v > 0
                           for v in result.values()) or
                        any(isinstance(v,list) and v for v in result.values()))
            scores.append(1.0 if has_data else 0.45)
            parts.append(f"{tc['name']}: {'data returned' if has_data else 'empty result'}")
        elif isinstance(result, list):
            scores.append(1.0 if result else 0.45)
            parts.append(f"{tc['name']}: {len(result)} rows")
        else:
            scores.append(0.75); parts.append(f"{tc['name']}: scalar result")
    avg = sum(scores) / len(scores)
    return avg, "; ".join(parts) + f" → completeness {avg:.0%}"


def _factor_parameters(tool_calls: list[dict]) -> tuple[float, str]:
    names = [tc["name"] for tc in tool_calls]
    site_id_verified = "tool_list_sites" in names
    site_dependent = [tc for tc in tool_calls
                      if tc["name"] not in NAVIGATION_TOOLS
                      and tc.get("args", {}).get("site_id")]
    if not site_dependent:
        return 1.0, "No site-specific parameters — no assumption risk."
    if site_id_verified:
        return 1.0, "site_id verified via tool_list_sites — parameters reliable."
    return 0.72, (
        "site_id assumed from question, not verified via tool_list_sites — "
        "if the id doesn't match exactly, results may be empty."
    )


WEIGHTS = {"match": 0.35, "chain": 0.25, "completeness": 0.25, "parameters": 0.15}


# ── two-level reasoning builder ───────────────────────────────────────────────

def _build_reasoning(
    question: str,
    tool_calls: list[dict],
    reply: str,
    score: int,
    f_match: float, e_match: str,
    f_chain: float, e_chain: str,
    f_complete: float, e_complete: str,
    f_params: float, e_params: str,
) -> str:
    """
    Returns a reasoning string with two sections separated by \\n\\n:
      Section 1 — plain English sentence (what happened, why this confidence).
      Section 2 — detailed scoring breakdown.
    """
    NAVIGATION_TOOLS_local = NAVIGATION_TOOLS   # closure

    ans_tools = [tc for tc in tool_calls if tc["name"] not in NAVIGATION_TOOLS_local]
    nav_tools = [tc for tc in tool_calls if tc["name"] in NAVIGATION_TOOLS_local]

    # ── Level 1: plain-language summary ───────────────────────────────────────
    if not tool_calls:
        summary = "No database tools were called — this answer came from model memory and may be inaccurate."
    else:
        # describe primary answer tool
        primary = ans_tools[0]["name"].replace("tool_", "").replace("_", " ") if ans_tools else "navigation lookup"
        nav_phrase = " after resolving the site name" if nav_tools else ""

        # extract the key data point returned
        data_phrase = ""
        for tc in ans_tools:
            result = tc.get("result") or {}
            if not isinstance(result, dict): continue
            priority = [
                    "boreholes", "pile_locations", "pile_tests", "dpsh_probes", "test_pits",
                    "avg_embedment_m", "n_refusals", "avg_shortfall_m", ...
                ]
            for k in priority:
                if result.get(k) is not None:
                    data_phrase = f", which returned {k.replace('_',' ')}: {result[k]}"
                    break
            if data_phrase: break

        # confidence verdict in plain English
        if score >= 90:
            quality = f"directly and reliably answered the question{data_phrase}"
            why = "the tool was a strong match, returned real data, and parameters were verified."
        elif score >= 75:
            quality = f"answered the question{data_phrase} with minor caveats"
            why = "small gaps in tool matching or parameter verification reduce certainty slightly."
        elif score >= 60:
            quality = f"partially answered the question{data_phrase}"
            why = "the question required multiple steps or the tool wasn't a perfect match."
        else:
            quality = f"attempted to answer{data_phrase} but with significant uncertainty"
            why = "verify this answer manually before relying on it."

        summary = (
            f"The {primary} tool{nav_phrase} {quality}. "
            f"Confidence is {score}% — {why}"
        )

    # ── Level 2: detailed breakdown ────────────────────────────────────────────
    # tools summary line
    if tool_calls:
        nav_str = f"navigation: {', '.join(tc['name'] for tc in nav_tools)}" if nav_tools else ""
        ans_str = f"answer: {', '.join(tc['name'] for tc in ans_tools)}" if ans_tools else ""
        tool_summary = " → ".join(filter(None, [nav_str, ans_str]))
        tool_line = f"Tools called ({len(tool_calls)} total): {tool_summary}."
    else:
        tool_line = "Tools called: none."

    # data highlights
    highlights = []
    for tc in ans_tools:
        result = tc.get("result") or {}
        if not isinstance(result, dict): continue
        priority = ["boreholes", "pile_locations", "pile_tests", "dpsh_probes", "test_pits",
                    "n_refusals", "avg_shortfall_m", "total_tests", "passed", "failed",
                    "n_zones", "n", "undecided_zones", "n_undecided",
                    "zones"]
        for k in priority:
            if result.get(k) is not None:
                highlights.append(f"{tc['name']} → {k}={result[k]}")
                break

    detail = (
        f"Confidence: {score}%\n"
        f"{tool_line}\n"
        + (f"Data returned: {'; '.join(highlights)}.\n" if highlights else "")
        + "\n"
        f"Scoring breakdown (weighted):\n"
        f"• Question-tool match (35%): {f_match:.0%} — {e_match}\n"
        f"• Chain length (25%): {f_chain:.0%} — {e_chain}\n"
        f"• Result completeness (25%): {f_complete:.0%} — {e_complete}\n"
        f"• Parameter confidence (15%): {f_params:.0%} — {e_params}"
    )

    return f"{summary}\n\n{detail}"


# ── main confidence + reasoning entry point ────────────────────────────────────

def _calculate_confidence_and_reasoning(
    question: str, tool_calls: list[dict], reply: str
) -> tuple[int, str]:

    if not tool_calls:
        refusal = any(w in reply.lower() for w in
                      ["cannot","can't","don't have","not supported","unable","unsupported"])
        factual = any(w in reply.lower() for w in
                      ["there are","there is","in total","pile","zone","borehole","dpsh","plt-","bh0"])
        if refusal:
            return 50, "The question was acknowledged but could not be answered with the available tools. No database query was executed."
        if factual:
            return 20, (
                "No database tools were called, but the answer contains factual claims.\n\n"
                "WARNING: This answer was generated from model memory, not live database data. "
                "It may be incorrect. Ask again or verify manually."
            )
        return 70, "No database query was needed — this is a general or explanatory answer."

    f_match,    e_match    = _factor_question_match(question, tool_calls)
    f_chain,    e_chain    = _factor_chain_length(tool_calls)
    f_complete, e_complete = _factor_completeness(tool_calls)
    f_params,   e_params   = _factor_parameters(tool_calls)

    raw   = (f_match * WEIGHTS["match"] + f_chain * WEIGHTS["chain"] +
             f_complete * WEIGHTS["completeness"] + f_params * WEIGHTS["parameters"])
    score = max(5, min(100, round(raw * 100)))

    reasoning = _build_reasoning(
        question, tool_calls, reply, score,
        f_match, e_match, f_chain, e_chain, f_complete, e_complete, f_params, e_params
    )
    return score, reasoning


# ── endpoint ───────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        agent = get_agent()
    except AgentNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        response   = await agent.run(request.message)
        tool_calls = _extract_tool_calls(response)
        reply      = response.text.strip()

        confidence, reasoning = _calculate_confidence_and_reasoning(
            request.message, tool_calls, reply
        )
        return {"reply": reply, "confidence": confidence, "reasoning": reasoning}

    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}")