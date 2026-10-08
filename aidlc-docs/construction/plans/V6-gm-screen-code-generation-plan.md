# V6 GM 화면 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**지금 하는 것**: Construction V6(실행 6/9), Code Generation 1부(계획).
- 승인된 V6 기능 설계대로 GM 화면을 다시 짠다: 지도 + 턴 도구 + 탭 다섯 개, 턴 결과 띠 하나.
- 화면 쪽 이중 실행과 늦은 답을 막는다.
- 이 계획이 V6 코드 생성의 유일한 기준이다.

**근거**:
- 요구사항 `inception/requirements/follow-up-requirements.md`
  - FR-S3, 이 화면의 FR-S5·S6·FR-L1, FR-D5·D7·D8·D9
  - FR-C5(플레이 `gm_busy` 문장)
  - FR-C13 GM 쪽: #14, #15, RE-F01, F02, F04, F05, F11, F14
- 유닛 `inception/application-design/follow-up/unit-of-work.md` V6
- 승인된 FD `construction/V6-gm-screen/functional-design/*`
  - BR-V6-01..35, TP-V6-1..17, frontend-components § 1~7
  - FD 리뷰 01의 R-01..R-10은 Accepted risk다. 아래 § 1.1 실행 메모가 다룬다.
- 이어받는 것: V5 code-summary § 7(V6 몫), V4 계약(`Button busy`, `Dialog variant`, `useMedia`, `useWorldNames`), V2 리뷰의 "V4·V6·V8 select 배치"

**단계 표기**:
- 단계마다 체크박스를 고친다.
- 단계는 웹 게이트(tsc + vitest)가 GREEN인 상태로 끝낸다. 백엔드는 바뀌지 않으므로 pytest는 처음과 끝에만 돌린다.
- 그래서 Step 3·4는 새 파일과 호환되는 변경만 한다. 기존 부품의 계약을 바꾸고 옛 소비자(`GmHub`, 지금 `GmPage`)를 없애는 일은 Step 5 한 커밋에서 한다(§ 1.3).
- 단계마다 `feat/follow-up`에 커밋한다. **이 계획의 승인이 이 커밋들의 허락이다.**
- 푸시·PR은 사람이 한다.

---

## 1. 단위 맥락

| 항목 | 내용 |
|---|---|
| 요구사항 | FR-S3, FR-S5, FR-S6, FR-L1, FR-D5·D7·D8·D9, FR-C5(표시), FR-C13(GM 쪽) |
| 웹: 새로 | `features/gm/{GmLayout,GmSessionView,GmHeader,ClosedBanner,MapPane,TurnTools,TurnBand,GmTabs,RegionTab,EventCard,EventForm,useGmSession,useGmData,sessionLabel}.ts(x)`(`badgeOf`는 `MapPane.tsx`가 내보낸다) |
| 웹: 바뀜 | `routes/GmPage.tsx`(다시 씀) |
|  | `features/gm/{PlayerStrip,EventPanel,SeedPanel,DistortionPanel,RumorPanel,RegionKnowledgePanel,TimelinePanel,DeedPanel,WorldStateOverlay,useBulkRumors,bulk}.ts(x)` |
|  | `api/http.ts`(`conflictKind`, `isBusy`) |
|  | `hooks/{useTurnRun,useWorldNames}.ts` |
|  | `ui/Select.tsx`(`group`), `layout/Section.tsx`(제어 `open`) |
|  | `i18n/{ko,en}.ts`, `i18n/index.ts`(`timelineText`의 `region_removed`) |
| 웹: 없앰 | `features/gm/{GmHub,ManualTurnPanel}.tsx`, `WorldStateOverlay.tsx`의 `useWorldState`와 토글 컴포넌트 |
| 웹: 남김 | `SessionBar.tsx`: 에디터 `WorldFileBar`의 세션 시작이 `variant="picker"`로 쓴다. GM은 더 쓰지 않는다. `variant="full"` 정리는 V8(§ 1.3 R-01) |
| 테스트: 고침 | `web/src/__tests__/{gm,components,deeds,errors.describe.prop,ui.primitives,layout,hooks,play.turn,design.grep,fr-d8,pure}.test.*`. `play.test.tsx`와 `components.test.tsx`의 `SessionBar` 묶음은 그대로다 |
| 테스트: 새 파일 | `gm.layout.test.tsx`, `gm.data.test.tsx`, `gm.parts.test.tsx` |
| 바꾸지 않는 것 | 서버(V6는 백엔드를 바꾸지 않는다), 에디터(V8; `MapOverlay` 어댑터도 V8), 일괄 동시성 5와 대상 규칙, 사건 생명주기 규칙 |
| 의존 | V2 바탕, V4 계약, V5 서버 코드(`gm_busy`, `rumor_inactive`, `region_removed` 줄, 왜곡 PUT이 저장한 행을 돌려줌) |

### 1.1 실행 메모 (FD 리뷰 01, 승인 때 Accepted risk)

〔R-01〕 **slant는 enum이 아니다.**
- 판단의 slant는 LLM이 쓴 한두 단어다. 서버가 값을 닫지 않고, V2가 `format.enums.test.ts:34`로 "slant is not an enum"을 정해 두었다.
- 그래서 라벨로 바꾸지 않는다. 판단 줄에 "보는 눈: <slant>"로 원문을 그대로 보인다. 번역 대상도 아니다(V3 번역 종류에 없음).
- BR-V6-24의 대상과 TP-V6-12의 순회에서 slant를 뺀다.
- 상위 `component-methods.md` § 1.4의 `EnumKind`에는 slant가 있다. 코드(V2 결정)를 따르고, 이 차이를 code-summary § 5에 적는다.

