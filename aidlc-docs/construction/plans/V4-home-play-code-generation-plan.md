# V4 홈·플레이 화면 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V4(실행 4/9), Code Generation 1부(계획). 승인된 V4 기능 설계대로 홈과 플레이를 다시 짠다. 데모 방문자가 키 없이 한국어로 홈 → 플레이를 걷게 한다. 이 계획이 V4 코드 생성의 유일한 기준이다.

**근거**:
- 요구사항 `inception/requirements/follow-up-requirements.md`
  - FR-S1·S2·S5·S6, FR-L1, FR-D8
  - FR-C13(홈·플레이 쪽), FR-C14(RE-F08), FR-C5(표시)
  - NFR-7
- 유닛 `inception/application-design/follow-up/unit-of-work.md` V4. 코드 목록의 `AppNav.tsx`는 `layout/AppShell.tsx`로 읽는다
- 승인된 FD `construction/V4-home-play/functional-design/*`
  - BR-V4-01~26, TP-V4-1~15, frontend-components § 1~7
  - 리뷰 02의 R-11은 Accepted risk다. 아래 실행 메모 § 1.1이 다룬다
- 이어받는 것: V3 code-summary § 7, V3 리뷰 #6, V2 리뷰 § 6 "소유 유닛으로 넘긴 것"(V4 몫)

**단계 표기**:
- 단계마다 체크박스를 고친다. 단계는 그 단계의 게이트가 GREEN인 상태로 끝낸다(tsc, vitest, 백엔드는 바뀌지 않으므로 pytest는 처음과 끝에만 돌린다).
- 단계마다 `feat/follow-up`에 커밋한다. **이 계획의 승인이 이 커밋들의 허락이다.**
- 푸시·PR은 사람이 한다.

---

## 1. 단위 맥락

| 항목 | 내용 |
|---|---|
| 요구사항 | FR-S1(홈), FR-S2(플레이), FR-S5(상태), FR-S6(접근성), FR-L1(표기), FR-D8(수치·enum), FR-C13(RE-F03, 늦은 답), FR-C14(RE-F08), FR-C5(`gm_busy` 표시) |
| 웹: 새로 | `hooks/{useMedia,useWorldNames,usePlaySession,useTurnRun}.ts` |
|  | `features/home/{HomeHero,MyWorlds,WorldRow}.tsx` |
|  | `features/play/{PlayLayout,PlayHeader,ResultBand,ActionDock,TalkSheet,PlayMap}.tsx` |
| 웹: 바뀜 | `routes/{HomePage,PlayPage}.tsx`, `types.ts`(`RegionView.gm_busy?`) |
|  | `features/home/{DemoCards,DemoCard}.tsx` |
|  | `features/play/{RegionScene,NpcList,ActionBar,MovePanel,PlayLog,DialoguePanel,NewSessionForm,NarrationCard,summary.ts}` |
|  | `ui/{Dialog,Button}.tsx` |
|  | `layout/AppShell.tsx`(한 줄) |
|  | `features/editor/BuildPanel.tsx`(한 줄) |
|  | `map/WorldMap.tsx`(play 바탕 그림, V2 이월) |
|  | `i18n/{ko,en}.ts` |
| 테스트 | `web/src/__tests__/{home,play,dialogue,deeds,layout,ui.primitives,hooks,design.grep,i18n.style,gm,map.worldmap}.test.*` 고침(`gm.test`는 Button busy 단언 하나, `map.worldmap`은 play 바탕 하나) |
|  | 새 파일: `play.layout.test.tsx`, `play.turn.test.tsx`, `home.cards.test.tsx`, `fr-d8.test.tsx` |
| 바꾸지 않는 것 | 서버(V4는 백엔드를 바꾸지 않는다), GM 화면(V6), 에디터 화면(V8 — BuildPanel 한 줄만), 지도 편집 동작 |
| 의존 | V2 바탕(`ui/`·`layout/`·`map/`·`format/`·`errors/`·`hooks/`), V3 이름표·`*_ko`. V5의 `gm_busy`는 없으면 false |
| 내는 계약 | V6·V8에 셋을 낸다. |
|  | - `Button busy` = `aria-disabled` + 누름 무시 |
|  | - `Dialog variant` |
|  | - `useMedia`·`useWorldNames` |

### 1.1 실행 메모 (FD 리뷰 02, 승인 때 Accepted risk)

