# Application Design (Consolidated) — Rumor Distortion / Game Session (Phase 1)

요구사항: `inception/requirements/rumor-distortion-requirements.md`. 결정: AD-R Q1–Q6 = 모두 A (SQLAlchemy / ensure_schema / GameMasterService / SessionQueryEngine / advance_turn / SessionRumor 신설 + Neo4j Rumor 삭제).

## 개요
정적 캐노니컬 레이어(Neo4j/OpenSearch) 위에 **동적 게임 세션 레이어(PostgreSQL)**를 추가한다. 세션은 캐노니컬을 **읽기 참조만** 하고, 자신의 Rumor/지지도/승격/타임라인/리전 왜곡 상태를 PostgreSQL에 보관한다. GameMaster가 턴 단위로 소문을 생성/재생성/승격/강등하며 그 변경을 타임라인에 기록한다. NPC 쿼리는 세션 컨텍스트에서 Knowledge(+승격)+Rumor만 본다.

## 컴포넌트 (요약)
- **모델**: GameSession, SessionRumor, RegionDistortion, TimelineEntry (+ SessionStatus/TimelineKind).
- **포트/어댑터**: SessionRepository(포트) · PostgresSessionRepository(SQLAlchemy) · InMemorySessionRepository(mock).
- **로직/서비스**: RumorGenerator(LLM) · PromotionPolicy(순수) · GameMasterService(턴 오케스트레이터) · SessionService(생애주기) · SessionQueryEngine(세션 NPC 쿼리).
- **API**: `api/routers/session.py`.
- **정리**: 미사용 Neo4j `Rumor` 모델/매핑 제거.

자세한 책임/메서드/의존은 `components.md` · `component-methods.md` · `services.md` · `component-dependency.md`.

## 요구사항 ↔ 컴포넌트 매핑
| FR | 컴포넌트 |
|---|---|
| R1 세션 생애주기 | SessionService, SessionRepository, (Postgres/InMemory) |
| R2 소문 생성(왜곡·체인) | RumorGenerator, GameMasterService |
| R3 지지도/승격·강등 | PromotionPolicy, GameMasterService, SessionRepository |
| R4 GameMaster/턴/Timeline | GameMasterService, TimelineEntry, SessionRepository |
| R5 NPC 쿼리 규칙 | SessionQueryEngine (+ 캐노니컬 QueryEngine 재사용) |
| R6 웹 | (S3 단위; API는 Session Router) |
| NFR 포트/격리/인프라 | SessionRepository 포트, PostgreSQL, 캐노니컬 읽기 전용 |

## 단위(Units) 배치 (Units Generation에서 확정)
- **S1**: 모델 + SessionRepository(포트/Postgres/InMemory) + SessionService + 세션 CRUD API + 인프라(PostgreSQL/SQLAlchemy/ensure_schema) + Neo4j Rumor 제거.
- **S2**: RumorGenerator + PromotionPolicy + GameMasterService + SessionQueryEngine + 소문/턴/타임라인/세션쿼리 API.
- **S3**: 웹 UI(세션·생성 버튼·표시·이력/타임라인 열람) + dead buildWiki 정리.

## 설계 원칙
- 포트 추상화(테스트 mock), 레이어 격리(세션→캐노니컬 읽기만), 순수 로직 분리(PromotionPolicy/confidence/timeline), graceful LLM/DB, 회귀 보존(캐노니컬 경로 무변경).
