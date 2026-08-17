from fastapi import APIRouter
from pydantic import BaseModel

from app.services.foundry_service import FoundryService
from app.config import settings
from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


foundry_service = FoundryService(
    endpoint=settings.foundry_project_endpoint,
    agent_name=settings.foundry_agent_name,
)


class ChatRequest(BaseModel):
    message: str


@router.post("")
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
):

    result = foundry_service.chat(
        request.message
    )

    return result