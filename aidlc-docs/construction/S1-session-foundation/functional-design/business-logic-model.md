# S1 — Business Logic Model (Functional Design)

Unit **S1**. Ports/adapters + 얇은 라이프사이클 서비스 + 와이어링/인프라.
확정 답: FD-S1 Q1=B / Q2=A / Q3=A / Q4=A / Q5=A. (도메인은 `domain-entities.md`.)

모든 외부 I/O는 포트 뒤(NFR-R1). 오프라인 테스트는 in-memory 어댑터로 mock.

---

## 1. `SessionRepository` 포트 (`locus/session/repository.py`, Protocol)

캐노니컬 `GraphRepository`/`SearchRepository`와 동일한 포트 컨벤션. 기술 비종속.

```python
class SessionRepository(Protocol):
    def ensure_schema(self) -> None: ...           # idempotent DDL (NFR-R3)
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def health_check(self) -> bool: ...

    # sessions
    def create_session(self, world_id: str) -> GameSession: ...   # turn=0, status=OPEN
    def get_session(self, session_id: str) -> GameSession | None: ...
    def list_sessions(self, world_id: str) -> list[GameSession]: ...
    def close_session(self, session_id: str) -> GameSession: ...
    def bump_turn(self, session_id: str) -> int: ...              # turn+=1; returns new turn (S2 사용)

    # rumors
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor: ...
    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None: ...
    def list_rumors(self, session_id: str, region_id: str | None = None) -> list[SessionRumor]: ...
    def delete_rumor(self, session_id: str, rumor_id: str) -> None: ...

    # region distortion
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None: ...
    def get_region_distortion(self, session_id: str, region_id: str) -> float | None: ...
    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]: ...

    # timeline
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry: ...
    def list_timeline(self, session_id: str) -> list[TimelineEntry]: ...   # turn, then created_at
```

계약 노트:
- `upsert_rumor`: `id` 기준 insert-or-update(승격 플래그/ support 갱신에 사용).
- `set_region_distortion`: `(session_id, region_id)` upsert(FD-S1 Q1=B 기본 row 존재 위에 갱신).
- `close_session`: 이미 CLOSED면 멱등(현재 상태 반환). 없는 세션은 에러.
- 모든 rumor/distortion/timeline 메서드는 `session_id` 범위로 격리(세션 간 누수 없음, NFR-R2).

## 2. `PostgresSessionRepository` 어댑터 (`locus/storage/postgres_session_repo.py`)

`SessionRepository`의 **SQLAlchemy** 구현(AD-R Q1=A).

- **연결**: `Engine`(설정 `session_db_url`). `connect`/`disconnect`는 engine dispose 관리. `health_check`=`SELECT 1`.
- **`ensure_schema`**(AD-R Q2=A): idempotent DDL — 4 테이블(`game_sessions`/`session_rumors`/`region_distortions`/`timeline_entries`) + 인덱스를 `CREATE TABLE IF NOT EXISTS`로 생성. CLI `init-schema` 및 앱 부팅 시 호출 가능.
- **컬럼 매핑**(FD-S1 Q3=A 하이브리드):
  - 핵심 필드 → 정규 컬럼. 인덱스: `session_rumors(session_id)`, `session_rumors(session_id, region_id)`, `timeline_entries(session_id)`, `region_distortions` PK=`(session_id, region_id)`.
  - `provenance`(SessionRumor) / `payload`(TimelineEntry) → `JSONB` 컬럼.
  - `id`=애플리케이션 `new_id()`; `created_at`=`server_default=func.now()`(FD-S1 Q4=A).
- **정렬**: `list_timeline` = `ORDER BY turn ASC, created_at ASC`.
- 행↔Pydantic 변환은 어댑터 내부(row→model, model→params). 도메인 모델은 SQLAlchemy 비종속 유지.

## 3. `InMemorySessionRepository` (`locus/session/memory_repo.py`)

오프라인 테스트용 dict 기반 구현. 모든 포트 메서드 충족(NFR-R1, NFR-R5).