〔R-02〕 **key 경계와 상태 소유.** 아래 표가 FD frontend-components § 5.2의 "`GmPage`가 `selected`와 `tab`을 가진다"를 대신한다.

| 상태·훅 | 가진 곳 | `key={sessionId}` 경계 | 세션을 바꾸면 |
|---|---|---|---|
| `useGmSession`(세션, 월드, 이름표, 세션 목록) | `GmPage` | 밖 | 세션은 새로 읽는다. 월드·이름표·목록은 같은 월드면 남는다 |
| `selected`(고른 지역) | `GmPage` | 밖 | 같은 월드면 남고, 월드가 바뀌면 비운다 |
| `mapUrl`·`mapName`, `overlayOn` | `GmPage` | 밖 | 남는다 |
| `tab`, 결과 띠, "새로" id 집합, 쓰기 오류 줄 | `GmSessionView` | 안 | 처음 값([지역] 탭, 없음) |
| `useGmData`(사건·기록·상태·소문·씨앗·행적·플레이어), `useBulkRumors` | `GmSessionView` | 안 | 새로 읽는다. 옛 요청의 답은 버린다 |
| "NPC가 아는 것" 펼침, 사건 폼 초안 | `GmSessionView` | 안 | 처음 값(닫힘, 빈 설명) |

- `GmSessionView`가 `GmLayout` 전체를 그린다. 지도도 그 안에 있어 세션을 바꾸면 다시 마운트된다.
  - 월드 자료는 `GmPage`가 가지므로 다시 읽지 않고 바로 그린다. BR-V6-16의 "같은 월드면 지도는 남는다"는 화면에 보이는 지도를 뜻한다.
  - 새 세션을 읽는 동안에는 직전 월드를 그대로 쓴다: `world = data && (!session || data.world_id === session.world_id) ? data : null`.
- **자기 키의 data만 쓴다.**
  - `useGmData`의 모든 자원은 loader가 `{ key, value }`를 돌려준다. 화면은 `key`가 지금 키와 같을 때만 `value`를 쓴다(`usePlaySession`과 같은 생각).
  - 그래서 지역을 바꾸면 옛 지역 소문 카드는 사라진다. 새 지역 소문이 올 때까지 소문 자리는 로딩 줄이다.
  - 같은 키의 `reload`는 화면을 그대로 두므로 BR-V6-10과 맞는다.
- TP-V6-6에 더한다: 지역을 A → B로 바꾸고 B의 소문 읽기를 붙잡는다. 그동안 A의 소문 카드와 공신력 슬라이더가 없다.

〔R-03〕 **쓰기 답으로 바로 고치기.**
- `useGmData`는 덧씌우기 상태 둘을 가진다.
  - `rumorPatch: Record<rumorId, SessionRumor>`
  - `distPatch: Record<regionId, {distortion, feedback_share}>`
- 화면은 자원 값 위에 덧씌우기를 얹어 보인다.
- 덧씌우기는 그 자원(소문, 상태)의 새 답이 도착하면 비운다. 쓰기 뒤의 다시 읽기 답에는 저장된 값이 들어 있다.
- `useResource`는 바꾸지 않는다.
- **플레이어 띠**
  - 키는 `["gm-player", sid]`이고 `rev`를 넣지 않는다.
  - 턴 진행 뒤와 [다시 확인]에서 `reload`한다.
  - 같은 키 다시 읽기가 실패하면 마지막 값을 두고 오류 문장을 붙인다(`useResource`의 같은 키 규칙).

〔R-04〕 **세션 목록.**
- 목록은 `listSessions(world_id)`(키 `[world_id]`)를 쓰고, 이럴 때 `reload`한다: 새 세션, 턴 진행, 세션 끝내기.
- 고르기의 "지금 세션" 항목 라벨은 목록이 아니라 `getSession` 답으로 만든다. 그래서 목록이 낡아도 지금 세션의 턴과 상태는 맞다.
- 지금 세션이 목록에 없으면(새 세션 직후) 그 항목을 목록 앞에 더해 보인다.
- 테스트: 새 세션 뒤 고르기에 새 세션이 있다. 턴 뒤 라벨이 "N+1턴"이다.

〔R-05〕 **`conflictKind`의 반환형과 호출부.**
- 반환형은 하나로 정한다: `"closed" | "turn_running" | "gm_busy" | "rumor_inactive" | "conflict" | null`.
  - code가 있으면 code로 가른다. 그 밖의 code 있는 409(`seed_running`, `world_exists` …)는 `"conflict"`다.
  - code 없는 옛 서버: 문장에 "session is closed"가 있으면 `"closed"`, 아니면 `"turn_running"`(지금의 "busy" 자리).
- `isBusy(kind) = kind === "turn_running" || kind === "gm_busy"`.
- **동작이 바뀌는 곳**: 지금은 code 있는 409가 모두 "busy" 갈래로 갔다. 이제 `conflict`·`rumor_inactive`는 그 갈래로 가지 않는다.

