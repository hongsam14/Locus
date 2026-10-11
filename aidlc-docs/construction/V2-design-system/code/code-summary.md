# V2 디자인 시스템 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V2 코드 생성을 마쳤다(Step 1~16). 고르신 B안(등불 아래 선술집)이 토큰, 글꼴, 프리미티브, 배치 틀, 지도, 표기 규칙, 오류 문장, 요청 도우미로 들어갔다. 네 화면은 그 위에서 B 톤으로 그대로 동작한다. 이 문서는 바뀐 것, 확인, 실측, 이탈, 남은 일을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V2-design-system-code-generation-plan.md`(16단계, 승인 2026-10-07; 〔실행 메모 R-01~R-06〕 포함).
캡처: 비공개 Artifact https://claude.ai/artifact/5kbtr4mDxcWmG3DA8xtBsu (네 화면 1280·390px, 크기 실측). 시안: https://claude.ai/artifact/MVUpR3nDzrrez29HHg1UmK (B 줄).

## 1. 기준선과 결과

| 항목 | 기준선 (Step 1.2, `371554d`) | 결과 (Step 14·15, `dcef428`) |
|---|---|---|
| pytest | 948 | **974** (+26 오류 code) |
| vitest | 202 (9 파일) | **381** (22 파일), 시드 11·22로 두 번 GREEN |
| ruff · black · tsc | clean | clean |
| mypy (`locus api`) | 11 (6 파일) | 11 (6 파일), 늘지 않음 |
| 경계 테스트 | 4 passed | 4 passed |
| `npm audit --omit=dev` | 0 | **0** |
| `npm audit` (dev 포함) | 5 (moderate 3, high 2) | 5 (같음; 정리는 V9 FR-T2) |
| JS gzip | 96.6 kB | **118.2 kB** (예산 125.6 kB) |
| CSS gzip | 4.2 kB (원본 15.7 kB) | **84.7 kB** (원본 261.6 kB) — § 6 |
| 홈 첫 화면 글꼴 | 762 kB (Gaegu 한글 두 굵기) | **121 kB** (데모만), 370 kB (한글 이름이 긴 월드 둘 더) |
| 390px 가로 스크롤 | 에디터·GM에 있음(UX-02) | 홈·플레이·GM·에디터 없음. 플레이 NPC 대화만 418px(V4) |

## 2. 단계별 기록

- **Step 1** 기준선. 진행 문서 커밋(`371554d`).
  - 〔Step 1.3 정정〕 FD domain-entities § 2와 BLM § 3의 글꼴 굵기를 나눔명조 700, Noto 400·700으로 고쳤다(NFR R-01).
  - 오류 본문 전체를 비교하는 pytest는 0건이다. `["detail"]`만 읽는 곳 둘(`test_gm_mode_api.py:132`, `test_uploads.py:78`)이 있다.
- **Step 2** 서버 오류 `code`(`48c4121`).
  - `api/errors.py`: `ApiError`, 순서 있는 `ERROR_CODES` 19줄, `DEFAULT_CODES`, `code_for`, `http_error`(표를 위에서부터 본다).
  - `api/main.py`: Starlette `HTTPException` 처리기(본문 없는 상태는 그대로, `headers` 전달), 검증 422에 `code`, `Exception` 500을 JSON으로.
  - 던지는 자리를 `ApiError`로 바꿨다: `uploads.py`(미들웨어 `JSONResponse`와 예외 넷), `deps.py` 셋, `routers/world.py` 여덟, `routers/world_editor.py` 넷. `region_in_use`는 객체 `detail`(`session_ids`)을 지킨다.
  - 테스트 `tests/api/test_error_codes.py` +26: 표 19줄, 하위 클래스 우선, 표 밖 예외 다시 던짐, 기본값, 처리기, 404·405·422·500, 503·언어, 미들웨어 413. 기존 테스트 넷에 `code` 단언을 더했다(`sessions_open`·`sessions_busy`, `region_in_use`, `bad_map_json`, `too_large` ×2).
