## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (plan) — V2 디자인 시스템
**Reviewed artifact:** `aidlc-docs/construction/plans/V2-design-system-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-07T12:35:07Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/V2-design-system-code-generation-plan.md > Step 4.3, 4.4 (and Steps 5–8 that follow) | Step 4.4는 `setupTests.ts`에 `afterEach(clearToasts)`를 두고, Step 4.3은 `renderWithShell`이 Toaster를 감싼다고 한다. 그러나 `ui/toast.ts`·`ui/Toaster.tsx`는 Step 9.2에서야 생긴다(`ls web/src/ui`에 둘 다 없음). 계획은 "import만 준비", "자리만 둔다"라고 쓰는데, `setupTests.ts`는 `vite.config.ts`의 `setupFiles`라 모든 테스트 파일이 로드한다. 존재하지 않는 모듈을 import하면 Step 4부터 Step 8까지 vitest 전체가 RED이고, 4.5·5.5·6.4·7.5·8.8의 "GREEN 뒤 커밋" 규칙을 지킬 수 없다. | `clearToasts`의 연결을 Step 9.2로 옮기거나, Step 4에서 `ui/toast.ts`의 최소 저장소(`toast`·`clearToasts`)를 먼저 만들고 Step 9가 확장하게 한다. `renderWithShell`도 Step 10에서 처음 만들고 4.3은 Toaster 없는 MemoryRouter·capabilities 대역만 둔다고 못박는다. | New |
| R-02 | Major | aidlc-docs/construction/plans/V2-design-system-code-generation-plan.md > Step 15.1, 15.3 | "역공학 때의 스크래치 도구(`re-scratch/mock/server.mjs` + `shoot.mjs`)"를 쓴다고 하지만 작업 공간에도 `/tmp`·홈에도 없고(`ls re-scratch` 실패), 저장소에 추적되지도 않으며, 어디서 가져오는지 계획이 말하지 않는다. 완료 조건(가짜 API 캡처 1280·390px)과 NFR R-02의 글꼴 실측이 이 도구에 기대는데, 개발자는 계획만으로 실행할 수 없다. 가짜 API가 새 화면(`/api/capabilities`, 세션·세계 응답)을 어디까지 흉내 내야 하는지도 없다. | 도구의 실제 위치를 적거나, 없으면 Step 15에 "가짜 API와 촬영 스크립트를 스크래치에 새로 만든다"를 단계로 넣고 필요한 엔드포인트 목록(홈·플레이·GM·에디터 네 화면이 부르는 GET)과 woff2 바이트 측정 방법(네트워크 기록 도구)을 정한다. | New |
| R-03 | Minor | aidlc-docs/construction/plans/V2-design-system-code-generation-plan.md > Step 3.1 vs Step 4.1 | Step 3이 `@fontsource/gaegu`를 지우지만 `web/src/index.css:4-7`은 4.1까지 `@fontsource/gaegu/*.css`를 import한다. 3.3의 tsc·vitest는 CSS를 처리하지 않아 GREEN이지만 `vite build`는 Step 3 커밋에서 깨진다(중간 커밋이 빌드 불가). | gaegu 제거를 Step 4.1(import를 바꾸는 같은 커밋)로 옮긴다. | New |
| R-04 | Minor | aidlc-docs/construction/plans/V2-design-system-code-generation-plan.md > Step 12.1 | "대화상자 아홉 곳"이라 하지만 나열된 것은 여덟(GmHub, DeedPanel, ConfirmDelete, WorldFileBar, BuildPanel, DemoCard = `<Modal` 6곳(grep 6건 일치) + MapCanvas, NewSessionForm). 개수가 틀리거나 빠진 한 곳이 있다. 또 select 13곳 중 `web/src/SessionBar.tsx`(루트 파일)는 FD frontend-components § 1.3 소유 표에 없다. | 개수를 여덟으로 고치거나 빠진 곳을 적는다. SessionBar의 소유 유닛과 "기계적" 변경 범위를 § 1.1 메모에 한 줄 더한다. | New |
| R-05 | Minor | aidlc-docs/construction/plans/V2-design-system-code-generation-plan.md > Step 13.3 | `docker build -t locus-web web`은 `nginx.conf`를 이미지에 복사할 뿐 문법을 검사하지 않는다. "설정이 읽히는지 확인"이 이 명령으로는 보장되지 않는다. 또한 `location /assets/`가 `location /`의 `try_files`와 겹치지 않는지, 해시 없는 파일(폰트 경로 포함)이 `/assets/`에 없는지도 적혀 있지 않다. | 빌드한 이미지에서 `nginx -t`를 돌리는 것으로 바꾸고, 빌드 산출물에 `/assets/` 아래 해시 없는 파일이 없는지 한 줄 확인한다. | New |
| R-06 | Minor | aidlc-docs/construction/plans/V2-design-system-code-generation-plan.md > Step 8.4–8.5, 8.7 | 지금 MapOverlay는 `data-testid="map-overlay"`, `region-marker-<id>` 등을 가지며 editor.test·gm.test·components.test가 이를 쓴다. WorldMap이 이 testid를 유지한다는 문장이 8.4에 없고 8.7은 "지금 테스트 GREEN"만 말한다. 컨테이너가 고정 `width: W, height: H`에서 컨테이너 너비를 따르는 viewBox 1000×625로 바뀌므로 기존 좌표 단언(editor.test:681 근처 끌기)이 달라질 수 있다. | 8.4에 유지할 testid 목록을 적고, 끌기 단언이 jsdom의 0×0 rect에서 어떤 대체 경로(`meetMatrix`)로 같은 값을 내는지 한 문장으로 못박는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| Existing paths named (api/errors.py, main.py, uploads.py, deps.py, routers, web/src files, ui/*, nginx.conf, __tests__) | all exist; new paths (errors/, format/, hooks/, layout/, map/, test/) are declared new | OK |
| Call sites: `<select` in non-test tsx | 13 lines in 9 files | Matches plan "13곳(9파일)" |
| Call sites: `type="file"` | 4 (EditorPage, GmPage, BuildPanel, WorldFileBar) | Matches plan |
| Call sites: `<Modal` | 6 + 2 self-built dialogs = 8 | Plan says 9 (R-04) |
| HTTPException raise sites in api/ vs Step 2.3 | deps 3, uploads 5 (+1 JSONResponse), world.py 8, world_editor 4; all covered by listed codes | OK |
| Exception classes of ERROR_CODES (19 rows) exist; subclass order (AugmentationConflict subclasses, UnsupportedWorldFile < ValueError, InvalidAction/ConversationExists/AppraisalExists < ValueError) | exist, ordering rule covers them | OK |
| Tests comparing full error body (Step 1.4) | only `r.json()["detail"] ==` at test_uploads.py:78 and test_gm_mode_api.py:132 | detail unchanged; additive code safe |
| `Exception` handler vs tests expecting propagation | test_world_api.py:292 uses pytest.raises(RuntimeError) with default client; test_keyless_api uses raise_server_exceptions=False | Starlette re-raises after the handler; OK |
| `setupFiles` includes setupTests.ts for all tests | web/vite.config.ts `setupFiles` | Confirms R-01 |
| `ui/toast.ts`, `ui/Toaster.tsx` exist before Step 9 | not in web/src/ui | Confirms R-01 |
| `re-scratch` tool | not found in workspace, /tmp, home; not referenced in aidlc-docs/inception or V2 docs | Confirms R-02 |
| index.css gaegu imports vs Step 3 | web/src/index.css:4-7 import gaegu | Confirms R-03 |
| Old test hooks the plan relies on (AppNav components.test:561-579, llm-notice gm.test:632·648, `../layout`·`../viz` in pure.test) | all present as claimed | OK |
| TP-V2-1..16 coverage | 1-15 mapped to steps; TP-V2-16 via 1.2/11.4/12.5/14.1 | OK |
| Accepted-risk notes (FD R-10/R-11, NFR R-01..R-05, Units R-03) | each has a step and trace row | OK, subject to R-01 ordering |
| Boundaries/contracts for V3/V4/V5/V6/V8 (ERROR_CODES, {detail, code}, ui/layout/map/format/errors/hooks API) | produced in Steps 2, 5–10 | OK |

### Summary

The plan is well-grounded: paths and call-site counts mostly check out and the FD/NFR rules, accepted-risk notes and TP-V2 cases all have steps. The two real defects are that Step 4 wires `clearToasts` and a Toaster-wrapping helper into the global test setup before those modules exist (breaking GREEN for Steps 4–8), and Step 15 depends on a scratch capture tool that is not present or specified. Fix those two and the Minor items (gaegu removal order, Modal count, nginx check, WorldMap testids) in the plan before approval.
