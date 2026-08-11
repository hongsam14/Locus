# 루머 / 게임세션 — Phase 2 하드닝 (코드리뷰 후속) — 검증 질문지

**사이클**: Phase 2(P1+P2+P3) 완료 후 브라운필드 재개. 고강도 코드리뷰가 턴 엔진에서
여러 findings를 도출했습니다. 이미 수정·커밋(`81be437`)된 명확한 정합성/효율 항목은
**이번 범위에서 제외**합니다:
- [1] 왜곡 포화 후 resolve가 baseline으로 복원 ✅ 완료
- [3] 이벤트 없는 빈 턴에 support 감쇠 없음 ✅ 완료
- [9] 턴당 `list_rumors` 1회 조회 ✅ 완료

이 질문지는 구현 전에 **설계 판단이 필요한 나머지 findings**의 범위를 정합니다.
각 질문의 `[Answer]:` 태그 뒤에 문자(예: A)를 적어주세요. 해당하는 항목이 없으면
`X`를 고르고 설명을 덧붙여 주세요.

---

## 질문 1 — 사이클 범위
이번 사이클에서 다룰 나머지 코드리뷰 findings는 무엇인가요?

A) 세션 레이어 항목만: **[2]** 루머 지수 증가(정합성) + **[8]** 루머 단건 support upsert(효율)
B) 세션 레이어 항목 + 프론트엔드 refresh 워터폴(`SessionPanel.refresh` 병렬화)
C) B 전체 + 범위 밖 canonical 빌드 항목 **[4]**(`orchestrator.set_wiki`가 `topology.build` 이후 실행) / **[5]**(연결 지역이 2개가 아닌 barrier terrain이 조용히 버려짐) 조사
D) **[2]** 루머 증가만(영향도 최대의 정합성 이슈); 나머지는 보류
X) 기타 (아래 [Answer]: 태그 뒤에 설명)

[Answer]: C

---

## 질문 2 — [2] 루머 증가 억제
현재 `_collect_sources`는 기존 세션 루머를 모두 다시 왜곡 소스로 넣고, `advance_turn`은
매 턴 삭제 없이 3-체인을 덧붙여서, 이벤트가 있는 지역의 루머 집합이 매 턴 약 4배(지수)로
늘어납니다. 매 턴 자동 append를 어떻게 억제할까요?

A) **자동 append 경로에서만** 기존 세션 루머를 소스 집합에서 제외(캐노니컬 지식만으로 생성) → 증가가 선형 O(K·3)/턴; 수동 `generate_rumors`는 루머 체이닝 동작 유지
B) 지역당 총 루머 수를 설정 가능한 상한으로 제한(초과 시 생성 중단)
C) append 대신 매 턴 대상 지역을 자동 **regenerate**(기존 삭제 후 재생성)
D) 현재 append + 루머 피드백 시맨틱 유지(FD-P2 Q5=A); 증가는 문서화만 하고 수동 `regenerate_region`으로 억제(현상 유지)
X) 기타 (아래 [Answer]: 태그 뒤에 설명)

[Answer]: 각 루머의 공신력이라는 수치가 있긴 하지만, 이 문제는 더 깊게 생각해봐야 할 듯. 이 월드를 다이나믹하게 만드는 거의 핵심 변수이기 때문에.

---

## 질문 3 — [8] Support upsert 효율
`advance_turn`의 support 자동 진화가 세션 루머를 건별로 upsert하고, Postgres 어댑터는
루머마다 SELECT+UPDATE 트랜잭션을 하나씩 엽니다. 선호하는 해법은?

A) `SessionRepository` 포트에 **배치** 메서드(예: `upsert_rumors(list)`) 추가 — 인메모리 + Postgres(+ SQLite 테스트 어댑터)에 턴당 트랜잭션 1회로 구현
B) 단건 `upsert_rumor` 시그니처는 유지하되, 턴의 쓰기들을 단일 리포지토리 트랜잭션/unit-of-work로 감싸기
C) 변경 없음 — 비용 감수(로컬 단일 운영자용 저작 도구, SLA 없음)
X) 기타 (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

---

## 질문 4 — 프론트엔드 refresh 워터폴
`SessionPanel.refresh()`가 독립적인 read 엔드포인트 4개를 순차 await합니다. 바꿀까요?

A) 독립 read들을 `Promise.all`로 병렬화(왕복 깊이 1회)
B) 순차 유지(변경 없음)
X) 기타 (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

---

## 질문 5 — 범위 밖 canonical 빌드 항목 ([4], [5])
이 항목들은 월드 빌드 경로(세션 레이어 아님)에 있고 Phase 2에서 **변경되지 않았습니다** —
리뷰어가 환각한 "과거 버전"과 비교한 것입니다. 그와 별개로 [4] `set_wiki`는 실제로
`topology.build` 이후에 실행(빌드 시점엔 wiki 미사용)되고, [5]는 연결 지역이 2개가 아닌
barrier terrain을 버립니다. 방향은? (질문 1이 C일 때만 실제 조치)

A) 이번 사이클에서 조사하고, 실제 결함으로 **확인되면** 수정
B) 별도 향후 과제로 이관; 이번 사이클에선 손대지 않음
C) 설계상 의도로 간주; 조치 없음
X) 기타 (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A

---

## 질문 6 — 프로세스 깊이
이번 변경은 **기존** 세션 유닛에 대한 개선입니다(신규 컴포넌트/서비스 없음).
AI-DLC 파이프라인을 어디까지 돌릴까요?

A) **경량** 사이클 — User Stories / Application Design / Units Generation SKIP; 요구사항 → 변경별 Functional Design(경량) → Code Generation → Build & Test (2026-06-09 MVP-improvements 사이클과 동일 방식)
B) **풀** 사이클 — 모든 조건부 단계(Application Design, Units Generation 등) 실행
X) 기타 (아래 [Answer]: 태그 뒤에 설명)

[Answer]: B. 프로젝트 전면 재점검을 하기 위해서.

---

## 질문 7 — 확장(Extensions)
Phase 2의 확장 설정을 유지할까요?

A) Phase 2와 동일 — Security Baseline **off**, 순수 함수 대상 Property-Based Testing **on (Partial)**
B) 변경 (아래 [Answer]: 태그 뒤에 설명)
X) 기타 (아래 [Answer]: 태그 뒤에 설명)

[Answer]: A
