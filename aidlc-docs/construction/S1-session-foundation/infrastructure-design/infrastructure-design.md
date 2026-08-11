# S1 — Infrastructure Design (PostgreSQL 세션 레이어)

Unit **S1**. NFR-R3: 세션 전용 **PostgreSQL**를 기존 공유 스택에 추가. 캐노니컬(Neo4j/OpenSearch)은 불변.
확정 답: **SI-Q1=A**(`postgres:16-alpine`)/**Q2=A**(바인드마운트 `./data/postgres`)/**Q3=A**(psycopg3 + SQLAlchemy 동기)/**Q4=A**(단일 `SESSION_DB_URL`)/**Q5=A**(앱 시작 + `init-schema` 둘 다)/**Q6=A**(`app` → postgres `service_healthy` 의존).

---

## 1. 논리 → 인프라 매핑

| 논리 컴포넌트(App Design) | 인프라 매핑 |
|---|---|
| `PostgresSessionRepository`(C3) | `postgres` 컨테이너(SQLAlchemy `Engine` 대상) |
| `SessionRepository` 포트(C2) | 인프라 비종속 — 어댑터만 postgres 의존 |
| `InMemorySessionRepository`(C4) | 인프라 없음(프로세스 내, 오프라인 테스트) |
| `ensure_schema`(idempotent DDL) | 앱 부팅 + `locus init-schema`(SI-Q5=A) |
| 세션 API(C10) | 기존 `app`(uvicorn) 컨테이너에 라우터 추가(신규 서비스 없음) |

세션 레이어는 **단일 신규 인프라(PostgreSQL)** 만 추가한다. 앱/웹은 기존 컨테이너 재사용.

## 2. `postgres` 서비스 정의 (docker-compose)

| 항목 | 값 | 근거 |
|---|---|---|
| image | `postgres:16-alpine` | SI-Q1=A, 명시 핀 정책(neo4j:5.15 / opensearch:2.13.0과 동일) |
| container_name | `locus-postgres` | 명명 규칙 정합 |
| ports | `5432:5432` | 표준 PG 포트 |
| env | `POSTGRES_USER=${SESSION_DB_USER:-locus}`, `POSTGRES_PASSWORD=${SESSION_DB_PASSWORD:-locus}`, `POSTGRES_DB=${SESSION_DB_NAME:-locus_session}` | SI-Q4=A, URL과 동일 값 |
| volume | `./data/postgres → /var/lib/postgresql/data` (바인드마운트) | SI-Q2=A, Neo4j/OpenSearch 패턴 정합 |
| healthcheck | `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` (interval 10s, retries 10) | `service_healthy` 의존 게이트 |
| restart | `unless-stopped` | 기존 서비스 정합 |
| networks | `locus-net` | 공유 네트워크 |
| profiles | **기본(인프라 tier)** — neo4j/opensearch와 함께 `docker compose up -d`로 기동 | 세션 DB는 인프라 |

## 3. 연결 구성 (SI-Q3/Q4=A)

- **드라이버**: psycopg3(`psycopg`), SQLAlchemy **동기** 엔진(`create_engine`). URL 스킴 `postgresql+psycopg://`. 기존 동기 오케스트레이터(Neo4j/OpenSearch 동기)와 정합.
- **단일 env**: `SESSION_DB_URL`
  - 호스트 실행 기본값: `postgresql+psycopg://locus:locus@localhost:5432/locus_session`
  - 컨테이너 네트워크(app 서비스): `SESSION_DB_URL=postgresql+psycopg://locus:locus@postgres:5432/locus_session` 로 **override**(host=`postgres`) — `NEO4J_URI`/`OPENSEARCH_URL` override와 동일 패턴.
- `locus/config/settings.py`: `session_db_url: str = Field(default="postgresql+psycopg://locus:locus@localhost:5432/locus_session", alias="SESSION_DB_URL")`.
- 비밀값은 `.env`(`env.example`에 `SESSION_DB_*` 추가). 로컬 전용 기본값(보안 off 정책 정합).

## 4. 스키마 부트스트랩 (SI-Q5=A)

- `PostgresSessionRepository.ensure_schema()` = idempotent DDL(`CREATE TABLE IF NOT EXISTS` × 4 + 인덱스). FD `business-logic-model.md` §2.
- 호출 지점 **둘 다**(기존 SchemaInitializer 패턴 정합):
  1. `app` 컨테이너 command: `python -m locus init-schema` 단계에서 세션 스키마도 생성.
  2. `api/main.py` 부팅 시 `session_repo.connect()` + `ensure_schema()`.
- 여러 번 호출 안전(BR-S1-17). 기존 데이터 비파괴.

## 5. 의존성 (pyproject)

- 추가: `sqlalchemy>=2.0,<3`, `psycopg[binary]>=3.1,<4`. (런타임 `dependencies`)
- 캐노니컬 의존(neo4j/opensearch-py/fastapi)은 그대로.

## 6. 영향 받지 않는 것 (격리, NFR-R2)

- Neo4j/OpenSearch 서비스·볼륨·env·헬스체크 변경 **없음**.
- PostgreSQL 미가용이 캐노니컬 빌드/쿼리 경로를 막지 않음(분리 기동; BR-S1-19). 단, SI-Q6=A로 `app`은 postgres healthy를 기다린 후 기동(세션 API 안정성 우선).

## 7. N/A (범위 외)

매니지드 DB(RDS 등), 복제/HA, 커넥션 풀러(pgbouncer), 백업 자동화, TLS/인증 강화 — 로컬 단일 인스턴스 MVP 범위 외. 운영 강화는 Operations/후속 사이클.
