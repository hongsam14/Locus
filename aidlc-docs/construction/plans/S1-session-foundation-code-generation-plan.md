# S1 (Session Foundation & Infra) — Code Generation Plan

**Single source of truth for S1 code generation.** Brownfield; 코드 위치 = `locus/session/`(신규 패키지) + `locus/storage/`(어댑터) + `api/`(라우터/와이어링). 문서 요약만 `aidlc-docs/construction/S1-session-foundation/code/`.

## Unit Context
- **FR/NFR**: FR-R1(세션 생애주기) + NFR-R1(포트)/R2(격리)/R3(인프라) + 미사용 Neo4j Rumor 제거.
- **Dependencies**: 기존 U1 토대(models/config/storage ports/WorldLoader). S2/S3가 S1에 의존.
- **Contracts 제공**: 세션 도메인 모델, `SessionRepository` 포트(+Postgres/InMemory 어댑터), `SessionService`, 세션 API(라이프사이클/타임라인), `session_db_url` 설정, postgres 인프라.
- **설계 근거**: FD `{domain-entities,business-logic-model,business-rules}.md`, Infra `{infrastructure-design,deployment-architecture}.md`, `nfr/nfr-light.md`.

## Steps

### A. 세션 도메인 + 포트
- [x] **Step 1 — 패키지 골격**: `locus/session/__init__.py`, `tests/session/__init__.py`.
- [x] **Step 2 — 도메인 모델** (`locus/session/models.py`): `SessionStatus`/`TimelineKind` enums, `GameSession`/`SessionRumor`/`RegionDistortion`/`TimelineEntry` (Pydantic v2), `DEFAULT_DISTORTION_DEGREE=0.3`. `new_id()`·`Provenance` 재사용. 범위 검증(degree/support/confidence∈[0,1]). [FD domain-entities]
- [x] **Step 3 — 모델 테스트(+PBT)**: round-trip(hypothesis), 범위 클램프/검증, 기본 enum 값. [NFR-R5]
- [x] **Step 4 — SessionRepository 포트** (`locus/session/repository.py`): Protocol — sessions/rumors/region-distortion/timeline + ensure_schema/connect/disconnect/health_check. [FD business-logic-model §1]

### B. 어댑터
- [x] **Step 5 — InMemory 어댑터** (`locus/session/memory_repo.py`): dict 기반, 정렬 계약(timeline turn→created_at), 세션 격리, 단조 clock. [NFR-R1]
- [x] **Step 6 — 포트 계약 테스트** (`tests/session/test_repository_contract.py`): CRUD, timeline 정렬, distortion upsert/PK, 세션 격리(in-memory). [NFR-R1]
- [x] **Step 7 — Postgres 어댑터** (`locus/storage/postgres_session_repo.py`): SQLAlchemy Core/ORM 동기, 하이브리드 컬럼(핵심=정규+인덱스, provenance/payload=JSONB), `ensure_schema`(CREATE IF NOT EXISTS ×4 + 인덱스), `new_id()`/`server_default=now()`. row↔모델 변환. [Infra SI-Q3/Q4]
- [x] **Step 8 — Postgres 어댑터 테스트** (`tests/storage/test_postgres_session_repo.py`): SQL 구성/매핑 단위(엔진 mock 또는 sqlite-skip); live 통합은 Build&Test(operator).

### C. 서비스 + API
- [x] **Step 9 — SessionService** (`locus/session/service.py`): start(world 검증→404 + 모든 region 기본 distortion seed)/close/get/list/get_timeline. `WorldLoader`/`GraphRepository`로 region 읽기(read-only). [FD §4, BR-S1-2/3]
- [x] **Step 10 — Service 테스트** (`tests/session/test_service.py`): world 존재/미존재, 기본 distortion seed(모든 region degree=0.3), start→close 라이프사이클, 이력. mock repo+loader.
- [x] **Step 11 — API 라우터** (`api/routers/session.py`): start/history/get/close/timeline 5 라우트(`app.state` 주입), world 미존재/없는 세션 → 404. [FD §5]
- [x] **Step 12 — API 테스트** (`tests/session/test_session_api.py`): TestClient + in-memory repo로 라우트 happy/404.
- [x] **Step 13 — 와이어링** (`api/main.py`): `session_repo`(Postgres)+`session_service` app.state 주입, 부팅 시 connect+ensure_schema. `locus/config/settings.py` `session_db_url` 추가.

### D. 인프라 + 정리
- [x] **Step 14 — 인프라 파일**: `docker-compose.yml` `postgres:16-alpine` 서비스(기본 tier, healthcheck, 바인드마운트) + `app` `depends_on` postgres; `scripts/setup-volumes.sh` `./data/postgres`; `pyproject.toml` `sqlalchemy>=2`/`psycopg[binary]>=3`; `env.example` `SESSION_DB_*`. [Infra Design]
- [x] **Step 15 — Neo4j Rumor 제거**: `locus/models/graph.py` `Rumor`; `graph_mapping.py` `rumor_to_node`/`node_to_rumor`/`distorted_from_edges`; `models/io.py` `Rumor` import+`KnowledgeGraph.rumors`; loader/exporter/persist/orchestrator의 rumor 경로. consensus auto-rumor view·`ScopeLink.is_rumor`는 **유지**. [FD §7, BR-S1-20/21]
- [x] **Step 16 — Rumor 제거 회귀 정리**: `tests/`에서 Neo4j Rumor 직렬화/매핑 **전용** 테스트만 삭제/수정. consensus auto-rumor view 테스트 유지. [FD-S1 Q5=A, NFR-R6]
- [x] **Step 17 — 문서**: `construction/S1-session-foundation/code/code-summary.md`.

**Verification**(작성만; 실행은 Build&Test): 전체 pytest GREEN, ruff/black clean, 외부 호출(Postgres/Neo4j/LLM) mock 오프라인. 기존 테스트 회귀 0.

## FR/NFR Coverage
- FR-R1.1 생애주기 → Step 9,11 · FR-R1.2 참조만 → Step 2,9 · FR-R1.3 PostgreSQL → Step 7,14.
- NFR-R1 포트 → Step 4,5,7 · NFR-R2 격리 → Step 9,15 · NFR-R3 인프라 → Step 14 · NFR-R5 PBT → Step 3 · NFR-R6 회귀 → Step 15,16.

## Notes
- 테스트는 작성만(실행은 Build&Test). Postgres 어댑터 자체는 live(operator)로 검증, 오프라인은 in-memory.
- 스타일: black(line 100), ruff, 타입 힌트, Pydantic v2. SQLAlchemy 2.0 스타일.
- S2 의존 계약 안정화: 포트 시그니처/모델 필드는 component-methods.md와 일치 유지.
