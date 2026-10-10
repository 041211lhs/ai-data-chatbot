"""앱 진입점: FastAPI 생성, CORS 설정, 라우터 연결, 공통 예외 처리.
로컬 실행: uvicorn main:app --reload  →  http://127.0.0.1:8000/docs"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import ALLOWED_ORIGINS, missing_env
from routers import chat, conversations, data
from services.errors import AIServiceError, DuplicateError, NotFoundError
from services.firestore import DatabaseNotConfigured

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 서버가 켜질 때 필수 환경 변수가 비었는지 로그로 알린다 (값 자체는 찍지 않는다)
    missing = missing_env()
    if missing:
        logger.warning("필수 환경 변수 누락: %s", ", ".join(missing))
    logger.info("CORS 허용 도메인: %s", ALLOWED_ORIGINS)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="반도체 생산지수 AI 비서 API",
    description="KOSIS 반도체 생산지수를 저장·요약하고, 요약을 시스템 프롬프트에 주입해 답하는 챗봇 API",
    version="1.0.0",
)

# 브라우저는 다른 도메인(Vercel)에서 이 API(Render)를 부를 때 CORS 허용 목록을 확인한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.get("/", tags=["health"], summary="서버 상태 확인 (콜드스타트 깨우기용)")
def health():
    missing = missing_env()
    return {"status": "ok" if not missing else "degraded", "missing_env": missing, "docs": "/docs"}


def _error(code: int, msg: str) -> JSONResponse:
    return JSONResponse(status_code=code, content={"detail": msg})


@app.exception_handler(NotFoundError)
async def not_found(_: Request, e: NotFoundError):
    return _error(404, str(e))


@app.exception_handler(DuplicateError)
async def duplicate(_: Request, e: DuplicateError):
    return _error(409, str(e))


@app.exception_handler(DatabaseNotConfigured)
async def db_not_configured(_: Request, e: DatabaseNotConfigured):
    return _error(503, f"DB 설정 오류: {e}")


@app.exception_handler(AIServiceError)
async def ai_error(_: Request, e: AIServiceError):
    logger.error(e)
    return _error(502, str(e))


@app.exception_handler(Exception)
async def unexpected(_: Request, e: Exception):
    logger.exception(e)
    return _error(500, "서버 내부 오류가 발생했다")