〔실행 메모 R-11〕 대화 시트의 기록 칸 정리(BLM § 2.5, BR-V4-21, TP-V4-8):
- PlayPage가 언마운트되거나 라우트를 떠날 때는 `navigate`를 부르지 않는다. 남은 `state.talk` 칸은 둔다.
- 시트를 열기 전에 `state.talk`가 `{ sessionId, regionId, npcId }`이고 지금 세션·지역과 맞는지 본다. 어긋나면 열지 않는다(되돌아와도 엉뚱한 시트가 열리지 않는다). 그래서 열 때 넣는 state는 `{ talk: { sessionId, regionId, npcId } }`다.
- `replace` 정리는 같은 PlayPage 안에서 **지역이 바뀔 때**와 **폭이 넓음으로 바뀔 때**만 한다. 이때는 그 시점의 `location`을 쓴다(effect 안에서 `useLocation()` 값).
- 세션이 바뀌면(`/play/a` → `/play/b`) 새 위치의 `state`가 없으므로 시트가 닫힌다. 정리할 것이 없다.
- TP-V4-8을 바꾼다. "시트를 연 채 [홈으로]·메뉴로 떠나면 위치가 목적지로 남는다(되돌아가지 않음)", "옛 세션·지역의 `state.talk`로는 시트가 열리지 않는다".
- **이 메모가 승인된 FD 줄을 대신한다**(코드 계획 리뷰 01 R-06): BLM § 2.5의 "지역이 바뀜·세션이 바뀜·언마운트" 줄, BR-V4-21의 "이동·세션 변경·언마운트·폭 변경 때 남은 칸은 replace로 지운다", TP-V4-8의 "언마운트하면 칸이 남지 않는다". 코드와 테스트는 이 메모를 따른다. code-summary § 5에 이탈로 적는다.
- **새 state 모양으로 다시 쓴 폭 전환**
  - 넓음으로 바뀜(시트가 열린 채): `state.talk`가 지금 세션·지역과 맞으면 `activeNpcId = state.talk.npcId`, 그다음 `navigate(location, {replace: true, state: null})`.
  - 넓음에서 좁아짐(열 안 대화 중): `navigate(location, {state: {talk: {sessionId, regionId, npcId: activeNpcId}}})`, 그다음 `activeNpcId = null`.
- 테스트(Step 7.3, `play.layout.test.tsx`)
  - 시트를 연 채 세션이 바뀌면 시트가 닫힌다(새 위치에 state 없음).
  - 다른 지역·세션의 `state.talk`가 있는 위치로 들어오면 시트가 열리지 않는다.
  - 두 폭 전환에서 대화가 이어진다.

### 1.2 이 계획이 정한 세부 (FD 범위 안)

- **사전 키**
  - 새 키는 V2 문체 접두어를 따른다.
    - `action.*`: 조작
    - `notice.*`·`empty.*`·`error.*`·`hint.*`: 해요체
    - `label.*`: 값 이름
    - `story.*`·`log.*`: 해라체
  - 두 화면이 쓰던 옛 `home.*`·`demo.*`·`play.*` 키는 문장이 바뀌는 것만 새 키로 옮기고, 그대로 쓰는 것은 둔다.
  - `nav.gmLocked`는 `hint.gmLocked`로 옮긴다. V2 i18n.style의 LEGACY 목록에서 빼고 AppShell을 고친다.
  - `log.*` 두 줄(`log.deed_seeded`, `log.rumor_spread`)은 마침표를 더해 해라체로 맞추고, `i18n.style.test`의 STORY에 `log`를 더한다(V2 주석 "log.* moves over with the play screen").
- **폴링 기본값**: `pollMs=700`, `maxPolls=120`. PlayPage props로 바꿀 수 있다(테스트).
- **좁음의 "더 보기"**: 지식 3개, 기록 5줄. 버튼은 `action.showMore`("N개 더 보기")다.
- **캡처 도구**
  - 세션 scratchpad `v2/cap/{server-v2.mjs,shoot-v2.mjs}`를 V4용 사본(`v4/cap/`)으로 늘린다.
  - 가짜 API가 하는 일:
    - 이름표 `GET /api/world/worlds/{w}/names`는 `emberleaf.ko.json`에서 만든다.
    - 지식 `*_ko`를 채운다.
    - 세션 목록을 준다.
    - 턴 진행은 `act` 202 → `turn-runs` done(결과 포함)으로 흉내 낸다.
  - 폭은 1280·768·390이다.

### 1.3 실행 메모 (코드 계획 리뷰 02, 승인 때 Accepted risk)
- 〔실행 메모 R-11〕 `gm.test.tsx`의 PlayPage 시험 둘을 Step 7.3에서 함께 고친다(V6 소유 파일이지만 PlayPage를 렌더한다).
  - `:96-113`(`play-gm-btn` → `/gm/:sid`)은 메뉴 `nav-gm`으로 가는 시험으로 바꾼다.
  - `:326` 이후 "PlayPage after U7" 블록은 새 화면에 맞춘다.
  - 대상 파일은 Step 7 시작 때 `grep -rln PlayPage web/src/__tests__`로 확정하고 code-summary에 적는다.
- 〔실행 메모 R-12〕
  - (a) ActionBar의 `Field` 라벨과 `outline-none` 제거는 **Step 6.7에서** 한다. 기존 테스트가 testid로 찾으므로 안전하다. Step 7.1a에서는 이 두 가지를 빼고 막힌 줄 이유와 결과 띠만 켠다.
  - (b) Step 2.3의 `Button`은 `aria-disabled:` 변형으로 `disabled:`와 같은 꺼진 모양을 낸다(`aria-disabled:cursor-not-allowed aria-disabled:border-line aria-disabled:bg-disabled aria-disabled:text-disabled-fg`). 스피너는 그대로 보인다.

---

## 2. 단계

