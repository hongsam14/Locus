## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** NFR Requirements (light) — U5 NPC 대화·언어
**Reviewed artifact:** aidlc-docs/construction/U5-npc-dialogue-language/nfr/nfr-light.md
**Class:** advisory
**Iteration:** 1
**Date:** 2026-09-30T12:15:11Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | nfr-light.md > §1 NFR-5 ("최악 지연은 호출당 약 97초 … 한 요청이 그 이상 걸리지 않는다"); §5-2·NFR-8 (operations.md에 97초 기재); N5-3 | 산술과 결론이 둘 다 틀리다. (1) `retry.py`는 `stop_after_attempt(3)`이므로 대기는 시도 사이 두 번(1초, 2초)뿐이다: 30×3+1+2 = **93초**. 97은 4초 대기(세 번째 대기)를 더한 값인데 그 대기는 일어나지 않는다. (2) 더 중요하게, `openai_provider.py`의 `ChatOpenAI(timeout=30)`는 `max_retries`를 지정하지 않는다(`langchain_openai` 기본 `None` → openai SDK 기본 2회 재시도). 그래서 `with_retry` 한 시도가 SDK 안에서 최대 3번(각 30초)까지 갈 수 있고 실제 상한은 약 270초(3×3×30 + 백오프)다. "한 요청이 그 이상 걸리지 않는다"는 이 근거로는 참이 아니다. 이 숫자가 operations.md와 UI 진행 표시·프록시 타임아웃 판단으로 이어진다 | 숫자를 코드에서 다시 유도해 적는다: `with_retry` 층은 93초이고 SDK 재시도가 겹치면 약 270초라는 점을 밝히거나, 코드 플랜에서 `max_retries=0` 고정(그러면 93초)을 결정한다. 어느 쪽이든 N5-3·NFR-5 행·FD BLM §2.2의 "≈97초" 문구와 operations.md 기재를 같은 값으로 맞추고, "그 이상 걸리지 않는다" 단언은 근거가 선 뒤에만 남긴다 | New |
| R-02 | Major | nfr-light.md > §1 NFR-3 ("구조 단언: `say` 한 번에 `LLM.complete` 1회, UoW 1개, 스냅샷 조회 1회") | 승인된 흐름(BLM §2.2)에서 "스냅샷 조회 1회"는 참이 아니다. `require_npc_here(snapshot, …)`가 스냅샷을 한 번 읽고, `region_knowledge.region_sources`가 내부에서 `self._snapshots.get(session.world_id)`를 다시 부른다(`locus/play/region_knowledge.py`의 `knowledge_for_region`과 같은 경로). 즉 최소 2회다(캐시 히트라도 `get` 호출은 2번). 또 UoW 1개도 "저장 UoW"만 센 것이라 `require_open`·`require_player`·`get_conversation`의 읽기 호출이 UoW 밖 개별 조회인지 명시가 없다. 이 단언을 그대로 테스트로 옮기면 처음부터 실패하거나, 실패를 막으려고 카운터를 느슨하게 고칠 수 있다 | 단언을 실제 흐름에 맞게 다시 쓴다: (a) `LLM.complete` 정확히 1회, (b) `repo.uow()` 진입 정확히 1회(저장 단계), (c) 스냅샷은 "세션당 한 번 로드되는 캐시(`WorldCache`)를 통해 읽고 `say`가 그래프/검색 저장소를 직접 치지 않는다"로 바꾸거나 `get` 호출 상한을 2로 적는다. 코드 플랜의 테스트 이름과 함께 고정한다 | New |
| R-03 | Minor | nfr-light.md > §2 동시성 ("경쟁하면 한쪽이 제약 위반을 받고 재조회한다") vs. functional-design/business-logic-model.md §2.2 저장 블록 | NFR 노트는 `UNIQUE (session_id, npc_id)` 경쟁 시 "재조회"를 약속하지만 승인된 `say` 흐름의 저장 UoW에는 재조회·재시도가 없다. `conv is None`을 UoW 밖에서 읽고 LLM 호출(수 초~수십 초)을 지난 뒤 만들기 때문에 창이 넓다. 지금 흐름대로면 진 쪽은 LLM 응답을 버린 채 500이 된다 | 코드 플랜에서 결정한다: 제약 위반을 잡아 `get_conversation`로 재조회 후 그 대화에 append하는 분기를 추가하거나, 노트의 문구를 "진 쪽은 오류로 끝난다(감수)"로 낮춘다. 어느 쪽인지 테스트(동일 npc 동시 첫 `say`) 하나로 고정 | New |
| R-04 | Minor | nfr-light.md > §1 NFR-6 프롬프트 주입 문장 ("최악의 결과는 … 데이터는 바뀌지 않는다") | 폭발 반경이 좁게 쓰였다. 플레이어 텍스트는 (1) 저장된 뒤 다음 `say`의 `recent`(최근 10개)로 다시 프롬프트에 들어가므로 NPC 답이 오염되면 그 대화 안에서 지속된다, (2) 세션에 인증·호출 제한이 없어 500자 입력으로 유료 LLM 호출을 무한 반복할 수 있다(NFR-5는 "상한은 플레이어의 속도"라고만 적음). 두 번째는 주입이 아니라 비용 남용이지만 같은 자유 텍스트 입구에서 나오는 위험이다. 캐노니컬 데이터가 안 바뀐다는 결론 자체는 BLM과 부합한다 | 문장에 "오염은 해당 대화의 이후 턴으로 이어질 수 있음"과 "요청 빈도 제한 없음 → 비용은 플레이어 속도에 비례(로컬 데모 전제로 감수)"를 명시하고 N5-4에 함께 남긴다. 제한을 두려면 세션당 분당 상한 env를 코드 플랜에서 정한다 | New |
| R-05 | Minor | nfr-light.md > §1 NFR-3 수치·검증 ("start·history·npcs p95 ≤ 100ms") | 검증 방법이 없다. 오프라인 스위트는 측정 도구가 없고(`tests/**`에 지연 측정 없음) 라이브는 operator-run이다. 목표만 있고 무엇으로 확인하는지가 없어 검사 불가능한 수치다. 구조 단언(R-02)만 테스트로 남는다 | 이 수치를 "라이브 확인은 operator-run, 오프라인은 LLM·그래프 호출 0회 단언으로 대체"로 적거나 목표에서 뺀다 | New |
| R-06 | Minor | nfr-light.md > §1 NFR-1 계약 변경 (2) | 호출처 목록은 맞다(`locus/play/wiring.py:96`, `tests/play/test_player_mode.py:641`; `tests/play/helpers.py`·`tests/shared/test_wiring.py`는 `assemble_play`를 통해 간접). 다만 (1)(3)과 달리 (2)는 새 인자가 필수인지 기본값이 있는지 안 적혀 있다. `test_player_mode.py:641`은 `_Snap` 페이크로 직접 생성하므로 필수 인자면 그 테스트에 `region_knowledge` 페이크가 필요하다 | (2)에 "필수 위치 인자, `_services()`(test_player_mode.py:636-642) 한 곳 수정"처럼 결정을 적는다 | New |