- 내부: `dict[session_id → GameSession]`, `dict[session_id → list[SessionRumor]]`, `dict[(session_id, region_id) → degree]`, `dict[session_id → list[TimelineEntry]]`.
- `ensure_schema`/`connect`/`disconnect`=no-op, `health_check`=`True`.
- `created_at`/시간: 결정론 테스트를 위해 단조 증가 카운터 또는 주입 가능한 clock 사용(서버 now 흉내). 정렬 계약(turn, created_at)을 동일하게 보장.
- Postgres 어댑터와 **동일한 행위 계약**(같은 입력→같은 가시 결과)을 테스트로 고정.

## 4. `SessionService` (`locus/session/service.py`)

GameSession 라이프사이클 위 얇은 계층(SessionRepository 위임). **세션 시작 시 world 검증 + 기본 distortion row 생성**을 오케스트레이션.

```python
class SessionService:
    def __init__(self, repo: SessionRepository, loader: WorldLoader): ...

    def start_session(self, world_id: str) -> GameSession:
        # 1) FD-S1 Q2=A: 캐노니컬에 world 존재 검증 (없으면 거부; BR-S1-2)
        # 2) repo.create_session(world_id)  -> turn=0, status=OPEN
        # 3) FD-S1 Q1=B: 그 world의 모든 region에 기본 RegionDistortion row 생성
        #    (degree=DEFAULT_DISTORTION_DEGREE)  -> repo.set_region_distortion(...)
        ...
    def close_session(self, session_id: str) -> GameSession: ...   # status=CLOSED, closed_at=now
    def get_session(self, session_id: str) -> GameSession: ...      # 없으면 에러
    def list_sessions(self, world_id: str) -> list[GameSession]: ...
    def get_timeline(self, session_id: str) -> list[TimelineEntry]: ...
```

- **world 검증 경로**(Q2=A): `WorldLoader`/`GraphRepository`로 그 `world_id`의 Region 노드 존재 확인. region 0개 또는 world 미존재 → `WorldNotFoundError`(API 404). 동일 호출에서 얻은 region 목록을 기본 distortion row 생성에 재사용.
- 세션 시작은 **읽기 전용으로만** 캐노니컬에 접근(NFR-R2).

## 5. API Router (`api/routers/session.py`) — S1 부분

S1은 라이프사이클/타임라인 라우트만(소문/턴/distortion/세션쿼리는 S2 확장). 서비스는 `app.state` 주입.

```
POST /api/session/worlds/{world_id}/sessions          -> GameSession        (start)
GET  /api/session/worlds/{world_id}/sessions          -> list[GameSession]  (history)
GET  /api/session/sessions/{session_id}               -> GameSession
POST /api/session/sessions/{session_id}/close         -> GameSession
GET  /api/session/sessions/{session_id}/timeline      -> list[TimelineEntry]
```
- `start`에서 world 미존재 → 404. 없는 session 조회 → 404.

## 6. 와이어링 / 설정 / 인프라 (NFR-R3)

- **`locus/config/settings.py`**: `session_db_url: str = Field(default="postgresql+psycopg://locus:locus@localhost:5432/locus_session", alias="SESSION_DB_URL")` (정확한 driver/기본값은 Infrastructure Design에서 확정).
- **`api/main.py` app.state**: `session_repo`(PostgresSessionRepository) · `session_service`(SessionService) 주입. 부팅 시 `session_repo.connect()` + `ensure_schema()`. 기존 graph/search/llm/loader 재사용.
- **docker-compose**: `postgres` 서비스 추가(세션 전용 볼륨/env). 기존 Neo4j/OpenSearch 유지. → 상세는 **Infrastructure Design**(이 단위).
- **pyproject**: SQLAlchemy(+ psycopg) 의존성 추가.
- **CLI**(선택): `init-schema`가 `session_repo.ensure_schema()`도 호출(세션 테이블 준비).

## 7. 테스트 모델 (NFR-R5 / NFR-R6)

- **포트 계약 테스트**: `InMemorySessionRepository`로 CRUD/timeline 정렬/distortion upsert/세션 격리 검증.
- **SessionService 테스트**: world 검증(존재/미존재→에러), 기본 distortion row 생성(모든 region degree=0.3), start→close 라이프사이클, 이력 목록.
- **회귀**: Neo4j `Rumor` 제거 후 기존 캐노니컬 테스트 GREEN(FD-S1 Q5=A로 rumor 전용 테스트만 제거). ruff/black/tsc 클린.
- Postgres 어댑터 자체는 live(operator-run) 통합으로 검증, 오프라인은 in-memory.
