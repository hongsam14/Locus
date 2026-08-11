# Rumor / Game-Session **Phase 2** — Unit of Work Plan

> 입력: 승인된 rumor-phase2-{requirements, execution-plan, application-design}. 단위 분할은 AD-P Q6=A로 확정(P1→P2→P3).
> 대부분의 decomposition 결정이 선행 승인으로 확정되어, 잔여 경계 질문 1건만 제시.

## 단위 분할 (확정 — AD-P Q6=A / execution-plan)
- **P1 Event Foundation**: SessionEvent 모델(C1) + enums/매핑/ TimelineKind 확장(C2) + SessionRepository Event CRUD(C6, postgres+memory, ensure_schema `session_events`) + 수동 Event API(C7 일부).
- **P2 Dynamic Engine**: dynamics 순수(C3) + EventSuggester LLM(C4) + GameMasterService 확장·advance_turn 시퀀스(C5) + suggest/approve/advance API(C7 일부) + TurnResult 확장.
- **P3 Web UI**: SessionPanel Event UI(C8) + api.ts/types.
- **빌드 순서**: P1 → P2 → P3 (순차, dependency 강제).

## 잔여 경계 질문 (UOW-P)

### UOW-P Q1 — P1의 API 범위
P1에 **수동 Event API**(`POST /events`, `GET /events`, `POST …/resolve`, `DELETE …/events/{eid}`)를 포함해 P1을 독립적으로 테스트/시연 가능하게 할까요? (suggest/approve/advance-turn 확장은 엔진이 필요하므로 P2)

A) **포함** — P1 = 모델+포트+스키마+수동 CRUD API. P1 단독으로 Event 생성/조회/해소(복원 없는 단순 상태전이) 가능. suggest/approve/advance는 P2.
B) **제외** — P1 = 모델+포트+스키마만(순수 데이터 계층). 모든 API는 P2.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

> 참고: A 권장 — Phase 1 S1이 모델+포트+API(5 routes)를 함께 묶어 단위 독립 검증한 패턴과 일치. (resolve의 distortion 복원 로직은 dynamics 의존이므로 P2에서 완성; P1의 resolve는 상태전이까지.)

---

## 산출물 (생성 완료) — `aidlc-docs/inception/application-design/rumor-phase2/`
- [x] `unit-of-work.md` — P1/P2/P3 정의·책임·컴포넌트·스토리(FR) 매핑·코드 조직.
- [x] `unit-of-work-dependency.md` — 단위 의존성 매트릭스 + 빌드 순서 + 조정 지점.
- [x] `unit-of-work-story-map.md` — FR-P* / NFR-P* → 단위 매핑(전 요구사항 할당 확인).
- [x] 단위 경계·의존성 검증; 모든 요구사항 단위 할당 확인(미할당 0).
