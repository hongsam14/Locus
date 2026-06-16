# Unit-A (Model & Wiki Structure) — Code Generation Plan

**Single source of truth for Unit-A code generation.** Brownfield: 기존 파일 **수정**(복사본 금지).
설계: `construction/unitA-model-wiki/functional-design/` (domain-entities/business-logic-model/business-rules).
범위: 영역 1(real_world 삭제+교차참조) + 영역 2(WikiPrior 커뮤니티) + 영역 3(Knowledge.title).

## Unit Context
- **의존성**: 없음(첫 빌드 단위). Unit-B(인제스션)는 이 단위의 모델/도메인 변경에 의존.
- **데이터 초기화**: 마이그레이션 없음(Q4/Q11/Q15=B). 기존 데이터 폐기·재빌드 전제.
- **불변식**: BR-A9(NPC 단일 world) / BR-A13(`__realworld__` 잔재 0).

---

## 코드 생성 단계

### 그룹 1 — 도메인 모델 (Business Logic 기반)
- [x] **Step 1: `locus/models/enums.py`** — `WikiDomain` enum 추가(GEOGRAPHY/GEOLOGY/CLIMATE/ECOLOGY/ECONOMY/LOGISTICS/CULTURE/HISTORY/POLITICS/RELIGION/MILITARY/TECHNOLOGY/OTHER).
- [x] **Step 2: `locus/models/graph.py`** —
  - `Knowledge.title: str`(필수) 추가.
  - `WikiPrior`: `world_id: str`(필수) + `domains: list[WikiDomain]`(default `[]`, 빌더가 채움) 추가.
  - `WikiPriorLink`(신규): world_id/source_id/target_id/relation/weight[0,1]/cross_domain/provenance.
  - `World.kind` realworld 의미 제거(필드는 유지, 특수 분기 삭제).
- [x] **Step 3: `locus/models/io.py`** — `KnowledgeView.title: str | None = None`(export/UI 라벨용, 선택).
- [x] **Step 4: `locus/models/__init__.py`** — `WikiDomain`, `WikiPriorLink` export.
- [x] **Step 5: title fallback 헬퍼** — `locus/models/graph.py` 또는 `ingestion/mapping.py`에 `fallback_title(statement)->str`(≈60자, 단어 경계). BR-A2.

### 그룹 2 — Repository / 영속화 매핑
- [x] **Step 6: `locus/storage/graph_mapping.py`** —
  - `knowledge_to_node`/`node_to_knowledge`: title 왕복.
  - `knowledge_doc.text`: `title + statement + topic`(BR-A3, Q6=A).
  - `wikiprior_to_node`/`node_to_wikiprior`: `world_id`(노드 world_id로) + `domains` 왕복. `wikiprior_doc.meta`에 domains 포함.
  - `wikipriorlink_to_edge`(신규, type=`PRIOR_RELATED_TO`) + `edge_to_wikipriorlink`(역매핑).
- [x] **Step 7: `locus/storage/base.py`** — `SearchRepository.hybrid_search`의 `world_id: str | None`로 시그니처 확장(None=전 world, 교차참조용). `GraphRepository` 필요 시 도메인 전역 조회는 검색으로 처리(그래프 변경 최소).
- [x] **Step 8: `locus/storage/neo4j_repo.py` / opensearch 어댑터** —
  - OpenSearch `hybrid_search`: `world_id` None이면 파티션 필터 생략, `filters`(label=WikiPrior, domains) 적용.
  - neo4j `NODE_LABELS`/World 라벨 특수 처리 정리(World 노드 미영속 반영). `PRIOR_RELATED_TO` 엣지 지원 확인.
- [x] **Step 9: `locus/storage/persistence.py`** — `persist_graph`에 `prior_links: list[WikiPriorLink]` 인자 추가 → `PRIOR_RELATED_TO` 엣지 upsert. priors 노드/문서는 기존대로(이제 world_id는 인자 그대로).

### 그룹 3 — Wiki 비즈니스 로직 (영역 1+2)
- [x] **Step 10: `locus/commonsense_wiki/schemas.py`** — `PriorSuggestion.domains: list[WikiDomain]` 추가(distill 시 동시 분류).
- [x] **Step 11: `locus/commonsense_wiki/distiller.py`** — 범용화: 각 `WikiPrior`에 `world_id` + `domains` 설정(비면 `[OTHER]`). docstring realworld 제거.
- [x] **Step 12: `locus/commonsense_wiki/linker.py`(신규) `WikiPriorLinker`** — 임베딩 top-k 후보 → LLM 관계 판정(신규 schema `PriorLinkVerdict`) → `WikiPriorLink` 생성(BR-A6/A7/A8, cross_domain 플래그, world 내부, graceful).
- [x] **Step 13: `locus/commonsense_wiki/base.py` `CommonsenseWiki`** — `world_id` 기본값(REALWORLD) 제거 → 필수 인자. docstring 갱신(단일 world, NPC 경로 BR-A9).
- [x] **Step 14: `locus/commonsense_wiki/cross_world.py`(신규) `CrossWorldWikiExplorer`** — `world_domains(world_id)`(합집합 계산, BR-A11) + `search_related_priors(world_id, query, k)`(전 world 글로벌 검색, 현재 world 제외, read-through, BR-A10). 기획자 전용.
- [x] **Step 15: `locus/commonsense_wiki/admin.py` `WikiAdmin`** — `upsert_prior(prior)`(prior.world_id 사용)/`list_priors(world_id)` 명시 인자. REALWORLD 제거.

