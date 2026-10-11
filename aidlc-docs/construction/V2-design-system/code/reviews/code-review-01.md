# V2 디자인 시스템 — Code Review 01

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**이 리뷰가 하는 것**: 승인된 V2 코드(`git diff 371554d..0f14710`, 커밋 14개)가 승인된 설계(BR-V2-*)를 지키는지, 그리고 "기계적" 교체가 기존 동작을 깨지 않았는지 결함 위주로 확인한다. 코드는 고치지 않았다(리뷰 전용).
- 크기: `web/src` 위주 134파일, +5589/−1895(테스트 포함).
- 대상: `api/{errors,main,uploads,deps}.py`·`routers/{world,world_editor}.py`, `web/src/{ui,hooks,errors,format,i18n,layout,map}/`, `api/http.ts`, `capabilities.ts`, `MapOverlay.tsx`, 네 라우트와 `features/**`의 교체, `index.css`, `nginx.conf`, 새 테스트.

**방법**: U8과 같은 방식을 작게 돌렸다.
- 탐색 각도 다섯을 병렬로 돌렸다: 서버 오류 code / 프리미티브·요청 도우미 / 지도 / 기계적 화면 교체 / 사전·표기·테스트·빌드.
- 각도마다 가능한 것은 버리는 vitest·스크립트로 재현했다. 재현물은 세션 scratchpad에만 두었고, 저장소에는 잠깐 복사해 돌린 뒤 지웠다. 리뷰 뒤 `git status`는 리뷰 전과 같다.
- 이 세션이 상위 후보의 코드 자리를 직접 다시 읽어 확인했다(§ 1의 1~7).
- 판정: **C** = 입력·결과로 재현했거나 코드로 기제가 확정됨. **P** = 기제는 실재하지만 브라우저 히트 테스트·배포 설정처럼 이번에 직접 돌리지 못한 조건에 달림.

## 1. 지적 (심각도 순)

| # | 위치 | 지적 | 판정 | 심각도 | 권장 조치 |
|---|---|---|---|---|---|
| 1 | `features/editor/ConfirmDelete.tsx:45`, `ui/ConfirmDialog.tsx:44·50` | 지울 수 없는 지역(열린 세션이 서 있음, BR-U3-9/16)의 삭제 대화상자는 `busy={busy \|\| blocked}`를 넘긴다. 옛 Modal에서 `busy`는 확인 버튼만 껐다. ConfirmDialog는 `busy`일 때 [취소]도 끄고 Esc·바깥 누름도 무시한다. 그래서 막힌 삭제 대화상자는 닫을 길이 없고, 확인 버튼은 돌고 있는 것처럼 보인다. 새로고침만 빠져나간다 | C | **high** | `busy`와 "확인만 끄기"(`confirmDisabled`)를 가른다. 막힘은 확인만 끈다. 막힌 계획으로 열어 [취소]·Esc가 닫는지 테스트한다 |
| 2 | `api/routers/world.py:157·188·404`, `api/deps.py:42`, `web/src/api/http.ts:124-127` | 키 없는 서버에서 월드 빌드는 `need_service`를 거쳐 `503 … "code": "service_unavailable"`이다. `needsLlm`은 이제 code를 먼저 보므로 false를 준다. BuildPanel이 "LLM 키가 필요합니다" 대신 원문 `Error: 503 …`을 보인다(BR-U8-27 퇴행). capabilities를 모르거나 낡았을 때 생긴다. 같은 조건의 NPC 초안은 `llm_unavailable`이라 둘이 어긋난다 | C(서버·클라이언트 재현) | **medium** | 세 자리는 `llm_unavailable`을 보낸다(`need_service`에 code 인자). FD domain-entities § 5의 "deps·라우터의 … unavailable → service_unavailable" 줄도 정정한다. 빌드 503 vitest를 더한다 |
| 3 | `ui/Toaster.tsx:60`, `ui/Dialog.tsx` | 모달 대화상자가 열려 있을 때 알림 카드를 누르면(닫기 ×) Radix가 "바깥 누름"으로 보고 대화상자를 닫는다. 카드가 `pointer-events-auto`라 눌리기 때문이다. NewSessionForm이 닫혀 입력이 사라지거나 확인 질문이 취소된다 | C | **medium** | Dialog의 `onPointerDownOutside`에서 대상이 알림 영역 안이면 `preventDefault` |
| 4 | `map/WorldMap.tsx:328` | 라벨 묶음이 `pointerEvents="none"`이라 지역 이름을 눌러도 지역이 골라지지 않는다. 옛 지도는 이름이 표식 `<g>` 안에 있어 눌렸다. 에디터의 [지역 추가] 도구에서는 이름을 누르면 svg 빈 곳 누름이 되어 그 자리에 새 지역 폼이 열린다 | P(기제 확정, 브라우저 히트 테스트 미재현) | **medium** | 받침을 누르면 그 지역을 고르게 한다(받침에 `onClick`·포인터 허용, 또는 라벨을 지역 `<g>`로) |
| 5 | `map/WorldMap.tsx:135`, `map/labels.ts:31-41·67-68` | 고른 지역·갈 수 있는 지역은 자기 표식 자리를 `r+7`로 잡는데 라벨 후보는 `r+4`에서 시작한다. 네 후보가 모두 자기 자리와 겹쳐 늘 "아래"로 떨어지고, 아래 이웃 표식을 덮을 수 있다. 속성 테스트는 모든 표식을 `r+2`로 모델링해 놓쳤다 | C | **medium** | 라벨을 놓을 때 자기 표식 자리는 빼고 본다(또는 후보 간격을 자기 고리 바깥에서 시작). 속성 테스트 생성기에 고른 지역을 넣는다 |
| 6 | `ui/FileInput.tsx:33-49` | 숨긴 `<input type=file class="sr-only">`가 탭 순서에 남아, 보이지 않는 1px 요소에 초점이 먼저 간다(BR-V2-07). 보이는 버튼의 이름은 "파일 고르기"뿐이라 BuildPanel에 같은 이름 버튼이 넷이다(BR-V2-23) | C | **medium** | input에 `tabIndex={-1}`, 버튼 `aria-labelledby`를 라벨+버튼으로 |
| 7 | `routes/EditorPage.tsx:~149`, `routes/GmPage.tsx:~158` | 지도 그림을 고른 뒤에도 "아직 고른 파일이 없어요"가 그대로다. `chosen`을 넘기지 않는다. 옛 브라우저 input은 이름을 보였다 | C | medium-low | 고른 이름을 상태로 두고 `chosen`으로 넘긴다 |
| 8 | `ui/toast.ts`, `ui/Toaster.tsx:59`, `routes/PlayPage.tsx` | 알림 저장소가 앱 전역이라 `play:run`(위험, 스스로 닫히지 않음) 카드가 다른 화면·다른 세션으로 가도 남아 오른쪽 위(언어 전환·메뉴 버튼)를 가린다. 옛 알림 목록은 화면 상태라 이동하면 사라지고 6초 뒤 닫혔다 | C | low-medium | 라우트(경로) 이동 때 알림을 비우거나, 화면이 자기 key의 카드를 떠날 때 닫는다 |
| 9 | `web/nginx.conf` | gzip이 꺼져 있다(nginx:alpine 기본 `#gzip on;`). NFR-4 크기는 gzip 기준인데 브라우저는 JS 약 390 kB, CSS 262 kB를 그대로 받는다. `index.html`에 `Cache-Control: no-cache`가 없어 "새 빌드는 다음 로드에 닿는다"는 주석이 보장되지 않는다. V2 전부터 있던 틈이지만 V2가 CSS를 15.7 → 262 kB로 키웠다 | P(설정 추론, compose 미기동) | low-medium | `gzip on; gzip_types text/css application/javascript …`, `location = /index.html { add_header Cache-Control "no-cache"; }`. B&T에서 실제 머리를 본다 |
| 10 | `map/WorldMap.tsx:260-284` | 대륙·지방 지역은 골라도 선택 고리가 없고, GM 상태 겹쳐 보기의 색·고리(`region-fill-*`)가 빠진다. 데모에는 대륙 1·지방 3이 있다 | C | low-medium | 이름 둘레에 선택 표시, 겹쳐 보기 색은 이름 받침 색으로 |
| 11 | `map/WorldMap.tsx:263-272` | 대륙·지방 이름(26·18 단위, 넓은 자간)이 넓은 누름 영역이 되어 그 위에서 [지역 추가]·끌기·연결선 누름을 가로챈다 | P | low-medium | 이름 글에는 포인터를 끄고 작은 누름 영역만 남긴다 |
| 12 | `map/labels.ts:67` | 라벨 후보가 지도 경계를 보지 않는다. 아래 끝(y≈0.99)이나 좌우 끝의 지역 이름이 지도 밖으로 잘린다. 끌기는 0..1로 자르므로 끝으로 끈 지역의 이름이 사라진다 | C | low-medium | 경계 밖 후보는 겹친 것으로 친다 |
| 13 | `ui/Toaster.tsx`(× 32px), `layout/LangSwitch.tsx`(36px), `ui/Tabs.tsx`(40px) | 휴대폰 폭의 누름 영역이 44px보다 작다(BR-V2-08) | C(코드) | low | 640px 미만에서 `min-h-11 min-w-11` |
| 14 | `hooks/useResource.ts:38·57` | 키가 `null`이 되어도 옛 data가 `ready`로 남는다(설계: `loading`). 키 A→B에서 B가 실패하면 A의 data와 `error`가 같이 남는다. 오류 뒤 `reload()`는 답이 올 때까지 `error`다. 아직 쓰는 화면은 없다 | C | low | null 키는 `loading`·data 비움, 키가 바뀌면 data 비움, reload는 `loading`으로 |
| 15 | `ui/toast.ts:35` | 같은 key 카드를 바꿀 때 새 알림에 없는 칸(body·action·region)이 옛 값으로 남는다(BR-V2-22 "내용을 바꾼다"). 지금 호출부는 `body: x \|\| undefined`를 넘겨 우연히 안전하다 | C | low | 바꿀 때 key·id만 남기고 칸을 통째로 바꾼다 |

## 2. 낮은 심각도와 정리 (지금 고치거나 소유 유닛으로)

| 위치 | 지적 | 제안 |
|---|---|---|
| `format/bands.ts:105` | `numberWithMeaning`이 숫자는 반올림하고 단계는 원값으로 골라 "0.15 · 거의 그대로"가 나올 수 있다(0.1499…) | 반올림한 값으로 단계를 고른다 |
| `format/dates.ts:30·35` | `turnLabel`·`turnAt`에 FD의 `lang?` 인자가 없다 | 인자를 더한다 |
| `errors/describe.ts:57` | 네트워크 판정 정규식이 느슨해 `TypeError("…fetchX is not a function")`이 "서버에 닿지 못했어요"가 된다 | 브라우저 문구(`Failed to fetch`, `NetworkError when attempting to fetch resource.`, `Load failed`)만 |
| `ui/Dialog.tsx:43-46` | 확인한 동작이 연 버튼을 지우면(삭제 행) 초점이 body로 간다 | 연 요소가 문서에 없으면 대화상자의 앞 요소나 main으로 |
| `capabilities.ts:24-27` | `resetCapabilities()`가 진행 중 읽기를 끊지 않아 테스트 사이에 실패 시각이 샌다(테스트만) | 세대 번호 |
| `ui/Button.tsx` | 기본 `type`이 없어 form 안의 FileInput·StatusView 버튼이 제출 버튼이 된다(지금은 잠복). `busy`의 native disabled로 초점이 body로 빠진다 | FileInput·StatusView 안 버튼에 `type="button"`; busy는 `aria-disabled`로 |
| `hooks/useAction.ts` | `onDone`이 던지면 성공한 쓰기가 오류로 보인다 | `onDone`을 try 밖에서 |
| `ui/StatusView.tsx` | `state="error"`인데 `error`가 없으면 children을 그린다 | 일반 오류 문장을 그린다 |
| `routes/EditorPage.tsx:173` | 지역 삭제 요약(자식·NPC·연결·지식 수)이 6초 뒤 닫힌다(옛 인라인 Toast는 닫을 때까지 남음) | V8: 결과를 인스펙터 안에 남긴다 |
| `features/editor/BuildPanel.tsx:81-93` | Esc·바깥 누름이 이제 [닫기]와 같아 한가한 패널의 메모·파일·리포트를 지운다 | V8, 또는 입력이 있으면 바깥 누름을 막는다 |
| `features/play/ActionBar.tsx:83`, `ui/Button.tsx:14`, `ui/Toaster.tsx:32` | 선언 입력의 `outline-none`이 초점 고리를 지운다(V2 전부터). 보조 버튼 hover와 입력 focus가 `sunken` 위의 `line-strong`(2.77:1, 허용 표 밖). 알림의 `text-event`가 `sunken` 위(8.9:1, 표에 없음) | ActionBar는 V4. 버튼 hover는 경계를 `fg`로, 표에 `event`/sunken 줄을 더하거나 카드 바탕을 surface로 |
| 화면 select·지도 선택 칸 | "배치 그대로"가 엄밀히는 아니다: Select가 44px·보이는 라벨이라 몇 줄이 높아졌고, 지도 선택 칸이 상태 줄 안의 점선 상자가 됐다 | V4·V6·V8 배치 때 정리 |
| `map/WorldMap.tsx:216-231` | 연결선이 1000단위 안에서 그려져 실제 굵기가 줄었다(약 1.8px, 전 4.2px). 막힘 점선의 틈은 눌리지 않는다 | 투명한 넓은 누름 선을 겹친다 |
| `map/WorldMap.tsx:350-361` | 배지 자리를 라벨 배치가 잡지 않아 위쪽 받침의 배지가 자기 표식 위에 그려진다 | 배지 높이를 받침 크기에 넣는다 |
| `map/WorldMap.tsx` play 모드 | 확대할 때 바탕 그림이 viewBox를 따르지 않는다(아직 쓰는 화면 없음) | V4에서 그림을 svg `<image>`로 |
| `format/enums.ts`, `format.enums.test.ts` | "서버에 값이 더해지면 빠진 라벨로 드러난다"는 주석이 사실이 아니다. 백엔드 enum과 대조하는 테스트가 없다 | 백엔드 enum 파일을 읽어 대조하는 테스트 |
| `__tests__/design.grep.test.ts:24` | 원색 검사가 `#rrggbbaa`·`#rgba`·`oklch(`·이름 색·Tailwind 기본 팔레트 클래스(`text-red-600`)를 놓친다. `@theme`가 기본 팔레트를 지우지 않는다 | 정규식을 넓히고 `--color-*: initial`로 기본 팔레트를 지운다 |
| BR-V2-09 | "Button·Badge·Tabs에 `font-heading` 없음" 검사가 없다 | grep 테스트에 더한다 |
| 파일을 읽는 테스트 | `src/…`·`../locus/…` 상대 경로라 vitest를 web/ 밖에서 돌리면 ENOENT(CI는 web/이라 괜찮음) | 주석으로 전제를 적거나 경로를 루트 기준으로 계산 |
| 약한 테스트 | 해라체 검사 대상 키 0개, `hooks.test`의 언마운트 뒤 data 단언은 실패할 수 없음, 레터박스 속성의 첫 조건은 왕복 속성의 결과, Emberleaf 라벨 테스트가 0개 마을에도 통과 | 단언을 고친다 |
| `tests/api/test_error_codes.py:120-121` | 언어 오류 단언이 400·503 둘 다 받는다(실제는 400 `unsupported_lang`) | 400과 code로 못박는다 |
| `String(e)` 화면 | 원문에 `,"code":"…"`가 더해져 보인다(가산 변경의 결과) | 화면 유닛이 `describeError`로 바꿀 때 사라진다 |
| `CLAUDE.md:21` | `src/i18n.ts`·`ui/LlmNotice`를 아직 적는다 | 주기 끝 문서 정리(V9) 또는 지금 |

## 3. 결함 아님

- **연결 선택의 방향**: `uniqueEdges`는 무게가 같으면 먼저 온 방향을 남긴다. 데모는 쌍마다 두 방향이 같은 무게라, 에디터가 연결을 고를 때 인스펙터가 다른 쪽 끝을 열 수 있다. 에디터는 쌍을 연결 하나로 다루므로(BR-U3-10) 결함은 아니다. 강조는 두 방향 모두 된다.
- **`play:busy` key 하나에 두 문장**: "세션 닫힘"과 "턴 진행 중"이 같은 key다. 실제 순서(진행 중 → 닫힘)에서는 새 문장이 옛 문장을 바르게 바꾼다. 잃는 것이 없다.
- **BuildPanel 안의 교체 질문에서 Esc**: 질문만 닫히고 패널과 메모는 남는다.

## 4. 확인한 것

- **서버**:
  - 처리기는 FastAPI 기본과 같은 키(`starlette.exceptions.HTTPException`)를 대체한다. 본문 없는 상태와 `headers`를 그대로 넘긴다. 405는 `Allow`를 지키고 HEAD 404는 본문이 없다.
  - 500은 `ServerErrorMiddleware`가 JSON으로 쓰고 다시 던져 로그에 남는다.
  - `ERROR_CODES` 순서를 바꿨어도 바뀐 상태 코드가 없다. 덮는 예외 집합은 옛 `http_error`를 포함한다.
  - 바꾼 던지는 자리 20곳의 상태와 detail이 그대로다.
  - `tests/api` 146 통과.
- **웹 바탕**:
  - 알림 저장소의 스냅샷 참조가 안정적이고, 타이머는 version에 따라 다시 걸린다.
  - Dialog는 열 때 초점을 기억하고, Esc와 이름 붙이기가 된다. ConfirmDialog는 바쁠 때 닫히지 않는다.
  - Select의 빈 값과 placeholder, FileInput의 파일 복사 순서가 맞다.
  - `useResource`의 번호와 abort 순서, `useAction`의 ref 가드가 맞다.
  - HttpError 파싱(비JSON, null, 배열)이 맞고, conflictKind는 V2 전과 같다.
- **지도**:
  - 화면 행렬 역변환(스크롤 포함), 레터박스, `meetMatrix` 대체 경로가 맞다.
  - 끌기 문턱, 포인터 잡기, 자르기, "누르기만 하면 저장 안 함"이 맞다.
  - [지역 추가] 클릭(그림 위 포함)과 연결 도구 두 번 누르기가 V2 전과 같다.
  - GM 어댑터의 색·배지 병합과 testid가 맞다.
- **화면 교체**:
  - 네 라우트의 셸 props(world·session·llmOff)가 옛 AppNav와 같다. LangSwitch는 하나다.
  - 확인 처리기는 두 번 불리지 않는다.
  - select의 값 변환과 옵션은 옛 동작과 같다.
  - BuildPanel의 파일 상태와 닫기 로직이 그대로다.
  - 클래스 대응이 뜻을 바꾸지 않는다.
- **사전·표기·빌드**:
  - `i18n/index.ts`의 사전 뒤 코드는 옛 파일과 바이트 단위로 같다. 옛 키 323개의 ko·en 값이 그대로다. 키는 489개씩이고 placeholder가 맞으며 en에 한글이 없다.
  - 단계 경계가 FD 표와 같다.
  - 모든 클래스 토큰이 컴파일되고, TSX의 `var(--…)`는 모두 있는 변수다.
  - fast-check 시드가 워커까지 간다(`FC_SEED=4242`로 확인).
  - 번들에 `node:fs`·fast-check·테스트 도우미가 없다.
  - CI는 바뀌지 않고 새 테스트를 그대로 돌린다.

## 5. 남은 결정 (사람이 고른다)

- § 1의 15건과 § 2를 지금(V3 전에) 고칠지, 소유 유닛(V4·V6·V8·V9)에서 고칠지.
- § 1의 9(nginx gzip·index.html 캐시)는 배포 설정이다. 실제 머리는 B&T에서 compose로 확인한다.

## 6. 처리 결과 (사람의 선택: 바탕 결함 15건과 정리 일부)

2026-10-07. 사람이 고른 범위는 § 1 15건 전부와, § 2 가운데 V2 자기 코드에 속한 정리다.
- 결함마다 재현 테스트를 붙였다.
- 고치기 전 코드에 새 테스트를 돌려 실패하는 것을 확인했다(대화상자 3, 지도 6, 알림 2, 도우미 7).

