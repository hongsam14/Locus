# Services — Rumor Distortion / Game Session (Phase 1)

## SessionService (생애주기)
- 책임: GameSession 시작/종료/조회/이력, 타임라인 조회. SessionRepository 위 얇은 계층.
- 오케스트레이션: 단순 위임. 신규 세션 생성 시 turn=0, status=OPEN.

## GameMasterService (턴 오케스트레이터) — 핵심
- 책임: 한 세션의 동적 상태를 **턴 단위로 변화**. Phase 1 동작:
  1. `generate_rumors(region)` — 그 리전의 distortion_degree를 기준으로 캐노니컬 Knowledge(+기존 Rumor)에서 강도별 체인 Rumor 생성·저장 → GENERATE 타임라인.
  2. `regenerate_region(region)` — 기존 세션 rumor 폐기 후 재생성 → REGENERATE.
  3. `adjust_support(rumor, value)` — 지지도 수동 조정 → ADJUST_SUPPORT.
  4. `set_region_distortion(region, degree)` — 리전 왜곡 강도 설정 → SET_DISTORTION.
  5. `advance_turn()` — PromotionPolicy로 승격/강등 재평가·적용, turn++ → PROMOTE/DEMOTE + ADVANCE_TURN.
- 협력: RumorGenerator(LLM), PromotionPolicy(순수), SessionRepository(영속), WorldLoader/GraphRepository(캐노니컬 원본 읽기).
- 패턴: 기존 `PipelineOrchestrator`와 동일한 "단일 오케스트레이터" 스타일(AD-R Q3=A).
- graceful: LLM 실패 시 해당 생성 생략, 타임라인엔 부분 결과 기록, 턴 진행 계속(NFR-R4).

## SessionQueryEngine (세션 NPC 쿼리)
- 책임: 세션 컨텍스트에서 NPC가 보는 지식 = 캐노니컬 Knowledge(direct/inherited/global) + 승격 Rumor(direct처럼) + 일반 Rumor. **propagated/auto-rumor 제외**(FR-R5.1).
- 협력: 캐노니컬 `QueryEngine`(무변경 재사용) + SessionRepository(세션 rumor/승격 조회).
- 비세션(캐노니컬) 쿼리는 기존 `QueryEngine` 그대로(회귀 없음, FR-R5.2).

## 서비스 상호작용 (시퀀스 개요)
```
[웹] 세션 시작 → SessionService.start_session → SessionRepository.create_session
[웹] 리전 "소문 생성" → GameMasterService.generate_rumors
       → (WorldLoader 캐노니컬 Knowledge 읽기) → RumorGenerator.generate_chain(LLM)
       → SessionRepository.upsert_rumor* + append_timeline(GENERATE)
[웹] support 조정 → GameMasterService.adjust_support → upsert_rumor + timeline
[웹] 턴 진행 → GameMasterService.advance_turn → PromotionPolicy.evaluate
       → upsert_rumor(promoted/demoted) + bump_turn + timeline
[NPC/웹] 세션 쿼리 → SessionQueryEngine.knowledge_for_region
       → QueryEngine(캐노니컬) + SessionRepository(세션 오버레이)
[웹] 과거 세션 열람 → SessionService.list_sessions / get_timeline
```

## 와이어링 (api/main.py app.state)
- `session_repo`(PostgresSessionRepository) · `session_service` · `game_master`(GameMasterService) · `session_query`(SessionQueryEngine).
- 기존 graph/search/llm/embedding/loader 재사용. PostgreSQL 연결은 설정 `session_db_url`.