### Checks Run

| Check | Result |
|---|---|
| `regenerate_region` 호출처 grep | 맞음: `api/routers/gm.py:135` 1 + `tests/play/test_play_services.py` 84·100·181·203 + `tests/play/test_player_mode.py:935` = 6곳. 프런트에 참조 없음(응답은 `list[RumorOut]` 유지) |
| `PlayService(` 생성처 grep | `locus/play/wiring.py:96`, `tests/play/test_player_mode.py:641` 두 곳. 그 외는 `assemble_play` 경유(`tests/play/helpers.py:49`, `tests/shared/test_wiring.py:107`, `api/main.py:64`) — R-06 |
| `enrichment_for`/`localize_*` 호출처 grep | `api/schemas.py` 내부 4곳, `api/routers/gm.py:59,74`, `api/routers/knowledge.py:29`, `api/routers/play.py:107,163`; 테스트 직접 호출 없음. `TranslationService.enrich`는 이미 `lang` 인자를 가짐 — 계약 (3)은 기본값으로 안전 |
| `retry.py` 재계산 | 3시도, 대기 2회(1+2) → 93초. 97 불일치; `ChatOpenAI`에 `max_retries` 미지정(SDK 기본 2) — R-01 |
| `say` 구조 단언 vs BLM §2.2 | LLM 1회·저장 UoW 1개는 참. 스냅샷 조회는 `require_npc_here` + `region_sources` 내부 `get`으로 2회 — R-02 |
| 테스트 수 | 백엔드 `def test_` 461개 정의(파라미터화로 475 가능, 실행 없이 확정 불가); vitest `it(` 39개 = 노트의 39와 일치 |
| mypy 기준선 11 | 상태 문서 없이 U4 코드 리뷰 기록(`U4 code-review-01.md`: "11 errors")과 일치; 이번 검토에서는 mypy를 실행하지 않음 |
| U4 접점 스폿체크 | `tests/conftest.py`에 `locus` 프로파일(`print_blob=True`) 있음; `llm_available`는 `locus/play/models.py:328,367`, `LlmUnavailableError`는 `locus/play/errors.py:26`·`api/errors.py:35`(503 매핑)에 있음 |
| `tests/play/strategies.py` 재사용 | 존재 확인(노트가 주장하는 U4 생성기 위치) |
| 요구 NFR-1~9 누락 점검 | 9개 모두 행이 있다. NFR-3의 진행 상태 표시는 §3(전송 중 표시)이 커버. NFR-9는 요구 원문(월드 교체 시 세션 닫기·경고)이 U2/U1 범위이고 U5 행은 "사라진 NPC" 해석으로 좁혀 쓴다 — 결함은 아님 |

### Summary

READY이나 Major 둘은 게이트 전에 읽어 볼 가치가 있다(Major 2개 이하라 판정은 막지 않는다). R-01은 문서에 실릴 "최악 97초"가 코드와 다르고("한 요청은 그 이상 걸리지 않는다"는 SDK 재시도까지 감안하면 거짓), R-02는 테스트로 옮기면 바로 깨질 구조 단언이다. 세 계약 변경의 호출처 목록은 트리와 일치하고, 테스트 수(475+39)·mypy(11)·U4 접점도 맞다. 프롬프트 주입 서술은 결론(캐노니컬 데이터 불변)은 정직하나 대화 내 지속 오염과 비용 남용을 빠뜨렸다(R-04). 제안: 이후 유닛이 대화 마침 판단(요구 FR-C8/C10, NFR-5 보강)을 더하면 "대화는 턴 예산 밖" 문장이 바뀌므로 그때 이 행을 다시 볼 것.
