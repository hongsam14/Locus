# Application Design Plan — Rumor Distortion / Game Session (Phase 1)

요구사항: `inception/requirements/rumor-distortion-requirements.md`. 신규 세션 레이어 컴포넌트/서비스 설계.

## 작업 체크리스트 (답변 후 생성)
- [x] components.md — 세션 레이어 컴포넌트 정의/책임/인터페이스
- [x] component-methods.md — 메서드 시그니처(상세 규칙은 per-unit FD)
- [x] services.md — 서비스(오케스트레이션) 정의
- [x] component-dependency.md — 의존/통신/데이터 흐름
- [x] application-design.md — 통합본
(산출물: `aidlc-docs/inception/application-design/rumor-session/`)

---

## 설계 확인 질문 (컴포넌트/서비스 수준)

### AD-R Q1 — PostgreSQL 접근 기술
`SessionRepository` PostgreSQL 어댑터를 무엇으로 구현하나요?

A) **SQLAlchemy(Core/ORM)** — 모델/마이그레이션 편의, 풍부한 생태계
B) **psycopg(3) 직접 SQL** — 경량, 의존성 최소, 명시적 SQL
C) **SQLModel**(Pydantic+SQLAlchemy) — 기존 Pydantic 모델과 친화
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-R Q2 — 세션 스키마 부트스트랩
세션 테이블 생성/마이그레이션은?

A) 앱/CLI 시작 시 idempotent `ensure_schema`(기존 Neo4j/OpenSearch SchemaInitializer 패턴과 동일)
B) Alembic 등 정식 마이그레이션 도구 도입
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-R Q3 — GameMaster 서비스 형태
GameMaster(턴 단위 생성/재생성/승격/강등 오케스트레이션)는?

A) **단일 오케스트레이터 서비스**(`GameMasterService`)가 RumorGenerator·승격로직·Timeline을 조율(기존 PipelineOrchestrator 패턴)
B) 기능별 분리(생성/승격/타임라인 각각 서비스) + 얇은 파사드
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-R Q4 — 세션-aware NPC 쿼리 구현 위치
NPC 쿼리(Knowledge+승격+Rumor, propagated 비노출)는?

A) **신규 `SessionQueryEngine`**이 기존 `QueryEngine`(캐노니컬 consensus) + 세션 오버레이(Rumor/승격)를 합성. 기존 QueryEngine 무변경
B) 기존 `QueryEngine`에 옵션 `session_id` 추가해 내부 분기
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-R Q5 — "턴" 진행 모델
GameMaster 턴은 어떻게 진행되나요?

A) **명시적 `advance_turn` 액션**: 호출 시 현재 상태로 승격/강등 재평가 + 타임라인 1엔트리. 소문 "생성" 버튼은 별도 액션(생성도 타임라인 기록). 즉 액션마다 타임라인 누적, turn 카운터는 advance 시 증가
B) 모든 액션이 곧 1턴(생성=턴, 조정=턴)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-R Q6 — 세션 Rumor와 캐노니컬 Rumor 모델 관계
요구사항 데이터모델의 `SessionRumor`(PostgreSQL)와 기존 `Rumor`(Neo4j 모델, 현재 미사용 생성)의 관계는?

A) **세션 전용 모델 신설**(`SessionRumor` 등 `locus/session/`), 기존 Neo4j `Rumor` 노드 경로는 이 기능에서 사용 안 함(그대로 둠)
B) 기존 `Rumor` 모델을 재사용하되 저장만 PostgreSQL로
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 그리고 neo4j 전용 Rumor 모델은 삭제.