- **Step 3** 의존(`80d3137`): `@radix-ui/react-dialog` ^1.2.0, `@radix-ui/react-tabs` ^1.1.22, `@fontsource/{noto-sans-kr,nanum-myeongjo,im-fell-english-sc}` ^5.3.0, 개발 의존 `fast-check` ^4.10.2. Gaegu는 Step 4.1에서 뺐다(〔실행 메모 R-03〕).
- **Step 4** 토큰(`a40c806`).
  - `index.css`를 다시 썼다: B 토큰(바탕·글·선·강조·상태·옅은 바탕·지도), 역할별 글꼴, 모양, `color-scheme: dark`, `:focus-visible`.
  - 대비 테스트(TP-V2-1): 허용 쌍 49칸을 계산한다. 알파 색은 바탕에 합성한 뒤 계산한다(NFR R-04).
  - fast-check 시드는 실행마다 하나다(`src/test/globalSetup.ts`가 출력하고 `setupTests.ts`가 적용).
- **Step 5** 사전과 표기 규칙(`1a0f9e3`).
  - `i18n.ts`를 `i18n/{index,ko,en}.ts`로 나눴다(import 경로는 그대로).
  - 키를 161개 더했다: enum 15종, 단계 낱말 8종, 오류 34 code, 안내, 조작 이름.
  - `format/`: `enumLabel`, `bandOf`·`degreeWord`·`decayWord`·`numberWithMeaning`, `formatDate`·`formatDateTime`(`timeZone?`, FD R-11), `turnLabel`·`turnAt`.
  - 테스트: enum 전수, 단계 속성(fast-check), 날짜(UTC 고정), 문체(키 접두어).
- **Step 6** 오류 문장(`d61e0e7`).
  - `HttpError.code`·`.detail`을 더했다. `conflictKind`·`needsLlm`은 code를 먼저 보고, code가 없는 서버를 위해 옛 문자열 판단을 남겼다.
  - `describeError`를 만들었다. 속성 테스트: 제목은 늘 있고 원문을 섞지 않는다.
- **Step 7** 요청 도우미(`2f039a9`).
  - `useResource`: abort, 요청 번호로 늦은 답 버림, reload 중 data 유지.
  - `useAction`: ref 가드라 같은 틱의 두 번째 호출도 막는다.
  - capabilities: 실패를 캐시하지 않고 30초 뒤 다음 마운트에서 다시 읽는다(RE-F09).
- **Step 8** 지도(`ba10694`).
  - `map/`: 화면 행렬 역으로 정규화(jsdom에서는 `meetMatrix`), 단계별 모양, 받침 라벨(정해진 순서의 탐욕 배치), 토큰 연결선, 쌍마다 한 번, play 확대 상자.
  - `MapOverlay`는 어댑터다. testid는 유지했다.
  - `layout.ts`는 `map/autoLayout.ts`로 옮겼고 `viz.ts`는 지웠다.
- **Step 9** 프리미티브(`a6255f9`).
  - Button, Badge, Card(+Panel 별칭), Field(라벨 필수), Textarea, Select(브라우저 `<select>`), FileInput, Tabs(Radix), Dialog, ConfirmDialog(Radix Dialog), toast 저장소와 Toaster, StatusView·InlineError.
  - `afterEach(clearToasts)`를 연결했다(FD R-10).
- **Step 10** 배치 틀(`e5bf93d`): AppShell(메뉴 규칙은 AppNav와 같음, LLM 띠 하나, Toaster), SplitView, Section, LangSwitch. 테스트 도우미 `renderWithShell`.
- **Step 11** 셸·알림·안내(`33a8f2f`, 기계적).
  - 네 라우트를 AppShell로 감쌌다. AppNav는 지웠다.
  - 화면마다 그리던 LLM 안내를 지웠다. 플레이 화면은 자기 view 값을 셸에 넘긴다(`llmOff` prop).
  - 알림 목록을 `toast({key})`로 바꿨다.
- **Step 12** 대화상자·select·파일 입력·옛 클래스(`d34e4f3`, 기계적).
  - 대화상자 **아홉** 곳(§ 5 이탈 1), select 13곳, 파일 입력 셋(EditorPage, GmPage, BuildPanel).
  - 옛 클래스를 새 토큰으로 바꾸고 별칭을 지웠다.
  - Modal·Toast·NotificationCenter·LlmNotice를 지웠다.
