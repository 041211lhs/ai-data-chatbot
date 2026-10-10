"""Pydantic 모델: 요청 데이터가 형식에 맞는지 라우터에 닿기 전에 자동으로 검사한다.
형식이 틀리면 FastAPI가 422 에러와 함께 어디가 틀렸는지 알려 준다."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator

DATE_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"  # 월별 데이터라 YYYY-MM 형식만 받는다


# ---------- 데이터 ----------
class DataCreate(BaseModel):
    date: str = Field(..., pattern=DATE_PATTERN, examples=["2026-08"])
    value: float = Field(..., ge=0, le=1000, examples=[160.5], description="생산지수(2020=100)")
    memo: str = Field("", max_length=200, examples=["AI·HBM 호황"])

    @field_validator("memo")
    @classmethod
    def strip_memo(cls, v: str) -> str:
        return v.strip()


class DataUpdate(BaseModel):
    """수정은 바꿀 필드만 보내면 된다."""
    date: str | None = Field(None, pattern=DATE_PATTERN)
    value: float | None = Field(None, ge=0, le=1000)
    memo: str | None = Field(None, max_length=200)


class DataItem(BaseModel):
    id: str
    date: str
    value: float
    memo: str = ""


# ---------- 대화 ----------
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=4000)


class ConversationCreate(BaseModel):
    title: str = Field("새 대화", max_length=100)
    messages: list[Message] = Field(default_factory=list, max_length=200)


class ConversationSummary(BaseModel):
    """목록 조회용: messages는 넣지 않는다(불러오기는 GET /api/conversations/{id})."""
    id: str
    title: str
    message_count: int
    updated_at: str


class Conversation(BaseModel):
    id: str
    title: str
    messages: list[Message]
    created_at: str
    updated_at: str


# ---------- 채팅 ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000, examples=["최근 반도체 생산 흐름이 어때?"])
    conversation_id: str | None = Field(None, description="이어서 대화할 때만 보낸다. 없으면 새 대화를 만든다.")

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("빈 메시지는 보낼 수 없다")
        return v.strip()


class ChatResponse(BaseModel):
    conversation_id: str
    reply: str