### Step 1 — 진행 기록과 기준선
- [ ] 1.1 진행 기록을 커밋한다: audit, state, V4 FD 계획(체크), FD 산출물·리뷰 둘, 이 계획(`docs(aidlc): V4 functional design approved; V4 code plan`).
- [ ] 1.2 기준선을 잰다: `npx vitest run`(424 + skip 1), `npx tsc --noEmit`, `pytest -q`(1048), `npm audit --omit=dev`(0), JS gzip(`vite build` 결과의 gzip 값). 390px 가로 스크롤은 V2 캡처의 기록 값을 옮겨 적는다(홈 0, 플레이 대화 418; 다시 찍지 않음). code-summary § 1에 적는다.

### Step 2 — 공유 바탕: `useMedia`, `Dialog` 변형, `Button busy` (BR-V4-24·26, frontend-components § 4.1·5)
- [x] 2.1 `hooks/useMedia.ts`: `matchMedia` 구독이다. 없으면 false다. `hooks/index.ts`가 내보낸다.
- [x] 2.2 `ui/Dialog.tsx` `variant: "center" | "sheet" | "full"`(기본 center). 클래스만 다르고 동작(이름·초점·Esc·복귀·알림 영역 누름 무시)은 같다.
- [x] 2.3 `ui/Button.tsx`(코드 계획 리뷰 01 R-03)
  - `busy`면 native `disabled` 대신 `aria-disabled="true"`를 둔다.
  - `onClick`을 감싸 바쁜 동안 `e.preventDefault()` 후 돌아간다. 클릭의 기본 동작을 막으므로 `type="submit"` 버튼의 마우스 제출과 Enter 암묵 제출이 함께 막힌다(암묵 제출도 기본 버튼에 click을 보낸다). 바쁜 submit 버튼의 Enter 제출이 막히는지 테스트한다.
  - `disabled`(바쁨 아님)는 native 그대로다.
  - 미리 돌려 본 결과 깨지는 기존 테스트는 둘이다(2026-10-08 시험, 변경을 되돌림).
    - `ui.primitives.test.tsx` "Button › shows work in progress and cannot be pressed while busy"
    - `gm.test.tsx` "U6 review carry-overs › #13 and C1: one void per confirmation"
  - 둘을 `toHaveAttribute("aria-disabled", "true")`와 "누름 무시"로 고친다. 그 밖의 `busy={…}` 쓰는 곳(에디터·GM·SessionBar·ConfirmDialog 등 28곳)은 테스트가 깨지지 않았다.
  - 규칙: 바쁜 버튼 단언은 `aria-disabled`, `disabled` 버튼 단언은 `toBeDisabled()`다.
- [x] 2.4 테스트(`ui.primitives`, `hooks`)
  - `useMedia`의 matchMedia 대역
  - Dialog 세 변형의 이름·Esc·초점 복귀
  - Button busy는 클릭을 무시하고 초점이 유지된다
- [x] 2.5 커밋: `feat(web): useMedia; dialog sheet and full variants; a busy button keeps its focus (V4)`

### Step 3 — 메뉴 활성 표시와 사전 문체 정리 (BR-V4-09, § 1.2)
- [x] 3.1 `layout/AppShell.tsx`: 월드 없는 "에디터"를 `Link to="/"`로 바꾼다. `nav.gmLocked`는 `hint.gmLocked`로 옮긴다(호출부 `AppShell.tsx:71`).
- [x] 3.2 `i18n`(코드 계획 리뷰 01 R-02)
  - ko `hint.gmLocked` = "세션을 고르면 열려요"(해요체, 옛 "…열립니다"는 i18n.style에 걸린다). en `hint.gmLocked` = "Opens once you pick a session".
  - `nav.gmLocked`는 두 사전에서 지운다.
  - `log.*` 두 줄에 마침표를 더한다.
  - `i18n.style.test`: STORY에 `log`를 더하고, LEGACY에서 `nav.gmLocked`를 뺀다.
- [x] 3.3 테스트
  - `layout.test.tsx:60`의 `t("nav.gmLocked")`를 `t("hint.gmLocked")`로 고친다.
  - 홈에서 `nav-editor`에 활성 클래스·`aria-current`가 없는지 본다.
  - `deeds.test`처럼 `t()`로 비교하는 곳은 키 이름을 쓰지 않으므로 영향이 없다(`grep -rn "gmLocked" web/src`로 확인).
- [x] 3.4 커밋: `fix(web): the editor menu item is not active on the world list; play log lines in the story register (V4, UX-13)`

### Step 4 — 플레이 도우미 셋 (BLM § 2.1·2.2, BR-V4-16·17·19, R-11 무관)
- [x] 4.1 `hooks/useWorldNames.ts`: 키는 `[worldId, requestLang]`이다. `names.world_id !== worldId`면 null이다. `nameOf(kind, id, field, fallback)`.
- [x] 4.2 `hooks/usePlaySession.ts`
  - `useResource([sessionId, requestLang], …getSession·getRegion·getLog(30))`
  - `session.id !== sessionId`면 data는 null이다.
  - `reload()`
  - **data와 오류의 우선(코드 계획 리뷰 01 R-08)**: data가 있으면 오류가 와도 data를 그대로 그리고, 그 위에 `InlineError` 한 줄과 [다시 시도]를 둔다. data가 없을 때만 오류 화면이다. 스켈레톤은 data도 오류도 없이 읽는 중일 때다.
- [x] 4.2a `web/src/types.ts`: `RegionView`에 `gm_busy?: boolean`을 더한다(V5가 서버 칸을 더한다. 그전에는 없음 = 거짓).
- [x] 4.3 `hooks/useTurnRun.ts`
  - `act`: 409는 진행 중(알림 `play:busy`)·닫힘(reload)으로 나뉘고, 400은 false다.
  - `act` 뒤 `reload()`와 폴링을 나란히 시작한다.
  - 폴링: 상한이 넘으면 `slow`, 예외면 `error` + reload. 실패는 알림 `play:run`, 예산·LLM은 알림.
  - `outcome`은 결과 띠에 들어간다. `recheck`, `clearOutcome`이 있다.
  - 화면에 들어오면 `listTurnRuns(running)`으로 재진입한다.
  - 세션이 바뀌거나 언마운트되면 멈춘다.
  - run 없이 `turn_running`·`gm_busy`면 1초 × 5번 다시 읽는다.
- [x] 4.4 테스트(`play.turn.test.tsx`, `hooks.test.tsx`)
  - TP-V4-9: 가짜 타이머로 상한·`slow`·`recheck`
  - 폴링 예외 경로
  - 409 두 갈래
  - TP-V4-10: B를 읽는 동안 A data 없음, 늦은 답 버림, 행동 뒤 스켈레톤 없음
  - 이름표의 `world_id` 가드
  - 실행 기록: 테스트는 모두 `play.turn.test.tsx` 한 파일에 두었다(12개). 상한은 가짜 타이머 대신 `pollMs=1`·`maxPolls=3`으로 재고, 1초 × 5번 다시 읽기만 가짜 타이머를 쓴다. 400 거절(false + 오류)도 확인한다. 상한·세션 가드·월드 가드를 하나씩 지우면 테스트가 하나씩 실패한다.
- [x] 4.5 커밋: `feat(web): play session, turn run and world name hooks — late answers dropped, polling capped (V4, RE-F08)`

### Step 5 — 홈 (FR-S1, BR-V4-05~09·12, TP-V4-1~4)
- [x] 5.1 `features/home/HomeHero.tsx`: 사전 `label.homeKicker`, `story.homeTagline`, `story.homeLead`.
- [x] 5.2 `features/home/DemoCard.tsx`를 다시 쓴다(BLM § 1.2).
  - 상태: new, loaded, resume, 세션 읽기 중·실패, 409 질문 경로
  - 카드 안에서 `listSessions(name)`을 읽고 열린 것만 최근순으로 쓴다.
  - 시작 지역 이름은 `useWorldNames(name)`에서 찾는다.
  - 문구는 `*_ko`를 쓴다.
  - [데모 다시 불러오기] ghost 버튼(`demo-fresh-*`) → `useReplaceConfirm`.
  - `describeError`를 쓴다.
- [x] 5.3 `features/home/{MyWorlds,WorldRow}.tsx`
  - 데모 id를 뺀다.
  - `name_ko`를 쓴다.
  - 열린 세션은 중립 배지다.
  - [이어 하기]는 누를 때 `listSessions`를 읽는다.
  - [새 세션]·[편집]을 둔다.
  - [자료로 새 월드 만들기]는 머리에 하나 둔다.
- [x] 5.4 `routes/HomePage.tsx`를 조립만 하게 고친다.
  - 두 목록은 `useResource([…, requestLang])`이다.
  - 상태는 스켈레톤·오류·빈 상태다.
  - 빌드 뒤와 데모 불러오기 뒤에 다시 읽는다.
- [x] 5.5 `features/play/NewSessionForm.tsx`(코드 계획 리뷰 01 R-05)
  - 선택 prop `worldId?: string`를 받는다.
  - `useEffect(() => setRegion(""), [worldId])`로 월드가 바뀌면 지역 선택을 비운다(RE-F03).
  - 다른 호출부 `web/src/SessionBar.tsx:122`는 `worldId`를 넘기지 않아 지금 동작 그대로다(V6 소유, 바꾸지 않음).
  - `features/editor/BuildPanel.tsx`: 월드 id 칸 아래 `hint.worldIdChars` 한 줄.
- [x] 5.5a 이 단계의 사전 키(ko·en)를 이 커밋에서 더한다(코드 계획 리뷰 01 R-04).
  - `label.homeKicker`, `story.homeTagline`, `story.homeLead`
  - `label.myWorlds`, `action.continue`, `action.newSession`, `action.reloadDemo`
  - `notice.sessionsUnreadable`, `label.openSessions`, `label.startAt`, `hint.worldIdChars`, `empty.noWorlds`
- [x] 5.6 테스트
  - `home.cards.test.tsx`: TP-V4-1, TP-V4-2
    - BR-V4-06: 열린 세션 배지의 클래스에 `danger`가 없다(TP-V4-12 뒤 절반, 코드 계획 리뷰 01 R-09)
  - `home.test.tsx`: § 7.1 표대로 고친다(EX-2, held-world, EX-13, 목록). TP-V4-3, TP-V4-4