| 호출부 | closed | turn_running | gm_busy | rumor_inactive | conflict |
|---|---|---|---|---|---|
| `useTurnRun.act`(플레이) | 다시 읽기(닫힘 띠) | 알림 `play:busy` "턴을 진행하고 있어요" + 다시 읽기 + 이어 받기(지금과 같음) | 알림 `play:gmBusy` "GM이 잠깐 세계를 손보는 중이에요…" + 다시 읽기 + 이어 받기 | 해당 없음(`act`는 내지 않음) → `setRefusal(describeError)` | `setRefusal(describeError)`(바뀜: 전에는 busy 알림) |
| `DialoguePanel` | 지금과 같음 | 지금과 같음 | 지금과 같음 | 지금과 같음 | 지금과 같음 |
| `DeedPanel`(무효화) | 알림 문장 + 페이지에 알림(지금과 같음) | `describeError` 문장(안내 줄) | 같음 | 오류 줄 | 오류 줄(바뀜: 전에는 "턴 진행 중" 안내) |
| GM 쓰기 감싸기(`GmSessionView`) | BLM § 6 표 | BLM § 6 표 | BLM § 6 표 | BLM § 6 표 | 사전 문장 |

- 고치는 기존 단언
  - `gm.test.tsx:271-279`: `"busy"` → `"turn_running"`
  - `errors.describe.prop.test.ts:83-84`: `turn_running` code → `"turn_running"`
  - `gm_busy`·`rumor_inactive`·`seed_running` 줄을 더한다.
- `DialoguePanel`은 `=== "closed"`만 보므로 바뀌지 않는다.

〔R-06〕 **일괄 생성의 실패 갈래.**
- 실패는 넷으로 센다: `llm`(503 `llm_unavailable`), `closed`, `busy`(`turn_running`·`gm_busy`), `other`.
- 첫 `closed`나 `turn_running`이 오면 일괄을 멈춘다. 남은 지역은 보내지 않는다.
  - 오류 줄에 그 문장을 보인다.
  - `closed`면 세션을 다시 읽는다. `turn_running`이면 플레이어 띠를 다시 읽는다.
- `gm_busy`는 그 지역만 실패로 세고 계속한다.
- 끝 알림 본문 예: "7/10 만듦 · AI 키가 없어 2 · 바빠서 1". 0인 갈래는 뺀다.
- `bulk.ts` `mapLimit`에 `shouldStop?: () => boolean`을 더한다. 일꾼은 다음 지역을 꺼내기 전에 묻는다. 언마운트(`useMounted`)와 위 멈춤이 모두 이것을 쓴다.
- 일괄 중에는 [세션 끝내기]와 [플레이어 없는 새 세션]이 꺼진다. 세션 고르기는 켜져 있고, 바꾸면 일괄이 멈춘다(BR-V6-17).

〔R-07〕 **"새로"와 기록 비용.**
- [턴 진행]을 누를 때 기록 자원이 `ready`가 아니면 id 집합을 기억하지 않는다(`null`). 그러면 그 턴의 결과에는 "새로"를 달지 않는다. BR-V6-08에 이 줄을 더한 것으로 읽는다.
- 플레이어 탭 등 다른 곳이 같은 사이에 만든 줄도 "새로"가 될 수 있다. 진행 전에 없던 줄이므로 받아들인다.
- **알려진 제약**: 쓰기마다 `getTimeline`이 전부를 읽는다(서버가 쪽 나누기를 하지 않음). 줄이 수천이면 느려진다. code-summary § 6에 적고, V9가 `next-cycle.md`에 서버 쪽 나누기를 올린다.

〔R-08〕 **배치 세부.**
- **오른쪽 열 높이**: `sticky top-4 max-h-[calc(100vh-2rem)] overflow-y-auto`. 머리 높이를 재지 않는다.
  - 처음에는 열의 아래가 화면 밖에 있을 수 있다. 페이지를 내리면 열이 붙박이가 되어 다 보인다.
  - V2 `SplitView`(`lg:max-h-[calc(100vh-6rem)]`)와 같은 생각이다.
- **펼침과 초안**: Radix 탭이 숨은 탭을 언마운트하므로 "NPC가 아는 것" 펼침과 사건 폼 초안(분류·설명·규모·수명)은 `GmSessionView`가 가진다.
  - `layout/Section`에 제어 props `open?`·`onOpenChange?`를 더한다. 없으면 지금처럼 스스로 가진다.
- **1열에서 결과 띠의 지역 이름**: 누르면 [지역] 탭을 열고, 탭 영역을 `scrollIntoView({ block: "start" })`로 보이게 한다. 초점은 [지역] 탭 버튼으로 옮긴다.
  - 지도 누름은 스크롤하지 않는다. 탭이 지도 바로 아래에 있기 때문이다.
  - 사건 카드의 지역 이름은 이미 탭 안이다.
  - 이 줄이 BLM § 7의 "좁은 화면에서는 탭 영역으로 스크롤하지 않는다"를 결과 띠에 한해 대신한다.

〔R-09〕 **월드 교체 경고 "busy and could not be closed"**(V5 → V6 이월 목록에 있던 것)
- 이 문장은 빌드 보고서 경고(`BuildWarning`, `api/routers/world.py:174`)로 나온다. 보이는 곳은 에디터 `BuildReportPanel`·`BuildPanel`과 홈 `DemoCard`다. GM 화면에는 나오지 않는다.
- 그래서 V6에서 고치지 않고 **V8(에디터)**로 넘긴다. V8이 넘어가면 V9가 `next-cycle.md`에 적는다. code-summary § 7에 적는다.

