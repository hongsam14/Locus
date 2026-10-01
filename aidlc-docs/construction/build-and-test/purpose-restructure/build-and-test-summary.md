# Build and Test Summary — Purpose Restructure (U1~U8)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG. 처음 온 사람이 명령 두 줄과 [바로 플레이]로 데모를 겪는다.
**지금 하는 것**: 이 주기의 Build & Test 결과입니다. 이 호스트에서 실제 스택을 띄우고 라이브 시나리오를 키 있이 돌렸습니다(사람의 선택 A).

실행: 2026-10-01T18:52:28Z, 코드 `01b1455`(브랜치 `feat/purpose-restructure`)

## 빌드
| 항목 | 결과 |
|---|---|
| `docker compose --profile service up -d --build --wait` | app·web 이미지 빌드, 다섯 서비스 healthy(neo4j·opensearch·postgres는 127.0.0.1에만) |
| 포트 | 이 호스트는 3000을 다른 스택이 써서 `WEB_PORT=13000`을 명령줄로만 줬다(.env는 그대로) |
| `/health` | `{"status":"ok", world·knowledge·play·localization 모두 true}` |
| `/api/capabilities` | `{"llm":true,"vlm":true,"embedding":true}` |
| web(nginx) | `:13000/` 200, `:13000/api/capabilities` 200 (프록시) |
| 이미지 안 확인 | `check_packaged()` [], `import api.main` 됨, `License-Expression: MIT`, `License-File: LICENSE` (U8 리뷰 후속에서 확인) |

## 오프라인 테스트
| 항목 | 결과 |
|---|---|
| pytest | **948 passed** |
| vitest | **202 passed** |
| ruff · black (`locus api tests scripts`) · tsc | clean |
| mypy (`locus api`) | 11 (기준선, 늘지 않음) |
| `npm audit --omit=dev` | 0 |

## 통합 — 라이브 시나리오 (키 있음)
`python scripts/live_scenario.py --base http://localhost:8000 --world emberleaf` → **15 passed, 0 failed, 0 skipped**, 종료 0. 전체 출력: `live-scenario-2026-10-02.log`

| 단계 | 결과 |
|---|---|
| 1 기동 · 2 데모 · 3 세션 · 4 이동 | PASS (데모 불러오기 LLM 0, 지역 12, 항구 T0 → 목초지 T1) |
| 5 대화 | PASS (목초지 NPC가 버섯밭 이야기를 한다) |
| 6 선언 · 6a 대화 마침 | PASS (T2 선언, T3 판단 2건이 전할 만함 → 목초지에 행적 소문) |
| 7 씨앗 | PASS (마름병 ACTIVE plague 0.5, 턴 소모 없음) |
| 8 이동 · 9 행적 1칸 | PASS (T4: 항구·Sylvarch에 있음, Ironcrag·Gutterlight에 없음) |
| 9a 기다리기 · 10a 왜곡도 | PASS (T5: 항구 0.65·소문 2, Ironcrag 0.36·소문 0) |
| 10b 다르게 듣기(대화) | PASS (항구 NPC는 목초지의 병충해는 모르지만, 누군가 곡물창고를 그을렸다는 소문은 들었다 — 퍼진 행적 소문) |
| 11 행적 3칸 전 | PASS (T5에 Ironcrag 없음, 판단 T3) |
| 12 세계 상태 | PASS (목초지 사건 1·소문 6, 한 칸 너머 지역에만 소문) |

## 남은 것
- **다른 월드 정리**
  - 사람이 청한 일이다. 대상은 `aldermoor`(지역 8, 열린 세션 2), `demo`(16, 1), `demo00`(10, 0)이다.
  - 셋 다 World File로 백업했다(앱 볼륨 `/app/data/backups/`와 호스트 `data/backups/*-before-u8-cleanup.world.json`).
  - 열린 세션 닫기와 그래프·검색 삭제는 Claude Code 권한 가드(되돌릴 수 없는 삭제)가 막아 **하지 않았다**. 사람이 직접 돌리거나 권한을 준다.
- **화면 확인(사람)**: `:13000` 데모 카드 [바로 플레이] → 플레이 화면, GM 화면의 씨앗 패널
- **CI 첫 실행**: 원격 push 필요
- **실제 PostgreSQL 동시성(#10)**: GM 설정 ∥ 사건 해소 겹침
- **다음 주기 목록**: U8 code-summary §10(리뷰 #9~#15, 상한 밖, 정리, 설계 메모)

## 전체
- 빌드: 성공
- 오프라인 테스트: 모두 통과
- 라이브 통합: 15/15 통과
- 다음 단계: Operations(이 주기는 placeholder) 또는 다음 주기
