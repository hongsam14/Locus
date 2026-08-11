# Phase 2 — Requirement → Unit Story Map

> User Stories는 SKIP(기존 persona/스토리가 GameMaster/디자이너 actor 커버). 여기서는 **요구사항(FR-P*/NFR-P*)을 단위에 매핑**해 전수 할당을 보장.

## Functional Requirements
| 요구사항 | 단위 | 비고 |
|---|---|---|
| FR-P1.1 Event 저장(SessionEvent) | P1 | 모델 + 테이블 |
| FR-P1.2 Event 속성/필드 | P1 | category/magnitude/lifecycle/status/contributions/provenance |
| FR-P1.3 SessionRepository Event CRUD + ensure_schema | P1 | postgres + memory |
| FR-P2.1 수동 Event 생성 | P1 | create_event + POST /events |
| FR-P2.2 LLM Event 제안(매 턴) | P2 | EventSuggester + suggest_events |
| FR-P2.3 suggest-then-approve | P2 | approve/discard + status 전이 |
| FR-P2.4 카테고리 기본 lifecycle | P1 | CATEGORY_DEFAULT_LIFECYCLE + override |
| FR-P3.1 결정론적 distortion delta | P2 | dynamics.distortion_delta |
| FR-P3.2 토폴로지 전파 | P2 | dynamics.propagate_delta(best_path_weights) |
| FR-P3.3 advance_turn 일괄 적용 | P2 | advance_turn 6단계 시퀀스 |
| FR-P3.4 persistent 누적 | P2 | apply_deltas + contributions 누적 |
| FR-P3.5 one_shot 1회→resolve | P2 | advance_turn 내 자동 resolve |
| FR-P3.6 해소=이벤트 + 복원 | P1(상태전이)+P2(복원) | resolve_event + restore_contributions |
| FR-P4.1 주 대상 리전 소문 보존+갱신 | P2 | _update_region_rumors |
| FR-P4.2 전파 이웃 distortion만 | P2 | propagate_delta 결과만 적용 |
| FR-P4.3 소문 갱신 시점=턴 | P2 | advance_turn 내 |
| FR-P4.4 수동 경로 유지 | P2 | 기존 generate/regenerate 회귀 |
| FR-P5.1 support 자동 진화 | P2 | dynamics.evolve_support |
| FR-P5.2 승격/강등 재평가 | P2 | promotion.evaluate 재사용 |
| FR-P5.3 수동 support 공존 | P2 | adjust_support 유지 |
| FR-P6.1 TimelineKind 확장 | P1 | EVENT_* enum |
| FR-P6.2 TurnResult 확장 | P2 | applied/created event ids |
| FR-P7.1/7.2 NPC 쿼리 불변 | P2 | 회귀 확인(변경 없음) |
| FR-P8.1 Event 생성 폼 | P3 | SessionPanel |
| FR-P8.2 LLM 제안 승인 UI | P3 | SessionPanel |
| FR-P8.3 Event 목록/해소 | P3 | SessionPanel |
| FR-P8.4 Timeline event 표시 | P3 | SessionPanel |
| FR-P8.5 distortion 시각화 | P3 | SessionPanel |

## Non-Functional Requirements
| NFR | 단위 | 비고 |
|---|---|---|
| NFR-P1 포트 추상화 | P1(포트)+P2(사용) | Event CRUD additive |
| NFR-P2 레이어 격리(캐노니컬 읽기만) | P2 | advance_turn loader 읽기 |
| NFR-P3 LLM graceful | P2 | EventSuggester try/except → [] |
| NFR-P4 결정론/PBT | P2 | dynamics 순수 함수 PBT |
| NFR-P5 회귀(177+14 GREEN, NPC 불변) | P1/P2/P3 | 단위별 + 전체 |
| NFR-P6 인프라 무변경 | P1 | ensure_schema additive, compose 불변 |

## 커버리지 확인
- 모든 FR-P1..P8, NFR-P1..P6이 ≥1 단위에 할당됨. **미할당 0**. Out-of-scope(루머 피드백·Event 상호작용)는 Phase 3.
