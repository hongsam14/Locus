# X1 Localization Backend — Functional Design Plan

## Plan (artifacts after answers)
- [x] `construction/X1-localization-backend/functional-design/domain-entities.md`
- [x] `construction/X1-localization-backend/functional-design/business-logic-model.md`
- [x] `construction/X1-localization-backend/functional-design/business-rules.md`
- [x] NFR-light 노트

---

## Functional Design Questions (FD-X1)

`[Answer]:`에 알파벳. 각 질문에 **권장안** 표시.

### FD-X1 Q1 — 번역 캐시 무효화 규칙 (FR-UX3.5)
캐시된 번역을 언제 재번역하나요?

A) **(권장)** 원문 텍스트 **해시(source_hash)** 기준 — 원문이 바뀌면 재번역, 같으면 캐시 재사용
B) 무효화 없음 — 최초 1회 번역 후 항상 캐시 신뢰(원문 변경 드묾 가정)
X) Other

[Answer]: A

### FD-X1 Q2 — 캐노니컬 Knowledge 번역 대상 필드 (Q4=B)
`Knowledge`는 `statement`(사실 본문) + `title`(한 줄 라벨) 둘 다 영어입니다. 무엇을 번역?

A) **(권장)** `title` + `statement` 둘 다
B) `statement`만
X) Other

[Answer]: A

### FD-X1 Q3 — 캐노니컬 번역 캐시 범위 (world vs session)
캐노니컬 지식은 세션과 무관하게 동일합니다. 캐시 키 범위는?

A) **(권장)** **world 범위** — `(kind=knowledge, id, lang)`, `world_id` 파티션, `session_id=null`. 세션 간 재사용(효율).
B) 세션 범위 — 세션마다 별도 캐시
X) Other

[Answer]: A

### FD-X1 Q4 — 번역 실패 시 표기 (SEC-C 폴백)
Translator/LLM 실패 시 조회 응답은?

A) **(권장)** 원문(영어)로 조용히 폴백, ko 캐시에 저장 안 함(다음 조회 재시도). 프론트는 원문 표시.
B) 원문 폴백 + 응답에 "번역 실패" 플래그 포함(프론트가 실패 표기)
X) Other

[Answer]: A

### FD-X1 Q5 — `region_changes.rumors_added` 소스 (FR-UX2.6)
advance_turn이 지역별로 알릴 "추가된 소문"의 정의는?

A) **(권장)** 이번 턴 **새로 생성/추가된** 소문 id(이벤트 대상 지역 append 등)
B) 상태 변동(승격/강등/프룬)만 알리고 신규 생성은 제외
X) Other

[Answer]: A

### FD-X1 Q6 — 생성 시점 번역 실패 격리 (Q3=A)
생성 시점(rumor/event/timeline) 번역이 실패하면?

A) **(권장)** 콘텐츠 생성은 성공시키고 번역은 best-effort(실패 시 조회 때 재시도) — 회복력 우선
B) 번역까지 성공해야 생성 커밋(실패 시 생성도 롤백)
X) Other

[Answer]: A

### FD-X1 Q7 — 번역 배치 상한 (SEC-E)
`localize_many` 배치/병렬 상한은?

A) **(권장)** 합리적 기본(예: 1회 최대 20건, 소배치 순차)을 settings로 조정 가능하게
B) 상한 없음(전 지역 한 번에)
X) Other

[Answer]: A
