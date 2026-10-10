"""시계열 분석: 저장된 데이터에서 요약(프롬프트 주입용)과 통계(그래프용)를 만든다.
DB와 분리된 순수 계산 함수라서 데이터만 넣으면 어디서든 같은 결과가 나온다."""
from statistics import mean, pstdev

UNIT = "반도체 및 부품 생산지수(2020=100, 출처: KOSIS 광업제조업동향조사)"
TREND_THRESHOLD_PCT = 3.0  # 이보다 작게 변하면 '유지'로 본다


def _r(x: float | None, n: int = 1):
    return None if x is None else round(x, n)


def _trend(values: list[float]) -> dict:
    """최근 12개월 평균을 직전 12개월 평균과 비교한다. 데이터가 적으면 절반씩 나눠 비교한다."""
    window = min(12, len(values) // 2)
    if window == 0:
        return {"direction": "판단 불가", "text": "데이터가 부족해 추세를 판단할 수 없음"}
    recent = mean(values[-window:])
    prev = mean(values[-2 * window:-window])
    change = (recent - prev) / prev * 100 if prev else 0.0
    if change >= TREND_THRESHOLD_PCT:
        direction = "상승"
    elif change <= -TREND_THRESHOLD_PCT:
        direction = "하락"
    else:
        direction = "유지"
    return {
        "direction": direction,
        "window_months": window,
        "recent_avg": _r(recent),
        "previous_avg": _r(prev),
        "change_pct": _r(change),
        "text": f"{direction} (최근 {window}개월 평균 {recent:.1f}, 직전 {window}개월 대비 {change:+.1f}%)",
    }


def _yoy(items: list[dict], idx: int) -> float | None:
    """전년 같은 달 대비 증감률(%). 1년 전 데이터가 없으면 None."""
    y, m = items[idx]["date"].split("-")
    target = f"{int(y) - 1}-{m}"
    prev = next((it["value"] for it in items if it["date"] == target), None)
    if not prev:
        return None
    return (items[idx]["value"] - prev) / prev * 100


def _memo_groups(items: list[dict]) -> list[dict]:
    """memo의 첫 부분(국면 이름)이 같은 연속 구간을 묶어 구간별 평균을 낸다."""
    groups = []
    for it in items:
        label = (it.get("memo") or "").split(" / ")[0].strip()
        if not label:
            continue
        if groups and groups[-1]["memo"] == label:
            groups[-1]["end"] = it["date"]
            groups[-1]["_vals"].append(it["value"])
        else:
            groups.append({"memo": label, "start": it["date"], "end": it["date"], "_vals": [it["value"]]})
    return [
        {"memo": g["memo"], "period": f"{g['start']} ~ {g['end']}", "months": len(g["_vals"]), "average": _r(mean(g["_vals"]))}
        for g in groups
    ]


def build_summary(items: list[dict]) -> dict:
    """items는 date 오름차순 정렬된 [{date, value, memo}] 목록."""
    if not items:
        return {"period": None, "count": 0, "unit": UNIT, "metrics": None, "trend": "데이터 없음"}

    values = [it["value"] for it in items]
    hi = max(items, key=lambda it: it["value"])
    lo = min(items, key=lambda it: it["value"])
    last = items[-1]
    trend = _trend(values)

    yearly: dict[str, list[float]] = {}
    for it in items:
        yearly.setdefault(it["date"][:4], []).append(it["value"])

    return {
        "period": f"{items[0]['date']} ~ {last['date']}",
        "count": len(items),
        "unit": UNIT,
        "metrics": {
            "average": _r(mean(values)),
            "max": {"value": hi["value"], "date": hi["date"]},
            "min": {"value": lo["value"], "date": lo["date"]},
            "latest": {"value": last["value"], "date": last["date"], "memo": last.get("memo", "")},
            "std": _r(pstdev(values)),
            "latest_yoy_pct": _r(_yoy(items, len(items) - 1)),
        },
        "trend": trend["text"],
        "trend_detail": trend,
        "yearly_average": {y: _r(mean(v)) for y, v in yearly.items()},
        "memo_groups": _memo_groups(items),
        "recent_12": [{"date": it["date"], "value": it["value"]} for it in items[-12:]],
    }


def build_statistics(items: list[dict]) -> list[dict]:
    """그래프용 시계열: 원값 + 12개월 이동평균 + 전년 동월 대비 증감률."""
    out = []
    for i, it in enumerate(items):
        window = [x["value"] for x in items[max(0, i - 11): i + 1]]
        out.append({
            "date": it["date"],
            "value": it["value"],
            "ma12": _r(mean(window)) if len(window) == 12 else None,
            "yoy_pct": _r(_yoy(items, i)),
        })
    return out
