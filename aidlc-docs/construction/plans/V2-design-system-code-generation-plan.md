# V2 디자인 시스템 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V2(실행 2/9), Code Generation 1부(계획). 고르신 B안(등불 아래 선술집)을 코드로 옮긴다. 네 화면이 그 위에서 B 톤으로 그대로 동작하게 한다. 이 계획이 V2 코드 생성의 유일한 기준이다.

**근거**:
- 요구사항: `inception/requirements/follow-up-requirements.md` FR-D1~D9, FR-S5·S6, FR-C13, NFR-1·3·4·5·6·7·9
- 유닛: `inception/application-design/follow-up/unit-of-work.md` V2, 의존·계약 `unit-of-work-dependency.md` § 3·4
- 설계: `inception/application-design/follow-up/{components,component-methods}.md` § 1·7
- 승인된 FD: `construction/V2-design-system/functional-design/*` (BLM, BR-V2-01~26, domain-entities, frontend-components; 리뷰 02의 R-10·R-11은 Accepted risk → 아래 실행 메모)
- 승인된 NFR: `construction/V2-design-system/nfr/nfr-light.md` (리뷰 01의 R-01~R-05는 Accepted risk → 아래 실행 메모)

**단계 표기**: 단계마다 체크박스를 고친다. 단계는 그 단계의 테스트가 GREEN인 상태로 끝내고, 단계마다 `feat/follow-up`에 커밋한다. **이 계획의 승인이 이 커밋들의 허락이다.** 푸시·PR은 사람이 한다.

---

## 1. 단위 맥락

| 항목 | 내용 |
|---|---|
| 요구사항 | FR-D1(시안, FD에서 끝남) · FR-D2 토큰 · FR-D3 글꼴 · FR-D4 프리미티브 · FR-D5 배치 틀 · FR-D6 지도 좌표 · FR-D7 지도 시각(바탕) · FR-D8 표기 규칙 · FR-D9 오류 문장(+서버 `code`) · FR-S5 상태 처리 도구 · FR-S6 프리미티브 접근성 · FR-C13 요청 도우미 · RE-F09(capabilities) |
| 백엔드 | `api/errors.py`, `api/main.py`, `api/uploads.py`, `api/deps.py`, `api/routers/world.py`·`world_editor.py`(오류를 던지는 자리에서 `code`만) |
| 프론트 | `web/src/{index.css, i18n/, format/, errors/, hooks/, ui/, layout/, map/, api/http.ts, capabilities.ts, setupTests.ts, test/}` + 화면 파일의 기계적 변경(FD frontend-components § 1.3·§ 6) |
| 설정 | `web/package.json`·`package-lock.json`(Radix 둘, 글꼴 셋, fast-check), `web/nginx.conf`(`/assets/` 캐시) |
| 바꾸지 않는 것 | 화면 배치와 문구(V4·V6·V8), 번역 칸(V3), `gm_busy`(V5), mypy 게이트(V9), `index.html` 머리(V9) |
| 의존 | 없음(V1 끝남) |
| 내는 계약(§ 3 계약) | V4·V6·V8: `ui/`·`layout/`·`map/`·`format/`·`errors/`·`hooks/` 공개 API. V3·V5: `ERROR_CODES` 표와 `{"detail", "code"}` 본문 |

### 1.1 실행 메모 (리뷰 지적, Accepted risk)
- **NFR R-01**: Step 1.3에서 FD 두 곳의 글꼴 굵기를 고치고 〔Step 1.3 정정〕으로 표시한다.
  - domain-entities § 2: 나눔명조 700만, Noto Sans KR 400·700.
  - BLM § 3 표: 같은 값.
  - 지금 코드의 `font-medium`은 0곳이고 `font-bold`는 2곳(700)이라 매핑할 것이 없다.
