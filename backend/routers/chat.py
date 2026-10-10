from fastapi import APIRouter

from schemas import ChatRequest, ChatResponse
from services import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="AI 채팅 (데이터 요약 주입 + 자동 저장)")
def chat(body: ChatRequest):
    return chat_service.chat(body.message, body.conversation_id)