〔R-10〕 **이름표·세션 목록 읽기 실패.**
- **이름표(`worldNames`) 실패**: 화면에 알리지 않고 영어 이름으로 보인다(V4와 같은 대체 규칙).
  - [다시 시도]가 보일 때는 그것도 다시 읽는다. `useWorldNames`가 `reload`를 돌려주게 바꾼다.
- **세션 목록 실패**: 고르기에는 지금 세션 하나만 보이고, 옆에 작은 문장 "세션 목록을 읽지 못했어요"와 [다시 시도]를 둔다. 이 [다시 시도]는 목록만 다시 읽는다.
- BR-V6-18의 검증에 이름표 실패 → 영어 대체 한 줄을 더한다.

### 1.2 이 계획이 정한 세부 (FD 범위 안)

- **쓰기 감싸기**
  - `GmSessionView`의 `gmWrite(kind, fn)` 하나가 모든 GM 쓰기를 감싼다: 오류 줄 지우기 → `fn()` → 성공이면 `data.after(kind)`, 실패면 BLM § 6 표.
  - 각 버튼은 자기 `useAction(() => gmWrite(kind, fn))`을 가진다.
  - 카드마다 바쁨은 카드 컴포넌트(`EventCard`, 씨앗 줄)가 자기 `useAction`을 가지는 것으로 만든다.
- **다시 읽기 표**: `useGmData.after(kind)`는 BLM § 3 표를 `AFTER: Record<GmWrite, ResourceName[]>` 상수 하나로 둔다. TP-V6-4는 이 상수가 아니라 실제 GET 호출을 센다.
  - 쓰기 14종(`GmWrite`): `turn`, `suggest`, `approve`, `discard`, `resolve`, `create`, `seed`, `distortion`, `support`, `generate`, `regen`, `bulk`, `void`, `close`. BLM § 3 표는 13줄이다. `generate`와 `regen`이 한 줄을 나눈다.
  - [플레이어 없는 새 세션]은 쓰기 표에 없다. 새 세션으로 옮겨 가는 것이고, 목록 다시 읽기는 `useGmSession`이 한다(§ 1.1 R-04).
- **세션 라벨** `sessionLabel(session, lang)`(순수 함수)
  - "N턴 · 진행 중 · 10월 8일 14:05"
  - 날짜가 없으면 id 앞 8자
  - 겹치면 " · " + id 앞 4자
  - 끝난 세션은 `group: "끝난 세션"`
- **배지와 범례**
  - 배지는 `String(active_rumors)` + (`deed_rumors > 0`이면 ` ✦${deed_rumors}`).
  - 범례 사전 키: `gm.legend.color`, `gm.legend.count`, `gm.legend.deed`.
- **결과 띠 문장**: GM 말투 키를 새로 둔다.
  - `gm.turnPassed` "{n}턴이 지났어요", `gm.quietTurn` "조용한 턴이었어요"
  - `gm.budget`, `gm.llmFailed`
  - V4의 `story.*`는 플레이 이야기 말투라 쓰지 않는다.
  - 지역 줄은 V4 `changeSummary`·`changeTitle`을 쓴다.
- **사전 접두어**: 새 GM 문구는 `gm.*`, 세션 머리는 `session.*`(있는 키 `session.close` "닫기"는 그대로 두고 새 키 `session.end` "세션 끝내기"를 쓴다 — 코드 계획 리뷰 02 R-06, § 1.3을 따름), 기록은 `timeline.*`, 오류는 `error.*`.
- **탭 라벨**: "지역", "사건", "씨앗", "기록", "행적". 사건 탭 배지는 제안 수다(0이면 없음).
- **수치**는 모두 `numberWithMeaning(kind, v)`로 만든다.
  - 왜곡 `distortion`, 몫 `share`, 공신력 `support`, 규모 `magnitude`, 확신 `confidence`, 감쇠 `decay`, 판단 `salience`.
  - GM 코드에 `.toFixed(`는 없다.

### 1.3 실행 메모 (코드 계획 리뷰 01)

〔R-01〕 **`SessionBar`는 남긴다.**
- FD(BLM § 1.5, frontend-components § 5 트리)는 "에디터는 이제 세션 띠가 없다"는 전제로 `SessionBar.tsx`를 없앤다고 했다. 그 전제는 틀렸다. 에디터 `WorldFileBar.tsx:106`이 `SessionBar variant="picker"`로 세션 고르기·[새 세션]·[플레이 시작]을 쓴다.
- 그래서 V6는 GM에서만 `SessionBar`를 떼어 내고, 파일은 남긴다. 에디터 쪽 배치는 V8 몫이다.
- [플레이어 없는 새 세션]을 GM에 두는 결정은 그대로다. 다만 "GM 화면이 유일한 곳"이라는 까닭은 틀렸다(에디터에도 [새 세션]이 있음). code-summary § 5에 적는다.
- `session.close` 값은 바꾸지 않는다. `GmHeader`는 새 키 `session.end`를 쓴다.

〔R-02〕 **단계마다 GREEN.** Step 3·4는 새 파일과 호환 변경만 한다. 기존 부품의 계약 변경, 화면 조립, `GmHub`·`ManualTurnPanel`·`useWorldState` 없애기, 사전 값 바꾸기, 옛 테스트 고치기는 Step 5 한 커밋에서 한다.