- **FD R-10**: `ui/toast.ts`에 테스트용 `clearToasts()`를 두고 `setupTests.ts`의 `afterEach`가 부른다(Step 4.4).
- **FD R-11**: `formatDate`·`formatDateTime`은 `(iso, lang?, timeZone?)`다(Step 5.3).
- **NFR R-02**: 글꼴은 실측 옆에 데이터에 따른 최악값(전체 조각 합)을 참고로 적는다. 홈은 데모 하나와 새 월드 하나, 두 번 잰다(Step 15.3).
- **NFR R-03**: JS가 125.6 kB를 넘으면 사유를 적고 첫 화면 JS로 판정한다. 필요하면 GM·에디터 라우트를 `React.lazy`로 나눈다(Step 14.4).
- **NFR R-04**: 대비 테스트는 알파 색(`map-plate` 90%, 둘레 빛 22%)을 그 바탕 위에 합성한 뒤 계산한다. 표 밖 조합은 감수한 위험이다. 화면 유닛의 캡처와 B&T가 본다(Step 13.1).
- **NFR R-05**: `web/nginx.conf`에 해시 파일 `/assets/` 불변 캐시 헤더를 단다(Step 13.3).
- **Units R-03(V2 몫)**: 다른 유닛과 겹치는 파일은 FD frontend-components § 1.3 표를 따른다. `web/package.json`은 V2가 의존을 더하고 V9가 audit만 고친다. `NewSessionForm`·`MapCanvas`·`BuildPanel`은 V2가 대화상자·select·파일 입력을 기계적으로 바꾸고 V4·V8이 배치를 바꾼다. 커밋 메시지에 "mechanical"을 적어 뒤 유닛이 구별하게 한다.

### 1.2 실행 메모 (코드 계획 리뷰 01, 승인 때 Accepted risk)
- 〔실행 메모 R-01〕 Step 4.3은 대비 도우미(`src/test/contrast.ts`)만 만들고 `renderWithShell`은 만들지 않는다. Step 4.4는 fast-check 시드 설정만 둔다. `afterEach(clearToasts)`는 Step 9.2에서 `ui/toast.ts`와 함께 연결한다. `renderWithShell`(MemoryRouter + Toaster + capabilities 대역)은 Step 10.3에서 처음 만든다. 그래서 Step 4~8의 커밋은 모두 GREEN이다.
- 〔실행 메모 R-02〕 캡처 도구는 이 세션의 스크래치에 있다: `/tmp/claude-1000/-home-thinkpad-Desktop-src-Locus/31f256ed-f021-4e89-9228-82166a61182b/scratchpad/re-scratch/mock/{server.mjs,shoot.mjs}`. 세션이 바뀌어 없으면 스크래치에 다시 만든다.
  - 가짜 API는 네 화면이 부르는 GET을 흉내 낸다: `/api/langs`, `/api/capabilities`, 월드 목록·데모 목록, 월드 그래프(지역·연결), 세션 목록·세션 보기·지역 보기·이동·로그·NPC, GM 상태·왜곡도·소문·사건·씨앗·행적·타임라인, 에디터의 지역·지식·NPC·스코프 없음·보강.
  - 촬영은 headless Chrome(CDP)이다. 글꼴 바이트는 CDP `Network.loadingFinished`의 `encodedDataLength`를 `.woff2` 요청마다 더한다.
- 〔실행 메모 R-03〕 `@fontsource/gaegu` 제거는 Step 3이 아니라 Step 4.1(`index.css` import를 바꾸는 같은 커밋)에서 한다. 그래서 Step 3 커밋도 `vite build`가 된다.
- 〔실행 메모 R-04〕 대화상자는 **여덟 곳**이다(`<Modal`을 쓰는 여섯 곳 + MapCanvas·NewSessionForm 자체 대화상자). "아홉"은 Modal 컴포넌트까지 센 수였다. `web/src/SessionBar.tsx`는 GM 화면과 에디터의 WorldFileBar가 함께 쓰고 소유는 V6다. V2는 그 안의 select만 기계적으로 바꾼다.
- 〔실행 메모 R-05〕 Step 13.3은 이렇게 확인한다.
  - `docker build -t locus-web web` 뒤에 `docker run --rm locus-web nginx -t`로 설정을 검사한다.
  - `vite build` 산출물의 `assets/` 아래 파일 이름이 모두 해시를 가지는지 확인한다(`ls`로 `-<hash>.` 꼴).
  - `location /assets/`는 `location /`의 `try_files`보다 앞서 맞는다(접두어가 더 길다).
- 〔실행 메모 R-06〕 `WorldMap`은 지금 testid를 유지한다: `map-overlay`, `region-marker-<id>`, `player-marker-<id>`, `region-badge-<id>`, `connection-line*`. 지금 테스트에는 좌표값을 단언하는 곳이 없다. 끌기 테스트(editor.test:681)는 "옮기지 않음"만 본다. jsdom에서는 `getScreenCTM`이 없으므로 `meetMatrix(getBoundingClientRect(), viewBox)` 대체 경로를 탄다. rect가 0×0이면 정규화는 지금 `toNorm`처럼 `{0.5, 0.5}`를 준다.

---

## 2. 단계

