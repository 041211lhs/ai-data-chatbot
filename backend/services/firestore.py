"""Firestore 연결. 서버가 처음 DB를 쓸 때 한 번만 연결하고 이후엔 재사용한다."""
import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

from core.config import FIREBASE_SERVICE_ACCOUNT_JSON

DATA = "data"
CONVERSATIONS = "conversations"

_db = None


class DatabaseNotConfigured(RuntimeError):
    pass


def get_db():
    global _db
    if _db is not None:
        return _db

    raw = FIREBASE_SERVICE_ACCOUNT_JSON.strip()
    if not raw:
        raise DatabaseNotConfigured("FIREBASE_SERVICE_ACCOUNT_JSON 환경 변수가 비어 있다")

    if raw.startswith("{"):
        cred = credentials.Certificate(json.loads(raw))  # Render: JSON 내용을 통째로 붙여 넣은 경우
    elif os.path.exists(raw):
        cred = credentials.Certificate(raw)  # 로컬: 키 파일 경로를 적은 경우
    else:
        raise DatabaseNotConfigured(f"서비스 계정 키 파일을 찾을 수 없다: {raw}")

    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    _db = firestore.client()
    return _db
