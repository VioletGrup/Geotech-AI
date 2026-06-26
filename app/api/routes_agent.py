import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.agent import get_agent, AgentNotConfiguredError
from app.utils.logger import get_logger

router = APIRouter(prefix="/agent", tags=["agent"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


def _parse_response(raw: str) -> dict:
    """
    Split the raw LLM text into reply, confidence (0-100), and reasoning.
    The LLM is instructed to append:
        CONFIDENCE: <0-100>
        REASONING: <text>
    """
    confidence = None
    reasoning  = None
    reply      = raw.strip()

    # Extract CONFIDENCE line
    conf_match = re.search(r"CONFIDENCE:\s*(\d+)", raw, re.IGNORECASE)
    if conf_match:
        confidence = min(100, max(0, int(conf_match.group(1))))

    # Extract REASONING block (everything after REASONING: up to next section or end)
    reas_match = re.search(r"REASONING:\s*(.+?)(?=\nCONFIDENCE:|\nREASONING:|$)",
                           raw, re.IGNORECASE | re.DOTALL)
    if reas_match:
        reasoning = reas_match.group(1).strip()

    # Strip CONFIDENCE and REASONING lines from the user-facing reply
    reply = re.sub(r"\n?CONFIDENCE:\s*\d+", "", reply, flags=re.IGNORECASE).strip()
    reply = re.sub(r"\n?REASONING:\s*.+", "", reply, flags=re.IGNORECASE | re.DOTALL).strip()

    return {
        "reply":      reply,
        "confidence": confidence,   # int 0-100 or null
        "reasoning":  reasoning,    # str or null
    }


@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        agent = get_agent()
    except AgentNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        response = await agent.run(request.message)
        return _parse_response(response.text)
    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}")