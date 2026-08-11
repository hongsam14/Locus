# Rumor / Game-Session **Phase 2** — Application Design Plan

> 입력: `inception/requirements/rumor-phase2-requirements.md`, `inception/plans/rumor-phase2-execution-plan.md` (둘 다 APPROVED).
> 목적: 신규/확장 컴포넌트·메서드·서비스·의존성 식별(상세 비즈니스 로직은 per-unit Functional Design). 캐노니컬 불변, 세션 레이어 additive.

## 식별된 컴포넌트 (요구사항에서 도출 — 확정은 아래 질문 답변 후)
- **SessionEvent** (model) — 신규 도메인 엔티티 (FR-P1).
- **EventCategory / EventLifecycle / EventStatus** (enums) + **category→기본 lifecycle 매핑** (FR-P2.4, CL1.3).
- **dynamics (pure)** — distortion delta + 토폴로지 전파(best_path_weights 재사용) + support 자동 진화 + accumulated 복원 (FR-P3, FR-P5).
- **EventSuggester** (LLM) — 세션 상태 → Event 제안(미커밋) (FR-P2.2).
- **GameMasterService** (확장) — create/suggest/approve/resolve event + advance_turn 통합 시퀀스 (FR-P2, P3, P4, P5, P6).
- **SessionRepository** (확장) — Event CRUD (FR-P1.3).
- **session API** (확장) — additive 라우트.
- **web** (P3 단위) — SessionPanel 확장.

---

## 설계 질문 (AD-P) — 각 `[Answer]:`에 A/B/… 또는 X) Other

### AD-P Q1 — 순수 진화 로직(distortion/support) 배치
distortion delta·토폴로지 전파·support 진화·accumulated 복원 등 **순수 함수**를 어디에 둘까요? (기존 `promotion.py`가 순수 승격 로직의 선례)

A) **신규 `locus/session/dynamics.py`** 모듈에 순수 함수로 모음(promotion.py 패턴 계승). GameMasterService가 호출.
B) 기존 `promotion.py` 확장 + game_master에 인라인.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-P Q2 — LLM EventSuggester 배치
LLM이 Event를 제안하는 로직을 어디에? (기존 `rumor_generator.py`의 `RumorGenerator`가 LLM 컴포넌트 선례)

A) **신규 `locus/session/event_suggester.py`** 의 `EventSuggester` 클래스(LLMProvider 주입), `EventDraft`(미커밋) 리스트 반환. graceful 실패.
B) GameMasterService 메서드로 인라인.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-P Q3 — suggest → approve → advance 흐름(엔드포인트 구조)
CL2.1=A(승인 게이트) + CL2.2=B(매 턴 LLM 제안) 흐름을 어떻게 노출할까요?

A) **분리된 단계** — `POST …/suggest-events`(LLM 제안 생성, 미적용) → 사용자 채택 `POST …/events`(또는 approve) → `POST …/advance-turn`(활성 Event 일괄 적용). UI가 턴 진행 전 제안→승인.
B) **advance_turn 통합** — advance_turn이 다음 턴 제안을 결과로 함께 반환(별도 호출 없음).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-P Q4 — SessionEvent.status 모델 (제안 영속화 여부)
LLM 제안 Event를 DB에 저장하나요, 승인된 것만 저장하나요?

A) **status = suggested | active | resolved** — LLM 제안 = `suggested`(영속), 승인 → `active`, GM 수동 생성 = `active` 직행, 해소 → `resolved`. 폐기된 제안은 삭제(또는 미저장).
B) **status = active | resolved** — 제안은 응답에만 실리는 휘발 데이터(승인 시에만 INSERT).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-P Q5 — accumulated 복원의 다중 리전 처리 (FR-P3.6)
persistent Event 해소 시 누적분(accumulated_delta) 복원을, 전파로 영향받은 **이웃 리전**까지 되돌릴까요?

A) **주 대상 + 전파 이웃 모두 복원** — Event가 적용 시 주 대상 + 이웃별 기여분을 기록하고, 해소 시 동일 비율로 차감(대칭).
B) **주 대상 리전만 복원** — 이웃 전파분은 복원 안 함(잔류, 단순화).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-P Q6 — 단위 분할 확인
실행 계획의 단위 분할(P1 Event Foundation → P2 Dynamic Engine → P3 Web UI)을 유지할까요?

A) **유지** (P1 모델/포트/스키마/수동 CRUD API → P2 엔진/턴/LLM/진화 → P3 웹).
B) 조정 필요(아래 Other에 기술).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 산출물 계획 (답변 후 생성) — `aidlc-docs/inception/application-design/rumor-phase2/`
- [ ] `components.md` — 컴포넌트 정의 + 책임 + 인터페이스 (SessionEvent, enums, dynamics, EventSuggester, GameMasterService 확장, SessionRepository 확장, API).
- [ ] `component-methods.md` — 메서드 시그니처 + 입출력 타입 (비즈니스 규칙은 FD로 이연).
- [ ] `services.md` — GameMasterService 오케스트레이션(advance_turn 시퀀스) + 서비스 상호작용.
- [ ] `component-dependency.md` — 의존성 매트릭스 + 통신 패턴 + advance_turn 데이터 흐름.
- [ ] `application-design.md` — 위 통합 문서.
- [ ] 일관성/완전성 검증.