- 실행 기록(Step 5)
  - Hero 머리글은 `font-heading`이다. V2 규칙 "display 글꼴은 로고에만"(`design.grep`)이 FD의 "display, 작게"보다 앞선다.
  - [데모 다시 불러오기](`demo-fresh-*`)는 다시 불러온 뒤 홈에 남고 카드가 세션을 다시 읽는다. 409 경로의 [새로](`demo-reload`)와 시작 지역이 없을 때의 버튼은 문구("새로 불러와 플레이")대로 불러온 뒤 플레이로 간다.
  - "내 월드"는 데모 목록이 답할 때(데이터 또는 오류)까지 스켈레톤이다. 데모 월드가 잠깐 줄로 보였다 사라지지 않게 한다.
  - 빌드 창을 닫을 때도 두 목록을 다시 읽는다. 예외로 끝난 빌드도 월드를 썼을 수 있다.
  - `hint.worldIdChars`는 "…써 주세요"로 권하는 말이다. 서버는 데모 이름 말고는 월드 id 문자를 막지 않는다.
  - `home.buildFromSources`는 "자료로 새 월드 만들기"로 바꾸고, 쓰지 않게 된 `home.title`·`home.openSessions`는 지웠다.
  - TP-V4-1·2(`home.cards.test.tsx`)는 api를 대역하지 않고 fetch 대역으로 경로별로 답한다. `?lang=`이 실제 요청에 붙는지 본다. `home.test.tsx`는 매 테스트 전에 api 대역을 `mockReset`한다(실패한 테스트의 남은 답이 다음 테스트로 새지 않게).
  - 돌연변이 확인: 폼 비우기, 데모 거르기, 최근순, 언어 키, 중립 배지를 하나씩 되돌리면 각각 테스트가 실패한다.
- [x] 5.7 커밋: `feat(web): home rebuilt — one card per demo, my worlds, Korean names, lists follow the display language (V4, FR-S1)`

### Step 6 — 플레이 부품 (FR-S2, BR-V4-10·11·13·14·18·19·21·23)

**GREEN 규칙(코드 계획 리뷰 01 R-01)**: 이 단계 커밋에서 옛 `PlayPage`는 아직 그대로 돈다.
- 새 부품(`PlayHeader`, `ResultBand`, `ActionDock`, `TalkSheet`, `PlayMap`, `PlayLayout`)은 새 파일이라 옛 화면에 영향이 없다.
- 기존 부품(`RegionScene`, `NpcList`, `MovePanel`, `PlayLog`, `ActionBar`, `DialoguePanel`)에는 **선택 prop만 더한다.** 기본값은 지금 동작이다: `names` 없음 = 영어, `compact=false`, `highlightId` 없음, 막힌 줄은 지금 표시.
- 화면이 보이는 것을 바꾸는 변경은 Step 7에서 옛 PlayPage와 함께 바꾼다. 막힌 줄 이유 문장, ActionBar의 보이는 라벨, 결과 띠로 옮김이 여기에 든다.
- 그래서 `play`·`dialogue`·`deeds` 테스트는 Step 6에서 그대로 통과한다. 새 부품과 새 prop은 이 단계의 부품 테스트로 본다.
- [x] 6.1 `PlayHeader`
  - 경로(`level_path_ids` → 이름표)
  - 지역명·단계 라벨·턴 라벨
  - `closed-banner` + [홈으로]
  - `gm-busy-notice`
- [x] 6.2 `ResultBand`
  - `role=status`
  - 제목(N턴 / 조용히 지나감)
  - 지역 변화 줄: `summary.ts`를 쓰고 이름은 이름표
  - 선언 문장: `narration-card` 유지
  - [닫기]
- [x] 6.3 `RegionScene`·`NpcList`
  - 장면 글(이름표)
  - 사람 카드(이름표, [말 걸기], 키 없음 안내)
  - 지식·전해 들은 것·소문(말 단계 배지, 수치 없음)
  - `compact`(좁음 더 보기)
- [x] 6.4 `MovePanel`
  - 이름표
  - `enumLabel("travelBy")` + `unit.turns`
  - 막힌 줄 회색 + `notice.moveBlocked`
  - `highlightId` 강조와 스크롤
- [x] 6.5 `PlayLog`
  - 기록의 `payload` id로 이름표를 찾는다.
  - `turnAt`
  - 좁음 5줄 + 더 보기
- [x] 6.6 `PlayMap`
  - `WorldMap mode="play"`
  - 이름표로 바꾼 `regions`
  - focus·reachable·player
  - 보기 전용: `onSelect`는 갈 수 있는 곳이면 `onPickReachable`
  - `map/WorldMap.tsx`(코드 계획 리뷰 01 R-07): **play 모드에서만** 바탕 그림을 svg `<image>`(`x=0 y=0 width=1000 height=625`, viewBox 안)로 그려 확대를 따르게 한다. edit·gm 모드는 지금의 `<img>` 그대로라 V6·V8 화면과 테스트에 영향이 없다. `map.worldmap.test.tsx`에 "play 모드의 바탕은 svg 안 image이고, edit 모드는 img" 테스트를 더한다.