### Step 1 — 기준선과 정리
- [x] 1.1 진행 기록 커밋: `feat/follow-up`에 남은 문서(audit, state, V1 code-summary, V1 계획 체크, V2 FD·NFR·리뷰, 이 계획)를 커밋한다(`docs(aidlc): V1 complete; V2 functional design and NFR light approved; V2 code plan`).
- [x] 1.2 기준선을 잰다: `pytest -q`, `npx vitest run`, `ruff check locus api tests`, `black --check locus api tests`, `npx tsc --noEmit`, `mypy locus api`(11), `npm audit --omit=dev`(0), `npm audit`(dev 포함, 수 기록), JS gzip(96.6 kB). code-summary § 1 표에 적는다.
- [x] 1.3 〔Step 1.3 정정〕 FD 글꼴 굵기 두 곳(위 NFR R-01).
- [x] 1.4 오류 본문 전체를 비교하는 pytest가 없는지 다시 확인한다(`grep -rn '== {"detail"' tests`, `.json()["detail"] ==`). 있으면 Step 2에서 함께 고친다.

### Step 2 — 서버 오류 `code` (FR-D9, BR-V2-15, TP-V2-8)
- [x] 2.1 `api/errors.py`:
  - `ApiError(HTTPException)`(`code` 속성)를 둔다.
  - 순서 있는 `ERROR_CODES: list[tuple[type[Exception], int, str]]`(FD domain-entities § 5의 1~19줄)와 `DEFAULT_CODES: dict[int, str]`를 둔다.
  - `http_error()`가 표를 위에서부터 보게 한다. 표에 없으면 지금처럼 다시 던진다.
  - `PLAY_ERRORS`는 그대로 둔다.
- [x] 2.2 `api/main.py`:
  - `starlette.exceptions.HTTPException` 처리기를 둔다. 본문은 `{"detail", "code"}`이고 `headers`를 넘긴다.
  - `RequestValidationError` 처리기에 `code: "validation_failed"`를 더한다.
  - `Exception` 처리기는 500 `{"detail": "internal error", "code": "error"}`를 낸다.
  - `/api/health`는 그대로 둔다.
- [x] 2.3 직접 던지는 자리에 code를 붙인다(`ApiError(..., code=…)`):
  - `routers/world.py`: `sessions_busy`, `sessions_open`, `bad_map_json`, `bad_world_file`, `service_unavailable`, `invalid_request`, `not_found`
  - `routers/world_editor.py`: `region_in_use`(객체 detail 유지), `service_unavailable`, `llm_unavailable`
  - `uploads.py`: `too_large`, `bad_image`, 그리고 `BodyLimitMiddleware`의 직접 `JSONResponse`에 `"code": "too_large"`
  - `deps.py`: `service_unavailable`, `unsupported_lang`
- [x] 2.4 `tests/api/test_error_codes.py`(TP-V2-8):
  - `ERROR_CODES` 각 줄을 매개변수화해 상태와 code를 단언하고, 하위 클래스가 먼저 맞는지 본다.
  - 라우터 직접 오류를 실제 요청으로 확인한다. `sessions_open`·`region_in_use`는 `session_ids` 객체가 유지되는지 본다.
  - `BodyLimitMiddleware` 413의 code를 확인한다(content-length 초과 요청).
  - 없는 라우트 404와 405의 code를 확인한다.
  - 422 검증 오류의 code와 지금 `detail`을 확인한다.
  - 500 처리기를 `TestClient(app, raise_server_exceptions=False)`로 확인한다.
- [x] 2.5 pytest·ruff·black·mypy(≤ 11)를 돌리고 커밋한다(`feat(api): error responses carry a code — ordered ERROR_CODES, Starlette/validation/500 handlers, body-limit 413 (V2 Step 2)`).

### Step 3 — 의존성 (NFR light § 3)
- [x] 3.1 `web/package.json` 의존을 바꾼다.
  - 더함: `@radix-ui/react-dialog` ^1.2.0, `@radix-ui/react-tabs` ^1.1.22, `@fontsource/noto-sans-kr` ^5.3.0, `@fontsource/nanum-myeongjo` ^5.3.0, `@fontsource/im-fell-english-sc` ^5.3.0
  - 지움: `@fontsource/gaegu`
  - 개발 의존에 더함: `fast-check` ^4.10.2
- [x] 3.2 `npm install`(잠금 파일 갱신)을 하고 `npm audit --omit=dev` 0을 확인한다. dev audit 수는 기준선보다 늘지 않아야 한다.
- [x] 3.3 tsc·vitest를 돌려 그대로 GREEN인지 보고 커밋한다(`build(web): Radix dialog and tabs, Noto Sans KR / Nanum Myeongjo / IM Fell English SC, fast-check; Gaegu out (V2 Step 3)`).

