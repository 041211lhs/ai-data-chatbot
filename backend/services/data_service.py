"""data 컬렉션 CRUD. 문서 하나 = 한 달치 (date, value, memo)."""
from datetime import datetime, timezone

from google.cloud.firestore_v1.base_query import FieldFilter

from services.errors import DuplicateError, NotFoundError
from services.firestore import DATA, get_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_item(doc) -> dict:
    d = doc.to_dict()
    return {"id": doc.id, "date": d["date"], "value": d["value"], "memo": d.get("memo", "")}


def _date_taken(date: str, except_id: str | None = None) -> bool:
    docs = get_db().collection(DATA).where(filter=FieldFilter("date", "==", date)).limit(2).stream()
    return any(doc.id != except_id for doc in docs)


def list_data() -> list[dict]:
    docs = get_db().collection(DATA).order_by("date").stream()
    return [_to_item(doc) for doc in docs]


def create_data(date: str, value: float, memo: str) -> dict:
    if _date_taken(date):
        raise DuplicateError(f"{date} 데이터가 이미 있다. 수정(PUT)을 사용하라")
    now = _now()
    ref = get_db().collection(DATA).document()
    ref.set({"date": date, "value": value, "memo": memo, "created_at": now, "updated_at": now})
    return {"id": ref.id, "date": date, "value": value, "memo": memo}


def update_data(item_id: str, changes: dict) -> dict:
    ref = get_db().collection(DATA).document(item_id)
    if not ref.get().exists:
        raise NotFoundError(f"id {item_id} 데이터가 없다")
    if "date" in changes and _date_taken(changes["date"], except_id=item_id):
        raise DuplicateError(f"{changes['date']} 데이터가 이미 있다")
    ref.update({**changes, "updated_at": _now()})
    return _to_item(ref.get())


def delete_data(item_id: str) -> None:
    ref = get_db().collection(DATA).document(item_id)
    if not ref.get().exists:
        raise NotFoundError(f"id {item_id} 데이터가 없다")
    ref.delete()
