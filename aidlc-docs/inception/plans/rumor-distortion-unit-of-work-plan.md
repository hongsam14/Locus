# Unit of Work Plan — Rumor Distortion / Game Session (Phase 1)

App Design(`inception/application-design/rumor-session/`) 기반 단위 분해. 3-unit 분할은 Workflow Planning·App Design에서 확정됨; 아래는 경계 최종 확인.

## 분해 (제안 — 확정본)
- **S1 — Session Foundation & Infra**
  - 세션 도메인 모델(GameSession/SessionRumor/RegionDistortion/TimelineEntry + enums).
  - `SessionRepository` 포트 + `PostgresSessionRepository`(SQLAlchemy, `ensure_schema`) + `InMemorySessionRepository`(mock).
  - `SessionService`(생애주기) + 세션 CRUD API(`api/routers/session.py`의 세션/타임라인 부분).
  - 인프라: docker-compose PostgreSQL, 설정(`session_db_url`), SQLAlchemy 의존성. **Infrastructure Design 여기.**
  - 정리: 미사용 Neo4j `Rumor` 모델/매핑 제거.
  - FR: R1, NFR-R1/2/3.
- **S2 — Rumor Engine**
  - `RumorGenerator`(LLM 강도 체인) + `PromotionPolicy`(순수) + `GameMasterService`(generate/regenerate/adjust/set-distortion/advance_turn + Timeline) + `SessionQueryEngine`(세션 NPC 쿼리).
  - API: 소문 생성/재생성/support/distortion/advance-turn/세션쿼리.
  - FR: R2, R3, R4, R5.
- **S3 — Web UI**
  - 세션 생성/선택/종료, 리전 "소문 생성" 버튼, support/distortion 표시, 승격 상태, 과거 세션·타임라인 열람.
  - dead `buildWiki()` 정리.
  - FR: R6.
- **빌드 순서**: S1 → S2 → S3 (S2는 S1 포트/모델, S3는 S2 API 의존).

## 작업 체크리스트 (생성 산출물)
- [x] `unit-of-work.md` (rumor-session) — 단위 정의/책임/코드 위치
- [x] `unit-of-work-dependency.md` — 의존 매트릭스
- [x] `unit-of-work-story-map.md` — FR↔단위 매핑(본 사이클 User Stories SKIP → FR 기준)
(산출물: `aidlc-docs/inception/application-design/rumor-session/`)

---

## 확인 질문

### UOW-R Q1 — 단위 경계 확정
위 3-unit 분할(S1 Foundation+Infra / S2 Rumor Engine / S3 Web)과 빌드 순서(S1→S2→S3)로 진행할까요?

A) 그대로 진행
B) 조정 필요(아래에 어떻게 나눌지 기술 — 예: SessionQueryEngine을 별도 단위로, 또는 S1/S2 통합)
X) Other (please describe after [Answer]: tag below)

[Answer]: 
