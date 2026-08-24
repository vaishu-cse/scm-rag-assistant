from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.maf_agent_service import MafAgentService

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


maf_agent_service = MafAgentService()


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(
    request: ChatRequest,
    _current_user: User = Depends(get_current_user),
):
    try:
        return await maf_agent_service.chat(request.message)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc