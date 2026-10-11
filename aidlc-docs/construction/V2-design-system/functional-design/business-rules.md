# V2 디자인 시스템 — Business Rules

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기를 포함한다.
**지금 하는 것**: V2 Functional Design. 디자인 기반이 지킬 규칙과 각 규칙을 확인하는 방법을 정한다.

표기:
- **검증**은 그 규칙을 지키는지 보는 방법이다.
  - 테스트: vitest·pytest로 자동 확인
  - 검사: 테스트 안에서 하는 grep·계산
  - 사람: Build and Test 체크리스트
- 레이아웃 자동 게이트는 없다(Q7=B). 그래서 배치 규칙은 사람 확인과 캡처로 본다.

---

## A. 토큰과 모양

| ID | 규칙 | 근거 | 검증 |
|---|---|---|---|
| BR-V2-01 | 원색 값(`#rgb`, `#rrggbb`, `rgb(`, `hsl(`)은 `web/src/index.css`의 `@theme` 안에만 둔다. 화면·프리미티브·지도 코드는 의미 토큰만 쓴다. 옛 토큰 클래스(`bg-paper`, `bg-paper-card`, `text-ink`, `text-ink-soft`, `bg-ink`, `bg-ink/…`, `border-ink`, `accent-ink`, `text-paper`, `bg-highlight`, `sketch-border`, `sketch-shadow`, `.ink-underline`)는 남지 않는다. `font-display`는 로고에만 쓴다 | FR-D2, X2 BR-X2-1 | 검사: `web/src` 아래 `.ts`·`.tsx`(테스트 제외)에서 원색 값과 옛 클래스 이름을 grep하면 0건이다. `font-display`는 `layout/AppShell.tsx`와 `index.css` 밖에서 0건이다(파일 범위 검사) |
| BR-V2-02 | 화면에 원문 enum을 보이지 않는다. enum 값은 `enumLabel`로, 0~1 수치는 `format/`의 함수로 보인다 | FR-D8, UX-04 | 테스트: `format/` 전수 테스트(BR-V2-11). 화면은 V4·V6·V8에서 바꾸고, 그 유닛 테스트가 원문이 없음을 본다 |
| BR-V2-03 | 화면 코드에 `String(e)`·`String(err)`·`e.message`를 사용자 글로 새로 쓰지 않는다. 오류는 `describeError`를 거친다. 지금 51곳은 V4·V6·V8이 화면을 다시 쓰며 없앤다 | FR-D9, UX-06 | 검사: V2가 만든 파일과 V2가 고친 줄에는 0건이다. V9에서 저장소 전체가 0건이다 |
| BR-V2-04 | 테마는 하나(B)다. `:root`에 `color-scheme: dark`를 둔다. 테마를 `prefers-color-scheme`으로 바꾸지 않는다 | CQ2=A, Q1=B | 테스트: `index.css`를 읽어 `color-scheme: dark`가 있고 `prefers-color-scheme`이 없다 |
| BR-V2-05 | 조작 경계(입력·버튼·카드·Select·FileInput)는 `line-strong`을 쓰고, bg·chrome·surface 바탕 위에만 둔다(3.1 이상). 조작은 `sunken` 위에 두지 않는다(2.77). `line`은 장식 구분선에만 쓴다 | NFR-3(UI 경계 3:1), 리뷰 R-05 | 검사: 프리미티브 소스에 `border-line ` 단독 사용이 없다. 대비 표 테스트(BR-V2-06) |
| BR-V2-06 | 대비: 글 토큰과 경계 토큰은 `domain-entities.md` § 1.6 **허용 쌍 표**(정본)의 바탕 위에서만 쓴다. 표 밖 조합은 쓰지 않는다. 글은 4.5:1 이상, UI 경계는 3:1 이상이다. 비활성 글도 4.5:1 이상이다(지금의 `opacity-40`을 쓰지 않음) | NFR-3, 요구사항 리뷰 R-05 | 테스트: `tokens.contrast.test.ts`가 허용 쌍 표의 모든 칸을 WCAG 상대 휘도로 계산한다. 값은 `index.css`에서 읽는다. 표 밖 사용은 리뷰와 캡처로 본다 |
| BR-V2-07 | 초점이 보인다. 키보드로 닿는 모든 조작은 `:focus-visible`일 때 accent 2px 고리(2px 띄움)를 보인다. `outline: none`만 두고 대체가 없는 곳은 없다 | FR-S6 | 테스트: 프리미티브마다 초점 클래스가 있는지 렌더 테스트. 사람: 탭으로 한 바퀴 |
| BR-V2-08 | 누르는 영역은 휴대폰 폭(640px 미만)에서 44×44px 이상이다. 데스크톱의 작은 버튼(`size="sm"`)은 36px 이상이다 | NFR-7, 시안 B | 테스트: Button의 크기 클래스 단언. 사람: 390px 캡처 |

## B. 글꼴과 문체

| ID | 규칙 | 근거 | 검증 |
|---|---|---|---|
| BR-V2-09 | 글꼴 역할: 장식(IM Fell English SC)은 로고와 라틴 장식 줄에만 쓰고 한글에는 쓰지 않는다. 제목은 나눔명조, 본문·버튼·배지·입력·탭·알림은 Noto Sans KR, 내레이션은 나눔명조 700이다. Gaegu는 빠진다 | FR-D3, UX-01, A-3 | 검사: `package.json`에 `@fontsource/gaegu`가 없다. Button·Badge·Tabs에 `font-heading`·`font-display`가 없다 |
| BR-V2-10 | 문체는 사전 키의 첫 마디로 정한다(BLM § 4). 조작 이름(`action.` `nav.` `tab.`)은 마침표가 없고 "~요"·"~다"로 끝나지 않는다. 안내(`notice.` `error.` `confirm.` `empty.` `hint.`)의 ko는 "요." "요?" "요"로 끝나는 해요체다. 이야기(`story.` `log.` `timeline.`)의 ko는 "다."로 끝나는 해라체다. 값 이름(`enum.` `word.` `label.` `unit.`)은 마침표가 없다 | Q2=A | 테스트: `i18n.style.test.ts`가 새 접두어 키만 검사한다. 옛 키는 V4·V6·V8에서 옮기며 검사 대상에 들어온다 |

## C. 표기 규칙

| ID | 규칙 | 근거 | 검증 |
|---|---|---|---|
| BR-V2-11 | enum 값 목록은 `format/enums.ts` 한 곳에 둔다(`domain-entities.md` § 4). 모든 (kind, value)에 ko·en 라벨이 있다. 모르는 값은 원문을 보이고 개발 빌드에서 경고한다 | FR-D8, NFR-6 | 테스트: 값 집합을 전부 돌며 두 언어 라벨이 비어 있지 않고, ko 라벨이 원문 값(영문 소문자 식별자)과 같지 않음을 확인한다. 모르는 값 하나로 원문 반환을 확인한다 |
| BR-V2-12 | 단계 함수(§ 3 표)는 **전부**다: [0,1]의 모든 값에 정확히 한 단계를 준다. **단조**다: a ≤ b이면 단계(a) ≤ 단계(b)다. 경계는 아래를 넣고 위를 뺀다(마지막만 1 포함). 밖의 값은 자르고, `NaN`·`null`은 "—"다 | FR-D8, PBT-03 | 속성 테스트(fast-check): 생성기는 [0,1] 실수와 경계값 주변(경계 ± 1e-9)을 섞는다. 경계 예시 테스트도 둔다 |
| BR-V2-13 | 플레이어 화면은 0~1 수치를 숫자로 보이지 않고 단계 낱말만 보인다. GM·에디터 화면은 숫자 두 자리와 단계 낱말을 함께 보인다(`numberWithMeaning`) | FR-D8 | V4·V6·V8 화면 테스트. V2는 함수 테스트 |
| BR-V2-14 | 날짜는 표시 언어의 로캘로, 보는 사람의 시간대로 보인다. 브라우저 로캘은 쓰지 않는다 | UX-07, 리뷰 R-09 | 테스트: `timeZone: "UTC"`로 고정하고 `"2026-10-02T12:00:00Z"`를 보면 en은 "Oct 2, 2026", ko는 "2026년 10월 2일"이다 |

## D. 오류

| ID | 규칙 | 근거 | 검증 |
|---|---|---|---|
| BR-V2-15 | 앱이 내는 모든 오류 응답은 `{"detail": …, "code": "<문자열>"}`이다. 범위는 BLM § 6.1의 네 자리다: Starlette `HTTPException` 처리기(라우트 404·405 포함), 검증 실패 처리기, 잡히지 않은 예외(500) 처리기, `BodyLimitMiddleware`의 직접 413. `/api/health`의 503 상태 보고는 범위 밖이다. `detail`의 모양은 지금과 같다(문자열 또는 객체). `code`는 `ERROR_CODES`의 순서 있는 표에서 처음 맞는 줄이고, 없으면 상태별 기본이다. `region_in_use`는 표가 아니라 라우터가 객체 `detail`로 던진다 | FR-D9, NFR-5, 설계 Q6=A, 리뷰 R-03 | 테스트(pytest): 표의 예외마다 상태·code. 하위 클래스가 기반보다 먼저 맞음(`UnsupportedWorldFile` → 422, `RunFinishedError` → `run_finished`). 라우터 직접 오류(`sessions_open`, `sessions_busy`, `too_large` …). `region_in_use`와 `sessions_open`의 `detail`이 `session_ids`를 가진 객체 그대로임. content-length 초과 413이 미들웨어에서 `code`를 가짐. 없는 라우트 404·405, 422 검증 오류, 500의 `code` |
| BR-V2-16 | `describeError`는 **언제나** 제목을 준다(빈 문자열 아님). 우선순위는 code 사전 문장 → 상태 문장 → network → unknown이다. 원문은 `raw`에만 두고 제목에 섞지 않는다. 사전의 모든 `error.<code>.title`은 ko·en이 있다 | FR-D9, UX-06 | 속성 테스트(fast-check): 생성기는 (상태 ∈ 400~599, code ∈ 알려진 code ∪ 모르는 문자열 ∪ 없음, 본문 ∈ JSON·비JSON·빈 문자열)다. 제목이 비지 않고 원문 본문을 포함하지 않는다. 예시 테스트: 표의 code마다 문장 |

## E. 배치·지도

| ID | 규칙 | 근거 | 검증 |
|---|---|---|---|
| BR-V2-17 | 어느 폭(320~1920px)에서도 가로 스크롤이 생기지 않는다. 1024px 이상에서 SplitView는 2열이고 옆 패널은 320~420px이며 자체 스크롤을 가진다. 1024px 미만에서는 1열로 쌓인다. 본문 최대 너비는 1240px이고 좌우 여백은 24px(640px 미만 16px)이다 | FR-D5, UX-02·03, 요구사항 리뷰 R-05 | 사람: 1280·390px 캡처(UOW-Q4=A)와 B&T 체크리스트. 테스트: SplitView가 두 영역과 `asideLabel`을 렌더하고 쌓는 순서를 따른다 |
| BR-V2-18 | 지도는 컨테이너 너비에 맞춰 줄어든다(고정 800×500 없음). 누름·끌기 좌표는 그려진 영역 기준으로 정규화한다. `toClient`와 `normalizeFromMatrix`는 서로 역이다 | FR-D6 | 속성 테스트(fast-check, PBT-02): 생성기는 (정규화 점 ∈ [0,1]², viewBox, `meet` 축척과 이동을 가진 행렬)이고, 왕복 오차가 1e-9 이하다. 예시: 레터박스(좌우 여백) 상태에서 그림 밖 누름은 [0,1] 밖이 되어 `onAddAt`이 불리지 않는다. 끌기(`onMove`)는 [0,1]로 자른다(지금 `drag.ts`의 `toNorm`과 같음) |
| BR-V2-19 | 라벨은 받침 위에 그린다. `placeLabels`는 정해진 순서(지금 위치 → 선택 → 갈 수 있음 → 나머지, 무리 안에서는 y·x·id)로 라벨을 하나씩 놓는다. **놓는 시점에** 후보 넷(아래·오른쪽·왼쪽·위) 가운데 이미 놓인 받침·모든 표식과 겹치지 않는 첫 자리에 둔다. 그런 자리가 없으면 아래에 둔다. 결과는 입력 순서와 상관없이 같다. 지역 단계는 모양과 크기로 구별한다(대륙·지방은 표식 없이 라벨, 마을 동그라미, 구역 네모, 지형 세모) | FR-D7, UX-18, UX-40, 리뷰 R-09 | 속성 테스트(fast-check, PBT-03): 생성기는 지도 위 점 2~30개와 이름 길이 1~12자다. (1) 각 라벨은 놓는 시점에 빈 후보가 있었다면 그 후보에 있다. (2) 입력을 섞어도 결과가 같다. 예시 테스트: Emberleaf 12지역의 겹침 수를 코드 단계에서 재서 기록한다. 0이 목표이고, 아니면 후보 간격을 고친다 |
| BR-V2-20 | LLM 꺼짐 안내는 한 화면에 한 번만 보인다(AppShell 띠). 문장에 `.env`·환경 변수 이름이 없다. 꺼진 버튼은 까닭을 보조 글로 보이되 같은 띠를 다시 그리지 않는다 | FR-D9, UX-08 | 테스트: LLM 꺼짐 capabilities로 AppShell을 그리면 안내가 정확히 1개다. 사전 검사: `notice.llmOff*`에 `.env`·`OPENAI` 문자열이 없다 |

