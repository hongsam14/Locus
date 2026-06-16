# S1 — Deployment Architecture (PostgreSQL 추가)

Unit **S1**. 기존 Compose 토폴로지에 `postgres`(세션 DB) 1개 추가. 캐노니컬 토폴로지 불변.
확정 답: SI-Q1~6 = 모두 A.

---

## 1. Compose 토폴로지 (변화)

```
locus-net (bridge)
├── 인프라 tier (기본 프로파일: docker compose up -d)
│   ├── neo4j         :7687/:7474   (vol neo4j_*)        [불변]
│   ├── opensearch    :9200         (vol opensearch_data)[불변]
│   └── postgres      :5432         (vol ./data/postgres) ◀── 신규(S1)
│
├── tools 프로파일
│   └── dashboard     :5601                               [불변]
│
└── service 프로파일 (--profile service)
    ├── app  :8000   depends_on: neo4j, opensearch, postgres(healthy) ◀── postgres 의존 추가
    └── web  :3000   depends_on: app(healthy)               [불변]
```

- `postgres`는 **기본 인프라 tier**에 속함 → `docker compose up -d`만으로 세션 DB 기동(neo4j/opensearch와 동일 계층).
- 신규 서비스는 `postgres` 하나뿐. 세션 API는 기존 `app` 컨테이너에 라우터로 추가(컨테이너 증가 없음).

## 2. 기동 순서 / 헬스 게이트 (SI-Q6=A)

```
1. neo4j        → healthcheck(HTTP 7474)        ┐
2. opensearch   → healthcheck(_cluster/health)  ├ 인프라 동시 기동
3. postgres     → healthcheck(pg_isready)       ┘
4. app          → depends_on 모두 service_healthy 후 기동
                  └ command: `python -m locus init-schema`  (Neo4j 제약/인덱스 + 세션 테이블 ensure_schema)
                  └ then: `uvicorn api.main:app`  (부팅 시 session_repo.connect()+ensure_schema 재확인)
                  └ healthcheck: GET /health
5. web          → app healthy 후 기동(nginx, /api → app:8000 프록시)
```

- `app`이 `postgres: service_healthy`를 기다리므로 세션 API는 DB 준비 완료 상태에서만 노출.
- 컨테이너 네트워크에서 `app`은 `SESSION_DB_URL`을 `...@postgres:5432/...`로 override(host=서비스명) — `NEO4J_URI=bolt://neo4j:7687` override와 동일 패턴.

## 3. 볼륨 / 영속 (SI-Q2=A)

| 볼륨 | 마운트 | 비고 |
|---|---|---|
| `./data/postgres` | `/var/lib/postgresql/data` | 바인드마운트, 호스트 영속·검사. `scripts/setup-volumes.sh`에 `./data/postgres` mkdir 추가 |

- 기존 `./data/{neo4j/*, opensearch}` 패턴과 동일. 세션 데이터는 재기동 간 보존(과거 세션 이력 열람, FR-R6.4).

## 4. 환경변수 (.env / env.example 추가)

```
SESSION_DB_URL=postgresql+psycopg://locus:locus@localhost:5432/locus_session
SESSION_DB_USER=locus
SESSION_DB_PASSWORD=locus
SESSION_DB_NAME=locus_session
```
- compose `postgres`는 `POSTGRES_USER/PASSWORD/DB`로 위 값 주입. `app`은 컨테이너용 `SESSION_DB_URL`(host=postgres) override.
- 로컬 전용 기본 자격증명(보안 off 정책 정합); 운영 강화는 범위 외.

## 5. 헬스체크 정의

| 서비스 | 명령 | interval / retries |
|---|---|---|
| postgres | `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` | 10s / 10 |
| app(변화 없음) | `curl -sf http://localhost:8000/health` | 15s / 5 (start_period 30s) |

## 6. 검증(운영자 실행, live)

- `docker compose up -d` → `postgres` healthy 확인(`docker compose ps`).
- `locus init-schema` → 세션 테이블 4종 생성 확인(`\dt` on `locus_session`).
- `--profile service up` → `app`이 postgres healthy 후 기동, `/health` 200.
- 재기동 후 `./data/postgres` 영속 → 이전 세션 이력 유지.

## 7. 롤백 / 영향 격리

- `postgres` 서비스/볼륨 제거만으로 세션 레이어 비활성화 가능(캐노니컬 무영향, NFR-R2).
- 세션 DB 장애는 세션 API에 국한(캐노니컬 빌드/쿼리 경로는 독립 동작, BR-S1-19).
