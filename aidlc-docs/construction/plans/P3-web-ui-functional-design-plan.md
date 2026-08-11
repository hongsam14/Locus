# P3 Web UI — Functional Design Plan

> 단위: P3 (최종). 입력: P2 코드(이벤트 API/advance-turn 확장), 기존 `web/src` (SessionBar/SessionPanel/api.ts/types.ts).
> 범위: FR-P8 (Event 생성 폼 · LLM 제안 승인 · Event 목록/해소 · distortion 시각화 · Timeline event 표시).

## 확정 (기존 구조에서)
- SessionPanel = GameMaster 허브(이미 advance-turn·distortion 슬라이더·generate/regen·소문 목록·timeline 보유). P3는 여기에 Event UI 추가.
- 백엔드 이벤트 API(P2): create/list/resolve/discard/suggest-events/approve + advance-turn 확장 결과(applied/resolved ids).

## 설계 질문 (FD-P3) — 각 `[Answer]:`에 A/B/… 또는 X) Other

### FD-P3 Q1 — Event UI 배치 (SessionPanel 확장)
Event 관련 UI를 어떻게 배치할까요?

A) **SessionPanel 확장**: (a) 선택 리전 섹션에 **Event 생성 폼**(category 선택·description·magnitude 슬라이더·lifecycle override, 대상=지도 선택 리전), (b) **세션 전역 Event 목록**(active/suggested/resolved + 항목별 approve/discard/resolve 액션·badge), (c) **"Suggest events (LLM)" 버튼**.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P3 Q2 — distortion 시각화 + 신규 read 엔드포인트
현재 distortion 슬라이더는 로컬 기본값(0.3)만 보여줘 이벤트로 변한 실제 값을 반영하지 못합니다. (P2 advance_turn이 per-region distortion을 동적 변경.)

A) **additive 백엔드 `GET /sessions/{sid}/distortions`**(list[RegionDistortion], `repo.list_region_distortions` 재사용) 추가 → SessionPanel이 **실제 per-region distortion** 표시(선택 리전 슬라이더 초기값·라벨 동기화). 지도 전체 틴트는 최소/선택.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P3 Q3 — Event 목록 범위
Event 목록을 어디까지 보여줄까요?

A) **세션 전역**(모든 리전), 각 항목에 region 라벨 표시.
B) 선택 리전만.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P3 Q4 — TS 타입 & api.ts 확장
프론트 계약 확장 방식은?

A) **types.ts**에 `SessionEvent`/`EventDraft`(+`EventCategory`/`EventStatus`/`EventLifecycle` string union) 추가, `TurnResult`에 `applied_event_ids`/`resolved_event_ids` 추가; **api.ts**에 `createEvent`/`listEvents`/`suggestEvents`/`approveEvent`/`resolveEvent`/`discardEvent`/`listDistortions`.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 산출물 계획 (답변 후 생성) — `aidlc-docs/construction/P3-web-ui/functional-design/`
- [x] `frontend-components.md` — SessionPanel 확장 컴포넌트 계층·props/state·상호작용·폼 검증·API 연동(data-testid).
- [x] `domain-entities.md` — TS 타입(SessionEvent/EventDraft/enum union) + TurnResult 확장 + 신규 distortions read.
- [x] `business-rules.md` — BR-P3-*: UI 상태/액션 규칙, 닫힌 세션 비활성, 승인/해소 흐름, 회귀(기존 14 vitest).