### Step 4 — 토큰·글꼴·테스트 바탕 (FR-D2·D3, BR-V2-04·06·07·09)
- [x] 4.1 `web/src/index.css`를 다시 쓴다.
  - `@theme`: FD domain-entities § 1.1~1.5의 색, 지도, 모양 토큰. `--font-display`·`--font-heading`·`--font-body`·`--font-story`.
  - `:root { color-scheme: dark }`, body 바탕과 글을 토큰으로 둔다.
  - `:focus-visible` 고리를 둔다.
  - 글꼴 import: Noto 400·700, 나눔명조 700, IM Fell SC 400.
  - 옛 토큰(`paper`, `ink` …)과 `.sketch-*`, `.ink-underline`은 **Step 12 끝에서** 지운다. 그때까지는 화면이 깨지지 않게 옛 이름을 새 값의 별칭으로 둔다. 예: `--color-paper-card: var(--color-surface)`, `--color-ink: var(--color-fg)`, `.sketch-border` = 새 경계. 뒤집힌 `bg-ink text-paper` 칩은 Step 12에서 손으로 고친다.
- [x] 4.2 `src/test/contrast.ts`(순수): WCAG 상대 휘도, 대비, 알파 합성. `__tests__/tokens.contrast.test.ts`(TP-V2-1)는 `index.css`를 읽어 domain-entities § 1.6 허용 쌍 표의 모든 칸을 단언한다.
- [x] 4.3 `src/test/render.tsx`: `renderWithShell(ui, {route, capabilities})`는 MemoryRouter, Toaster, capabilities 대역을 감싼다. Toaster는 Step 9에서 생기므로 이 단계에서는 자리만 둔다.
- [x] 4.4 `setupTests.ts`:
  - fast-check 전역 설정을 둔다. 시드는 `FC_SEED` 환경 변수 또는 난수이고, 출력한다(`fast-check seed: N (re-run: FC_SEED=N npx vitest run)`).
  - `afterEach(clearToasts)`를 둔다. `clearToasts`는 Step 9에서 생기고, 이 단계에서는 import만 준비한다.
- [x] 4.5 vitest·tsc를 돌리고 커밋한다(`feat(web): lamplit-tavern tokens, one dark theme, fonts by role, contrast test over the allowed pairs (V2 Step 4)`).

### Step 5 — 사전과 표기 규칙 (FR-D8, FR-L1, BR-V2-10~14)
- [ ] 5.1 `web/src/i18n.ts`를 `web/src/i18n/{index,ko,en}.ts`로 나눈다. 상태·`t`·`timelineText`·`logText`는 index에 둔다. import 경로 `./i18n`·`../i18n`는 그대로다(FD § 1.2). 키 일치 테스트를 유지한다.
- [ ] 5.2 새 키를 더한다(ko·en):
  - `enum.<kind>.<value>`: FD domain-entities § 4, 15종
  - `word.<measure>.<band>`: § 3, 8종
  - `error.<code>.title|action`, `error.status.<NNN>`, `error.network`, `error.unknown`: § 5
  - `notice.llmOff`
  - Step 9·10이 쓰는 `action.*`·`empty.*`·`hint.*`
- [ ] 5.3 `web/src/format/`:
  - `enums.ts`: 값 목록 한 곳
  - `labels.ts`: `enumLabel`
  - `bands.ts`: 단계 표, `bandOf`, `degreeWord`, `decayWord`, `numberWithMeaning`
  - `dates.ts`: `formatDate`·`formatDateTime`(`iso, lang?, timeZone?`), `turnLabel`, `turnAt`
- [ ] 5.4 테스트:
  - `format/enums.test.ts`(TP-V2-3, 전수)
  - `format/bands.prop.test.ts`(TP-V2-4, fast-check: 전부·단조·경계 ± 1e-9·자르기·NaN; 경계 예시)
  - `format/dates.test.ts`(TP-V2-5, UTC 고정)
  - `i18n.style.test.ts`(TP-V2-6: 새 접두어 키의 끝맺음)
  - 속성마다 변이를 한 번 넣어(예: 경계 비교를 `<=`로) 테스트가 잡는지 확인하고 code-summary에 적는다.
- [ ] 5.5 커밋한다(`feat(web): i18n split into ko/en modules, enum labels, measure bands, locale dates (V2 Step 5)`).

