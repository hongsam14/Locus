# X1 Localization Backend — Code Generation Plan (brownfield)

**Single source of truth for X1 code generation.** 워크스페이스 루트 = `/home/thinkpad/Desktop/src/Locus`. 앱 코드는 루트, 문서는 `aidlc-docs/`.

## Unit Context
- **유닛**: X1 Localization Backend (C1–C8). **의존**: 없음(기존 세션/LLM 계층 위 가산). **후속**: X3가 ko 응답·`region_changes` 소비.
- **FR/BR**: FR-UX3.2/3.3/3.5/3.6, FR-UX2.6(백엔드 셰이핑), BR-X1-1..27. **SEC**: A/C/E. **NFR**: UX2/3/5, PBT(Partial).
- **결정**: Q1=A/Q2=C/Q3=A/Q4=B/Q5=A/Q6=A/Q7=A + 리뷰 findings F1(append 수집)/F2a(타임라인 제외)/F3(ko 응답전용)/F4(warm 기본 off).

## Steps

### Step 1 — Settings + translation 패키지 스켈레톤 [x]
- `locus/config/settings.py`: `translation_enabled`(기본 True), `translation_target_lang`("ko"), `translation_model`(None), `translation_batch_size`(20) 필드 추가(alias 포함).
- `locus/translation/__init__.py` 생성(공개 심볼 export).
- (P-F1/Q1=A: 워밍 미구현 → `translation_warm_on_generate` 설정 없음. 번역은 조회 지연 단일 경로.)

### Step 2 — Translator (C1) [x]
- `locus/translation/translator.py`: `Translator(llm, model=None)` + `translate()/translate_many()`. 빈문자 통과(BR-X1-1), 실패 시 원문 폴백+경고 로그(BR-X1-3), 항목 독립(BR-X1-4). 시크릿 미로깅(SEC-A).

### Step 3 — Translation 엔티티 + RegionTurnChange + TurnResult 확장 (C2/C6) [x]
- `locus/session/models.py`: `Translation` 모델(kind/id/field/lang/text/source_hash/world_id/session_id/created_at) + `RegionTurnChange`.
- `locus/session/turn.py`: `TurnResult.region_changes: list[RegionTurnChange] = []` 가산(BR-X1-18).
- ko 응답 전용 필드: `SessionRumor.statement_ko: str|None=None`, `SessionEvent.description_ko: str|None=None`.
- **(P-F5 가드)** ko 필드는 **응답 전용·비영속**. postgres는 명시 컬럼 매핑이라 자동 무영속(검증됨); 주석으로 "response-only, not persisted" 명시. enrichment는 조회 반환 경로에서만 수행하고 `upsert_rumors`로 가는 인스턴스는 오염 금지(BR-X1-27).

### Step 4 — SessionRepository 포트 + InMemory 번역 캐시 (C2) [x]
- `locus/session/repository.py`(포트): `get_translation`, `get_translations_many`, `upsert_translation` 시그니처.
- `locus/session/memory_repo.py`: 딕셔너리 기반 구현(키 `(kind,id,field,lang)`), `source_hash` 저장.

### Step 5 — Postgres 번역 캐시 (C2) [x]
- `locus/storage/postgres_session_repo.py`: `translations` 테이블(가산, `ensure_schema` idempotent, 유니크 `(source_kind,source_id,source_field,target_lang)`), 세 메서드 구현. (오프라인은 SQLite로 테스트.)

### Step 6 — TranslationService (C3) [x]
- `locus/translation/service.py`: `TranslationService(repo, translator)` + `localize()/localize_many()`. 캐시우선·`source_hash` 무효화(BR-X1-6), 성공분만 저장(BR-X1-7), 배치 상한(BR-X1-22). `_hash(text)` 헬퍼(정규화+sha256).

### Step 7 — 조회 enrichment (C5) [x]
- `locus/models/io.py`: `KnowledgeView.statement_ko: str|None=None`, `title_ko: str|None=None`(응답 전용 옵션, BR-X1-27).
- `locus/session/query.py`: `SessionQueryEngine`에 `translation` 옵션 DI. `knowledge_for_region` 결과 items에 ko 부착 — `is_rumor`면 `localize("rumor",id,"statement")`, 아니면 캐노니컬 `localize("knowledge",id,"title"/"statement",world_id=)`(Q4=B 지연·world 캐시). `localize_many`로 N+1 회피(BR-X1-16).