- **Step 13** 검사 테스트(`ad566ca`).
  - grep 테스트 다섯: 원색 값, 옛 클래스, `font-display`는 로고만, 디자인 시스템 코드의 `String(e)`, 테마와 글꼴.
  - nginx `/assets/` 불변 캐시(NFR R-05). 이미지에서 `nginx -t`가 통과했고, 산출물 680개 모두 해시 이름이다(〔실행 메모 R-05〕).
- **Step 14** 게이트와 크기는 § 1, Emberleaf 라벨 겹침은 0/8.
- **Step 15** 캡처와 글꼴 실측(§ 1, Artifact). 캡처에서 지도 결함을 하나 찾아 고쳤다(`dcef428`, § 5 이탈 2).

## 3. 의도된 동작 변경 (NFR light § 7)

| # | 바뀐 것 | 테스트 영향 |
|---|---|---|
| C-1 | 같은 key의 알림은 쌓지 않고 내용이 바뀐다. 턴 알림 key는 `turn:<지역>`이고, 플레이 경고는 `play:run`(위험, 남음)·`play:budget`·`play:llm`·`play:busy`·`play:turn`, GM 일괄은 `gm:bulk`다 | 문구 단언은 그대로 |
| C-2 | LLM 꺼짐 안내는 셸의 띠 하나이고, 모든 화면에서 같은 문장(`notice.llmOff`)이다. GM 허브 안의 안내는 없어졌다 | home.test:276, components.test(에디터), play.test:162, gm.test(GmHub 단독) |
| C-3 | 모든 오류 응답에 `code`가 있다. 잡히지 않은 500은 JSON `{"detail": "internal error", "code": "error"}`다 | pytest에 단언 더함 |
| C-4 | 화면이 B 톤이다(어두운 바탕 하나, 나눔명조·Noto Sans KR·IM Fell SC, Gaegu 없음). 대화상자는 Esc와 바깥 누름으로 닫힌다(바쁠 때 제외). 닫히면 초점이 연 버튼으로 돌아온다 | 클래스 단언 0 |

## 4. 고친 기존 테스트 (FD frontend-components § 8.1 + 실행 중 발견)

| 테스트 | 바꾼 것 | 까닭 |
|---|---|---|
| `pure.test.ts:2-3·32` | import를 `../map`으로, 막힘 색 단언을 `var(--color-map-blocked)`로 | 파일 이동, 토큰(C-4) |
| `components.test.tsx` | AppNav 두 테스트를 `layout.test.tsx`로 옮김, GmHub 턴 알림은 `renderWithShell` + 카드 글을 기다림, 에디터 띠 문장 | AppNav 삭제, 알림이 셸로(C-1), C-2 |
| `gm.test.tsx` (LLM 없음 테스트) | GmHub 단독에는 띠가 없음을 단언하고, 버튼 꺼짐과 까닭 단언은 유지 | C-2 |
| `home.test.tsx:276`, `play.test.tsx:162` | `llm.offNotice`·`play.noLlm` → `notice.llmOff` | C-2 |
| `play.test.tsx:138` | 알림 영역이 아니라 카드 글을 기다림 | **FD 목록 밖**: 알림 영역이 늘 있어서(라이브 영역은 미리 있어야 읽힌다) "영역이 생길 때까지"가 곧바로 끝난다 |

select 다섯 곳과 파일 입력 일곱 곳의 `fireEvent.change` 단언은 고치지 않았다. testid가 브라우저 control에 그대로 있다. 대화상자를 역할과 버튼 이름으로 찾는 단언도 그대로다.

## 5. 이탈