### Step 6 — 오류 문장 (FR-D9, BR-V2-16)
- [ ] 6.1 `api/http.ts`:
  - `HttpError`에 `code`·`detail`을 더한다. 본문 JSON을 한 번 파싱한다.
  - `http()`가 `init.signal`을 넘긴다.
  - `conflictKind`·`needsLlm`·`openSessionsOf`·`detailOf`는 이름과 반환을 유지하고, code를 먼저 본다. code가 없을 때의 옛 문자열 판단은 남긴다(옛 서버 대비).
- [ ] 6.2 `web/src/errors/describe.ts`: `describeError(err, lang?) → DescribedError`(BLM § 6.2의 순서, `raw`는 300자).
- [ ] 6.3 `errors/describe.prop.test.ts`(TP-V2-7): fast-check 생성기는 상태 400~599, 알려진 code ∪ 모르는 문자열 ∪ 없음, 본문(JSON·비JSON·빈 문자열)이다. 제목이 비지 않고 원문 본문을 섞지 않는지 본다. 표의 code마다 예시도 둔다. 지금 `http`·`conflictKind` 테스트도 GREEN이어야 한다.
- [ ] 6.4 커밋한다(`feat(web): HttpError carries code and detail; describeError picks a user sentence by code, then status (V2 Step 6)`).

### Step 7 — 요청 도우미와 capabilities (FR-C13, BR-V2-24·25)
- [ ] 7.1 `web/src/hooks/useResource.ts`: AbortController, 요청 번호로 늦은 답 버림, `reload` 중 data 유지, 언마운트 abort.
- [ ] 7.2 `web/src/hooks/useAction.ts`: **ref 가드**, `busy` 상태는 보이기용, `onDone`, `error = describeError`, `clearError`, 언마운트 뒤 무시.
- [ ] 7.3 `capabilities.ts`: 실패하면 `pending`을 비우고 실패 시각을 적는다. 다음 마운트에서 30초가 지났으면 다시 읽는다. 성공은 캐시한다. `llmOff`·`resetCapabilities`는 유지한다.
- [ ] 7.4 테스트:
  - `hooks/*.test.tsx`(TP-V2-13): 늦은 첫 답, 언마운트, **같은 틱 두 번 `run()`**, reload 중 data
  - `capabilities.test.ts` 고침(TP-V2-14): 가짜 시계, 실패 → 10초 마운트 요청 없음 → 31초 마운트 요청, 성공 캐시
- [ ] 7.5 커밋한다(`feat(web): useResource / useAction request helpers; capabilities retries a failed read after 30 s (V2 Step 7, RE-F09)`).

### Step 8 — 지도 바탕 (FR-D6·D7, BR-V2-18·19)
- [ ] 8.1 `web/src/map/geometry.ts`: `normalizeFromMatrix`, `toClient`, `meetMatrix(rect, viewBox)`(CTM이 없을 때), `toPixels`(옮김).
- [ ] 8.2 `map/labels.ts`: `labelWidth`, `placeLabels`(정해진 처리 순서, 후보 넷, `occupied`에 표식).
- [ ] 8.3 나머지 지도 파일:
  - `map/edgeStyle.ts`: 토큰 변수, 같은 쌍 한 번, 막힘 ×
  - `map/autoLayout.ts`: `layout.ts`에서 옮긴다
  - `map/focus.ts`: `focusBox`
- [ ] 8.4 `map/WorldMap.tsx`(FD frontend-components § 4)를 만든다.
  - viewBox 1000×625를 쓰고 컨테이너 너비를 따른다.
  - 지역 단계마다 모양이 다르다. 라벨은 받침 위에 둔다. 표식, 선택 고리, 플레이어 말을 그린다.
  - 모드: edit(끌기는 `draggable`일 때만, 그림 밖 누름은 무시), gm(`overlay` 고리·배지), play(`focus`·`reachableIds`·흐림).
  - `role="img"`와 `label`을 단다.
- [ ] 8.5 `web/src/MapOverlay.tsx`를 어댑터로 바꾼다. 지금 props를 `WorldMap` props로 넘긴다(`mapImageUrl` → `background`, `markerId` → `playerRegionId`, `regionFill`·`regionBadge` → `overlay`, `onBackground` → `onAddAt`).
- [ ] 8.6 `web/src/layout.ts`·`viz.ts`를 지운다. 쓰던 곳(MapOverlay, `pure.test.ts`)의 import를 고친다. `pure.test`의 색 단언은 `var(--color-map-blocked)`로 바꾼다(FD § 8.1).
- [ ] 8.7 테스트:
  - `map/geometry.prop.test.ts`(TP-V2-9, 왕복과 레터박스 밖 누름)
  - `map/labels.prop.test.ts`(TP-V2-10: 놓는 시점 빈 후보, 입력 순서 무관, 표식 안 가림. Emberleaf 12지역 겹침 수를 출력한다)
  - `map/edgeStyle.test.ts`(TP-V2-11)
  - 지금 MapOverlay 테스트(components·gm·editor.test)가 GREEN이어야 한다. editor.test:681 끌기는 `meetMatrix` 대체 경로로 지금 값을 내야 한다.
