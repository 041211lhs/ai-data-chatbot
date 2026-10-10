"""대화 기록 API. 목록(GET /api/conversations)에는 messages가 없고, 불러오기는 GET /{id}로 한다."""
from fastapi import APIRouter, status

from schemas import Conversation, ConversationCreate, ConversationSummary
from services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=Conversation, status_code=status.HTTP_201_CREATED, summary="대화 저장")
def create_conversation(body: ConversationCreate):
    return conversation_service.create_conversation(body.title, [m.model_dump() for m in body.messages])


@router.get("", response_model=list[ConversationSummary], summary="대화 목록 (최근 순, messages 제외)")
def list_conversations():
    return conversation_service.list_conversations()


@router.get("/{conv_id}", response_model=Conversation, summary="대화 불러오기 (전체 messages)")
def get_conversation(conv_id: str):
    return conversation_service.get_conversation(conv_id)


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT, summary="대화 삭제")
def delete_conversation(conv_id: str):
    conversation_service.delete_conversation(conv_id)
