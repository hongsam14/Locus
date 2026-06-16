# Units of Work — Rumor Distortion / Game Session (Phase 1)

3 단위. 빌드 순서 **S1 → S2 → S3**. 캐노니컬(Neo4j/OpenSearch) 불변; 신규 세션 레이어(PostgreSQL).

## S1 — Session Foundation & Infra
- **책임**: 세션 레이어의 토대(모델·포트·어댑터·생애주기·인프라) + 미사용 Neo4j Rumor 제거.
- **구성**:
  - `locus/session/models.py` — GameSession, SessionRumor, RegionDistortion, TimelineEntry, SessionStatus, TimelineKind.
  - `locus/session/repository.py` — `SessionRepository` 포트(Protocol).
  - `locus/storage/postgres_session_repo.py` — SQLAlchemy 어댑터 + `ensure_schema`.
  - `locus/session/memory_repo.py` — InMemory 구현(테스트/오프라인).
  - `locus/session/service.py` — `SessionService`(start/close/list/get/get_timeline).
  - `api/routers/session.py` — 세션 CRUD + timeline 라우터(부분); `api/main.py` 와이어링; `locus/config.py` `session_db_url`.
  - 인프라: docker-compose `postgres` 서비스, env, SQLAlchemy 의존성(pyproject).
  - 정리: `locus/models/graph.py` `Rumor` 제거; `graph_mapping` rumor 매핑 제거; `KnowledgeGraph.rumors`·loader·exporter·persist·orchestrator의 rumor 경로 제거.
- **FR/NFR**: R1, NFR-R1/R2/R3.
- **인프라 설계**: 이 단위에서 Infrastructure Design 실행.

## S2 — Rumor Engine
- **책임**: 소문 생성(왜곡)·지지도/승격·GameMaster 턴·타임라인·세션 NPC 쿼리.
- **구성**:
  - `locus/session/rumor_generator.py` — `RumorGenerator`(LLM 강도 체인) + schema `RumorDraft`.
  - `locus/session/promotion.py` — `PromotionPolicy`(순수).
  - `locus/session/game_master.py` — `GameMasterService`(generate/regenerate/adjust_support/set_region_distortion/advance_turn + Timeline 기록).
  - `locus/session/query.py` — `SessionQueryEngine`(캐노니컬 QueryEngine + 세션 오버레이; propagated/auto-rumor 제외).
  - `api/routers/session.py` — 소문/턴/distortion/세션쿼리 라우터(확장); `api/main.py` 와이어링.
- **FR**: R2, R3, R4, R5.
- **의존**: S1(모델/포트/서비스) + 기존 `QueryEngine`/`WorldLoader`/`LLMProvider`.

## S3 — Web UI
- **책임**: 기획자 웹 흐름.
- **구성**:
  - `web/src/api.ts` — 세션/소문/턴/타임라인/세션쿼리 클라이언트; dead `buildWiki` 제거.
  - `web/src/` 컴포넌트 — 세션 생성/선택/종료, RegionPanel "소문 생성" 버튼 + support/distortion 표시 + 승격 상태, 과거 세션·타임라인 열람 패널.
  - `web/src/types.ts` — 세션/Rumor/Timeline 타입.
  - vitest 테스트.
- **FR**: R6.
- **의존**: S2 API.

## 코드 위치 (brownfield)
- 백엔드 신규 패키지 `locus/session/`; 어댑터는 `locus/storage/`; API는 `api/routers/session.py`; 웹은 `web/src/`. 문서는 `aidlc-docs/`.
