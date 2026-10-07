# Integration Test Instructions — Purpose Restructure (U1~U8)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: 이 주기의 Build & Test입니다. 이 문서는 실제 스택(Neo4j·OpenSearch·PostgreSQL·nginx·OpenAI)에 대고 데모 흐름을 끝까지 확인하는 방법을 적습니다.

오프라인 테스트는 로직을 덮는다. 여기서는 배선, 저장, 프록시, 실제 LLM을 거친 흐름을 본다. 도구는 `scripts/live_scenario.py`(표준 라이브러리, CI 밖)다(BR-U8-36, BLM §7).

## 준비
```bash
./scripts/setup-volumes.sh
cp env.example .env                       # 필수 두 값; LLM 단계까지 보려면 OPENAI_API_KEY
docker compose --profile service up -d --build --wait
```

## 실행
```bash
python scripts/live_scenario.py --base http://localhost:8000 --world emberleaf
```
- 대상 월드를 **교체**한다(열린 세션을 닫는다). 다른 월드는 건드리지 않는다.
- 단계마다 PASS·FAIL·SKIP을 찍는다. FAIL이 있으면 종료 코드 1이다. 1~3 중 하나가 FAIL이면 나머지는 SKIP이다.

| 단계 | 확인 | 키 없음 | 키 있음 |
|---|---|---|---|
| 1 기동 | `/health` ok, `/api/capabilities` | PASS | PASS |
| 2 데모 | 매니페스트에 emberleaf, 불러오기 ok(LLM 0), 지역 12 | PASS | PASS |
| 3 세션 | 항구(Saltwake Harbor)에서 T0 | PASS | PASS |
| 4 이동 | 강으로 Ambermeadow, T1 | PASS | PASS |
| 5 대화 | 그 지역 NPC 한 줄 | SKIP | PASS |
| 6 선언 | 서술, 선언 행적 기록(T2) | SKIP | PASS |
| 6a 대화 마침 | `end_talk` → 증인 판단(BR-U6-7). 전할 만하면 목초지에 행적 소문(T3). 전할 만한데 소문이 없으면 FAIL | SKIP | PASS(판단이 전할 만하지 않으면 PASS + 9·11 SKIP) |
| 7 씨앗 | 마름병 씨앗 → ACTIVE plague 0.5, 턴 소모 없음 | PASS | PASS |
| 8 이동 | 항구로, T(판단+1) | PASS | PASS |
| 9 행적 1칸 | 항구·Sylvarch에 행적 소문, Ironcrag·Gutterlight에는 없음 | SKIP | PASS |
| 9a 기다리기 | 한 턴 | PASS | PASS |
| 10a 다르게 듣기(왜곡도) | 항구와 Ironcrag의 왜곡도가 다르다(소문 수도 보고) | PASS | PASS |
| 10b 다르게 듣기(대화) | 항구 NPC에게 마름병을 묻는다 | SKIP | PASS |
| 11 행적 3칸 전 | T(판단+2)에 Ironcrag에 행적 소문 없음 | SKIP | PASS |
| 12 세계 상태 | Ambermeadow에 진행 중 사건 | PASS | PASS |

기대: 키 없음 **9 PASS · 6 SKIP**, 키 있음 **15 PASS**(증인 판단이 전할 만하지 않으면 13 PASS · 2 SKIP).

## 화면 확인 (사람)
- `http://localhost:3000`(이 호스트에서는 `:13000`) → 데모 카드 [바로 플레이] → 플레이 화면
- 키가 없으면 홈·에디터·GM 머리에 안내가 보이고 LLM 버튼이 꺼진다.
- GM 화면(플레이 화면의 GM 버튼) → 사건 씨앗 패널 [시작]

## 기록
실행 결과는 `build-and-test-summary.md`에 날짜, 명령, 단계 출력과 함께 남긴다.