1. **대화상자는 여덟이 아니라 아홉 곳이다.** BuildPanel은 Modal을 쓰는 것과 별개로 그 자체가 직접 만든 대화상자 틀이었다. 요구사항 리뷰 R-01이 이름을 든 곳이라 이것도 공유 Dialog로 바꿨다. 〔실행 메모 R-04〕의 "여덟"이 놓쳤다.
2. **지도 크기(Step 15에서 찾아 고침).**
   - 새 지도는 칸의 너비를 따른다. 그래서 지금 GM·에디터의 좁은 칸에서는 너무 작게 줄었다(첫 캡처).
   - 어댑터에 너비 `min(800px, 100vw − 32px)`를 주어 데스크톱에서는 예전 크기, 휴대폰에서는 화면 너비가 되게 했다.
   - 그냥 800px로 두면 flex 칸이 같이 늘어 390px에서 가로 스크롤이 생겼다(재캡처로 확인).
3. **Dialog의 초점 복귀.** Radix는 자기 Trigger로만 초점을 돌려준다. 화면은 자기 버튼으로 대화상자를 열므로, 열 때 초점이 있던 요소를 기억했다가 돌려주게 했다. 프리미티브 테스트가 잡았다.
4. **`Dialog.testId`.** 대화상자 안의 제목과 form을 testid로 찾는 기존 테스트를 지키려고 Content에 testid를 다는 prop을 더했다.
5. **`AppShell.llmOff` prop.** 플레이 화면은 서버 capabilities가 아니라 자기 view의 `llm_available`로 안내를 보였다(EX-16). 그 동작을 지키려고 화면이 셸에 알려 줄 수 있게 했다. 띠는 여전히 하나다.
6. **오류 사전 키.** FD는 `error.status.<NNN>`을 적었지만, 상태를 기본 code로 바꿔 같은 `error.<code>.*` 문장을 다시 쓴다. 문장은 같고 키가 적다.
7. **테스트 위치.** FD는 `format/…test.ts` 같은 경로를 적었지만, 저장소 관례대로 모두 `src/__tests__/`에 두었다.
8. **WorldFileBar 파일 입력은 그대로 뒀다.** 이미 숨긴 input과 자기 버튼이라 브라우저 문구가 보이지 않는다(UX-09 충족). 토큰만 바꿨다.
9. **용어 정정.** FD BLM § 6.1은 `/api/health`라고 적었지만 실제 경로는 `/health`다. 동작은 그대로다.
10. **영어 표시 캡처.** localStorage를 바꾸고 다시 읽는 방법으로는 en이 켜지지 않아 ko와 같은 그림이 나왔다. 그래서 갤러리에서 뺐다. en 문구는 vitest가 본다.

## 6. 남은 일과 알려진 한계

- **CSS 크기**: gzip 84.7 kB(전 4.2 kB)다.
  - 한글 글꼴 조각 341개마다 `@font-face`(woff2+woff 경로) 선언이 붙기 때문이다. NFR-4 예산(JS·글꼴)에는 없는 항목이지만 첫 화면을 막는 CSS다.
  - 줄이는 길은 둘이다. 하나는 우리 `@font-face`를 만들어 woff 대체 경로를 빼는 것(절반쯤)이고, 다른 하나는 화면에 쓰는 굵기·조각만 남기는 것이다.
  - V9 또는 다음 주기 후보로 `next-cycle.md`에 올린다(V9 FR-C14).
- **글꼴 최악값**: 네 글꼴의 모든 조각은 5.8 MB다. 실제로는 화면에 나온 글자의 조각만 받고(홈 121~370 kB, 플레이 121~157 kB, GM 158 kB), 한 번 받은 조각은 캐시에서 다시 쓴다(`/assets/` 불변 캐시). 데모 한국어판(V3)이 들어오면 홈과 플레이의 조각 수가 늘어나므로 V3·V4 캡처에서 다시 잰다.
- **화면 배치와 문구**: V4(홈·플레이), V6(GM), V8(에디터)가 맡는다.
  - 옵션 라벨의 원문 enum(단계, 연결 종류, 사건 분류)
  - `String(e)` 51곳
  - 플레이 대화 화면 390px 가로 스크롤(418px)
  - GM 지도의 끌기(RE-F05)
  - 지도 바탕 그림의 대체 문구 "world map"
  - `MapOverlay` 어댑터 제거(V8 끝)
