# Build and Test Summary — Follow-up 주기 (V1~V9)

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: 이 주기의 Build and Test 결과다. 이 호스트에서 실제 스택을 키와 함께 띄워 확인했다(사람의 선택 A).

실행: 2026-10-11T17:21Z~17:31Z (KST 2026-10-12), 코드 `5c8ec9b`(브랜치 `feat/follow-up`)

## 빌드
| 항목 | 결과 |
|---|---|
| `WEB_PORT=13000 docker compose --profile service up -d --build` | app·web 이미지 빌드, 다섯 서비스 healthy(인프라는 127.0.0.1에만) |
| `/health` | `{"status":"ok"}`, world·knowledge·play·localization 모두 true |
| `/api/capabilities` | `{"llm":true,"vlm":true,"embedding":true}` |
| web(nginx) | `:13000/` 200, `:13000/api/capabilities` 200(프록시) |
| nginx 머리 | `/` `no-cache`, `/assets/*.js` `public, max-age=31536000, immutable`, `/favicon.svg` `image/svg+xml` |
| 페이지 머리 | `<html lang="ko">`, `<title>Locus</title>`, 설명, theme-color, favicon |

## 오프라인 테스트
| 항목 | 결과 |
|---|---|
| pytest | **1262 passed**, ResourceWarning 0(이제 오류) |
| vitest | **825 passed** |
| mypy `locus api` | **0** (주기 시작 11) |
| ruff · black (`locus api tests scripts`) · tsc | clean |
| npm audit 전체 · `--omit=dev` | 0 · 0 (주기 시작 dev 5) |

## 통합 — 라이브 시나리오 (키 있음)
`python scripts/live_scenario.py --base http://localhost:8000 --world emberleaf` → **15 passed, 0 failed, 0 skipped**, 종료 0. 전체 출력은 `live-scenario-2026-10-12.log`에 있다.
- 6a: 판단 2건이 전할 만했다. 그래서 목초지에 행적 소문이 생겼다(T3).
- 9: T4에 항구·Sylvarch에는 있고, Ironcrag·Gutterlight에는 없다.
- **10a(V9 새 단언)**: 항구 0.65(사건 0.30, 소문 2), Ironcrag 0.36(사건 0.06, 소문 0).
  - 항구 0.65는 시작 0.3 + 사건 0.30 + 0.05다.
  - 10a는 피드백 몫을 뺀 값이 0.60 이상임을 확인했다. 그러니 0.05가 피드백 몫이거나 그보다 작다.
  - 몫 자체의 숫자는 따로 읽지 않았다.
- 10b: 항구 NPC는 목초지 역병은 모르지만, 곡물창고 소동 이야기는 들었다(퍼진 행적 소문).

## 통합 — 운영자 확인
| 확인 | 결과 |
|---|---|
| P1 두 해소 동시 | PASS — 200·200, 왜곡도 0.300 → 0.840 → 0.300 |
| P2 해소 ∥ 왜곡도 설정 | PASS — 200·200, 0.800, 사건 기여 없음 |
| P3 씨앗 시작 둘 | PASS — 201·409 `seed_running` |
| 잠금(V5 R-01) | PASS — `FOR UPDATE`로 쥔 사건 행의 해소가 4.1초 기다린 뒤 200 |
| P4 생성 중 닫기 (키) | PASS — 닫기 200, 생성 409 `session_closed`, 소문 0 |
| P5 끊긴 선언 | PASS — app을 죽였다 띄우니 run `failed/interrupted`, 턴 0 그대로, 지역 그대로, `turn_run_failed` 줄 |
| P6 GM 생성 중 플레이어 (키) | PASS — 409 `gm_busy`, "the session is busy with a GM write; retry shortly"(id 없음) |
| V7 라벨 있는 삭제 | PASS — Gutterlight 삭제가 그 지역 씨앗 둘(하나는 Sylvarch와 같은 id)을 지우고, `Region` Sylvarch는 남았다 |
| V7 백업 실패 | PASS — `ok:false`, `replaced:false`, stage `backup`, 옛 월드(지역 11) 그대로 |
| 에디터 한 바퀴 | PASS — 만든 지역이 골라짐, 끌기 저장, World File 불러오기 확인 뒤 "불러왔어요." |
| GM 한 바퀴 | PASS — 턴 결과 띠, 씨앗 진행 중, 세션 끝내기 → `closed` |
| 빌드 경고 단계 이름 | PASS — 서버 15개가 모두 화면 목록에 있다(정적 대조) |

## 확인하면서 알게 된 것
- **P5의 처음 방법(`docker compose restart app`)은 끊긴 run을 만들지 않는다.** 정상 종료는 진행 중인 run을 30초까지 기다려 마치므로, run이 `done`이 됐다. operations.md에 적힌 그대로의 동작이다. 복구 경로는 app을 죽여서 확인했다. V5 nfr-light § 3의 P5 줄은 "restart"라고 적혀 있다(integration 문서에 바로잡음).
- **[지역 추가] 도구는 지역을 만든 뒤에도 켜져 있다.** 이어서 지도를 누르면 또 새 지역 대화상자가 열린다. 여러 지역을 차례로 놓을 때 맞는 동작으로 보고 결함으로 적지 않았다. 다른 동작을 원하시면 다음 주기에 정한다.
- 확인용 스크립트 둘(`pg_smoke.py`, `walk.mjs`)은 세션 scratchpad에만 있다(V5 결정: 저장소에 두지 않음). 방법은 `integration-test-instructions.md`에 적었다.

## 하지 않은 것
- **V7 "CLI로 다시 빌드하는 동안 API가 반쪽 월드를 캐시하지 않는가"**와 **V8 "빌드 교체 → 이어 붙인 수"**는 돌리지 않았다. 둘 다 소스에서 LLM 빌드를 한 번 해야 한다(수 분, 호출 수십~수백 번). 사람에게 고른 확인 목록에 넣지 않았다. 오프라인으로는 V7 캐시 시험과 V8 빌드 리포트 시험이 이것을 본다.
- **화면 캡처의 사람 확인(V6 § 7)**: 이번 한 바퀴의 스크린숏은 scratchpad `v9/bt/walk*/`에 있다. 사람이 볼 캡처는 V6·V8 Artifact를 쓴다.

## 정리
- `emberleaf`를 데모로 다시 불러와 처음 상태로 돌렸다(지역 12, 열린 세션 0).
- 스택을 `down`했다. 데이터 볼륨은 남는다.
- 확인 중 만든 월드는 없다. 교체할 때마다 `locus_data` 볼륨에 백업이 남았다.

## 전체
- 빌드: 성공
- 오프라인 테스트: 모두 통과
- 라이브 통합: 15/15, 운영자 확인 12/12 통과(P5는 방법을 바꿔서)
- 다음 단계: Operations