### 그룹 4 — title 생성 경로 (영역 3)
- [x] **Step 16: `locus/ingestion/schemas.py`** — `ExtractedKnowledge.title: str | None` 추가.
- [x] **Step 17: `locus/ingestion/mapping.py` `to_knowledge`** — title 전달(LLM값 우선, 비면 `fallback_title`).
- [x] **Step 18: `locus/ontology/schemas.py` + `corroboration.py`** — `CorroborationSuggestion.title` 추가; corroboration Knowledge에 title(또는 fallback) 채움.
- [x] **Step 19: `locus/augmentation/apply.py`** — ADD로 생성하는 Knowledge에 title(answer.title 또는 fallback) 채움. (augmentation types에 title 필드 필요 시 추가.)

### 그룹 5 — 파이프라인/제거 리팩터링 (영역 1)
- [x] **Step 20: `locus/services/orchestrator.py`** — build_world에 distill→link→prior+link 우선 영속화→ontology(단일 world wiki)→나머지 영속화 통합. `from_factory`에 PriorDistiller/WikiPriorLinker 주입. BuildReport에 priors/links 카운트(선택).
- [x] **Step 21: `__realworld__` 제거** — `locus/__init__.py`(REALWORLD_WORLD_ID 삭제), `locus/commonsense_wiki/bundled.py` 삭제, `examples/realworld_sample/` 삭제, `locus/commonsense_wiki/builder.py`(WikiBuilder) 삭제, `locus/commonsense_wiki/__init__.py` exports 갱신(WikiBuilder/load_bundled_realworld 제거, linker/cross_world 추가).
- [x] **Step 22: `locus/__main__.py` (CLI)** — `build-wiki` 명령 + load_bundled_realworld import 제거. `build-world`는 orchestrator가 자체 distill(변경 최소). help/문구 갱신.

### 그룹 6 — API 레이어
- [x] **Step 23: `api/main.py`** — wiki_builder/WikiBuilder/load_bundled_realworld 와이어링 제거; CommonsenseWiki(world별로 orchestrator 내부 생성); cross_world explorer + wiki_admin 와이어링. `_STATE_KEYS` 갱신.
- [x] **Step 24: `api/routers/authoring.py`** —
  - `build_wiki`/`load_bundled_realworld` 엔드포인트 제거.
  - `upsert_prior`: prior.world_id 사용(경로에 world_id 명시 권장: `POST /worlds/{world_id}/priors`).
  - 신규 기획자 엔드포인트: `GET /worlds/{world_id}/related-priors`(CrossWorldWikiExplorer).
  - graph_summary의 prior_count 등 유지.

### 그룹 7 — 테스트 (각 그룹 후 작성/수정)
- [x] **Step 25: 모델/매핑 테스트** — `tests/models/*`(title 필수·왕복, WikiPrior domains/world_id, WikiPriorLink), `tests/storage/*`(graph_mapping 왕복, knowledge_doc text에 title, prior_link 엣지).
- [x] **Step 26: wiki 테스트 갱신/신규** — `tests/commonsense_wiki/test_wiki.py`·`test_wiki_build.py`에서 realworld 제거; `WikiPriorLinker`(임베딩 top-k 가드, cross_domain), `CrossWorldWikiExplorer`(글로벌·현재 world 제외·read-through), 범용 distiller(world_id/domains) 테스트.
- [x] **Step 27: ontology/ingestion/augmentation 테스트** — title 채움/ fallback, corroboration title.
- [x] **Step 28: services/orchestrator + api 테스트** — build_world가 priors+links 생성·단일 world wiki(BR-A9); authoring 라우터 신규/제거 반영.
- [x] **Step 29: 회귀 — `__realworld__` 잔재 0** — `grep -r "realworld\|REALWORLD\|load_bundled"` 0건(BR-A13). 전체 pytest GREEN, ruff/black 클린.

### 그룹 8 — 문서
- [x] **Step 30: 코드 요약** — `aidlc-docs/construction/unitA-model-wiki/code/` 에 변경 요약(modified/created/deleted) 작성. README/CLAUDE.md의 build-wiki/realworld 언급 갱신.

---

## Story Traceability
- 본 사이클은 User Stories를 SKIP했으므로 FR-IM 매핑으로 추적:
  - 영역1: FR-IM1.1~1.7 → Step 8,9,11,13,14,15,20,21,22,23,24
  - 영역2: FR-IM2.1~2.5 → Step 1,2,6,10,11,12,14,24
  - 영역3: FR-IM3.1~3.3 → Step 2,3,5,6,16,17,18,19
- 총 30 스텝(레이어별 그룹). 테스트는 그룹 완료 시점마다 작성.
