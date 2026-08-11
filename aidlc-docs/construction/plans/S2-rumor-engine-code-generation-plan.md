# S2 (Rumor Engine) — Code Generation Plan

**Single source of truth for S2 code generation.** Brownfield; 코드 위치 = `locus/session/`(신규 엔진 모듈) + `locus/query/engine.py`(순수 helper 추가) + `api/`(라우터 확장/와이어링). 문서 요약만 `aidlc-docs/construction/S2-rumor-engine/code/`.

## Unit Context
- **FR**: R2(생성·왜곡)/R3(support·승격)/R4(GameMaster·턴·Timeline)/R5(NPC 쿼리).
- **Dependencies**: S1(models/port/SessionService) + 기존 `WorldLoader`/`ConsensusEngine`/`QueryEngine`/`LLMProvider`(무변경 재사용). S3(Web)가 S2 API에 의존.
- **Contracts 제공**: RumorGenerator, PromotionPolicy, GameMasterService(generate/regenerate/adjust_support/set_distortion/advance_turn), SessionQueryEngine, 세션 API 확장.
- **설계 근거**: FD `{domain-entities,business-logic-model,business-rules}.md`. S1 nfr-light. Infra 변경 없음.

## Steps

### A. 순수/LLM 빌딩블록
- [x] **Step 1 — canonical_known helper** (`locus/query/engine.py`): 순수 함수 `canonical_known(view)=direct+inherited+global` 추가. **QueryEngine 클래스 무변경**. [Q7=A, BR-S2-22]
- [x] **Step 2 — helper 테스트** (`tests/query/test_query.py` 확장): canonical_known가 propagated/auto-rumor 제외, 기존 view_items 무회귀. [NFR-R6]
- [x] **Step 3 — RumorGenerator + RumorDraft** (`locus/session/rumor_generator.py`): `RumorDraft(statement)` structured schema; `generate_chain(...)` — degree 오름차순 체인, 텍스트 계보(distorted_from step i→i-1), confidence=src×(1-degree), support=0, graceful(중간 실패→앞 단계만). 기존 LLM structured-output 패턴 준수. [FD §1, BR-S2-2~7]
- [x] **Step 4 — RumorGenerator 테스트** (`tests/session/test_rumor_generator.py`): mock LLM — 체인 길이, distorted_from 계보/kind, confidence 공식, graceful 중단. 
- [x] **Step 5 — PromotionPolicy + PromotionResult** (`locus/session/promotion.py`, 순수): `DEFAULT_PROMOTION_THRESHOLD=0.6`; `evaluate(rumors, threshold)->PromotionResult`(전이만). [FD §2, BR-S2-10/11/13]
- [x] **Step 6 — PromotionPolicy 테스트(+PBT)** (`tests/session/test_promotion.py`): 경계 threshold, 멱등, 전이 정확성. [NFR-R5]

### B. 오케스트레이터 + 쿼리
- [x] **Step 7 — GameMasterService + TurnResult** (`locus/session/game_master.py`): generate_rumors(소스=direct+propagated+세션Rumor; degrees=[d/3,2d/3,d]) / regenerate_region(전체 삭제 후 재생성) / adjust_support / set_region_distortion / advance_turn(promote/demote 적용+bump_turn). 각 동작 → 정확히 1 TimelineEntry. 닫힌 세션 쓰기 거부. [FD §3, BR-S2-1~16]
- [x] **Step 8 — GameMasterService 테스트** (`tests/session/test_game_master.py`): in-memory repo + fake loader(ConsensusView) + mock generator — 생성/소스수집/재생성 삭제/support 조정/advance_turn 승격·강등·turn++/타임라인 항목·종류, graceful. 
- [x] **Step 9 — SessionQueryEngine** (`locus/session/query.py`): knowledge_for_region — canonical_known(view) + 세션 오버레이(승격→direct-like is_rumor=True, 비승격→rumor view); propagated/auto-rumor 제외; unique=direct+승격, shared=inherited+global. [FD §4, BR-S2-18~20]
- [x] **Step 10 — SessionQueryEngine 테스트** (`tests/session/test_session_query.py`): fake loader + in-memory repo — propagated/auto-rumor 제외, 승격 direct-like, 비승격 rumor 포함, region 미존재 404 경로.

### C. API + 와이어링
- [x] **Step 11 — API 라우터 확장** (`api/routers/session.py`): 6 라우트(generate/regen/support/distortion/advance-turn/knowledge). `game_master`/`session_query` 주입. 404(없는 세션/리전)/409(닫힌 세션)/422(범위). [FD §5]
- [x] **Step 12 — API 테스트** (`tests/session/test_session_api.py` 확장): TestClient + fakes — happy/404/409/422.
- [x] **Step 13 — 와이어링** (`api/main.py`): `game_master`=GameMasterService(session_repo, RumorGenerator(llm), loader), `session_query`=SessionQueryEngine(session_repo, loader). `_STATE_KEYS` 추가. [FD §6]
- [x] **Step 14 — `locus/session/__init__.py` export**: RumorGenerator/PromotionPolicy/GameMasterService/SessionQueryEngine/결과 타입 공개.
- [x] **Step 15 — 문서**: `construction/S2-rumor-engine/code/code-summary.md`.

**Verification**(작성만; 실행은 Build&Test): 전체 pytest GREEN, ruff/black clean, 외부 호출(LLM/DB) mock 오프라인. 기존 테스트 회귀 0.

## FR Coverage
- FR-R2 → Step 3,7 · FR-R3 → Step 5,7 · FR-R4 → Step 7 · FR-R5 → Step 1,9.

## Notes
- 테스트는 작성만(실행은 Build&Test). LLM/Postgres는 mock/in-memory.
- 스타일: black(line 100), ruff, 타입 힌트, Pydantic v2.
- S1 포트/모델 **무변경 재사용**; 캐노니컬 접근은 read-only(NFR-R2).
- Infra/NFR 단계 없음(S1 스택·nfr-light 적용).