〔R-03〕 `DialoguePanel`은 바꾸지 않는다.

〔R-04〕 쓰기 14종은 § 1.2에 적었다. Step 8.1의 vitest는 Step 1.2 기준선 이상이어야 한다.

〔R-05〕 `useWorldState`는 Step 5에서 없앤다. 호출부는 `GmPage.tsx:34`(다시 씀)와 `gm.test.tsx:18,167`(고침)이다.

---

## 2. 단계

### Step 1 — 진행 기록과 기준선
- [x] 1.1 진행 기록을 커밋한다: audit, state, V6 FD 계획(체크), FD 산출물·리뷰, 이 계획과 그 리뷰(`docs(aidlc): V6 functional design approved; V6 code plan`).
- [x] 1.2 기준선을 재서 code-summary § 1에 적는다.
  - `npx vitest run`(V4 끝 550), `npx tsc --noEmit`
  - `pytest -q`(1138), `npm audit --omit=dev`(0)
  - 첫 화면 JS gzip과 GM 청크 gzip(`vite build`, 스크래치 출력)
  - GM 390px 가로 스크롤과 1280 페이지 높이(약 2,130px)는 역공학 기록 값을 옮겨 적는다. 다시 찍지 않는다.

### Step 2 — 공유 바탕 (§ 1.1 R-05·R-06·R-08·R-10, BR-V6-20·29, TP-V6-9·16)
- [x] 2.1 `api/http.ts`: `conflictKind` 새 반환형과 `isBusy`(§ 1.1 R-05 표).
- [x] 2.2 `hooks/useTurnRun.ts`: `gm_busy`면 `play:gmBusy` 알림과 새 문장을 쓴다. `conflict`는 `setRefusal`로 간다. `DeedPanel.tsx`와 `GmHub.tsx`(Step 5까지 남음)의 `conflictKind` 비교는 새 반환형으로 맞춘다(`DeedPanel`은 표대로, `GmHub`는 `=== "closed"`만이라 그대로). `DialoguePanel.tsx`는 `=== "closed"`만 보므로 바꾸지 않는다.
- [x] 2.3 `i18n`(ko·en)
  - `error.gm_busy.{title,action}`, `error.rumor_inactive.{title,action}`, `play.gmBusy`
  - `timeline.event_resolved_removed`
  - `i18n/index.ts` `timelineText`: `kind === "event_resolved" && payload.reason === "region_removed"`면 새 키를 쓴다.
- [x] 2.4 `ui/Select.tsx`: 옵션 `group?`. 같은 group이 이어지면 `<optgroup label>`으로 묶는다.
- [x] 2.5 `layout/Section.tsx`: 제어 `open?`·`onOpenChange?`. 없으면 지금처럼 스스로 가진다.
- [x] 2.6 `hooks/useWorldNames.ts`: `reload`를 돌려준다.
- [x] 2.7 `features/gm/bulk.ts`: `mapLimit(items, limit, fn, shouldStop?)`. `BulkProgress` 타입을 이 파일로 옮기고 `ManualTurnPanel`·`useBulkRumors`가 여기서 가져오게 한다.
- [x] 2.8 테스트
  - `errors.describe.prop`: `conflictKind` code 표와 code 없는 문장
  - `gm.test` #11: 고친 단언
  - `play.turn`: `gm_busy` 알림 문장이 `turn_running`과 다르다. `conflict`는 거절 문장이다.
  - `deeds`: 무효화의 갈래
  - `ui.primitives`: Select 묶음
  - `layout`: Section 제어
  - `hooks`: `useWorldNames.reload`
  - `mapLimit`: 멈춤
  - `timelineText`: `region_removed`
- [x] 2.9 게이트 GREEN → 커밋 `feat(web): 409s told apart (gm_busy, rumor_inactive), grouped select, controlled section, a bulk run that can stop (V6)`

### Step 3 — GM 읽기·쓰기 훅 (BLM § 1·2·3·4, § 1.1 R-02·R-03·R-04·R-06·R-07·R-10, TP-V6-4·6·7·8)

이 단계는 새 파일과 호환되는 변경만 한다. 지금의 `GmPage`·`GmHub`는 그대로 동작한다(§ 1.3).

- [x] 3.1 `features/gm/useGmSession.ts`(새)
  - 세션(id 일치), 월드(§ 1.1 R-02의 직전 월드 규칙), 이름표, 세션 목록(R-04)
  - `retry()`: 실패한 것(세션·월드·이름표)을 다시 읽는다. `reloadSession()`, `reloadSessions()`도 둔다.
  - 상태: 세션 또는 월드가 없으면 loading·error다. 이름표와 목록의 실패는 `namesError`·`sessionsError`로 따로 둔다(R-10).
- [x] 3.2 `features/gm/useGmData.ts`(새)
  - 자원: events `[sid, lang]`, timeline `[sid]`, worldState `[sid]`, rumors `[sid, regionId, lang]`(regionId 없으면 읽지 않음), seeds `[sid]`, deeds `[sid, lang]`, player `[sid]`(getPlayer 404 → null, 진행 중 run)
  - loader는 `{ key, value }`를 돌려주고, 화면은 자기 키만 쓴다(R-02).
  - `after(kind)`: BLM § 3 표 = `AFTER` 상수(§ 1.2의 14종).
  - `rumorPatch`·`distPatch`(R-03)
  - `knowledgeRev`: 지식 패널을 다시 읽으라는 신호(턴, 소문 쓰기, 무효화)