| # | 처리 | 커밋 |
|---|---|---|
| 1 | `ConfirmDialog`에 `confirmDisabled`(확인만 끔). 막힌 삭제는 [취소]·Esc·바깥 누름으로 닫힌다 | `8def71f` |
| 2 | `need_service(…, code)`. 빌드 셋은 `llm_unavailable`. FD domain-entities § 5 정정 줄 | `fbdba50` |
| 3 | Dialog `onInteractOutside`가 `[data-toaster]` 안의 누름을 무시 | `8def71f` |
| 4 | 이름 받침이 지역을 고른다(포인터 허용). 실제 브라우저 `elementFromPoint`로 받침에 닿는 것을 확인 | `6403720` |
| 5 | `placeLabels`의 앵커 `r` = 표식+고리 자리, 그 사각형은 함수가 직접 잡는다. 같은 어긋남이 다시 생길 수 없는 모양 | `6403720` |
| 6 | 숨긴 input `tabIndex=-1`·`aria-hidden`. 버튼 이름 = 칸 라벨 + "파일 고르기", 설명 = 고른 파일 | `9155576` |
| 7 | 에디터·GM 지도 고르기가 고른 이름을 `chosen`으로 넘김 | `9155576` |
| 8 | 셸이 경로가 바뀔 때 알림을 비운다(같은 화면의 다른 세션 포함) | `b788379` |
| 9 | nginx `gzip on`·`index.html` `no-cache`. 네트워크 없는 `locus-web` 컨테이너 안에서 머리 확인: JS 118.8 kB·CSS 85.8 kB gzip, `/`·`/play/s1`·`/index.html` no-cache. 실제 compose 머리는 B&T에서 다시 본다 | `719cbf9` |
| 10 | 대륙·지방 이름에 틀: 선택은 accent 테두리, GM 상태는 색 씻김·고리(`region-fill-<id>`) | `6403720` |
| 11 | 대륙·지방 이름 글은 포인터를 받지 않고 가운데 작은 누름 영역만. 브라우저에서 이름 가장자리 누름이 지도로 가는 것을 확인 | `6403720` |
| 12 | 지도 밖으로 나가는 후보는 막힌 것으로 친다 | `6403720` |
| 13 | 알림 ×·행동 버튼, 언어 버튼, 탭이 640px 미만에서 44px | `b788379` |
| 14 | `useResource`: null 키 → loading, 새 키 실패는 옛 data를 버림, 오류 뒤 reload는 loading | `b1c5158` |
| 15 | key가 같은 알림은 내용을 통째로 바꾼다 | `b788379` |

§ 2에서 지금 고친 것:

| 항목 | 커밋 |
|---|---|
| `numberWithMeaning` 반올림 값으로 단계 | `874d73f` |
| `turnLabel`·`turnAt`의 `lang`(i18n `tFor`) | `874d73f` |
| 네트워크 판정을 브라우저 문구만으로 | `b1c5158` |
| Dialog 초점: 연 요소가 없으면 `<main id="main">`(셸에 main 랜드마크가 생김) | `8def71f` |
| `resetCapabilities` 세대 번호 | `b1c5158` |
| FileInput·StatusView 버튼 `type="button"` | `9155576` |
| `useAction` onDone을 try 밖으로, StatusView 오류는 내용으로 새지 않음 | `b1c5158` |
| 보조 버튼 hover 경계 `muted`, `event`/sunken 쌍을 허용 표와 대비 테스트에 | `b788379` |
| 연결선 투명 누름 선, 배지 자리 | `6403720` |
| 원색 검사 확장(#rgba·#rrggbbaa·색 함수·이름 색·기본 팔레트 클래스)과 `--color-*: initial`(빌드 CSS 동일), BR-V2-09 검사 | `3899500` |
| 백엔드 enum 대조 테스트(`format.enums.backend.test.ts`, 15종) | `3899500` |
| 파일을 읽는 테스트가 web/ 기준(`WEB_ROOT`) | `3899500` |
| 약한 테스트: 문체 검사 대상 수, 해라체는 키가 생길 때까지 보이게 skip, meet 속성, 언마운트 단언, Emberleaf를 마을마다 고른 상태로 | `3899500`·`6403720`·`b1c5158` |
| `test_error_codes`의 언어 단언을 400·`unsupported_lang`으로 | `fbdba50` |

소유 유닛으로 넘긴 것:

| 항목 | 넘긴 곳 |
|---|---|
| 지역 삭제 요약을 인스펙터에 남기기 | V8 |
| BuildPanel의 Esc·바깥 누름이 입력을 지움 | V8 |
| ActionBar `outline-none` | V4 |
| select·지도 고르기 칸 배치 | V4·V6·V8 |
| play 확대 때 바탕 그림 | V4 |
| `String(e)` 화면의 `"code"` 원문 | 각 화면 유닛(`describeError`로 바꿀 때) |
| `CLAUDE.md`의 `src/i18n.ts`·`ui/LlmNotice` | V9 |
| Button `busy`가 native disabled라 초점이 body로 빠짐(→ `aria-disabled`) | V4(화면이 `useAction`·busy 버튼을 처음 쓸 때) |

게이트(고친 뒤):
- 백엔드:
  - pytest 974
  - ruff·black 깨끗
  - mypy 11(기준선)
- 프런트엔드:
  - tsc 깨끗
  - vitest 423 통과, 1 skip(해라체 키 없음), 시드 둘(1749487009, 4242)
  - 런타임 npm audit 0
- 크기(gzip -9): JS 118.4 kB(예산 125.6), CSS 84.5 kB. 기본 팔레트를 꺼도 CSS는 같다.