- [x] 6.7 `ActionBar`
  - 선언 입력에 `Field` 라벨이 있다.
  - `outline-none`을 없앤다(V2 이월).
  - 상한 글자 수
  - 진행·느림·오류 표시: `turn-progress`, `turn-slow`, `turn-error`, `turn-recheck`
- [x] 6.8 `ActionDock`(좁음): 세 버튼을 띠 하나에 두고, 선언 시트(`Dialog variant="sheet"` + `ActionBar` 입력)와 이동 시트(`MovePanel`)를 연다.
- [x] 6.9 `TalkSheet`·`DialoguePanel`
  - `Dialog variant="full"` 래퍼
  - `DialoguePanel`의 390 가로 스크롤을 고친다(V2 이월). 긴 낱말은 줄 바꿈, 입력은 `min-w-0`
- [x] 6.10 이 단계 부품이 쓰는 사전 키(ko·en)를 이 커밋에서 더한다(§ 1.2 접두어, 코드 계획 리뷰 01 R-04).
  - `story.turnPassed`, `story.quietTurn`
  - `action.close`(있음), `action.showMore`, `action.recheck`, `action.goHome`
  - `notice.sessionClosed`, `notice.gmBusy`, `notice.turnSlow`, `notice.moveBlocked`, `notice.talkNeedsKey`
  - `label.declare`, `label.whereToGo`, `label.journey`, `label.peopleHere`, `label.knownHere`, `label.heardFar`, `label.rumorsHere`
  - `action.wait`, `action.declare`, `action.move`, `unit.turns`
  - 이미 있는 키는 다시 만들지 않는다(`grep`으로 확인).
- [x] 6.11 테스트: 부품 단위
  - TP-V4-6: 이름표·대체
  - TP-V4-7: 막힌 줄, 지도 누름 = 강조만
  - TP-V4-13: 접근성
  - 결과 띠 문장
- 실행 기록(Step 6)
  - `RegionScene.tsx`에 새 구역 `SceneText`·`PeopleHere`·`KnownHere`를 더했다. 장면 글은 행동 상자 위, 사람과 아는 것은 그 아래에 놓이므로(§ 1 표) 한 패널로는 놓을 수 없다. 옛 `RegionScene` 묶음은 옛 PlayPage가 쓰므로 Step 7에서 지운다.
  - `MovePanel`의 `words`는 Step 7에서 켜는 임시 prop이다(막힌 줄의 이유 문장과 버튼 없앰, `travelBy` 단어). Step 7에서 옛 갈래와 함께 없앤다. `bare`는 이동 시트용(제목은 시트가 가짐)이다.
  - `ActionBar`는 `TurnStatus`(진행·느림·오류 + [다시 확인])와 `DeclareForm`으로 나눴다. 휴대폰 띠와 선언 시트가 같은 둘을 쓴다. 버튼 문구 "선언하기 · 1턴"·"기다리기 · 1턴"도 지금 바꿨다(기존 테스트는 문구를 보지 않음). 진행 중 버튼의 `aria-disabled`(BR-V4-24)는 기존 테스트가 native `disabled`를 보므로 Step 7에서 화면과 함께 정한다.
  - 선언 입력의 옛 `maxLength={max×2}`는 없앴다. `Textarea`의 `maxLength`는 자체 글자 수(UTF-16)를 보여 서버식 글자 수와 겹친다. 막음은 빨간 글자 수와 꺼지는 [선언하기]가 한다. 붙여 넣기를 자르는 방식은 4만 자 선형 시험(`play.test`)이 실패해 버렸다.
  - 계획에 없던 사전 키 두 개: `label.yourStory`(내 행적 배지, GM이 쓰는 `badge.deed`와 나눔), `action.talk`("말 걸기", FD 문구). 쓰지 않게 된 `npc.talk`는 지웠다.
  - `NpcList`의 `talkOff`(이유 문장)를 주면 [말 걸기]가 꺼진다(BLM § 2.5). 예전 BR-U5-29(키 없이도 기록은 열림)와 어긋나는 FD 결정이며, 사람에게 알렸다.
  - `PlayHeader`의 경로는 `level_path`의 마지막(지역 자신)을 뺀다. 서버의 `level_path`는 꼭대기부터 그 지역까지다. 그래서 `play.test:94`("Aldermoor › Riverton")가 Step 7에서 의도한 변경이 된다.
  - `DialoguePanel`의 `String(e)` 둘을 `describeError` + `InlineError`로 바꿨다(BR-V4-15). 원문은 접어 둔 자세히에 남아 기존 "400" 단언이 그대로 통과한다.
  - 지도 범례는 넣지 않았다(사전 키 목록에 없고 시안에만 있음). 지도 바탕 그림은 지금 GM·에디터에서도 로컬 파일로만 고르므로 플레이에는 아직 없다. `PlayMap`은 `background`를 받을 자리만 둔다.
  - 세션 scratchpad가 비워져 V2 캡처 도구(`v2/cap/*.mjs`)가 사라졌다. Step 9에서 `v4/cap/`에 다시 쓴다.
  - "play 모드 바탕은 svg 안 image, edit 모드는 img" 시험은 `map.worldmap.test.tsx` 대신 `play.parts.test.tsx`(TP-V4-7 묶음)에 두었다.
  - 테스트 `play.parts.test.tsx` 22개. 돌연변이 확인: 서버 `reason` 표시, 지도의 아무 지역 누름, 경로에 자기 포함, 거절에도 시트 닫힘, 기록 이름 무시, 휴대폰 3개 제한 없앰을 하나씩 넣으면 각각 실패한다.
