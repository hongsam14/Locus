## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** NFR Requirements (light) — U4 플레이어 모드
**Reviewed artifact:** `aidlc-docs/construction/U4-player-mode/nfr/nfr-light.md`
**Class:** advisory
**Iteration:** 1
**Date:** 2026-09-30T01:40:58Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | nfr-light.md > §1 NFR-5, §5 항목 1; plan N-1; FD business-rules.md > BR-U4-18 | "지역당 활성 소문 ≤ 20"이 검증 가능한 규칙으로 닫혀 있지 않다. (1) 지역·턴당 신규 상한이 2이므로 활성이 19인 지역은 20을 넘겨 21이 된다 — "상한에 닿은 지역은 건너뛴다"는 20 이상일 때만 걸리고, `max_new = min(2, 20 - active)` 같은 절단 규칙이 없다. (2) "활성"의 정의가 없다(코드는 `r.active` = 비-pruned이고 promoted 포함 여부가 불명). (3) GM 수동 생성은 상한 예외(BR-U4-20)라 지역이 20을 넘을 수 있는데, 새 TP는 "어떤 턴 뒤에도 ≤ 20"이라 시작 상태가 이미 20 초과이면 거짓이 된다. (4) 상한 건너뛰기가 기존 `rumors_skipped_regions` 의미(예산 소진)와 섞인다. | 활성 수 정의(`active`·promoted 포함), 신규 수 = `min(max_new, cap - active, 예산 잔여)`, 시작 상태가 cap 이하일 때만 성립하는 불변식(또는 "턴이 cap 초과로 만들지 않는다: after ≤ max(before, cap)")으로 TP를 고쳐 적는다. 건너뜀 사유를 예산과 구분해 기록한다. | New |
| R-02 | Major | nfr-light.md > §2 종료, §1 NFR-4, plan N-3 | "LLM 호출 자체의 timeout은 provider 어댑터 설정에 의존한다(없으면 … `LLM_TIMEOUT_S`를 추가한다)"는 이미 답이 있는 조건문이다: `locus/shared/llm/retry.py`에 `CALL_TIMEOUT_SECONDS = 30.0`, 3회 재시도·백오프(1s→2s→4s)가 있어 호출당 최악 약 97초다. NFR-4는 "LLM 제공자가 **없을** 때"만 다루고 제공자가 있으나 느리거나 장애일 때는 다루지 않는다. 장애 시 한 턴은 예약 호출 8개까지 실패를 반복하고(체인은 지역별로 첫 단계에서 중단) 한 행동은 최대 5턴이므로 최악 수십 분 `running`이고, 그동안 가드가 세션을 409로 잠그며 폴링 UI만 돈다. 진행 중 실행의 상한 시간·실패 판정이 없다(재시작 때만 `interrupted`). | 최악 실행 시간을 계산해 NFR로 적고(호출 timeout·재시도 수 사실 반영), 실행 단위 deadline 또는 연속 LLM 실패 시 그 턴의 남은 소문 초안을 건너뛰는 회로 차단(예: 첫 호출 실패 뒤 예산 잔여 포기)과 `TurnRun` 실패 전환 규칙을 정한다. "없으면 추가" 문구를 사실로 바꾼다. | New |
| R-03 | Minor | nfr-light.md > §1 NFR-3 수치·검증; plan N-2 | p95를 `curl` 10회로 확인한다고 했는데 표본 10개의 p95는 최댓값이라 통계적으로 의미가 없고, 운영자 실행이라 회귀 게이트가 아니다. 또 `GET region`은 캐시 "적중"이어도 `WorldCache.get`이 매번 Neo4j 버전 마커를 재조회하고(`locus/knowledge/cache.py` `_current_version`) PG 소문 조회를 더하므로 100ms는 외부 왕복에 의존한다. | 표본 수(예: 50회, p95)와 조건(월드·소문 수)을 정하거나 수치를 "목표"로 격하한다. 오프라인 게이트로는 구조 단언을 둔다: `act`가 LLM 스텁을 0회 호출하고 UoW 1개만 연다. 마커 재조회 왕복을 예산에 포함해 적는다. | New |
| R-04 | Minor | nfr-light.md > §1 NFR-2; requirements NFR-2 | 요구 NFR-2는 PBT-08(hypothesis seed 로깅)을 blocking으로 든다. 노트는 "실패 예제는 hypothesis 데이터베이스(로컬)"만 적었고 seed 로깅·재현 방법(예: `@reproduce_failure`/`--hypothesis-show-statistics`/CI 출력)이 없다. 기존 테스트에는 conftest 프로파일이 없어(`tests/conftest.py` 없음) 유닛 코드 플랜이 스스로 만들어야 한다. | seed 로깅 방법(프로파일 등록 또는 pytest 옵션)을 한 줄로 정하고 코드 플랜 입력(§5)에 넣는다. | New |
| R-05 | Minor | nfr-light.md > §1 NFR-5·NFR-8, §5 항목 2; FD domain-entities.md > `PlayTuning` | env 목록이 FD와 어긋난다. FD는 `PlayTuning +3`(`max_move_cost`=`PLAY_MAX_MOVE_COST`, `max_new…`, `max_llm_calls…`)인데 노트는 `PLAY_MAX_MOVE_COST`를 빼고 `RUMOR_MAX_ACTIVE_PER_REGION`을 더해 "PlayTuning 3", NFR-8은 "새 env 3개"라 적는다. 실제는 PlayTuning 4 + Settings 1 = env 5개다. `max_move_cost`가 env로 바뀌면 "한 행동 ≤ 40 호출" 상한(5×8)은 고정이 아니라 `max_move_cost × max_llm_calls`다. | env 5개 목록을 확정하고 NFR-5의 40은 공식으로 적는다. `env.example`·`operations.md` 단계에 5개를 반영한다. | New |
| R-06 | Minor | nfr-light.md > §1 NFR-6, §2 실패 격리 | 배경 실행 실패 기록 규칙은 명확하나 `getTurnRun(sid, run_id)`가 run이 해당 세션 소속인지 검사하는 규칙이 없다(다른 세션 run id로 조회 가능). 인증 없는 로컬 데모라 위험은 낮다. | 조회 시 `run.session_id == sid` 아니면 404라고 한 줄 추가한다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| NFR-1..9 중 U4에 걸리는 항목이 표에 모두 있는가 | 9/9 행 있음(NFR-3의 "긴 작업 진행 표시"는 폴링으로 충족) | 누락 없음 |
| NFR-1 회귀 24곳 | `tests/play/test_advance_turn.py` 21 + `test_play_services.py` 3, `gm.py` 라우트 1 | 노트와 일치 |
| NFR-1 기준선 419 | 상태 문서 388 pytest + 31 vitest | 일치 |
| NFR-7 mypy 12 | `aidlc-state.md` U2 코드 리뷰 뒤 mypy 12; 요구는 "16→줄이기" | 일치(mypy는 이 환경에 없어 재실행하지 않음) |
| §2 "PG 11곳 `engine.begin()`" | `postgres_repo.py`에서 `begin()` 11곳 | 일치 |
| N-3 LLM timeout 조건문 | `retry.py` `CALL_TIMEOUT_SECONDS = 30.0`, `openai_provider.py` 사용 | 이미 존재 → R-02 |
| N-5 "운영 문서 `--workers 1`" | `operations.md:95` Single worker, `docker-compose.yml:139` | 일치 |
| NFR-3 `WorldCache` 적중 경로 | `cache.py` 적중에도 버전 마커 재조회 | R-03 |
| NFR-5 `narration` LLM 여부 | FD `narrate(changes)` 결정적, 예산 밖 호출 없음 | 예산 누수 없음 |
| 활성 소문 정의 | `memory_repo.list_rumors` `r.active`(비-pruned) 필터; FD에 "활성" 정의 없음 | R-01 |
| TP-U4-1~7 대응 | FD business-rules TP-U4-1~7 + 8(생성기)와 노트 서술 일치 | OK |
| NFR-9 세션 교체 닫기 | `__main__.py` `_guard_open_sessions`(--force) | CLI 경로 확인, 404 규칙은 U4 소관 |
| 신규 기술 스택 | 스레드·폴링·Core 트랜잭션, C-3/C-4 위반 없음 | OK |

### Summary

새 스택·인프라 없이 NFR-1~9의 U4 접점을 대부분 정확히 다루고 FD·코드와도 맞는다(호출처 24곳, 11곳 트랜잭션, 단일 워커). 다만 활성 소문 상한 규칙이 20 초과 경로를 막지 못하고 검증 불변식도 GM 예외와 충돌하며(R-01), LLM이 느리거나 장애일 때 배경 실행의 최악 시간·중단 규칙이 없다(R-02). Major 2건은 임계(2건 이하) 이내라 READY이고, 둘 다 코드 생성 플랜 단계에서 규칙을 확정하면 된다.