- [ ] 8.8 커밋한다(`feat(web): WorldMap — fits its container, matrix-based normalized coordinates, level shapes, plated labels, token edges; MapOverlay is an adapter (V2 Step 8)`).

### Step 9 — 프리미티브 (FR-D4, FR-S6, BR-V2-07·08·21~23)
- [ ] 9.1 다시 쓰거나 새로 만드는 것(FD frontend-components § 2):
  - 다시 씀: `ui/Button`, `Badge`, `Card`(`Panel`은 별칭), `Field`(label 필수), `Range`, `CommitRange`(모양만), `LocalizedText`·`InProgressBadge`(모양만)
  - 새로 만듦: `ui/Textarea`, `Select`(브라우저 `<select>`, testid는 안쪽에), `FileInput`(testid는 숨긴 input에), `Tabs`(Radix), `Dialog`·`ConfirmDialog`(Radix Dialog, `role="dialog"`, `error` 칸), `StatusView`, `InlineError`
- [ ] 9.2 `ui/toast.ts`(모듈 저장소: `toast`, key 교체, `clearToasts`)와 `ui/Toaster.tsx`를 만든다.
  - `aria-live`를 단다. 위험 알림은 `role="alert"`이고 사람이 닫을 때까지 남는다. 보통 알림은 6초 뒤 닫힌다.
  - testid는 자리 `notification-center`, 카드 `notif-<key|id>`이고 `data-region`을 단다.
- [ ] 9.3 `ui/index.ts` 내보내기를 고친다. `Modal`·`Toast`·`NotificationCenter`는 아직 지우지 않는다(Step 12에서 쓰는 곳을 바꾼 뒤 지움).
- [ ] 9.4 `ui/*.test.tsx`(TP-V2-12):
  - Dialog 초점·Esc·복귀·busy 두 번, ConfirmDialog의 error
  - Tabs 화살표
  - Select·FileInput의 라벨과 testid 위치
  - Button busy·크기 클래스
  - Toaster: 자동 닫힘, 위험 남음, 같은 key 교체, key 없음 쌓임
  - StatusView 넷
- [ ] 9.5 커밋한다(`feat(web): primitives on tokens — Button, Badge, Card, Field, Textarea, Select, FileInput, Tabs, Dialog, ConfirmDialog, Toaster, StatusView (V2 Step 9)`).

### Step 10 — 배치 틀 (FR-D5, BR-V2-17·20)
- [ ] 10.1 `web/src/layout/` 파일을 만든다.
  - `AppShell.tsx`: 머리띠, 메뉴(월드·플레이·GM·에디터, 잠김 규칙은 지금 AppNav와 같음), 640px 미만은 [메뉴]로 접음, `LangSwitch`, LLM 띠(testid `llm-notice`, `notice.llmOff`), Toaster
  - `SplitView.tsx`: 1024px 기준, `clamp`, 쌓는 순서
  - `Section.tsx`: 버튼, `aria-expanded`, `aria-controls`
  - `LangSwitch.tsx`: 지금 `features/play/LangToggle.tsx`를 옮긴다
- [ ] 10.2 `layout/*.test.tsx`(TP-V2-15): 세션 없음이면 GM 잠김, 에디터 링크, LLM 꺼짐이면 띠 1개, SplitView 두 영역과 순서. 지금 `components.test.tsx:561-579`의 AppNav 단언을 이리로 옮긴다.
- [ ] 10.3 `src/test/render.tsx`의 `renderWithShell`을 완성한다.
- [ ] 10.4 커밋한다(`feat(web): AppShell, SplitView, Section, LangSwitch (V2 Step 10)`).