- [x] 6.12 커밋: `feat(web): play parts — header, result band, scene, moves, log, small map, action dock and sheets (V4)`

### Step 7 — 플레이 화면 조립 (BLM § 2, BR-V4-02~04·15·16·18·20·21·22·25, R-11)
- [x] 7.1 `features/play/PlayLayout.tsx`: frontend-components § 1 표대로 폭별 순서를 정하고, `useMedia` 두 쿼리를 쓴다. 각 컴포넌트는 한 곳에만 렌더한다.
- [x] 7.1a Step 6에서 미뤄 둔 보이는 변경을 켠다. 막힌 줄 이유 문장, ActionBar의 라벨·초점 고리, 결과 띠를 쓰고 알림·NarrationCard 단독 표시를 없앤다.
- [x] 7.2 `routes/PlayPage.tsx`를 다시 쓴다(조립).
  - 쓰는 것: `usePlaySession`·`useTurnRun`·`useWorldNames`·`exportWorld`(지도용, 키 `[worldId]`)·`listNpcs`
  - 결과 띠: `outcome`
  - 대화: 넓음은 화면 상태, 그 밖은 `location.state.talk`. 〔실행 메모 R-11〕
  - 빈 `/play`와 오류 상태
  - `play-gm-btn`은 없앤다(GM은 메뉴로).
- [x] 7.3 테스트
  - `play.layout.test.tsx`: TP-V4-8, 세 폭. 중복 testid 없음. 대화 시트·기록 칸. R-11의 목적지 유지와 어긋난 `state.talk` 무시
  - `play.test.tsx`·`dialogue.test.tsx`·`deeds.test.tsx`: § 7.1 표대로 고친다. TP-V4-5, TP-V4-11
  - BR-V4-20: `play-gm-btn`이 없고 메뉴의 `nav-gm`이 그 세션의 GM으로 간다(코드 계획 리뷰 01 R-09)
  - BR-V4-22: [대화 끝내기]의 판단 결과가 `result-band`에 나오고, 이동하면 대화가 닫힌다
