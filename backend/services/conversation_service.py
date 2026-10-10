"""conversations 컬렉션. 문서 하나 = 대화 하나, messages 배열에 주고받은 메시지를 순서대로 담는다."""
from datetime import datetime, timezone

from google.cloud.firestore import Query

from services.errors import NotFoundError
from services.firestore import CONVERSATIONS, get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_conversation(title: str, messages: list[dict]) -> dict:
    now = _now()
    ref = get_db().collection(CONVERSATIONS).document()
    doc = {"title": title, "messages": messages, "message_count": len(messages), "created_at": now, "updated_at": now}
    ref.set(doc)
    return {"id": ref.id, **doc}


def list_conversations() -> list[dict]:
    """목록에는 messages를 빼고 제목·개수·수정 시각만 준다(가볍게)."""
    docs = get_db().collection(CONVERSATIONS).order_by("updated_at", direction=Query.DESCENDING).stream()
    return [
        {"id": doc.id, "title": d.get("title", ""), "message_count": d.get("message_count", 0), "updated_at": d.get("updated_at", "")}
        for doc in docs
        for d in [doc.to_dict()]
    ]


def get_conversation(conv_id: str) -> dict:
    snap = get_db().collection(CONVERSATIONS).document(conv_id).get()
    if not snap.exists:
        raise NotFoundError(f"id {conv_id} 대화가 없다")
    return {"id": snap.id, **snap.to_dict()}


def append_messages(conv_id: str, new_messages: list[dict]) -> None:
    conv = get_conversation(conv_id)
    messages = conv["messages"] + new_messages
    get_db().collection(CONVERSATIONS).document(conv_id).update(
        {"messages": messages, "message_count": len(messages), "updated_at": _now()}
    )


def delete_conversation(conv_id: str) -> None:
    ref = get_db().collection(CONVERSATIONS).document(conv_id)
    if not ref.get().exists:
        raise NotFoundError(f"id {conv_id} 대화가 없다")
    ref.delete()