### Step 8 — advance_turn append 수집 + region_changes 셰이핑 (C6, F1) [x]
- **(P-F4)** `shape_region_changes(...)`는 **순수 모듈 `locus/session/turn_changes.py`** 에 배치(입력=promoted/demoted/pruned/applied/resolved ids + rumors_by_region region_id + added_by_region + feedback_regions → `list[RegionTurnChange]`; 무변동 제외 BR-X1-21). PBT 용이(S12).
- `locus/session/turn.py`: step(2) `append_for_region` 반환을 `added_by_region`로 수집(F1). `turn_changes.shape_region_changes(...)` 호출 → `TurnResult.region_changes` 채워 반환. 기존 top-level 리스트 유지(가산).

### Step 9 — ~~생성 워밍 훅~~ **DROPPED (P-F1/Q1=A)** [x]
- 워밍 미구현. 번역은 조회 지연(Step 7/10) 단일 경로로 충족(FR-UX3.2). `rumor_service`/`event_service`에 `translation` DI **불필요** → 배선/테스트 없음. (BR-X1-13/26의 워밍은 문서상 옵션으로 남되 본 유닛 미구현 — 후속 최적화 여지.)

### Step 10 — API 응답 ko 부착 (C7) [x]
- **(P-F3 enrichment 소유자)** `api/routers/session.py`에 얇은 헬퍼 `_attach_ko(items, kind, *, world_id/session_id)` 도입 — `TranslationService`로 조회 반환 직전 ko 부착(read-path 단일 지점). `game_master`/`query`는 원 데이터만 반환.
- ko 부착 대상: **조회 경로만** — `list_rumors`(SessionRumor.statement_ko), `list_events`(SessionEvent.description_ko), `session_knowledge`(enrich된 `QueryResult`, Step 7).
- **(P-F2/Q2=A)** `generate_rumors`/`regen`은 **ko=null(지연)** 로 반환(방금 생성물 인라인 번역 안 함 — F4). ko는 이후 `list_rumors` 조회에서 부착.
- `advance-turn`은 `region_changes` 포함(모델 확장으로 자동). 입력 검증 유지(SEC-A). 신규 라우트 없음.

### Step 11 — Wiring + env (C8) [x]
- `api/main.py`: `Translator(llm, model)` → `TranslationService(repo, translator)` 생성, `SessionQueryEngine` + 세션 라우터(`_attach_ko`용)에서 사용하도록 배선. `translation_enabled=False`면 미주입(graceful, 원문만). (생성 서비스 DI 없음 — S9 드롭.)
- `env.example`: `TRANSLATION_*` 항목 문서화(주석).

### Step 12 — 테스트 [x]
- `tests/translation/test_translator.py`(폴백·빈문자·목 LLM), `test_translation_service.py`(캐시히트/무효화/배치, PBT: hash 안정성).
- `tests/session/test_translation_enrichment.py`(query·list ko 부착, 캐노니컬 지연, **generate/regen은 ko=null 확인 P-F2**, **enrich가 upsert 인스턴스 미오염 P-F5**), `test_turn_changes.py`(순수 `shape_region_changes` 그룹핑·무변동 제외, PBT — P-F4).
- `tests/storage/test_postgres_session_repo.py`·`tests/session/test_repository_contract.py` 확장(번역 CRUD, **statement_ko 비영속 확인 P-F5**).
- `tests/session/test_session_api.py` 확장(조회 응답 ko·`region_changes`).
- (워밍 테스트 없음 — S9 드롭.)

### Step 13 — 코드 요약 문서 [x]
- `aidlc-docs/construction/X1-localization-backend/code/code-summary.md` 작성(변경/신규 파일, 테스트 수, 결정 반영).

## Story/FR Traceability
- FR-UX3.3→S2 · FR-UX3.2/3.5→S6/S7/S10(조회 지연 경로) · FR-UX3.6/Q4B→S7 · FR-UX3.4/Q8→S3/S7/S10 · FR-UX2.6(백엔드)→S3/S8 · SEC-A→S10 · SEC-C→S2/S6 · SEC-E→S6. (S9 워밍 드롭 — P-F1.)

## Quality Gates
- 오프라인 pytest GREEN(신규 포함), ruff/black/compileall clean. 캐노니컬·기존 세션 회귀 0. ko/ region_changes 가산·후방호환.
