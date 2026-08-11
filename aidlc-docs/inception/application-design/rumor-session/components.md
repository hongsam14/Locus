# Components — Rumor Distortion / Game Session (Phase 1)

신규 패키지 `locus/session/` + PostgreSQL 어댑터 + 세션 API. 캐노니컬(Neo4j/OpenSearch)은 불변.
결정: AD-R Q1=A(SQLAlchemy)/Q2=A(ensure_schema)/Q3=A(GameMasterService)/Q4=A(SessionQueryEngine)/Q5=A(advance_turn)/Q6=A(SessionRumor 신설 + Neo4j Rumor 삭제).

## C1. Session 도메인 모델 (`locus/session/models.py`)
- **GameSession**: `id`, `world_id`, `status`(open/closed), `turn`(int), `created_at`, `closed_at`.
- **SessionRumor**: `id`, `session_id`, `region_id`, `distorted_from_id`(캐노니컬 Knowledge id 또는 SessionRumor id), `distorted_from_kind`(knowledge|rumor), `statement`(왜곡 텍스트), `distortion_degree`[0,1], `support`[0,1], `confidence`[0,1], `promoted`(bool), `provenance`.
- **RegionDistortion**: `session_id`, `region_id`, `distortion_degree`[0,1] (GameMaster 보유; Phase 1 수동/기본값).
- **TimelineEntry**: `session_id`, `turn`, `kind`(TimelineKind), `summary`, `payload`(dict), `created_at`.
- **enums**: `SessionStatus`(OPEN/CLOSED), `TimelineKind`(GENERATE/REGENERATE/PROMOTE/DEMOTE/ADJUST_SUPPORT/ADVANCE_TURN/SET_DISTORTION).
- 책임: 세션 레이어 순수 데이터(Pydantic). 캐노니컬 모델 참조는 id 문자열로만.

## C2. SessionRepository (포트, `locus/session/repository.py`)
- 책임: 세션 레이어 영속화 추상화(Protocol). 캐노니컬 Graph/Search와 동일한 포트 컨벤션.
- 인터페이스: 세션 CRUD, rumor CRUD, region-distortion get/set, timeline append/list, `ensure_schema`. (메서드는 component-methods.md)

## C3. PostgresSessionRepository (어댑터, `locus/storage/postgres_session_repo.py`)
- 책임: `SessionRepository`의 SQLAlchemy 구현. `ensure_schema`(idempotent DDL). connect/disconnect/health_check.
- 의존: SQLAlchemy Engine(설정 `session_db_url`).

## C4. InMemorySessionRepository (`locus/session/memory_repo.py`)
- 책임: 오프라인 테스트용 in-memory 구현(dict 기반). 모든 포트 메서드 충족.

## C5. RumorGenerator (`locus/session/rumor_generator.py`)
- 책임: 원본 statement + `distortion_degree`(강도별 체인 단계)로 LLM이 **실제 왜곡 텍스트** 생성. confidence = 원본 × (1−degree). graceful.
- 의존: `LLMProvider`. 신규 스키마 `RumorDraft`(structured output).

## C6. PromotionPolicy (`locus/session/promotion.py`, 순수)
- 책임: rumor 목록 + threshold → 승격/강등 결정(순수 함수). support≥threshold→promoted, 미만→demoted. PBT 대상.

## C7. GameMasterService (`locus/session/game_master.py`)
- 책임: 턴 단위 오케스트레이션 — 리전 소문 생성/재생성, support 조정, `advance_turn`(승격/강등 재평가 + turn++), 각 동작을 Timeline에 기록. 리전별 distortion 설정. (Phase 2: Event 연동.)
- 의존: SessionRepository, RumorGenerator, PromotionPolicy, **WorldLoader/GraphRepository**(캐노니컬 읽기 — 원본 Knowledge 조회).

## C8. SessionService (`locus/session/service.py`)
- 책임: 세션 생애주기(start/close/list/get) 얇은 서비스.
- 의존: SessionRepository.

## C9. SessionQueryEngine (`locus/session/query.py`)
- 책임: 세션 컨텍스트 NPC 쿼리 = 캐노니컬 `QueryEngine` 결과(direct/inherited/global Knowledge) + 세션 오버레이(승격 Rumor를 direct처럼, 일반 Rumor 추가) 합성. **propagated/auto-rumor view는 NPC 결과에서 제외**(기획자용으로만). 기존 QueryEngine 무변경.
- 의존: `QueryEngine`(캐노니컬), SessionRepository.

## C10. Session API Router (`api/routers/session.py`)
- 책임: 세션/소문/턴/타임라인/세션쿼리 HTTP 엔드포인트. 서비스는 app.state에서 주입.

## 삭제 (정리)
- **Neo4j 전용 `Rumor` 모델 제거**(AD-R Q6=A): `locus/models/graph.py` `Rumor`, `graph_mapping` `rumor_to_node/node_to_rumor/distorted_from_edges`, `KnowledgeGraph.rumors`, loader/exporter/persist의 rumor 경로, orchestrator `rumors=`. (현재 전부 미사용 `rumors=[]`.)
- **유지**: consensus의 auto-rumor `KnowledgeView`(is_rumor/distortion_degree)와 `ScopeLink.is_rumor`는 Rumor 노드와 무관 → 그대로 둠(기획자용 propagated 분류).
