# 계획서: 반도체 생산지수를 아는 AI 비서

## 1. 서비스 한 줄 소개

반도체 생산지수(KOSIS, 2017.01 ~ 2026.07, 115개월)를 저장해 두고, 그 데이터 요약을 바탕으로 답하는 AI 채팅 서비스다.
예시 질문은 "최근 반도체 생산 흐름이 어때?", "가장 생산이 많았던 달은?", "2022년 불황 때는 얼마나 떨어졌어?"이다.

## 2. 데이터

지난 과제의 `clean_production.csv`를 재사용한다.

| 필드 | 내용 |
|---|---|
| date | 연월 (예: 2024-03) |
| value | 반도체 및 부품 생산지수 (2020=100) |
| memo | 국면 이름(슈퍼사이클, 코로나, 불황 등), 이상치, 잠정치 표시 |

요약(`/api/data/summary`)에 들어갈 내용은 아래와 같다.

- 기간, 개수
- 평균, 최대(언제), 최소(언제), 최근값
- 최근 추세: 최근 12개월 평균 vs 직전 12개월 평균 → 상승/하락/유지
- 보너스 지표: 전년 동월 대비 증감률(YoY), 12개월 이동평균

## 3. 구조

```
ai-data-chatbot/
├─ backend/          ← Render에 배포
│  ├─ main.py        (앱 생성, CORS, 라우터 연결)
│  ├─ routers/       (data, conversations, chat: 주소만 담당)
│  ├─ services/      (firestore, summary 계산, openai 호출: 실제 일)
│  ├─ schemas.py     (Pydantic 입력 검증)
│  ├─ seed.py        (CSV 115개를 Firestore에 한 번 올리는 스크립트)
│  └─ requirements.txt
├─ frontend/         ← Vercel에 배포 (HTML/CSS/JS만)
│  ├─ index.html, style.css, app.js
│  └─ config.js      (배포 시 API_BASE_URL 환경변수로 생성)
└─ README.md
```

## 4. API (필수 9개)

- 데이터: POST·GET `/api/data`, PUT·DELETE `/api/data/{id}`, GET `/api/data/summary`
- 대화: POST·GET `/api/conversations`, GET·DELETE `/api/conversations/{id}` (불러오기는 (A) 방식)
- 채팅: POST `/api/chat` → 요약 조회 → 시스템 프롬프트에 주입 → GPT 호출 → 대화 자동 저장

## 5. 화면 (한 페이지)

- 왼쪽: 대화 목록 (불러오기, 삭제, 새 대화)
- 가운데: 채팅 (입력창, 말풍선, 로딩 표시, 서버 깨우는 중 안내 문구)
- 오른쪽: 요약 카드 + 그래프 + 데이터 표 (추가/수정/삭제, CSV·JSON 내보내기)
- 상단: 다크 모드 토글

## 6. 키와 계정

| 항목 | 상태 | 할 일 |
|---|---|---|
| OpenAI 키 | 코디세이 제공 키 있음 | `OPENAI_BASE_URL`, `OPENAI_MODEL`도 환경변수로 사용 |
| Vercel | 있음 | 마지막에 연결 |
| Firebase | 없음 | 프로젝트 생성 → Firestore 켜기 → 서비스 계정 키 JSON 다운로드 (클릭 단위로 안내 예정) |
| Render | 없음 | GitHub 계정으로 가입 (안내 예정) |
| GitHub | 있음 (041211lhs) | 새 저장소 `ai-data-chatbot` |

환경변수: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `FIREBASE_SERVICE_ACCOUNT_JSON`, `ALLOWED_ORIGINS`, (프론트) `API_BASE_URL`

## 7. 진행 순서

1. 백엔드 코드 작성 → Firestore 없이도 돌아가는 부분 먼저 확인
2. Firebase 준비 (사용자) → 데이터 115개 업로드 → 로컬에서 Swagger로 9개 API 확인
3. 프론트 작성 → 로컬에서 채팅·CRUD·불러오기 확인
4. GitHub 푸시 → Render 배포 (사용자 클릭 + 안내) → Vercel 배포
5. 스크린샷 3장 → README 마무리
