# Phase 2 — Components

> 입력: rumor-phase2-requirements.md + application-design-plan.md (AD-P Q1–Q6 = all A).
> 모든 신규/확장은 **세션 레이어(PostgreSQL) additive**. 캐노니컬(Neo4j/OpenSearch) 불변. 상세 비즈니스 규칙·공식은 per-unit Functional Design.

## 신규 컴포넌트

### C1. SessionEvent (도메인 모델)
- **위치**: `locus/session/models.py` (additive).
- **책임**: 한 리전에 영향을 주는 사건의 세션-스코프 표현. 캐노니컬 노드는 id로 참조만.
- **인터페이스(필드, 최종은 FD)**: `id`, `session_id`, `region_id`(주 대상), `category`(EventCategory), `description`, `magnitude`(0~1), `lifecycle`(EventLifecycle), `status`(EventStatus), `created_turn`, `resolved_turn`, `contributions`(dict: region_id→누적 적용 delta, 복원용), `provenance`(생성자 gm|llm).
- **불변식**: magnitude∈[0,1]; status 전이는 suggested→active→resolved (또는 active 직행).

### C2. Enums & 매핑 (additive in `models.py`)
- **EventCategory**: 사전 정의 분류(예: WAR, DISASTER, PLAGUE, FESTIVAL, …; 최종 집합은 FD).
- **EventLifecycle**: `ONE_SHOT` | `PERSISTENT`.
- **EventStatus**: `SUGGESTED` | `ACTIVE` | `RESOLVED` (AD-P Q4=A).
- **CATEGORY_DEFAULT_LIFECYCLE**: category→기본 lifecycle 매핑(예: disaster/festival=ONE_SHOT, war/plague=PERSISTENT). 생성 시 override 가능 (CL1.3).
- **TimelineKind 확장**: `EVENT_CREATED`, `EVENT_APPLIED`, `EVENT_RESOLVED` 추가(기존 값 불변).

### C3. dynamics (순수 로직 모듈) — AD-P Q1=A
- **위치**: `locus/session/dynamics.py` (신규, `promotion.py` 패턴 계승; 부수효과 없음, LLM/DB 비의존).
- **책임**: Event→distortion 변화·토폴로지 전파·support 자동 진화·accumulated 복원의 **결정론적 순수 계산**.
- **핵심 인터페이스(시그니처는 component-methods.md)**:
  - distortion delta = f(magnitude).
  - 토폴로지 전파: `best_path_weights(region_id, connections)` 재사용 → 이웃별 delta = base_delta × weight (임계값 이상만).
  - support 진화: 영향 리전 소문 강화↑ / 그 외 감쇠↓.
  - 복원: Event.contributions를 대칭 차감(주 대상 + 전파 이웃) (AD-P Q5=A).

### C4. EventSuggester (LLM 컴포넌트) — AD-P Q2=A
- **위치**: `locus/session/event_suggester.py` (신규, `RumorGenerator` 패턴 계승).
- **책임**: 세션 상태(리전·소문·턴)를 받아 LLM으로 Event 후보(`EventDraft`, 미커밋)를 제안. **graceful**: 실패 시 빈 리스트.
- **의존**: `LLMProvider` 포트(주입).
- **신규 타입**: `EventDraft`(region_id, category, description, magnitude) — 영속 전 후보.

## 확장 컴포넌트

### C5. GameMasterService (확장) — `locus/session/game_master.py`
- **추가 책임**: Event 라이프사이클(생성/제안/승인/해소) + advance_turn 통합 시퀀스(이벤트 적용→distortion 갱신→소문 add/update→support 진화→승격/강등→타임라인).
- **신규 메서드**: `create_event`, `suggest_events`, `approve_event`, `discard_event`, `resolve_event`; `advance_turn` 확장.
- **확장 타입**: `TurnResult`에 `applied_event_ids`/`created_event_ids` 추가(기존 필드 유지).
- **불변식 유지**: 캐노니컬 읽기 참조만(NFR-P2); 닫힌 세션 쓰기 금지(SessionClosedError).

### C6. SessionRepository (포트 확장) — `repository.py` (+`memory_repo.py`, `postgres_session_repo.py`)
- **추가 책임**: Event CRUD. 기존 시그니처 불변(additive).
- **신규 메서드**: `create_event`, `get_event`, `list_events(session_id, status?)`, `update_event`, `delete_event`.
- **스키마**: `postgres_session_repo.ensure_schema`에 `session_events` 테이블 additive(JSONB-variant for contributions/provenance, Phase 1 하이브리드 패턴 계승). `init-schema`가 함께 생성.

### C7. session API (확장) — `api/routers/session.py`
- **추가 라우트(additive)**:
  - `POST   /api/session/sessions/{sid}/events` — 수동 Event 생성(active).
  - `POST   /api/session/sessions/{sid}/suggest-events` — LLM 제안 생성(suggested, 영속).
  - `POST   /api/session/sessions/{sid}/events/{eid}/approve` — suggested→active.
  - `POST   /api/session/sessions/{sid}/events/{eid}/resolve` — active→resolved(+복원).
  - `DELETE /api/session/sessions/{sid}/events/{eid}` — suggested 폐기.
  - `GET    /api/session/sessions/{sid}/events?status=` — 목록.
  - (기존 `POST …/advance-turn` 동작 확장 — 시그니처 호환).

### C8. web (P3 단위) — `web/src/`
- **확장**: SessionPanel(Event 생성 폼·LLM 제안 승인·Event 목록/해소·distortion 시각화·Timeline event 항목), `api.ts`(신규 메서드), `types`(SessionEvent/EventDraft/EventCategory/…).

## 단위 매핑 (AD-P Q6=A)
- **P1 Event Foundation**: C1, C2, C6, C7(수동 create/list/resolve·delete), TimelineKind 확장.
- **P2 Dynamic Engine**: C3, C4, C5, C7(suggest/approve + advance-turn 확장), TurnResult 확장.
- **P3 Web UI**: C8.