- 실행 기록(Step 7)
  - PlayPage를 렌더하는 테스트 파일(R-11, `grep -rln PlayPage web/src/__tests__`): `play.test.tsx`, `dialogue.test.tsx`, `gm.test.tsx`, `deeds.test.tsx`.
  - `PlayPage`는 세션마다 `PlayScreen`을 새로 띄운다(`key={sessionId}`). 대화·가리킨 줄·말 수가 다른 세션으로 넘어가지 않는다. 데이터 쪽 지킴(늦은 답, 다른 세션 data)은 Step 4 도우미가 그대로 맡는다.
  - 대화 열림(R-11): 넓음은 화면 상태, 그 밖은 `state.talk = {sessionId, regionId, npcId}`이고 어긋나면 무시한다. [닫기]·Esc는 이 화면이 넣은 칸이면 `navigate(-1)`, 아니면(복원된 탭) 그 자리 `replace`라 화면을 떠나지 않는다. 지역이 바뀌면 남은 칸을 `replace`로 지우고, 폭이 바뀌면 시트↔열로 옮긴다. 언마운트·경로 이탈 때는 navigate하지 않는다.
  - 턴 진행 중(내 run, `turn_running`, `gm_busy`) 행동 버튼은 `aria-disabled` + 누름 무시로 끈다(BR-V4-24, 초점 유지). 닫힌 세션은 native `disabled`다. 선언 요청 중의 [선언하기]는 바쁜 버튼이다. `Button`이 `busy`와 호출자의 `aria-disabled`를 합치게 고쳤다(전에는 뒤에 펼친 `aria-disabled={undefined}`가 busy의 값을 지웠다). 회귀 시험을 더했다.
  - `useTurnRun`에 `refusal`을 더했다. 행동 거절(400 등)은 `error`(턴 확인 실패, [다시 확인])와 나뉘어 행동 자리의 `action-error`로 보인다. 섞여 있으면 400 뒤 [다시 확인]이 지난 run을 다시 폴링할 수 있었다.
  - 잡힌 세션 다시 읽기는 `useHeldRereads`가 맡아, 예전의 마운트 직후 "낡은 표시 확인" 읽기가 1초 간격 첫 회로 합쳐졌다(계속 잡힘: 7 → 6번).
  - 옛 `RegionScene` 묶음, `NarrationCard.tsx`, `MovePanel`의 옛 갈래와 `words` prop을 없앴다. 쓰지 않게 된 사전 키 14개(`play.title`·`noSession`·`hearsay`·`rumors`·`moves`·`move`·`turns`·`blocked`·`wait`·`gmMode`·`noLlm`·`log`·`declare`·`narrationTitle`)를 지웠다. 빈 `/play`용 키 두 개(`empty.noSession`, `hint.startFromDemo`)를 더했다.
  - 고친 기존 테스트(의도한 변경, TP-V4-15): `play.test` 7개(EX-13 경로·소문 단어·막힌 줄, EX-7 결과 띠, #15 `turn-error`, S02 둘과 #5(b)·#7의 `aria-disabled`, 잡힘 7→6), `deeds.test` 2개(거절 `action-error`, `KnownHere`와 "당신 이야기"), `dialogue.test` 1개(`people-here`), `gm.test` 1개(메뉴 `nav-gm`). `play.test`는 매 테스트 전 api 대역을 `mockReset`한다.
  - 새 테스트 `play.layout.test.tsx` 18개(TP-V4-5·8·10·11, BR-V4-22, R-11). 돌연변이 확인: 지역 변경 정리, 늘 `navigate(-1)`, 폭 전환 없음, 어긋난 state 믿기, 좁음 레이아웃에 이동 목록을 하나씩 넣으면 각각 실패한다.
- [x] 7.4 커밋: `feat(web): play screen rebuilt — two columns or one with an action dock, one result band, talk in the column or a sheet (V4, FR-S2)`

### Step 8 — FR-D8 검사와 표기 (BR-V4-10, TP-V4-12·14)
- [ ] 8.1 `fr-d8.test.tsx`: TP-V4-14. `ENUM_VALUES`의 `regionLevel`·`travelBy`·`sessionStatus`·`rumorOrigin` 전 값을 도는 렌더에서 원문 값과 `/\b0\.\d+\b/`가 없다.
- [ ] 8.2 `design.grep.test.ts`: TP-V4-12 정규식을 홈·플레이 파일 범위에 더한다(`\.toFixed\(`, `String\((e|err|error)\)`, `outline-none`).
- [ ] 8.3 커밋: `test(web): home and play show no raw enum, number or error text (V4, FR-D8)`

### Step 9 — 캡처 (사람 확인, BR-V4-01, 캡처 계획)
- [ ] 9.1 `v4/cap/`(세션 scratchpad, 코드 계획 리뷰 01 R-10)
  - 출발점은 V2의 `v2/cap/server-v2.mjs`(가짜 API + 정적 서버, node 22)와 `v2/cap/shoot-v2.mjs`(headless `google-chrome`, CDP)다. 둘을 `v4/cap/`으로 복사해 늘린다.
  - 세션이 바뀌어 없으면 같은 방식으로 다시 만든다. 저장소에는 두지 않는다.
  - 가짜 API에 더할 것
    - 이름표: `locus/world/demo/worlds/emberleaf.ko.json`에서 만든다.
    - 지식 `*_ko`, 세션 목록(열린·닫힌)
    - `act` 202 → `turn-runs/{id}` done(결과·선언 포함)
  - 촬영: 1280·768·390. 상태는 FD 캡처 계획 표대로다. `vite build` 산출물을 쓴다.
  - 각 장의 `document.documentElement.scrollWidth/clientWidth`를 잰다.
- [ ] 9.2 비공개 Artifact 한 장에 1280·768·390 쌍과 잰 값을 싣는다(V2 캡처 형식).
- [ ] 9.3 390·768에서 가로 스크롤이 있거나 캡처에서 결함이 보이면 고치고 다시 찍는다. 고친 것은 따로 커밋한다(`fix(web): … (V4 capture)`). 앞 단계 커밋을 고치지 않는다.

### Step 10 — 게이트와 요약
- [ ] 10.1 게이트: `tsc`, `vitest`(시드 둘), `npm audit --omit=dev`(0), `pytest`(1048, 백엔드 그대로), `ruff`·`black`(바뀐 파이썬 없음 확인), JS gzip(V2 예산 125.6 kB 이내).
- [ ] 10.2 `construction/V4-home-play/code/code-summary.md`를 쓴다.
  - § 1 기준선과 결과
  - § 2 파일
  - § 3 BR·TP 대응
  - § 4 테스트 변경(§ 7.1 표 + Button busy 단언 수)
  - § 5 이탈
  - § 6 알려진 한계
  - § 7 V5·V6·V8에 넘기는 것
- [ ] 10.3 커밋: `docs(aidlc): V4 code summary`

---

## 3. 요구 대응

| 요구 | 단계 |
|---|---|
| FR-S1 홈 | 5 |
| FR-S2 플레이 | 6, 7 |
| FR-S5 상태 | 4, 5, 7 |
| FR-S6 접근성 | 2, 6, 7 |
| FR-L1·FR-D8 | 3, 6, 8 |
| FR-C13·RE-F03 | 4, 5 |
| FR-C14·RE-F08 | 4 |
| FR-C5 표시 | 4, 6 |
| NFR-7(휴대폰) | 6, 7, 9 |
| V2·V3 이월 | 2(Button), 3(문체), 6(ActionBar 초점, 지도 바탕, 대화 폭), 5·6(이름표·목록 언어) |

**규모**: 10단계, 커밋 10개 안팎(캡처 고침에 따라 더). 웹만 바뀐다. 새 파일은 약 13개, 고친 파일은 약 20개다. 테스트는 vitest 약 60개를 더하고, 고치는 기존 테스트는 약 15개다.
