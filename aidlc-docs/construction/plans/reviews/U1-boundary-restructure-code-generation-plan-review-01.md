## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation — Part 1 (unit plan) — U1 경계 재정리
**Reviewed artifact:** `aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-09-29T13:45:06Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 8.1 (vs Step 3.3, 4.7, 6.4, 7.4, 9.1, 10.4) | `SharedContainer`/`assemble_shared`의 위치가 "`api/containers.py`(또는 `locus/shared/wiring.py`)"로 열려 있다. 그런데 Step 3.3·4.7·6.4·7.4는 `assemble_knowledge(shared: SharedContainer)` 등에서 이 타입을 import하고, 이 단계들은 Step 8보다 먼저 온다. `api/`에 두면 knowledge/world/play/localization이 `api`를 import하게 되어 component-dependency.md §1 행렬(모든 경계 → api ✗)을 어긴다. Step 10.4의 `test_boundaries`는 "api는 제외"라고 하고 검사 목록에도 `* → api`가 없어 이 위반을 잡지 못한다. 개발자가 어느 쪽을 고를지 추측해야 한다. | `SharedContainer`·`assemble_shared` 위치를 `locus/shared/wiring.py`로 못박고, 생성 단계를 Step 2(shared)로 앞당긴다. `test_boundaries`에 "`locus/**`가 `api`를 import하면 실패" 규칙을 추가하고 "api 제외"가 무엇을 뜻하는지(api가 import하는 쪽으로서만 제외) 명시한다. | New |
| R-02 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 2.2 (`SourceKind` 값 변경) 및 "스키마는 `init-schema`로 재생성(마이그레이션 없음)" | `SourceKind` 값을 `inferred-wiki→inferred`, `session-rumor/session-event→simulation`으로 바꾸면서 "마이그레이션 없음"의 근거를 PostgreSQL 재생성에만 둔다. 그러나 `Provenance.source`는 엄격한 enum(`locus/models/graph.py:56`, `extra="forbid"`)이고 Neo4j에 `prov_source`로 저장되며 `graph_mapping._provenance`가 그대로 읽는다(`locus/storage/graph_mapping.py:203-208`). 이미 빌드된 캐노니컬 월드(`inferred-wiki` 항목 포함)는 변경 후 로드 시 검증 오류로 깨진다. "동작(의미) 불변"·"바꾸지 않는 것" 주장과 어긋나고, 이 영향은 계획 어디에도 적혀 있지 않다. | 다음 중 하나를 계획에 적는다. (a) 기존 Neo4j 월드는 재빌드해야 한다는 것을 위험으로 명시해 사람이 받아들이게 한다. (b) `SourceKind`가 옛 값을 읽어 새 값으로 매핑하도록 한다(예: `_missing_` 또는 `_provenance` 변환). 그리고 옛 값을 읽는 테스트를 Step 10에 추가한다. | New |
| R-03 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 5.1, 5.3 vs Step 7.1, 7.2 | 순서가 맞지 않는다. Step 5.1은 `Translation`을 `session/models`에서 "제거(7단계로)"하고, 5.3은 `postgres_session_repo`·`memory_repo`에서 번역 테이블·메서드를 "제거(7단계로)"한 뒤, 7.1/7.2가 이를 "옛 postgres_session_repo에서 옮김"이라 한다. 그 시점에는 원본이 이미 지워졌거나 `git mv`로 다른 이름·위치가 되었다. 또 번역 테이블은 지금 모듈 전역 `_metadata` 하나를 play 테이블과 공유하고(`postgres_session_repo.py:47`), `ensure_schema()`가 `create_all`로 한꺼번에 만든다(:175-186). `ensure_play_schema`/`ensure_localization_schema`를 나누려면 MetaData를 둘로 갈라야 하는데 계획에 없다(`translations` 제외 확인 필요). | Step 7의 추출(모델·테이블·SAVEPOINT 처리·인메모리)을 Step 5의 삭제보다 앞에 두거나, 5.x에서 "복사 후 7.x에서 삭제"로 순서를 고친다. play와 localization이 별도 `MetaData`를 쓰도록 명시하고, `ALTER TABLE session_rumors ... ADD COLUMN IF NOT EXISTS active`(비 SQLite 분기)가 `ensure_play_schema`로 가는지 적는다. | New |
| R-04 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 5.3 | 승인된 유닛 정의를 조용히 뺐다. `unit-of-work.md` U1 책임은 "P3 `PostgresPlayRepository`(포트 구현, `ON CONFLICT`)"이고 `components.md` P3도 "upsert는 `ON CONFLICT`로 경합 제거"라 적는다. 계획 Step 5.3에는 `ON CONFLICT`가 없고 "범위 밖" 절에도 없다. 현재 코드는 select 후 update/insert라 경합이 남는다(`_upsert_rumor_conn` :277-288, `set_region_distortion` :326-348). 뺀다면 승인 산출물과 어긋나고, 넣는다면 "동작 불변"·SQLite 오프라인 테스트 방언 처리 계획이 필요하다. | 5.3에 `ON CONFLICT` 도입을 단계로 넣고(방언별 처리: PostgreSQL vs SQLite 테스트), 계약 테스트 항목을 적는다. 아니면 뒤 유닛으로 미룬다고 "범위 밖"에 쓰고 `unit-of-work.md` 불일치를 사람 판단으로 올린다. | New |
| R-05 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 8.1, 9.1 | `assemble_shared`가 Neo4j·OpenSearch 연결, 스키마 초기화, 공급자 팩토리, SQL 엔진을 한꺼번에 하도록 되어 있고, 9.1의 CLI가 이를 그대로 쓴다. 그러면 `init-schema --play`나 `--localization`도 Neo4j·OpenSearch가 떠 있어야 하고, `--world`도 LLM 공급자 생성이 필요하다. US-7.2의 "경계별 스키마 초기화가 분리" 취지와 맞지 않는다. 라이프사이클(연결·스키마 초기화·정리) 책임도 조립에 섞인다. | 플래그별로 필요한 저장소만 연결하도록 `assemble_shared`의 부분 조립 또는 지연 생성을 정한다. 스키마 초기화를 조립 밖으로 뺄지 적는다. | New |
| R-06 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 4.5 | "`examples/` 경로 해석 유지"라 썼지만 `locus/demo.py:15`는 `Path(__file__).resolve().parents[1] / "examples" / ...`이다. `locus/world/demo/__init__.py`로 옮기면 `parents[1]`이 `locus/world`가 되어 지도 이미지가 조용히 빠진다(파일이 없으면 생략하는 코드). 고치는 방법이 없다. | `parents[3]`로 바꾸는 것을 단계에 적고, 지도 포함 여부를 검증하는 테스트를 하나 둔다. | New |
| R-07 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 11.2 | 지금 `web/src/api.ts`(파일)가 있고 계획은 `web/src/api/`(디렉터리) + `index.ts`를 만든다. `api.ts`를 지운다는 말이 없어 `../api` import가 파일과 디렉터리 사이에서 모호하다. 옛 경로 `/api/query|authoring|session` 호출을 가진 파일이 이것 하나(`api.ts`)라는 점도 적혀 있지 않다. | `git rm web/src/api.ts`(또는 `git mv`로 `api/index.ts`)를 명시한다. | New |
| R-08 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 8.5, 10.3, 10.6, 15.1, 스토리 추적 | (a) 8.5는 "기존 엔드포인트를 그대로 옮김"이라 하나 실제 경로가 바뀐다(`advance-turn→advance`, `suggest-events→events/suggest`, `augment/session→augmentation/runs`, `/api/query/regions/{r}/knowledge→/api/knowledge/worlds/{w}/regions/{r}`, 세션 지역 지식 경로 이동). 옛→새 매핑표가 없어 프론트 재작성과 테스트 갱신이 추측에 기댄다. (b) 10.3의 "403/503"은 오타로 보인다(503만 정의). (c) `unit-of-work-story-map.md`가 U1에 배정한 US-5.1(`/gm` 스켈레톤)·US-7.3(STATUS docstring)이 스토리 추적표에 없다. (d) 10.6의 "mypy 오류 16"은 출처가 없다. (e) `unit-of-work.md`의 완료 기준 `docker compose --profile service` 앱 기동이 15.1에서 "docker build (가능하면)"로 약해졌다. | 옛→새 경로표를 code-summary 또는 8.5에 두고, 오타를 고치며, 추적표에 US-5.1·US-7.3을 넣는다. mypy 기준선은 Step 1.1에서 실측해 기록한다. 완료 기준을 낮춘 것은 사람 판단으로 드러낸다. | New |
| R-09 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 2.5 vs Step 13.1 | 2.5는 `traverse`·`get_region_subtree`·`get_region_ancestors`를 제거하는데, `tests/storage/test_storage.py:95`(`test_traverse_respects_min_weight_param`)가 동작을 검증한다. 13.1은 "동작을 검증하는 테스트면 코드도 남긴다"고 정해 규칙이 서로 다르다. 게다가 US-7.4의 "281개가 통과"와 10.6 기대치가 테스트 삭제로 달라진다. | 삭제되는 테스트를 이름으로 나열하고, 10.6 기대 수를 그만큼 조정한다. 2.5와 13.1의 판정 규칙을 하나로 맞춘다. | New |
| R-10 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 7.1, 7.3 | `component-methods.md` L2는 `TranslationStore`를 `get_many/upsert_many/purge`로 정의했으나 계획은 옛 이름(`get_translation` 등)을 "시그니처 동일"로 유지한다(`purge`는 U5라 타당하지만 이름 불일치는 적혀 있지 않다). `TranslationService.enrich`를 "객체를 바꾸지 않고 매핑을 반환"으로 바꾸는 것은 시그니처와 호출부(routers, `session/query.py`)가 모두 바뀌는 일인데, `tests/translation/test_translation_service.py`·`tests/session/test_localization_api.py` 갱신 단계가 10.2 이름 목록에 없다. | 7.1에 설계와의 차이(이름, purge 이월)를 명시하고, 10.2에 `enrich` 시그니처 변경에 따른 테스트 갱신을 넣는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| plan-named existing source paths (`locus/*`, `api/routers/*`, `tests/*`, `web/src/*`, `pyproject.toml`, `Dockerfile`, `docker-compose.yml`) vs `git ls-files` | 모두 실존; 새 경로는 계획이 신규로 선언 | OK |
| `pyproject.toml` 패키지 탐색 | `[tool.setuptools.packages.find] include = ["locus*"]`, `--cov=locus` | 하위 패키지 포함됨; Step 1.3 OK. `api/`는 패키지가 아니라 Dockerfile `COPY api`가 필요함(Step 12 맞음) |
| `settings.py`의 `..session` import | `settings.py:13`(TYPE_CHECKING)·:101(지연 import) | Step 2.3의 역방향 의존 ① 해소 주장은 사실 |
| `SourceKind` 옛 값의 영속 위치 | `Provenance.source`는 엄격 enum, Neo4j `prov_source`로 저장·로드 | 값 변경이 기존 월드를 깨뜨림 — R-02 |
| `traverse`/`get_region_*`/`TraversalSpec` 호출부 | 어댑터·`__init__`·`tests/storage/test_storage.py:95-100`뿐, 서비스 호출자 없음 | 제거 자체는 가능하나 테스트가 있음 — R-09 |
| `ConsensusParams` 기본값 vs `KnowledgeTuning` | 0.5 / 0.15, 필드명은 `rumor_min` | 값 일치; `rumor_min` 개명은 계획에 없음(3.2 `from_tuning`로 흡수 가능) |
| `RumorDynamicsParams` 필드 수 | 6개, 계획의 나열과 일치 | OK |
| `demo.py`의 `__file__` 경로 | `parents[1]` | 이동 시 깨짐 — R-06 |
| 현재 라우트 vs 계획 8.5 | `advance-turn`, `suggest-events`, `augment/session` 등 경로 이름이 다름 | 매핑표 없음 — R-08 |
| `GameMasterService` | 순수 위임 파사드 (`game_master.py`), 참조 40건(테스트 포함) | 삭제 가능; 10.2가 테스트 갱신을 다룸 |
| 경계 행렬 vs Step 10.4 위반 목록 | 다섯 경계 간 규칙은 일치, `* → api` 누락 | R-01 |
| 스토리 ID (US-7.1/7.2/7.4/1.1/8.5/9.3) 해석 | 모두 stories.md와 story-map에 실존; US-5.1·7.3은 story-map이 U1에 배정했으나 계획 추적표에 없음 | R-08 |
| FR-A2가 든 역방향 의존 4곳 대비 | config→session(2.3), enum/뷰(2.2), init-schema(9.1), canonical_known(3.2) 모두 단계 있음 | OK |
| `tests/` 이동 목록 vs `git ls-files tests` | 목록에 든 파일 실존, 누락 파일 없음(`tests/topology`, `tests/models` 등 포함) | OK |

### Summary

Major 4건(R-01~R-04)이라 NOT-READY다. 핵심은 (1) `SharedContainer` 위치가 열려 있어 경계 행렬을 어길 수 있고 검사도 그것을 못 잡는다는 점, (2) `SourceKind` 값 변경이 저장된 Neo4j 월드를 깨는데도 "동작 불변"으로 적혀 있다는 점, (3) 번역 코드를 지운 뒤에 옮기라는 단계 순서와 공유 `MetaData` 분리 누락, (4) 승인된 유닛 정의의 `ON CONFLICT`가 계획에서 빠졌다는 점이다. 그 밖의 구조(다섯 경계, 스토리 대부분의 추적, 역방향 의존 4곳)는 상류 산출물과 대체로 맞는다.
