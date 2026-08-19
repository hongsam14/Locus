# X3 Frontend UX Features — Frontend Components

결정: FD-X3 Q1=A(우상단 토스트 스택·지역별 1건·자동소멸+닫기) · Q2=A+progress-bar · Q3=A(전체생성/전체재생성 별도 버튼+Modal) · Q4=A(타임라인 i18n) · Q5=A(항목별 원문 토글) · Q6=A(백엔드 regen 승격 보존) · Q7=A(전체재생성도 승격 보존).

## C10 — i18n 사전 (`web/src/i18n.ts`)
- `messages: { ko: Record<string,string> }` — UI 라벨(버튼/헤더/상태) + **타임라인 kind 템플릿**.
- `t(key, params?)` — `{id}` 등 치환. 예 템플릿(F2a): `timeline.promote`="승격: {id}", `timeline.prune`="소멸: {id}", `timeline.event_applied`="이벤트 적용: {id}", `timeline.advance_turn`="턴 {turn} 진행", `timeline.generate`="소문 생성" 등. payload(rumor_id/event_id/region_id/turn)로 치환.
- 미정의 key는 원문 fallback.

## C11 — LocalizedText (`web/src/ui/LocalizedText.tsx`)
- props: `{ ko?: string | null; original: string; testId?: string }`.
- ko 있으면 ko 기본 표시 + 작은 "원문" 토글 버튼(클릭 시 원문↔번역, 로컬 `useState`). ko 없으면 원문만(토글 없음).
- 소문/이벤트/지식 텍스트 렌더에 사용.

## C12 — 전체 생성 / 전체 재생성 (SessionPanel 확장)
- **전체 생성 버튼**(`generate-all-btn`): 세션 전체 지역 중 **소문 0인 지역만** 대상. 지역 목록=distortions(이미 로드), 각 지역 `listRumors`로 유무 판정(Q6=B). 대상들에 `generateRumors` **병렬(Promise.all)**. 진행: **progress-bar + "N/M 완료"**(Q2=A+bar). 부분 실패는 개별 집계 후 요약 토스트.
- **전체 재생성 버튼**(`regen-all-btn`): **Modal 확인** 후 전체 지역 `regenRumors` 병렬(덮어쓰기). 승격 보존(Q7=A, 백엔드). 진행 동일.
- 병렬 상한(SEC-E): 동시 요청 합리적 상한(예: 4~6) — 청크 처리.

## C13 — 지역 재생성 개선 (SessionPanel)
- 기존 `regen-btn` 클릭 → **Modal 확인**(문구: "이 지역 소문을 재생성합니다. 승격된 소문은 보존됩니다.") → 확인 시 `regenRumors`. 승격 보존은 백엔드(BR-X3-대응).

## C14 — NotificationCenter (`web/src/ui/NotificationCenter.tsx`)
- 우상단 **fixed 토스트 스택**. props: `{ items: Notif[]; onDismiss(id) }`.
- `advance-turn` 응답의 `region_changes` → **지역마다 1건** Notif 생성(그 지역 변동 요약: "지역 {rid} — 2건 승격, 1건 소멸, 이벤트 1 해소" 등, i18n). 자동 소멸(수초 타이머) + 수동 닫기(Toast onClose).
- SessionPanel이 advanceTurn 결과에서 notifications 상태를 갱신하고 NotificationCenter를 렌더(position:fixed라 뷰포트 기준).

## C15 — api/types (`web/src/api.ts`, `types.ts`)
- `types.ts`: `SessionRumor += statement_ko?`, `SessionEvent += description_ko?`, `KnowledgeView(QueryResult.items) += statement_ko?/title_ko?`, 신규 `RegionTurnChange`, `TurnResult += region_changes: RegionTurnChange[]`.
- `api.ts`: 신규 엔드포인트 없음(전체 생성/재생성=프론트 병렬). 필요 시 헬퍼.

## 백엔드 터치 (Q6/Q7=A — X3 포함)
- `locus/session/rumor_service.py::regenerate_region`: **승격된 소문은 삭제하지 않고 보존**, 비승격만 삭제 후 재생성. 반환은 보존된 승격 + 신규. 오프라인 테스트 추가.
- (선택) game_master 위임 그대로. 기존 S2 규칙 "Q4=A drop all"에서 "승격 보존"으로 변경 — 주석/코드요약 명시.

## 컴포넌트 계약 보존
- 기존 `data-testid`·핸들러 유지. 신규 testid: `generate-all-btn`/`regen-all-btn`/`generate-progress`/`notif-{rid}`/`orig-toggle-{id}` 등.
- X2 프리미티브(Button/Modal/Toast/Card/Badge) 재사용.