### Step 11 — 화면 갈아 끼우기 1: 셸·알림·안내 (FD § 6, 기계적)
- [ ] 11.1 네 라우트(`HomePage`, `PlayPage`, `GmPage`, `EditorPage`)를 `AppShell`로 감싼다. `routes/AppNav.tsx`를 지운다.
- [ ] 11.2 `LlmNotice`를 쓰는 곳(Home·Play·Editor 라우트, GmHub)에서 안내를 지운다. 띠는 AppShell이 그린다. 버튼의 꺼짐과 까닭 글은 그대로 둔다.
- [ ] 11.3 `PlayPage`·`GmHub`의 알림 목록 상태와 `NotificationCenter`를 지우고 `toast({key})`로 바꾼다. key 규칙은 FD § 2를 따른다.
- [ ] 11.4 기존 단언을 고친다(FD § 8.1). `renderWithShell`로 감싸고, `llm.offNotice`·`play.noLlm` → `notice.llmOff`, gm.test:632·648을 바꾸고, `components.test`의 AppNav를 옮긴다. 고친 줄은 code-summary에 적는다.
- [ ] 11.5 vitest 전부 GREEN을 보고 커밋한다(`refactor(web): routes in AppShell; one LLM band; toasts replace the notification lists — mechanical, layouts unchanged (V2 Step 11)`).

### Step 12 — 화면 갈아 끼우기 2: 대화상자·select·파일 입력·옛 클래스 (FD § 6, 기계적)
- [ ] 12.1 대화상자 아홉 곳을 `ConfirmDialog`/`Dialog`로 바꾼다: GmHub, DeedPanel, ConfirmDelete, WorldFileBar, BuildPanel, DemoCard(이상 Modal), MapCanvas, NewSessionForm(자체 대화상자). 버튼 이름과 안쪽 testid를 유지한다. 그 뒤 `ui/Modal.tsx`·`Toast.tsx`·`NotificationCenter.tsx`·`LlmNotice.tsx`를 지운다.
- [ ] 12.2 `<select>` 13곳(9파일)을 `Select`로, 파일 입력 넷(EditorPage, GmPage, BuildPanel, WorldFileBar)을 `FileInput`으로 바꾼다.
- [ ] 12.3 옛 클래스를 바꾼다(FD BLM § 2.4 표). 뒤집힌 칩·버튼은 손으로 `Button variant="primary"`·`Badge tone="promoted"`로 바꾼다. 원색 값(`viz.ts`는 Step 8에서 끝남)이 남지 않게 한다.
- [ ] 12.4 `index.css`에서 옛 별칭 토큰과 `.sketch-*`·`.ink-underline`을 지운다.
- [ ] 12.5 vitest 전부 GREEN, tsc를 보고 커밋한다(`refactor(web): shared dialogs, select and file input; old ink/paper classes mapped to tokens — mechanical (V2 Step 12)`).

### Step 13 — 검사 테스트와 배치 설정
- [ ] 13.1 `__tests__/design.grep.test.ts`(TP-V2-2):
  - `web/src`의 `.ts`·`.tsx`(테스트 제외)에 원색 값과 옛 클래스 이름이 0이다.
  - `font-display`는 `layout/AppShell.tsx`·`index.css` 밖에서 0이다.
  - `package.json`에 gaegu가 없다.
  - `index.css`에 `color-scheme: dark`가 있고 `prefers-color-scheme`이 없다.
  - 대비 테스트에 알파 합성 규칙이 들어갔는지 확인한다(NFR R-04).
- [ ] 13.2 사전 검사: `notice.llmOff*`에 `.env`·`OPENAI`가 없다(BR-V2-20).
- [ ] 13.3 `web/nginx.conf`: `location /assets/ { … add_header Cache-Control "public, max-age=31536000, immutable"; }`(해시 파일만). `docker build -t locus-web web`으로 설정이 읽히는지 확인한다(compose 기동 없음).
- [ ] 13.4 커밋한다(`test(web): design grep checks; build(web): immutable cache for hashed assets (V2 Step 13)`).

### Step 14 — 게이트와 크기
- [ ] 14.1 `pytest`, `ruff`, `black`, `mypy locus api`(≤ 11), `tsc --noEmit`, `npx vitest run`, `npm audit --omit=dev` 0, dev audit 수(기준선 이하), `pytest tests/test_boundaries.py`를 돌린다.
- [ ] 14.2 `npx vitest run`을 두 번 다른 시드로 돌려 속성 테스트가 흔들리지 않는지 본다. 시드를 기록한다.
- [ ] 14.3 JS 크기: `npx vite build --outDir <스크래치>`로 빌드하고 `assets/*.js`의 gzip 합을 잰다. 예산은 125.6 kB다.
- [ ] 14.4 넘으면 사유를 적고 첫 화면 JS로 판정한다. 필요하면 `GmPage`·`EditorPage`를 `React.lazy`로 나누고 다시 잰다(NFR R-03).
- [ ] 14.5 Emberleaf 12지역 라벨 겹침 수를 적는다(TP-V2-10 출력). 0이 아니면 후보 간격을 고친다.