- [x] 3.3 `features/gm/useBulkRumors.ts`(호환 변경)
  - 지금 인자(`notify`, `fail`, `after`, `onCap`)는 그대로 두고, 선택 콜백 `onClosed?`, `onTurnRunning?`을 더한다.
  - 실패 갈래 넷과 첫 닫힘·턴 진행에서의 멈춤(R-06), `useMounted` + `shouldStop`을 넣는다.
  - 끝 알림 본문이 갈래별 문장이 된다.
  - `regenAll(ids)`의 대상은 부르는 쪽이 정한다. 지금의 `GmHub`는 그대로이고, Step 5의 `GmSessionView`는 상태의 지역을 넘긴다.
  - 기존 단언이 끝 알림 글을 보면 이 단계에서 고친다. 대상: `components.test.tsx` GmHub "generate-all fills only empty regions", `gm.test.tsx` "#5".
- [x] 3.4 `features/gm/sessionLabel.ts`(새, 순수 함수, § 1.2)
- [x] 3.5 테스트(`gm.data.test.tsx`, 새)
  - TP-V6-4: § 1.2의 쓰기 14종마다 실제 GET 호출 집합이 BLM § 3 표와 같다(매개변수 테스트, `api` 모듈 대역). 다시 읽기 중 로딩 없음.
  - TP-V6-6(훅 수준): 세션 A → B, B 붙잡기, A의 늦은 답을 풀어도 B의 값에 없다. 지역 A → B도 같다(R-02).
  - TP-V6-7: 503·409 섞인 일괄. 멈춤과 알림 본문. 5개 보낸 뒤 언마운트하면 호출은 5개다.
  - TP-V6-8(훅 수준): `retry`가 세션·월드·이름표를 읽는다. 이름표 실패는 영어 대체.
  - R-03: 공신력 저장의 답이 바로 보이고, 다음 답에서 덧씌우기가 비워진다. 플레이어 다시 읽기 실패에는 마지막 값과 오류.
  - R-04: 새 세션 뒤 목록에 있다. 턴 뒤 라벨이 바뀐다.
  - R-07: 기록이 준비되지 않았을 때 진행하면 "새로" 집합이 `null`이다.
  - `sessionLabel`: 날짜 없음, 겹침, 끝난 묶음.
- [x] 3.6 게이트 GREEN → 커밋 `feat(web): GM session and data hooks — own-key answers only, targeted re-reads, a bulk run that stops on close or a turn (V6, #15, RE-F11)`

### Step 4 — 새 GM 부품 (frontend-components § 4, BR-V6-13·14·26·27·31·33·34)

이 단계도 새 파일만 더한다. 지금의 화면은 아직 이것을 쓰지 않는다. 바뀌는 기존 부품과 사전 값은 Step 5에서 바꾼다.

- [x] 4.1 `GmHeader`(새)
  - 세션 고르기: `sessionLabel`, `group`
  - [플레이어 없는 새 세션]
  - [세션 끝내기] + `ConfirmDialog`(`session-close-confirm`, 대화상자 안 오류)
  - 목록 실패 문장(R-10)
- [x] 4.2 `ClosedBanner`(새)
- [x] 4.3 `MapPane`(새)
  - 토글(처음 켜짐), 말 범례, [지도 그림 고르기]
  - `WorldMap mode="gm"`: 끌기 없음, 플레이어 고리, 고른 지역, 상태 색·배지
  - 배지는 새 순수 함수 `badgeOf(state)`(§ 1.2)로 만든다. `WorldStateOverlay.tsx`의 `overlayOf`·`useWorldState`는 Step 5에서 정리한다.
- [x] 4.4 `TurnTools`(새): [턴 진행], 제안 개수와 [제안], [빈 지역 소문 만들기], [모든 지역 소문 다시 만들기](확인), 진행 막대. 버튼 옆 글 없이 `title`만 둔다.
- [x] 4.5 `TurnBand`(새): 제목, 지역 줄(버튼), 예산·LLM 줄, [닫기], `role="status"` 영역
- [x] 4.6 `EventCard`(새, 자기 `useAction`, 라벨·뜻, 지역 이름 버튼, "제안" neutral)과 `EventForm`(새, 라벨·검증·성공 때 설명만 비움, 초안은 제어 props)
- [x] 4.7 `GmTabs`(새): V2 `Tabs` 다섯, 사건 배지. 내용은 props로 받는다.
- [x] 4.8 `GmLayout`(새): 넓음 grid `minmax(0,1fr)_400px` + 오른쪽 열 붙박이(R-08), 1열 순서는 frontend-components § 1 표대로. `useMedia(WIDE)`를 쓰고, 각 부분은 한 번만 렌더한다.
- [x] 4.9 이 단계 부품이 쓰는 새 사전 키(ko·en)를 더한다.
  - `gm.*` 새 키와 `session.end` "세션 끝내기"
  - 있는 키의 값은 바꾸지 않는다. `session.close`는 에디터 `SessionBar`에 남는다. 그래서 `GmHeader`는 새 키를 쓴다.
