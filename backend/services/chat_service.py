"""AI 채팅: 데이터 요약을 시스템 프롬프트에 넣고(컨텍스트 주입) GPT를 호출한 뒤 대화를 저장한다."""
import json

from openai import OpenAI, OpenAIError

from core.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MAX_TOKENS, OPENAI_MODEL
from services import conversation_service, data_service
from services.errors import AIServiceError
from services.summary_service import build_summary

HISTORY_LIMIT = 10  # 이전 대화는 최근 10개 메시지만 함께 보낸다(토큰 절약)

SYSTEM_TEMPLATE = """당신은 반도체 생산 데이터 분석 비서입니다.

[사용자 데이터 요약]
- 데이터: {unit}
- 데이터 기간: {period}
- 총 레코드: {count}개
- 주요 지표: {metrics}
- 최근 트렌드: {trend}
- 연도별 평균: {yearly}
- 메모(국면)별 구간 평균: {groups}
- 최근 12개월 값: {recent}
- 전체 월별 값(연월:지수): {series}

[답변 규칙]
- 위 데이터를 근거로 숫자와 날짜를 들어 한국어로 짧고 친절하게 답하세요.
- 요약에 없는 값은 지어내지 말고, 데이터에 없다고 말하세요.
- 원인은 단정하지 말고 "~와 시기가 겹친다", "~로 보인다"처럼 표현하세요.
- 지수는 2020년 평균을 100으로 둔 값이라는 점을 필요할 때 설명하세요."""


def _client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise AIServiceError("OPENAI_API_KEY 환경 변수가 비어 있다")
    return OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL, timeout=60)


def build_system_prompt(summary: dict, items: list[dict]) -> str:
    """요약 + 전체 월별 값(115개월이라도 약 1천 토큰)을 넣어 특정 달 질문에도 답하게 한다."""
    dump = lambda x: json.dumps(x, ensure_ascii=False)
    return SYSTEM_TEMPLATE.format(
        unit=summary.get("unit"),
        period=summary.get("period"),
        count=summary.get("count"),
        metrics=dump(summary.get("metrics")),
        trend=summary.get("trend"),
        yearly=dump(summary.get("yearly_average", {})),
        groups=dump(summary.get("memo_groups", [])),
        recent=dump(summary.get("recent_12", [])),
        series=", ".join(f"{it['date']}:{it['value']}" for it in items),
    )


def chat(message: str, conversation_id: str | None) -> dict:
    # 1) 데이터 요약 조회 (GET /api/data/summary 와 같은 계산)
    items = data_service.list_data()
    summary = build_summary(items)

    # 2) 요약을 시스템 프롬프트에 삽입 + 이어지는 대화면 이전 메시지도 붙인다
    history = []
    if conversation_id:
        history = conversation_service.get_conversation(conversation_id)["messages"][-HISTORY_LIMIT:]
    messages = [{"role": "system", "content": build_system_prompt(summary, items)}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": message})

    # 3) GPT 호출 (max_completion_tokens로 비용 상한)
    try:
        res = _client().chat.completions.create(
            model=OPENAI_MODEL, messages=messages, max_completion_tokens=OPENAI_MAX_TOKENS
        )
        reply = (res.choices[0].message.content or "").strip()
    except OpenAIError as e:
        raise AIServiceError(f"AI 호출 실패: {e}") from e
    if not reply:
        raise AIServiceError("AI가 빈 답변을 보냈다. OPENAI_MAX_TOKENS를 늘려 보라")

    # 4) 대화 자동 저장
    new_messages = [{"role": "user", "content": message}, {"role": "assistant", "content": reply}]
    if conversation_id:
        conversation_service.append_messages(conversation_id, new_messages)
    else:
        title = message if len(message) <= 30 else message[:30] + "…"
        conversation_id = conversation_service.create_conversation(title, new_messages)["id"]

    return {"conversation_id": conversation_id, "reply": reply}
