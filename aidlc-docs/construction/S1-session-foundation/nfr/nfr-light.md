# S1 — NFR (Requirements + Design, Light)

Unit **S1**. NFR-R1~R6은 요구사항에 명시되어 FD/Infra에 이미 반영됨 → **light 단일 노트**(별도 질문 없음). 아래는 각 NFR을 측정 가능한 설계 결정·검증 방법으로 고정한다.

| NFR | 요구 | S1 설계 결정 (근거) | 검증 |
|---|---|---|---|
| **NFR-R1** 포트 추상화 | 세션 영속화는 `SessionRepository` 포트 뒤 + in-memory mock | C2 포트(Protocol), C3 Postgres 어댑터, C4 InMemory 어댑터. 도메인/서비스는 SQLAlchemy 비종속. (FD §1~3) | 포트 계약 테스트(in-memory), 서비스 테스트는 mock repo |
| **NFR-R2** 레이어 격리 | 세션은 캐노니컬을 읽기 참조만; 세션 쓰기가 캐노니컬 불변 | 세션 레코드는 캐노니컬 id 문자열만 보유(복사 없음). `SessionService`의 world 검증/region 조회는 read-only. postgres↔neo4j 분리 스택. (BR-S1-9/14/15) | 코드 리뷰 + 테스트: 세션 동작이 graph_repo write 미호출 |
| **NFR-R3** 인프라 | docker-compose에 PostgreSQL 추가, 기존 스택 유지 | `postgres:16-alpine` 기본 인프라 tier, 바인드마운트, `ensure_schema` idempotent. (Infra Design) | `docker compose up -d` + `pg_isready` healthy(operator) |
| **NFR-R4** LLM graceful | Rumor 생성 LLM 실패 시 진행 계속 | **S2 범위**(생성 로직). S1은 graceful 조회 계약(없는 항목 → None/빈 목록)만. (BR-S1-18) | S2에서 검증; S1은 조회 graceful 테스트 |
| **NFR-R5** 결정론/PBT | 순수 로직 + 포트 분리, PBT(Partial) | 모델 직렬화 round-trip + 범위 검증(degree/support/confidence∈[0,1]) PBT 대상. (승격/confidence 계산 순수 로직은 S2) | hypothesis round-trip + 범위 PBT |
| **NFR-R6** 회귀 | 캐노니컬/기존 테스트 GREEN, ruff/black/tsc 클린 | Neo4j Rumor 제거는 미사용 경로만(FD-S1 Q5=A). consensus auto-rumor view 유지. | 전체 pytest GREEN + ruff/black clean(Build&Test) |

## Design 결정 요약 (light)
- **커넥션/세션 관리**: SQLAlchemy 동기 `Engine`, 요청 단위 `Session`/`begin()` 트랜잭션. 풀러(pgbouncer) 미사용(로컬 MVP). (Infra SI-Q3=A)
- **트랜잭션 경계**: 각 repository 메서드 1 트랜잭션(원자적 upsert/append). 멀티스텝 오케스트레이션(예: start_session의 create+seed)은 서비스 레벨에서 순차 호출(부분 실패 시 graceful — 세션은 생성되되 누락 distortion은 재시드 가능).
- **성능**: 인덱스 `session_rumors(session_id[,region_id])`, `timeline_entries(session_id)`로 리전/세션 조회 O(log n). 세션 규모는 로컬 단판 수준 — 별도 캐시 없음.
- **보안**: 로컬 전용 기본 자격증명(보안 off 정책 정합). Security Baseline 확장 OFF.

## N/A (범위 외)
HA/복제, 백업 자동화, 커넥션 풀러, 멀티테넌시, 세션 검색 인덱싱(Q9=X). 운영 강화는 후속.
