# Phase 2 — Application Design (Consolidated)

> Rumor / Game-Session **Phase 2**: Event + Event 상호작용 → 동적 distortion 진화.
> 통합 문서 — 상세는 `components.md` / `component-methods.md` / `services.md` / `component-dependency.md`.
> 결정: AD-P Q1–Q6 = **all A**. 캐노니컬 불변, 세션 레이어 additive, Phase 1 패턴 계승.

## 1. 개요
정적/수동이던 per-region `distortion_degree`를 **Event 기반으로 턴마다 동적 진화**시키고, support 자동 진화 + 이벤트→소문 갱신을 추가한다. 신규 인프라 없음(기존 PostgreSQL 재사용, `session_events` 테이블 additive).

## 2. 컴포넌트 (요약)
| ID | 컴포넌트 | 신규/확장 | 위치 |
|---|---|---|---|
| C1 | SessionEvent (모델) | 신규 | `locus/session/models.py` |
| C2 | EventCategory/Lifecycle/Status enums + 매핑 + TimelineKind 확장 | 신규/확장 | `locus/session/models.py` |
| C3 | dynamics (순수: distortion/전파/support/복원) | 신규 | `locus/session/dynamics.py` |
| C4 | EventSuggester (LLM) + EventDraft | 신규 | `locus/session/event_suggester.py` |
| C5 | GameMasterService (event 라이프사이클 + advance_turn 확장) | 확장 | `locus/session/game_master.py` |
| C6 | SessionRepository (Event CRUD) | 확장 | `repository.py`(+memory/postgres 어댑터) |
| C7 | session API (event 라우트) | 확장 | `api/routers/session.py` |
| C8 | web (SessionPanel Event UI) | 확장 | `web/src/` |

## 3. 핵심 설계 결정
- **순수/부수효과 분리** (AD-P Q1=A): 모든 결정론 계산(distortion delta·토폴로지 전파·support 진화·복원)은 `dynamics.py` 순수 함수 → GameMasterService가 수집·영속. (NFR-P4, PBT)
- **LLM 컴포넌트 격리** (AD-P Q2=A): `EventSuggester`가 `RumorGenerator` 패턴으로 LLM 제안 캡슐화, graceful. distortion/support는 LLM 비의존(NFR-P3).
- **suggest→approve→advance 분리** (AD-P Q3=A): 제안(suggested 영속) → 승인(active) → advance_turn(active 일괄 적용). UI 승인 게이트(CL2.1).
- **status 영속** (AD-P Q4=A): `suggested|active|resolved` — 제안도 DB에 저장해 목록/승인 UI 지원.
- **대칭 복원** (AD-P Q5=A): persistent 해소 시 contributions(주 대상+전파 이웃)를 대칭 차감.
- **단위 분할** (AD-P Q6=A): P1 Event Foundation → P2 Dynamic Engine → P3 Web UI.

## 4. advance_turn 통합 시퀀스 (FR-P3.3)
활성 Event 수집 → distortion 갱신(주 대상 + 토폴로지 전파, persistent 누적·one_shot 1회→resolve) → 주 대상 리전 소문 add/update(기존/ support 보존) → support 자동 진화(영향=강화/그 외=감쇠) → 승격/강등 재평가 → 턴 증가 + Timeline 기록. (services.md 상세)

## 5. 불변식 / NFR 정합
- **레이어 격리(NFR-P2)**: 세션 처리가 캐노니컬을 읽기만; 쓰기는 PostgreSQL 세션 레이어로 한정.
- **회귀(NFR-P5)**: 기존 포트/라우트/모델 시그니처 불변; Phase 1 NPC 쿼리 규칙 불변(FR-P7). 177+14 테스트 GREEN 유지 목표.
- **인프라 무변경(NFR-P6)**: docker-compose 불변; `session_events`는 ensure_schema additive.

## 6. 데이터 모델 변경 (additive)
- 신규: `SessionEvent`(+enums) / `session_events` 테이블.
- 확장: `TimelineKind`(EVENT_*), `TurnResult`(applied/created event ids), `SessionRepository`(Event CRUD).
- mutate: `RegionDistortion`(이벤트가 동적 갱신), `SessionRumor`(support 진화·주 대상 add/update).
- 캐노니컬 모델 변경 없음.

## 7. Out of Scope (Phase 3) — 루머 피드백 루프, Event 간 상호작용/연쇄.

## 8. 다음 단계
Units Generation → per-unit (Functional Design + NFR-light + Code Gen) ×3 → Build & Test.
