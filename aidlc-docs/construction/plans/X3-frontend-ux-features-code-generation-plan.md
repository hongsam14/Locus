# X3 Frontend UX Features — Code Generation Plan (brownfield)

**Single source of truth for X3.** 앱 코드 `web/`(+ 소폭 `locus/`), 문서 `aidlc-docs/`.

## Unit Context
- 컴포넌트 C10–C15 + 백엔드 regen 승격 보존(Q6/Q7=A). 의존: X1(ko 응답·region_changes) + X2(프리미티브).
- FR: FR-UX2.1/2.2/2.3/2.4/2.5/2.6, FR-UX3.1/3.4. BR-X3-1..14. SEC-A/E.
- 결정: Q1=A/Q2=A+bar/Q3=A/Q4=A/Q5=A/Q6=A/Q7=A.

## Steps

### Step 1 — 백엔드: regen 승격 보존 (BR-X3-9) [x]
- `locus/session/rumor_service.py::regenerate_region`: 승격 소문은 삭제하지 않고 보존, 비승격만 삭제 후 재생성. 반환 = 보존된 승격 + 신규. 주석 갱신(S2 "drop all"→"preserve promoted").
- 테스트: `tests/session/test_*`(regen이 promoted 보존·비승격 교체 검증). 오프라인 pytest GREEN.

### Step 2 — types.ts [x]
- `web/src/types.ts`: `SessionRumor += statement_ko?`, `SessionEvent += description_ko?`, `KnowledgeView += statement_ko?/title_ko?`, 신규 `RegionTurnChange`, `TurnResult += region_changes?: RegionTurnChange[]`.

### Step 3 — i18n 사전 (C10) [x]
- `web/src/i18n.ts`: `messages.ko`(UI 라벨 + 타임라인 kind 템플릿) + `t(key, params?)`(`{id}`/`{turn}` 치환, 미정의→fallback). 타임라인: promote/demote/prune/generate/regenerate/advance_turn/set_distortion/adjust_support/event_created/event_applied/event_resolved 템플릿.

### Step 4 — 프리미티브 확장 (C11/C14) [x]
- `web/src/ui/LocalizedText.tsx`: `{ko?, original, testId?}` — ko 기본 + "원문" 토글(로컬 state). ko 없으면 원문만.
- `web/src/ui/NotificationCenter.tsx`: 우상단 fixed 토스트 스택 `{items, onDismiss}`, 자동 소멸 타이머 + 수동 닫기(X2 Toast 사용).
- `web/src/ui/index.ts` export 추가.

### Step 5 — SessionPanel 확장 (C12/C13/C14) [x]
- **전체 생성**(`generate-all-btn`): distortions 지역 목록 → 각 `listRumors`로 빈 지역 판정 → 병렬(청크 상한) `generateRumors` + progress(`generate-progress` bar + N/M) + 요약 토스트.
- **전체 재생성**(`regen-all-btn`): Modal 확인 → 전체 지역 `regenRumors` 병렬(진행 동일).
- **지역 재생성**(기존 `regen-btn`): Modal 확인("승격 보존") → `regenRumors`.
- **알림**: `advanceTurn` 결과 `region_changes` → 지역별 Notif → NotificationCenter 렌더(자동 소멸).
- 소문 텍스트: `<LocalizedText ko={r.statement_ko} original={r.statement}/>`. 타임라인: `t('timeline.'+kind, payload)`.

### Step 6 — RegionPanel 로컬라이즈 (C11) [x]
- 지식 항목 텍스트 `<LocalizedText ko={it.statement_ko} original={it.statement}/>`.

### Step 7 — 테스트/빌드 [x]
- vitest: 전체 생성 빈지역 판정·병렬 호출, 전체 재생성 Modal 확인, 지역 재생성 Modal, 알림 지역별 렌더, 원문 토글, 타임라인 i18n. 기존 계약 GREEN 유지.
- `npm test` + `npm run build`(tsc+vite) + backend `pytest` GREEN.

### Step 8 — 코드 요약 [x]
- `aidlc-docs/construction/X3-frontend-ux-features/code/code-summary.md`.

## Traceability
- FR-UX2.1/2.3→S5(C12) · FR-UX2.2→S5(regen-all Modal) · FR-UX2.4/2.5→S5(C13)+S1(백엔드) · FR-UX2.6→S4/S5(C14) · FR-UX3.1→S3(C10) · FR-UX3.4→S4/S5/S6(C11) · F2a→S3/S5 · SEC-E→S5.

## Quality Gates
- 프론트 vitest + 백엔드 pytest GREEN(신규 포함), tsc/vite clean, `data-testid` 회귀 0, 외부 CDN 없음.
