# S3 (Web UI) — Code Generation Plan

**Single source of truth for S3 code generation.** Frontend = `web/src/`; 백엔드 보강 1건 = `api/routers/session.py`(additive GET). 문서 요약만 `aidlc-docs/construction/S3-web-ui/code/`.

## Unit Context
- **FR**: R6(세션 웹 흐름) + R6.5(dead buildWiki 정리).
- **Dependencies**: S2 세션 API(11 라우트) + 본 단위 보강 GET rumors. 기존 `web/`(App/Toolbar/MapOverlay/RegionPanel/AugmentPanel, api.ts/types.ts).
- **설계 근거**: FD `{domain-entities,business-logic-model,business-rules}.md`. 새 인프라/npm 의존 없음.

## Steps

### A. 백엔드 보강 (additive, read-only)
- [x] **Step 1 — GET rumors 엔드포인트** (`api/routers/session.py`): `GET /api/session/sessions/{sid}/regions/{rid}/rumors -> list[SessionRumor]` via `game_master`(또는 session_repo). 없는 세션 → 404. [domain-entities §3]
- [x] **Step 2 — 엔드포인트 테스트** (`tests/session/test_session_api.py` 확장): 목록 반환 + 404. [NFR-R6]

### B. 프런트 타입 + 클라이언트
- [x] **Step 3 — TS 타입** (`web/src/types.ts`): GameSession/SessionRumor/RegionDistortion/TimelineEntry/TurnResult. [FD domain-entities §1]
- [x] **Step 4 — API 클라이언트** (`web/src/api.ts`): listSessions/startSession/closeSession/getTimeline/listRumors/generateRumors/regenRumors/setSupport/setDistortion/advanceTurn/sessionKnowledge. **`buildWiki` 제거**. [FD §6, Q6=A]

### C. 컴포넌트
- [x] **Step 5 — SessionBar** (`web/src/SessionBar.tsx`, 신규): 세션 드롭다운 + New + Close + status/turn. [FD §2, BR-S3-1/2]
- [x] **Step 6 — SessionPanel** (`web/src/SessionPanel.tsx`, 신규, GameMaster 허브): 턴/Advance Turn, 타임라인, 대상 리전 distortion 슬라이더 + Generate/Regenerate + 소문 목록(support 슬라이더 + 승격 배지). 닫힌 세션 비활성. [FD §3, BR-S3-3~13]
- [x] **Step 7 — RegionPanel 수정** (`web/src/RegionPanel.tsx`): `sessionId` prop → 있으면 `sessionKnowledge`, 없으면 캐노니컬. 소문 `is_rumor` 시각 구분. [FD §4, BR-S3-14/15]
- [x] **Step 8 — App 수정** (`web/src/App.tsx`): `sessionId`/`session` 상태, SessionBar + (세션 시)SessionPanel(selected 전달) + RegionPanel(sessionId 전달) 배치. **buildWiki 제거**. [FD §5]
- [x] **Step 9 — Toolbar 수정** (`web/src/Toolbar.tsx`): `onBuildWiki` prop/버튼 제거. [Q6=A, BR-S3-16]

### D. 테스트 + 검증
- [x] **Step 10 — vitest 확장** (`web/src/__tests__/components.test.tsx`): SessionBar(목록/생성/종료), SessionPanel(generate/advance/support onChange→setSupport/승격 배지/닫힌세션 비활성), RegionPanel(sessionId 분기), buildWiki 부재. `api` mock. [FD §8]
- [x] **Step 11 — 문서**: `construction/S3-web-ui/code/code-summary.md`.

**Verification**(실행은 Build&Test): 백엔드 pytest GREEN, 프런트 vitest GREEN, tsc + vite build 클린, ruff/black 클린. 기존 회귀 0.

## FR Coverage
- FR-R6.1 → Step 5,8 · FR-R6.2 → Step 6 · FR-R6.3 → Step 6 · FR-R6.4 → Step 6,5 · FR-R6.5 → Step 4,8,9.

## Notes
- 새 npm 의존성 없음(React+Vite+TS). 백엔드 변경은 read-only 라우트 1건.
- S2 API 계약 준수; 캐노니컬/세션 격리(NFR-R2)를 UI도 위반하지 않음.
