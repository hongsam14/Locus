# S1 (Session Foundation) — Infrastructure Design Plan

NFR-R3: 세션 전용 **PostgreSQL**를 기존 공유 스택(Neo4j/OpenSearch)에 **추가**한다. 캐노니컬 인프라는 불변.
이미 결정(전 Unit 공유, `construction/shared-infrastructure.md`): **로컬 + Docker Compose**, 보안 플러그인 off(로컬 전용), **바인드마운트 볼륨**(`./data/*`), `.env`/환경변수 구성, 프로파일(기본=인프라 / `service`=app+web / `tools`=dashboard). 아래 PostgreSQL 한정 선택만 확인합니다.

> N/A(범위 외, 공통): 메시징/큐, LB/게이트웨이, 오토스케일, 멀티테넌시, 매니지드 DB, HA/복제.

---

## Questions

## Question SI-Q1 — PostgreSQL 이미지/버전 핀
세션 DB 이미지는?

A) **`postgres:16-alpine`** 핀 — 경량·안정 LTS, 다른 핀(neo4j:5.15 / opensearch:2.13.0)과 동일한 명시적 핀 정책 (Recommended)
B) `postgres:15-alpine`
C) `postgres:16`(non-alpine)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SI-Q2 — 데이터 영속(볼륨)
세션 데이터 보존 방식은?

A) **바인드마운트** `./data/postgres` — Neo4j/OpenSearch와 동일 패턴, `setup-volumes.sh`에 디렉터리 추가, 호스트 영속·검사 가능 (Recommended — 기존 정합)
B) 명명 볼륨(`postgres_data`) — 단순하나 다른 서비스와 패턴 불일치
C) 임시(볼륨 없음) — 재기동 시 세션 초기화
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SI-Q3 — Python 드라이버 / SQLAlchemy 모드
SQLAlchemy 어댑터의 DB 드라이버는?

A) **psycopg3(`psycopg`) + SQLAlchemy 동기** — `postgresql+psycopg://...`. 기존 코드가 동기 오케스트레이터(Neo4j/OpenSearch 동기)와 정합, 최신 드라이버 (Recommended)
B) psycopg2-binary + 동기 — `postgresql+psycopg2://...`(전통적, 레거시)
C) asyncpg + SQLAlchemy async — 비동기(기존 동기 패턴과 불일치, 과설계)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SI-Q4 — 자격증명 / DB 이름 / env
세션 DB 접속 구성은?

A) **단일 `SESSION_DB_URL`** env(기본 `postgresql+psycopg://locus:locus@localhost:5432/locus_session`), compose는 `POSTGRES_USER/PASSWORD/DB`로 동일 값 주입; 컨테이너 네트워크에선 host=`postgres`로 override (Recommended — config는 URL 하나, NFR-R1 정합)
B) 분리 env(`SESSION_DB_HOST/PORT/USER/PASSWORD/NAME`)로 구성 후 URL 조립
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SI-Q5 — 스키마 부트스트랩 시점
세션 테이블(`ensure_schema`) 생성 시점은?

A) **앱 시작 시 + `locus init-schema`** 둘 다 호출 — 기존 SchemaInitializer 패턴과 동일(app command가 `init-schema` 실행), idempotent (Recommended)
B) 앱 시작 시에만(자동)
C) `init-schema`에서만(수동)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SI-Q6 — app 서비스의 postgres 의존
compose `app`(service 프로파일)이 postgres에 의존하나?

A) **`depends_on: postgres (service_healthy)`** 추가 + 컨테이너 네트워크 `SESSION_DB_URL` override(host=postgres). 세션 API가 DB 준비 후 기동 (Recommended)
B) 의존 안 함(느슨) — app은 DB 미가용 시에도 기동, 세션 경로만 실패(캐노니컬 경로는 동작)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `construction/S1-session-foundation/infrastructure-design/infrastructure-design.md` — 논리→인프라 매핑(postgres 서비스/포트/이미지/env/볼륨/드라이버/스키마)
- [ ] `construction/S1-session-foundation/infrastructure-design/deployment-architecture.md` — Compose 토폴로지 변화·기동 순서·헬스체크
- [ ] `construction/shared-infrastructure.md` 갱신 — 공유 스택에 PostgreSQL 추가(세션 레이어)

## Execution Checklist
- [x] 1. SI-Q1~6 반영 (all A)
- [x] 2. infrastructure-design.md 작성
- [x] 3. deployment-architecture.md 작성
- [x] 4. shared-infrastructure.md 갱신
- [ ] 5. (코드 단계 입력) docker-compose `postgres` 서비스 + `setup-volumes.sh` + pyproject 의존 + config `session_db_url`

생성: `construction/S1-session-foundation/infrastructure-design/{infrastructure-design,deployment-architecture}.md` + `shared-infrastructure.md` 갱신 (2026-06-15).