## F. 프리미티브 동작

| ID | 규칙 | 근거 | 검증 |
|---|---|---|---|
| BR-V2-21 | Dialog: 열리면 첫 조작에 초점이 가고, 안에 갇히고, 닫히면 연 요소로 돌아온다. Esc로 닫힌다. 제목이 `aria-labelledby`다. ConfirmDialog의 `busy` 동안 확인은 다시 눌리지 않는다 | FR-D4, FR-S6 | 테스트: Testing Library로 초점 위치·Esc·복귀·`busy` 중 두 번 누름 |
| BR-V2-22 | Toaster는 앱에 하나다. 알림은 `aria-live="polite"`이고 위험 알림은 `role="alert"`이다. 보통 알림은 6초 뒤 닫히고 위험 알림은 사람이 닫을 때까지 남는다. `key`가 같은 알림이 보이는 동안 다시 오면 그 카드의 내용을 바꾸고 시간을 다시 센다. `key`가 없으면 쌓인다(BLM § 10, 동작 변경) | FR-D4, 리뷰 R-02 | 테스트: 가짜 시계로 자동 닫힘과 위험 알림 남음, 같은 key 두 번 → 카드 1장(둘째 내용), key 없음 두 번 → 2장 |
| BR-V2-23 | Tabs는 `tablist`/`tab`/`tabpanel`이고 화살표 키로 옮긴다. Select·FileInput은 보이는 라벨을 가진다. 아이콘만 있는 버튼은 `aria-label`을 가진다 | FR-S6 | 테스트: 역할·이름 쿼리(`getByRole(name)`) |
| BR-V2-24 | `useResource`는 키가 바뀌거나 언마운트되면 이전 요청을 abort하고, 지금 키의 답만 반영한다. 첫 읽기 동안 state는 `loading`이고 빈 상태가 아니다. `useAction`은 진행 중 다시 불리면 실행하지 않는다. 가드는 ref라 같은 틱의 두 번째 호출도 막는다 | FR-C13, FR-S5, #14, #12(웹), 리뷰 R-07 | 테스트: 늦게 오는 첫 답과 빠른 둘째 답(둘째만 남음), 언마운트 뒤 답(상태 안 바뀜), **같은 틱에 `run()` 두 번 동기 호출 → 한 번 실행** |
| BR-V2-25 | capabilities: 실패한 읽기는 캐시하지 않는다. 다음 `useCapabilities` 마운트 때 마지막 실패에서 30초가 지났으면 다시 읽고, 30초 안이면 읽지 않는다(타이머 없음). 성공한 답은 페이지 수명 동안 쓴다. 모를 때는 아무것도 끄지 않는다 | RE-F09, BR-U8-26, 리뷰 R-07 | 테스트(가짜 시계): 실패 → 10초 뒤 마운트는 요청 없음 → 31초 뒤 마운트는 다시 요청. 성공 뒤 다시 요청 없음 |

## G. 크기 (NFR light에서 값 확정)

| ID | 규칙 | 근거 | 검증 |
|---|---|---|---|
| BR-V2-26 | JS gzip 합은 기준 96.6 kB의 1.3배(≈126 kB) 이내다. 첫 화면(홈)에서 받는 글꼴 합은 760 kB 미만이다 | NFR-4 | 빌드 뒤 측정 스크립트(NFR light에서 방법을 정함). 넘으면 사유를 code-summary에 적는다 |