- **옛 사전 키**: `play.*`·`gm.*`·`editor.*`는 화면 유닛이 새 접두어로 옮긴다. 지우는 것은 V9가 한다. 문체 테스트의 LEGACY 셋(`nav.gmLocked` → V4, `confirm.regen*` → V6)도 거기서 닫힌다.
- **다른 유닛과의 계약**(unit-of-work-dependency § 3): V2가 내는 공개 API는 `ui/`·`layout/`·`map/`·`format/`·`errors/`·`hooks/`이고, 오류 본문은 `{"detail", "code"}`다.
  - V3: 데모 번역 파일 경로 거절이 생기면 `ERROR_CODES`에 줄을 더한다.
  - V5: `GmBusyError`를 2번 줄(`TurnInProgressError`) 앞에 더한다.
- **운영자 확인**: nginx의 `/assets/` 캐시 머리는 이미지 설정 검사(`nginx -t`)까지만 했다. 실제 응답 머리는 B&T에서 compose로 띄워 본다.

## 7. 리뷰 지적 처리

| 지적 | 처리 |
|---|---|
| Units 리뷰 R-01 (새 폴더·파일 이동) | Step 5.1(i18n), 8.6(layout.ts·viz.ts), 10.1(LangSwitch), 11.1(AppNav) |
| Units 리뷰 R-03 (V2 몫: package.json, 기계적 변경) | 커밋 메시지에 "mechanical", FD § 1.3 표 |
| Units 리뷰 R-05(c) (RE-F09) | Step 7.3 |
| 요구사항 리뷰 R-01 (공유 대화상자) | Step 12.1, 아홉 곳 |
| 요구사항 리뷰 R-05 (대비 확인 방법, 폭 상한) | 대비 테스트(Step 4.2), SplitView 값(Step 10) |
| FD 리뷰 R-10 (`clearToasts`) | Step 9.2 `setupTests.ts` |
| FD 리뷰 R-11 (`timeZone?`) | Step 5.3 |
| NFR 리뷰 R-01 (글꼴 굵기 FD 정정) | Step 1.3 〔Step 1.3 정정〕 |
| NFR 리뷰 R-02 (글꼴 최악값과 새 월드 실측) | Step 15.3, § 1·§ 6 |
| NFR 리뷰 R-03 (넘으면 첫 화면 판정) | 넘지 않았다(118.2 ≤ 125.6) |
| NFR 리뷰 R-04 (알파 합성) | 대비 테스트의 `composite` |
| NFR 리뷰 R-05 (`/assets/` 캐시) | Step 13.3 |
| 코드 플랜 리뷰 R-01~R-06 | 〔실행 메모〕대로 지켰다. R-04의 수는 아홉으로 바로잡았다(이탈 1) |

## 8. 속성 테스트와 변이 확인 (NFR-6)

| 속성 | 테스트 | 변이 | 결과 |
|---|---|---|---|
| 단계 함수: 전부·단조·경계(PBT-03) | `format.bands.prop.test.ts` | 경계 `<` → `<=` | 3개 실패(잡음). 자르기 제거는 같은 결과를 내는 동등 변이 |
| 오류 문장: 제목이 늘 있고 원문을 섞지 않음(PBT-03) | `errors.describe.prop.test.ts` | 모르는 code를 그대로 쓰기 | 예시 테스트가 잡음 |
| 지도 좌표 왕복(PBT-02) | `map.geometry.prop.test.ts` | `invert()` 부호 | 3개 실패(잡음) |
| 라벨 배치: 첫 빈 자리·입력 순서 무관(PBT-03) | `map.labels.prop.test.ts` | "언제나 첫 후보" | 잡음. 처음 쓴 속성은 "언제나 아래" 변이를 놓쳐 더 강하게 고쳤다 |
| `useAction` 같은 틱 가드 | `hooks.test.tsx` | 상태 기반 가드 | 잡음 |

생성기(PBT-07)는 경계 ± 1e-9를 섞은 실수, 실제 code와 모르는 문자열, `meet` 축척·이동 행렬과 확대 상자, 한글·라틴 이름이다. 시드는 실행마다 출력되고 `FC_SEED`로 다시 돌린다(PBT-08).