- [x] 4.10 테스트(`gm.parts.test.tsx`, 새)
  - 부품마다 BR 단언
  - TP-V6-10의 머리 몫: 확인 없이는 `closeSession` 없음, 대화상자 안 오류, 고르기 라벨과 묶음
  - TP-V6-11: 사건 폼
  - TP-V6-14의 탭 키보드
  - TP-V6-15: `gm` 모드 끌기 없음, 배지·범례
  - 바쁜 버튼 `aria-disabled`
- [x] 4.11 게이트 GREEN → 커밋 `feat(web): new GM parts — session header with a confirmed end, map pane in words, turn tools, result band, event card and form, tabs, layout (V6, FR-S3)`

### Step 5 — 바꿔 끼우기: 기존 부품, 화면 조립, 옛 허브 없애기 (BLM § 1.3·5·7, BR-V6-01~12·15·16·18·24·25·28·29·35, § 1.1 R-01·R-02·R-08, TP-V6-1~3·5·6·17)

이 단계는 커밋 하나다. 기존 부품의 계약이 바뀌고 옛 소비자(`GmHub`, 지금 `GmPage`)가 같은 커밋에서 사라지므로, 중간 상태를 커밋하지 않는다(§ 1.3).

- [x] 5.1 기존 부품을 새 계약으로 바꾼다.
  - `PlayerStrip`: `useGmData.player`를 받는다. 자기 읽기를 없애고, [다시 확인]과 이름표를 둔다.
  - `DistortionPanel`·`RumorPanel`: 수치와 뜻, 공신력 라벨이 끄는 값을 따라감, 배지 라벨, 빈 상태
  - `RegionKnowledgePanel`: `Section` 제어 안, `knowledgeRev`에 `reload`(다시 마운트 없음), 스코프 라벨, 수치와 뜻
  - `EventPanel`: 세 묶음과 `EventCard`, 빈 문장, 끝남 접힘 10개 + 더 보기
  - `SeedPanel`: 자원을 받는다. 줄마다 `useAction`, 라벨·뜻.
  - `TimelinePanel`: 최신부터 20 + [더 보기], "새로", "N턴" 머리, 빈 상태
  - `DeedPanel`: "없던 일로 하기", "없던 일" 배지, "보는 눈: <slant>"(R-01), 수치와 뜻, `describeError`
  - `WorldStateOverlay.tsx`: `useWorldState`와 토글 컴포넌트를 없앤다. `distortionColor`는 남긴다. `overlayOf`는 Step 4의 `badgeOf`로 바꾸거나 없앤다(남는 쪽 하나).
- [x] 5.2 새 `RegionTab`: 요약 줄 + `DistortionPanel` + `RumorPanel` + `EventForm` + `RegionKnowledgePanel`, 빈 상태.
- [x] 5.3 새 `GmSessionView`(key 안)
  - 상태: `tab`, 결과, "새로" 집합, 쓰기 오류 줄, 펼침·초안
  - `gmWrite`, `useGmData`, `useBulkRumors`(새 콜백 연결, 다시 만들기 대상은 상태의 지역)
  - 지역 고르는 세 길 → `onSelect` + `tab="region"`. 1열의 결과 띠 클릭은 스크롤과 초점(R-08).
- [x] 5.4 `routes/GmPage.tsx`를 다시 쓴다.
  - `useGmSession`, `selected`·`mapUrl`·`overlayOn`
  - 오류 줄 + [다시 시도](`retry`), 로딩 줄
  - `<GmSessionView key={sessionId} …/>`
  - `SessionBar`를 더 쓰지 않는다.
- [x] 5.5 사전 값을 바꾼다: `deed.void` "없던 일로 하기", `deed.voided` "없던 일". 쓰는 곳은 `DeedPanel` 하나다(grep 확인).
- [x] 5.6 없앤다
  - `features/gm/{GmHub,ManualTurnPanel}.tsx`
  - `useWorldState`
  - 남은 import가 없는지 grep으로 확인한다. 테스트도 포함한다: `components.test.tsx`의 `GmHub`, `gm.test.tsx:18,167`의 `useWorldState`.
  - **`SessionBar.tsx`는 남긴다**(코드 계획 리뷰 01 R-01). 에디터 `WorldFileBar.tsx:106`의 세션 시작이 `variant="picker"`로 쓰고, `play.test.tsx:304-343`과 `components.test.tsx`의 `SessionBar` 묶음이 그것을 시험한다. GM이 쓰던 `variant="full"`(닫기·상태)은 쓰는 곳이 없어진다. 정리는 V8에 넘긴다(code-summary § 7).
- [x] 5.7 테스트
  - `gm.layout.test.tsx`(새)
    - TP-V6-1: 두 폭의 순서와 testid 하나
    - TP-V6-2: 세 길 → [지역] 탭, 제안 뒤 탭 그대로
    - TP-V6-3: 턴 이중 누름, 결과 띠, 알림 없음, "새로"
    - TP-V6-5: 대표 넷 이중 누름
    - TP-V6-6(화면 수준): 세션·지역 바꾸기 중 옛 답 미표시
    - TP-V6-8(화면 수준): 세션 실패 → [다시 시도] → 지도 표식
    - TP-V6-10의 화면 몫: 끝난 세션 띠, 쓰기 끔
  - 기존 테스트를 frontend-components § 7.1 표대로 고친다.
    - `components.test.tsx`의 `GmHub` 묶음(12)은 새 부품·화면 테스트로 옮긴다. 단언한 동작은 남긴다.
    - `gm.test.tsx`: `WorldStateOverlay`·`useWorldState`(167), `llm-required`(650), 턴 알림, `session-panel`, 타임라인 순서
    - `deeds.test.tsx`: 무효화 라벨
    - 고친 수와 이유를 기록해 code-summary에 적는다(TP-V6-17).
