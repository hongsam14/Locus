# S1 (Session Foundation & Infra) — Functional Design Plan

App Design: `inception/application-design/rumor-session/`. FR-R1 + NFR-R1/2/3 + Neo4j Rumor 제거.

## 작업 체크리스트 (답변 후 생성)
- [x] domain-entities.md — 세션 모델(GameSession/SessionRumor/RegionDistortion/TimelineEntry + enums), Neo4j Rumor 제거 범위
- [x] business-logic-model.md — SessionRepository 포트 계약, SessionService 로직, PostgreSQL 매핑/ensure_schema, in-memory mock
- [x] business-rules.md — 세션 생애주기/불변식/격리/graceful

생성 위치: `aidlc-docs/construction/S1-session-foundation/functional-design/` (2026-06-15). 답변 반영: Q1=B/Q2=A/Q3=A/Q4=A/Q5=A.

---

## 설계 확인 질문 (S1 잔여 결정)

### FD-S1 Q1 — RegionDistortion 기본값 & 존재성
리전별 `distortion_degree`가 아직 설정 안 된 경우?

A) **지연 기본값**: 미설정 시 기본 `0.3`(약한 왜곡)으로 간주, 명시 설정 시 그 값 사용(별도 row 없어도 동작)
B) 세션 시작 시 모든 리전에 기본값 row 생성(명시적)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### FD-S1 Q2 — 세션 시작 시 world 검증
`start_session(world_id)` 시 캐노니컬에 그 world가 존재하는지 검증?

A) **검증함**: Neo4j에 해당 world 노드/데이터 없으면 거부(404/에러). 잘못된 세션 방지
B) 검증 안 함: 임의 world_id 허용(느슨, graceful)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S1 Q3 — PostgreSQL 스키마 스타일(SQLAlchemy)
세션 데이터 컬럼 설계는?

A) **하이브리드**: 핵심 필드는 정규 컬럼(인덱스/쿼리 대상: session_id/world_id/region_id/status/turn/support/promoted/distortion_degree), 가변/중첩(provenance, timeline payload)은 JSON 컬럼
B) 전부 정규화 컬럼(중첩도 별 테이블)
C) 최소 컬럼 + 대부분 JSON(document 스타일)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S1 Q4 — id 생성 & 시간
세션/소문/타임라인 id와 타임스탬프는?

A) id는 기존 `new_id()`(uuid4) 재사용; 타임스탬프는 DB 서버 시간(`created_at` default now)
B) DB 시퀀스/serial id
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S1 Q5 — Neo4j Rumor 제거로 인한 기존 테스트 영향
미사용 `Rumor` 모델/매핑 제거 시 기존 rumor 관련 테스트(직렬화 등)는?

A) 해당 테스트만 삭제/정리(현재 rumors는 빈 값이라 실동작 영향 없음). consensus의 auto-rumor view 테스트는 유지
B) Rumor 모델 유지하되 deprecated 주석만(삭제 안 함)
X) Other (please describe after [Answer]: tag below)

[Answer]: A