### Step 15 — 캡처와 글꼴 실측 (UOW-Q4=A, NFR-2·4)
- [ ] 15.1 역공학 때의 스크래치 도구(가짜 API `re-scratch/mock/server.mjs` + headless Chrome `shoot.mjs`)로 새 빌드를 띄운다. 홈·플레이·GM·에디터를 1280·390px로 찍는다. 저장소 밖에서 한다.
- [ ] 15.2 캡처를 비공개 Artifact 페이지 하나에 올리고 사람에게 링크를 드린다(시안 B와 나란히).
- [ ] 15.3 같은 도구의 네트워크 기록으로 화면별 `woff2` 바이트 합을 잰다(홈은 데모와 새 월드, 플레이 데스크톱·휴대폰). 최악값(전체 조각 합)과 함께 code-summary에 적는다(NFR R-02).

### Step 16 — 기록
- [ ] 16.1 `aidlc-docs/construction/V2-design-system/code/code-summary.md`를 쓴다. 담을 것:
  - 기준선과 결과
  - 단계별 변경
  - 고친 기존 단언
  - 의도된 동작 변경 C-1~C-4
  - 크기·글꼴 실측
  - PBT 변이 확인과 시드
  - 실행 메모 처리
  - 남은 일: 화면 배치는 V4·V6·V8, `String(e)` 51곳은 화면 유닛, 옛 키 정리는 V9
- [ ] 16.2 aidlc-state·audit를 갱신하고 커밋한다(`docs(aidlc): V2 code summary`).

---

## 3. 완료 조건 (unit-of-work V2 + 공통)
- 고른 시안의 토큰이 `@theme`에 있다. 화면 코드에 원색 값·옛 클래스가 없다. 원문 enum·`String(e)`가 새로 생기지 않는다(TP-V2-2).
- 허용 쌍 대비가 기준 이상이다(TP-V2-1).
- JS gzip ≤ 125.6 kB(넘으면 사유와 첫 화면 판정), 홈 글꼴 < 760 kB(실측).
- 오류 응답에 `code`가 실린다(가산). 기존 vitest는 FD § 8.1 목록대로만 고친다.
- 가짜 API 캡처(1280·390px)를 Artifact로 보인다.
- 게이트 GREEN: pytest, vitest, ruff, black, tsc, mypy ≤ 11, `npm audit --omit=dev` 0, 경계 테스트.
- code-summary가 있고, 이 유닛에서 닫기로 한 리뷰 지적의 처리를 적었다.

## 4. 추적
| 요구사항 · 규칙 | 단계 |
|---|---|
| FR-D2 토큰, BR-V2-01·04·05·06 | 4, 12.3~12.4, 13.1 |
| FR-D3 글꼴, BR-V2-09 | 3, 4.1, 13.1 |
| FR-D4 프리미티브, FR-S6, BR-V2-07·08·21~23 | 9, 12.1~12.2 |
| FR-D5 배치 틀, BR-V2-17·20 | 10, 11 |
| FR-D6·D7 지도, BR-V2-18·19 | 8 |
| FR-D8 표기, BR-V2-02·11~14 | 5 |
| FR-D9 오류, BR-V2-03·15·16 | 2, 6, 11.2 |
| FR-C13 도우미, FR-S5, BR-V2-24 | 7, 9 |
| RE-F09, BR-V2-25 | 7.3 |
| NFR-1 회귀 0 | 1.2, 11.4, 12.5, 14.1 |
| NFR-3 대비 | 4.2, 13.1 |
| NFR-4 크기, BR-V2-26 | 3, 14.3~14.4, 15.3 |
| NFR-6 PBT(02·03·07·08·09) | 4.4, 5.4, 6.3, 8.7, 14.2 |
| NFR-2 사람 확인(캡처) | 15 |
| 요구사항 리뷰 R-01(공유 대화상자) | 12.1 |
| Units 리뷰 R-01(파일 이동) | 5.1, 8.6, 10.1, 11.1 |
| Units 리뷰 R-03(V2 몫) | 1.1 메모, 커밋 메시지 |
| Units 리뷰 R-05(c)(capabilities) | 7.3 |
| FD 리뷰 R-10·R-11 | 4.4·9.2, 5.3 |
| NFR 리뷰 R-01~R-05 | 1.3, 15.3, 14.4, 13.1, 13.3 |
