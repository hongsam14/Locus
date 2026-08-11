# Phase 2 — Component Methods

> 메서드 시그니처 + 고수준 목적 + 입출력. **상세 비즈니스 규칙/공식은 per-unit Functional Design**.
> 타입은 Pydantic v2 / Python 3.11. 순수 함수는 부수효과·LLM·DB 비의존.

## C3. dynamics (순수, `locus/session/dynamics.py`)
```python
def distortion_delta(magnitude: float) -> float:
    """magnitude(0~1) → 리전 distortion에 가할 delta(결정론적). FD에서 공식 확정."""

def propagate_delta(
    region_id: str, base_delta: float, connections: list[ConnectionEdge], *, min_weight: float
) -> dict[str, float]:
    """best_path_weights 재사용. {region_id: delta}; 주 대상=base_delta, 이웃=base_delta×weight(>=min_weight). FR-P3.2."""

def apply_deltas(
    current: dict[str, float], deltas: dict[str, float]
) -> dict[str, float]:
    """리전별 현재 distortion에 delta 적용 후 [0,1] clamp. 누적(persistent)도 동일 경로. FR-P3.4."""

def restore_contributions(
    current: dict[str, float], contributions: dict[str, float]
) -> dict[str, float]:
    """해소 시 Event.contributions를 대칭 차감(주 대상+이웃), clamp. FR-P3.6 / AD-P Q5=A."""

def evolve_support(
    rumors: list[SessionRumor], influenced_region_ids: set[str], *, reinforce: float, decay: float
) -> list[SessionRumor]:
    """영향 리전 소문 support↑(reinforce), 그 외 support↓(decay), clamp. FR-P5.1 / CL3.2."""
```

## C2. lifecycle 매핑 (순수, `models.py`)
```python
def default_lifecycle(category: EventCategory) -> EventLifecycle:
    """CATEGORY_DEFAULT_LIFECYCLE 조회. 생성 시 override 가능. CL1.3."""
```

## C4. EventSuggester (LLM, `event_suggester.py`)
```python
class EventDraft(LocusModel):
    region_id: str
    category: EventCategory
    description: str
    magnitude: float

class EventSuggester:
    def __init__(self, llm: LLMProvider) -> None: ...
    def suggest(
        self, *, world_id: str, region_ids: list[str], turn: int, context: str = "", n: int = 1
    ) -> list[EventDraft]:
        """세션 상태 기반 Event 후보 생성(미커밋). graceful: 실패 시 []. FR-P2.2."""
```

## C5. GameMasterService (확장, `game_master.py`)
```python
# --- event lifecycle ---
def create_event(
    self, session_id: str, region_id: str, *,
    category: EventCategory, description: str, magnitude: float,
    lifecycle: EventLifecycle | None = None,  # None → default_lifecycle(category)
) -> SessionEvent:
    """수동 생성(status=ACTIVE). EVENT_CREATED 타임라인. FR-P2.1."""

def suggest_events(self, session_id: str, *, n: int = 1) -> list[SessionEvent]:
    """LLM 제안 → status=SUGGESTED로 영속. FR-P2.2 / AD-P Q3=A,Q4=A."""

def approve_event(self, session_id: str, event_id: str) -> SessionEvent:
    """SUGGESTED→ACTIVE. FR-P2.3."""

def discard_event(self, session_id: str, event_id: str) -> None:
    """SUGGESTED 폐기(삭제). FR-P2.3."""

def resolve_event(self, session_id: str, event_id: str) -> SessionEvent:
    """ACTIVE→RESOLVED + contributions 복원(dynamics.restore_contributions). EVENT_RESOLVED. FR-P3.6."""

def list_events(self, session_id: str, *, status: EventStatus | None = None) -> list[SessionEvent]:
    """조회(닫힌 세션에도 허용)."""

# --- turn (확장) ---
def advance_turn(self, session_id: str, *, promotion_threshold: float = ...) -> TurnResult:
    """시퀀스(FR-P3.3): 활성 Event 수집 → distortion 갱신(주 대상+전파, 누적) →
    주 대상 리전 소문 add/update(보존, FR-P4.1) → support 진화(FR-P5.1) →
    승격/강등 재평가(promotion.evaluate) → one_shot 자동 resolve → 각 변경 타임라인.
    TurnResult(+applied_event_ids, +created_event_ids)."""
```
- **내부 헬퍼(확장)**: `_apply_active_events(session)`(dynamics 호출 + contributions 기록 + repo.set_region_distortion/update_event), `_update_region_rumors(session, region_id)`(보존+add/update; 기존 `_generate_for_region`를 보존형으로 분기).

## C6. SessionRepository (포트 확장)
```python
def create_event(self, event: SessionEvent) -> SessionEvent: ...
def get_event(self, session_id: str, event_id: str) -> SessionEvent | None: ...
def list_events(self, session_id: str, status: str | None = None) -> list[SessionEvent]: ...
def update_event(self, event: SessionEvent) -> SessionEvent: ...   # status/resolved_turn/contributions
def delete_event(self, session_id: str, event_id: str) -> None: ...
```
- PostgreSQL 어댑터 + in-memory mock 둘 다 구현. `ensure_schema`에 `session_events` DDL additive.

## C7. API (확장, `api/routers/session.py`) — 입출력 스키마
- `POST /sessions/{sid}/events` body{region_id, category, description, magnitude, lifecycle?} → SessionEvent.
- `POST /sessions/{sid}/suggest-events` body{n?} → list[SessionEvent](suggested).
- `POST /sessions/{sid}/events/{eid}/approve` → SessionEvent.
- `POST /sessions/{sid}/events/{eid}/resolve` → SessionEvent.
- `DELETE /sessions/{sid}/events/{eid}` → 204.
- `GET /sessions/{sid}/events?status=` → list[SessionEvent].
- `POST /sessions/{sid}/advance-turn` → TurnResult(확장 필드 포함, 호환).

## C8. web (P3) — 메서드(개요)
- `api.ts`: createEvent / suggestEvents / approveEvent / resolveEvent / discardEvent / listEvents / advanceTurn(기존).
- SessionPanel: Event 생성 폼, 제안 목록(승인/폐기), 활성/해소 Event 목록(해소 버튼), per-region distortion 표시, Timeline event 항목.