- [x] 5.8 게이트 GREEN → 커밋 `feat(web): GM screen rebuilt — map beside the turn tools and five tabs, one result band, nothing of the last session (V6, FR-S3, #14, RE-F01, RE-F02, RE-F04, RE-F05, RE-F14)`

### Step 6 — FR-D8 검사와 표기 (BR-V6-19·24·25, TP-V6-12·13)
- [ ] 6.1 `fr-d8.test.tsx`: TP-V6-12
  - `eventStatus`·`eventCategory`·`eventLifecycle`·`sessionStatus`·`scopeType`·`regionLevel` 전 값으로 다섯 탭과 머리를 렌더한다.
  - 원문 값이 없다. `/\b[mdt]\d/` 약어가 없다. 숫자 옆에 뜻이 있다.
  - slant는 대상이 아니다(R-01).
- [ ] 6.2 `design.grep.test.ts`: TP-V6-13
  - 범위는 `features/gm/**`와 `routes/GmPage.tsx`다.
  - 규칙은 `\.toFixed\(`, `String\((e|err|error)\)`, `outline-none`이다.
- [ ] 6.3 게이트 GREEN → 커밋 `test(web): the GM screen shows no raw enum, bare number or error text (V6, FR-D8)`

### Step 7 — 캡처 (사람 확인, BR-V6-01, 캡처 계획)
- [ ] 7.1 V4 캡처 도구(`scratchpad/v4/cap/{server.mjs,shoot.mjs}`)를 `scratchpad/v6/cap/`으로 복사한다. GM 읽기·쓰기 응답을 더한다: 세션 목록, 상태, 사건 세 갈래, 씨앗, 기록 40줄, 행적, 턴 결과.
  - 저장소에는 넣지 않는다.
  - 빌드는 스크래치 출력이다.
- [ ] 7.2 찍는다
  - 1280: [지역] 탭 / 턴 뒤 결과 띠 + [기록] "새로" / [사건] 세 묶음 / [행적] / 끝내기 확인 / 끝난 세션
  - 390: [지역] 탭 / 결과 띠 / 끝내기 확인
  - 768: [지역] 탭
  - 장마다 `scrollWidth == clientWidth`와 1280 페이지 높이를 잰다.
- [ ] 7.3 비공개 Artifact 한 장에 쌍으로 올린다. 잰 값, 바뀐 것, 봐 주실 것(범례·배지 말, 탭 구성)을 함께 싣는다.
- [ ] 7.4 가로 스크롤이 있거나 1280에서 오른쪽 열이 떨어지면 그 자리에서 고치고 다시 찍는다. 고친 커밋은 `fix(web): … (V6 captures)`다.

### Step 8 — 마무리
- [ ] 8.1 전체 게이트: tsc, vitest(Step 1.2 기준선 이상. 옮긴 테스트로 줄어든 수와 새 테스트 수를 code-summary § 4에 적는다), `pytest -q`(1138, 바뀌지 않음), `npm audit --omit=dev`(0), JS gzip(첫 화면이 V4 끝 114.83 kB보다 크게 늘지 않는다. GM은 지연 청크다).
- [ ] 8.2 `construction/V6-gm-screen/code/code-summary.md`
  - § 1 기준선과 결과
  - § 2 파일
  - § 3 BR → 테스트 표
  - § 4 고친 기존 테스트(TP-V6-17)
  - § 5 이탈: R-01 상위와 다름, R-02 소유 표, R-08 BLM § 7 줄, FD의 틀린 전제(BLM § 1.5와 frontend-components § 5의 `SessionBar` 없앰 — 코드 계획 리뷰 01 R-01)
  - § 6 알려진 제약: 기록 전부 읽기, 지도 키보드 조작, 직전 월드 규칙
  - § 7 넘기는 것: R-09 → V8, `SessionBar` `variant="full"` 정리 → V8, 서버 기록 쪽 나누기 → V9
- [ ] 8.3 audit, state 갱신 → 커밋 `docs(aidlc): V6 code summary`

---

## 3. 이야기 흐름(무엇이 어디서 확인되나)

| 완료 조건(unit-of-work V6) | 단계 | 확인 |
|---|---|---|
| 데스크톱에서 지도 옆에 패널, 허브가 기능별 | 4, 5 | TP-V6-1·2, 캡처 |
| 타임라인 최신부터 + 더 보기 | 5 | `gm.layout`·`gm.parts`(BR-V6-35) |
| 세션 닫기 확인, GM 지도 끌리지 않음 | 4, 5 | TP-V6-10·15 |
| [턴 진행] 두 번 눌러도 한 번 | 5 | TP-V6-3 |
| 세션을 바꾼 뒤 옛 답이 그려지지 않음 | 3, 5 | TP-V6-6 |
| 390px 가로 스크롤 없음 | 7 | 캡처 잰 값 |
| 캡처를 Artifact로 | 7 | Artifact 링크 |

규모: 8단계, 커밋 8~9개. 새 파일은 웹 14개와 테스트 3개다. 고치는 파일은 웹 약 20개와 테스트 11개이고, 없애는 파일은 2개다(`GmHub`, `ManualTurnPanel`). Step 5가 가장 큰 커밋이다.
