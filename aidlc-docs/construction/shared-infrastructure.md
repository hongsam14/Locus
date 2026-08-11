# Shared Infrastructure — Locus (전 Unit 공유)

U1 Foundation에서 정의된 인프라는 모든 Unit이 공유한다. 이후 Unit은 새 인프라를 추가하지 않고 이 스택 위에서 동작(U10 Web UI만 정적 프론트 서빙 추가).

## 공유 스택
| 서비스 | 이미지/런타임 | 포트 | 볼륨 | 용도 |
|---|---|---|---|---|
| neo4j | `neo4j:5` (Community) | 7687, 7474 | `neo4j_data` | 캐노니컬 그래프(토폴로지+온톨로지+Wiki) |
| opensearch | `opensearchproject/opensearch:2` (단일노드, 보안 off) | 9200 | `opensearch_data` | 하이브리드 검색(벡터+BM25) |
| **postgres** (S1+) | `postgres:16-alpine` | 5432 | `./data/postgres` (바인드) | **게임 세션 레이어**(SessionRepository: 세션/Rumor/distortion/timeline) |
| app | Python 3.11 + uvicorn | 8000 | — | 코어/서비스/API(authoring+serving+session) |
| (U10) web | Node/정적 빌드 | 5173/정적 | — | React 검토·편집 UI(차순) |
| 외부 | OpenAI API | — | — | LLM/VLM/Embedding |

## 공유 규약
- 단일 OpenSearch 인덱스 `locus_search` + `world_id` 필터(ND1-Q2=A).
- Neo4j 단일 그래프 + `world_id` 파티션; Wiki는 `__realworld__`.
- 모든 서비스는 `.env`/환경변수로 구성(ID/NFR1-Q6=A).
- SchemaInitializer가 제약/인덱스 부트스트랩(앱 시작 또는 `locus init-schema`).

## Compose 구성 (개선, Enola 패턴 참고)
- **프로파일**: 기본=인프라(neo4j/opensearch); `service`=app(uvicorn)+web(nginx); `tools`=OpenSearch Dashboards.
- **볼륨**: 바인드마운트 `./data/{neo4j/data, neo4j/logs, opensearch}` (호스트 영속·검사). `./scripts/setup-volumes.sh`로 생성.
- **버전 핀**: `neo4j:5.15-community`, `opensearchproject/opensearch:2.13.0`.
- **Neo4j APOC**: `NEO4J_PLUGINS=["apoc"]`(부팅 시 자동 다운로드) + apoc export/import 허용 + `dbms_security_procedures_unrestricted=apoc.*`. import/plugins 바인드마운트(`./data/neo4j/{import,plugins}`). (MVP 코드는 plain Cypher만 사용 — APOC는 향후 export/import·고급 절차용 사전 탑재.)
- **app**: `init-schema` 후 `uvicorn api.main:app` 실행, `/health` 헬스체크, `OPENAI_API_KEY` 필요.
- **web**: `web/Dockerfile`(node build → nginx) + `/api` 프록시 → app:8000.

## Rumor / Game Session 사이클 — PostgreSQL 추가 (S1, 2026-06-15)
- **신규 인프라**: 세션 전용 `postgres:16-alpine`(SI-Q1=A) — 캐노니컬(Neo4j/OpenSearch) 불변, **추가(additive)**. 상세: `construction/S1-session-foundation/infrastructure-design/`.
- **프로파일**: 기본 인프라 tier(neo4j/opensearch와 함께 `docker compose up -d`로 기동).
- **볼륨**: 바인드마운트 `./data/postgres`(SI-Q2=A) — `setup-volumes.sh`에 추가.
- **드라이버/연결**: SQLAlchemy 동기 + psycopg3, 단일 env `SESSION_DB_URL`(SI-Q3/Q4=A). 컨테이너 네트워크에선 host=`postgres` override.
- **스키마**: `PostgresSessionRepository.ensure_schema`(idempotent) — `init-schema` + 앱 부팅 둘 다(SI-Q5=A).
- **의존**: `app`이 `postgres: service_healthy` 대기(SI-Q6=A). pyproject에 `sqlalchemy`/`psycopg` 추가.
- **격리**: 세션 쓰기가 캐노니컬을 변경하지 않음(NFR-R2). postgres 장애는 세션 경로에 국한.

## Unit별 인프라 영향
- U2~U9: 새 인프라 없음(공유 스택 사용).
- U10(Web UI): 정적 프론트 빌드 서빙(개발 시 Vite dev server, 배포 시 정적 파일).
- S1(세션): PostgreSQL 추가(위). S2/S3: 새 인프라 없음(S1 스택 사용).

## N/A (전 Unit 공통, 범위 외)
메시징/큐, 로드밸런서, API 게이트웨이, 오토스케일, 멀티테넌시, 클라우드 매니지드 서비스, 고가용성.
