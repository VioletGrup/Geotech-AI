from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.agent import get_agent, AgentNotConfiguredError
from app.utils.logger import get_logger

router = APIRouter(prefix="/agent", tags=["agent"])
logger = get_logger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User question for the geotech advisor")


@router.post("/chat")
async def chat(request: ChatRequest):
    """Ask the geotech advisor agent. It calls the graph-backed prediction tools."""
    try:
        agent = get_agent()
    except AgentNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    try:
        response = await agent.run(request.message)
        return {"reply": response.text}
    except Exception as exc:
        logger.exception("Agent run failed")
        raise HTTPException(status_code=502, detail=f"Agent run failed: {exc}")