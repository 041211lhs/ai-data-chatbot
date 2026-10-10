"""환경 변수를 한곳에서 읽는다. 키는 코드에 쓰지 않고 .env(로컬) 또는 Render 환경 변수에서만 가져온다."""
import os

from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None  # 비우면 OpenAI 기본 주소
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))

# JSON 문자열 그대로 넣거나, 키 파일 경로를 넣어도 된다.
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

# 쉼표로 구분한 허용 도메인 목록 (예: https://my-app.vercel.app,http://localhost:5500)
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000",
    ).split(",")
    if o.strip()
]


def missing_env() -> list[str]:
    """비어 있는 필수 환경 변수 이름 목록. 값은 돌려주지 않는다."""
    required = {"OPENAI_API_KEY": OPENAI_API_KEY, "FIREBASE_SERVICE_ACCOUNT_JSON": FIREBASE_SERVICE_ACCOUNT_JSON}
    return [name for name, value in required.items() if not value.strip()]
