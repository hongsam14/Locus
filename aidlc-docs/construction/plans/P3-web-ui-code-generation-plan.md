# P3 Web UI — Code Generation Plan

> 단위: P3(최종). 입력: `construction/P3-web-ui/functional-design/*`. Brownfield in-place. additive — 기존 백엔드/프론트 회귀 0.
> 스토리: FR-P8(전체); NFR-P5(회귀). 의존: P2(이벤트 API/advance-turn 확장).

## 단위 컨텍스트
- **소유**: SessionPanel Event UI, TS 타입/ api.ts 확장, 1 additive 백엔드 read 라우트.
- **결정**: FD-P3 all A. distortion 실제값 표시 위해 `GET /sessions/{sid}/distortions` 추가.

## 단계
- [x] **Step 1 — NFR-light 노트**: `construction/P3-web-ui/nfr/nfr-light.md`(NFR-P5 회귀 / 인프라 무관).
- [x] **Step 2 — Backend read 엔드포인트**: `locus/session/game_master.py` `list_distortions(session_id)`(읽기, 닫힌 세션 허용) + `api/routers/session.py` `GET /sessions/{sid}/distortions`(→list[RegionDistortion], 404). (BR-P3-7)
- [x] **Step 3 — Backend test**: `tests/session/test_session_api.py` 확장 — distortions 조회(빈/값) + 404.
- [x] **Step 4 — TS types**: `web/src/types.ts` — `EventCategory`/`EventLifecycle`/`EventStatus` union, `SessionEvent`, `EventDraft`, `TurnResult` +applied/resolved ids. (BR-P3-8)
- [x] **Step 5 — api.ts**: `web/src/api.ts` — `createEvent`/`listEvents`/`suggestEvents`/`approveEvent`/`resolveEvent`/`discardEvent`/`listDistortions`.
- [x] **Step 6 — SessionPanel**: `web/src/SessionPanel.tsx` — events/distortions state, refresh 확장, Event 생성 폼(선택 리전), 세션 전역 Event 목록(approve/discard/resolve+badge), Suggest 버튼, distortion 슬라이더 실제값 동기화, 닫힌 세션 disabled, data-testid. (FR-P8 / BR-P3-1..6,9)
- [x] **Step 7 — vitest**: `web/src/__tests__/components.test.tsx` 확장 — create form/suggest/approve/discard/resolve/distortion 실제값/닫힌 세션 disabled + api mock에 신규 메서드 추가.
- [x] **Step 8 — Code summary**: `construction/P3-web-ui/code/code-summary.md`.

## 검증 게이트
- backend `pytest`(218 + 신규 GREEN), ruff/black/compileall 클린.
- frontend `npm test`(14 + 신규 GREEN), `tsc` + `vite build` 클린.
- 세션 라우트 +1(distortions).

## 주의
- SessionPanel 기존 동작(generate/regen/advance/support/promoted badge/timeline) 보존 — 기존 vitest 회귀 우선.
- api mock(components.test.tsx)에 신규 메서드 추가 안 하면 기존 테스트가 깨질 수 있음 → mock 갱신 포함.
