# Application Design 질문지 — 루머 동역학 & Phase 2 하드닝

컴포넌트/서비스 **구조**를 확정하기 위한 질문입니다(구체 수치·공식은 이후 Functional Design에서).
각 질문의 `[Answer]:` 뒤에 문자(A/B/…)를 적어주세요. 없으면 `X` + 설명.

기존 구조 참고: 순수 로직 `locus/session/dynamics.py`, SRP 서비스
`{rumor_service,event_service,distortion_service,turn}.py`, 코디네이터 `game_master.py`,
포트 `SessionRepository`(+ 인메모리/Postgres 어댑터), 애그리거트 `SessionEvent`.

---

## AD-H Q1 — 루머 동역학 로직의 위치 (FR-H1~H4)
새 순수 로직(감쇠·prune 판정·증식 자격·지역 피드백)을 어디에 둘까요?

A) 기존 `dynamics.py` 순수 모듈에 함수 추가(`decay_and_prune`, `is_eligible_source`, `region_feedback` 등) — Phase 2 dynamics와 일관
B) 신규 `rumor_dynamics.py` 순수 모듈로 분리(이벤트 dynamics와 파일 분리)
X) 기타

[Answer]: B

---

## AD-H Q2 — prune(정리) 메커니즘 (FR-H1)
바닥 임계 미만 루머를 어떻게 제거할까요?

A) 리포지토리 `delete_rumor`로 **하드 삭제**(집합이 실제로 유한, 가장 단순)
B) **소프트 플래그**(`active`/`pruned` 필드 추가, 행은 남겨 이력/타임라인 보존) — 스키마 가산 컬럼 필요
X) 기타

[Answer]:B

---

## AD-H Q3 — 증식 자격 게이트의 위치 (FR-H2, 자동 append 경로에만)
"support ≥ 임계값 루머만 새 왜곡 소스로 재사용"을 어디서 적용할까요?

A) `RumorService`의 소스 수집에 선택 파라미터(`min_source_support`) 추가 — TurnAdvancer(자동 append)는 임계값 전달, 수동 경로는 미전달(기존 동작)
B) 자동 append 전용 소스 수집 메서드를 별도로 만들어 항상 게이트 적용(수동 경로와 코드 분리)
X) 기타

[Answer]: A

---

## AD-H Q4 — 루머→지역 피드백의 소유자 (FR-H3)
루머 상태 집계를 지역 distortion에 되먹이는 로직은 어디에?

A) `dynamics.py` 순수 함수(`region_feedback(rumors) -> 지역별 delta`) + `TurnAdvancer`가 새 스텝으로 호출(결정적, 서비스 추가 없음)
B) 전용 서비스 `RumorFeedbackService`를 만들어 `TurnAdvancer`에 주입(SRP 강화, 클래스 증가)
X) 기타

[Answer]: B

---

## AD-H Q5 — 신규 튜닝 파라미터의 위치 (FR-H4)
감쇠율/바닥 임계/증식 임계/피드백 가중을 어디에 둘까요?

A) `dynamics.py` 모듈 상수(`MAX_EVENT_DELTA` 등과 동일 방식), 함수 인자로 오버라이드 가능
B) `config/settings.py`에 중앙화(환경변수로 튜닝 가능)
X) 기타

[Answer]: B. min_source_support도 마찬가지.

---

## AD-H Q6 — 배치 upsert 시그니처 (FR-H5)
`SessionRepository`에 추가할 배치 메서드의 형태는?

A) `upsert_rumors(rumors: list) -> list[SessionRumor]` — 저장된 리스트 반환, 단일 트랜잭션(기존 `upsert_rumor`와 대칭)
B) `upsert_rumors(rumors) -> None` — 반환 없음(fire-and-forget)
X) 기타

[Answer]: A

---

## AD-H Q7 — 승격(promoted) 루머의 prune 예외 (FR-H1 열린 파라미터)
승격된 루머도 support 바닥 미만이면 정리될까요?

A) 승격 루머는 prune **예외**(자동 삭제 안 함; promotion.evaluate의 강등으로만 상태 변화)
B) 승격 루머도 바닥 미만이면 prune 가능(강등 후 정리)
X) 기타

[Answer]: A
