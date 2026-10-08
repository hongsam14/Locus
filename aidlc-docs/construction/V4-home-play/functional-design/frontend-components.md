# V4 홈·플레이 화면 — Frontend Components

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V4 Functional Design. 홈과 플레이의 배치(1280·390), 요소, 컴포넌트, API 연결을 정한다.

결정(계획 `construction/plans/V4-home-play-functional-design-plan.md`):

| 질문 | 답 | 내용 |
|---|---|---|
| Q1 | A | 데모 카드가 데모 월드를 맡는다. 불러온 데모는 "내 월드"에서 빠진다 |
| Q2 | A | 턴 결과는 지역명 아래 결과 띠 하나에 담는다 |
| Q3 | A | 휴대폰은 아래 고정 행동 띠 + 시트를 쓴다 |
| Q4 | A | 지도는 보기 전용이고, 이동은 목록에서 한다 |
| Q5 | A | 대화는 넓은 화면에서 왼쪽 열 안, 좁은 화면에서 전체 시트로 연다 |

바탕: V2 시안 B줄(홈, 플레이 1280, 휴대폰 플레이)과 V2 `ui/`·`layout/`·`map/`·`format/`·`errors/`·`hooks/`.

---

## 1. 폭과 나뉨

| 이름 | 폭 | 홈 | 플레이 |
|---|---|---|---|
| 넓음 | `lg` 1024px 이상 | 가운데 1열(최대 1240px), 카드 2열 | 2열: 왼쪽 장면 `minmax(0,1fr)`, 오른쪽 `360px` |
| 중간 | 640~1023px | 1열 | 1열, 행동 상자는 장면 아래 화면 안 |
| 좁음 | 640px 미만(390 기준) | 1열 | 1열 + 아래 고정 행동 띠(Q3), 대화는 전체 시트(Q5) |

- **무엇이 DOM에 있는지는 `useMedia`가 정한다**(설계 리뷰 R-02).
  - `wide = useMedia("(min-width: 1024px)")`, `narrow = useMedia("(max-width: 639px)")`. 둘 다 거짓이면 중간이다.
  - 폭마다 각 컴포넌트를 **한 곳에만** 렌더한다. 같은 testid가 한 DOM에 둘 생기지 않는다(BR-V4-25).
  - CSS(Tailwind)는 간격·열 너비·글자 크기에만 쓰고, 숨김으로 같은 컴포넌트를 두 번 두지 않는다.
  - jsdom에는 `matchMedia`가 없어 훅이 거짓을 준다. 그래서 테스트의 기본은 **중간** 배치이고, 넓음·좁음은 대역으로 고른다.
- **플레이 섹션의 순서는 `PlayLayout`이 폭별 목록으로 정한다.** V2 `SplitView`는 aside 전체를 앞이나 뒤에 붙이므로 390의 섞인 순서를 만들 수 없어 플레이에는 쓰지 않는다. 홈은 1열이라 필요 없다.

| 컴포넌트 | 넓음(≥1024) | 중간(640~1023) | 좁음(<640) |
|---|---|---|---|
| `PlayHeader`·`ResultBand`·장면 글 | 장면 열 맨 위 | 맨 위 | 맨 위 |
| `ActionBar`(행동 상자) | 장면 열, 장면 글 아래 | 장면 글 아래 | 선언 시트 안에만(열렸을 때) |
| `ActionDock`(고정 띠) | 없음 | 없음 | 화면 아래 고정 |
| `PlayMap` | 오른쪽 열 맨 위 | 행동 상자 아래 | 장면 글 아래 |
| `MovePanel` | 오른쪽 열, 지도 아래 | 지도 아래 | 이동 시트 안에만(열렸을 때) |
| 사람 / `DialoguePanel` | 장면 열(대화 중이면 그 자리를 대화가 대신) | 사람은 지도·이동 아래, 대화는 `TalkSheet` | 사람은 지도 아래, 대화는 `TalkSheet` |
| 아는 것·전해 들은 것·소문 | 장면 열, 사람 아래 | 사람 아래 | 사람 아래(3개 + 더 보기) |
| `PlayLog` | 오른쪽 열, 이동 아래 | 맨 끝 | 맨 끝(5줄 + 더 보기) |

## 2. 홈 `/` (FR-S1, UX-12~16)

### 2.1 배치 — 1280

```
┌ AppShell ─────────────────────────────────────────────────────────────────┐
│ Locus   월드* 플레이 GM 에디터                            [한국어|English] │
│ (LLM 꺼짐 띠 — 있을 때만)                                                   │
├───────────────────────────────────────────────────────────────────────────┤
│  HERO                                                                     │
│   A SOLO TABLETOP RPG (display, 작게)                                      │
│   소문은 길을 따라 퍼지고, 마을마다 아는 것이 다르다   (h1, heading)       │
│   세계관 자료로 만든 월드에서 … 솔로 TRPG.   (본문 1~2줄)                  │
│                                                                           │
│  데모 월드 (h2)                                                           │
│  ┌ DemoCard ───────────────────────────────┐                             │
│  │ 엠버리프 섬  [키 없이 플레이] 배지                                      │
│  │ 나무 꼭대기의 마법사 … 사건 씨앗 세 개가 기다린다.                       │
│  │ 지역 12 · 시작 솔트웨이크 항구        (불러온 경우만)                    │
│  │ [이어 하기]  [새 세션]  [에디터에서 보기]   [데모 다시 불러오기](ghost)  │
│  │ 크레딧(작게)                                                            │
│  └──────────────────────────────────────────┘                             │
│                                                                           │
│  내 월드 (h2)                                  [자료로 새 월드 만들기]      │
│  ┌ WorldRow ───────────────────────────────────────────────────────────┐  │
│  │ 이름  id(작게)   지역 12 · 2026년 10월 2일 수정   [열린 세션 1] 배지   │  │
│  │                                   [이어 하기] [새 세션] [편집]        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│  (없으면) 빈 상태: "아직 만든 월드가 없어요" + [자료로 새 월드 만들기]      │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2.2 배치 — 390

```
┌ Locus        [한]  [≡] ┐
│ HERO (h1 두 줄 이내, 본문 한 줄 + 더 보기 없음) │
│ 데모 월드                                       │
│ ┌ DemoCard (그림은 위, 버튼은 세로로 꽉 차게) ┐ │
│ │ 엠버리프 섬  [키 없이 플레이]                │ │
│ │ 설명 3줄까지                                  │ │
│ │ 지역 12 · 시작 솔트웨이크 항구                │ │
│ │ [ 이어 하기 (primary, 꽉 참) ]                │ │
│ │ [ 새 세션 ] [ 에디터에서 보기 ]               │ │
│ └──────────────────────────────────────────────┘ │
│ 내 월드          [자료로 만들기]                 │
│ WorldRow: 이름 / 지역 12 · 수정일 / 배지 / 버튼 줄 │
└─────────────────────────────────────────────────┘
```

### 2.3 요소와 동작

| 요소 | 내용 | 누르면 | testid |
|---|---|---|---|
| Hero | 사전 `home.tagline`(h1), `home.lead`(본문). 정적이다 | — | `home-hero`(새) |
| 데모 카드 | 매니페스트 데모마다 하나. 제목·설명·크레딧은 `*_ko`가 있으면 그것을, 없으면 영어를 쓴다. 불러온 데모만 한 줄을 더한다(설계 리뷰 R-03): | 아래 | `demo-card-<name>`(유지) |
|  | - "지역 N": 월드 목록의 `region_count` |  |  |
|  | - "시작 <이름>": 그 월드의 이름표(`worldNames`)에서 `start_region_id`의 이름. 이름표에 없으면 "시작 …"을 빼고, 영어 이름을 얻으려고 월드 전체를 내보내지 않는다 |  |  |
|  | - NPC·씨앗 수와 시안의 미니 지도 그림은 넣지 않는다. 데이터를 얻으려면 월드 전체 내보내기가 필요하다 |  |  |
| └ 안 불러옴 | [바로 플레이](primary), [에디터에서 보기] | 불러오기 → 새 세션 → `/play/:id` / 불러오기 → 에디터 | `demo-play-<name>`, `demo-edit-<name>`(유지) |
| └ 불러옴, 열린 세션 있음 | [이어 하기](primary), [새 세션], [에디터에서 보기], [데모 다시 불러오기](ghost 버튼, 새 메뉴 프리미티브 없음 — 설계 리뷰 R-04) | 가장 최근 열린 세션으로 / 시작 지역에서 새 세션 / 에디터 / 교체 확인 흐름(`useReplaceConfirm`: "교체할까요?" → "N개 닫고?") | `demo-continue-<name>`(새), `demo-new-session-<name>`(새), `demo-edit-<name>`(유지), `demo-fresh-<name>`(새 버튼), 확인 `demo-confirm`(유지) |
| └ 불러옴, 열린 세션 없음 | [바로 플레이](primary = 새 세션, 묻지 않음), [에디터에서 보기], [데모 다시 불러오기] | 위와 같음 | `demo-play-<name>`, `demo-fresh-<name>` |
| └ 세션 읽기 실패 | 불러옴 상태의 버튼([새 세션]·[에디터에서 보기]·[데모 다시 불러오기])과 "세션을 읽지 못했어요 [다시 시도]" 한 줄. [이어 하기]는 숨긴다 | 다시 읽기 | `demo-sessions-error-<name>`(새) |
| └ 목록이 모르는 월드(409) | 안 불러옴 상태에서 [바로 플레이]가 409(이미 있음)를 받으면 지금처럼 묻는다: "이 월드로 / 새로". 이 경로에만 `demo-ask`·`demo-keep`·`demo-reload`가 남는다 | 이 월드로 = 새 세션 / 새로 = 교체 확인 흐름 | `demo-ask`·`demo-keep`·`demo-reload`(유지, 409 경로만) |
| 내 월드 | 월드 목록에서 **데모 이름과 같은 id를 뺀** 줄(Q1). 이름은 `name_ko` → `name`. 열린 세션 수는 목록의 `open_sessions`를 중립 배지로 보인다(빨간 글씨 아님, UX-14) | — | `my-worlds`(새), `world-row-<id>`(유지) |
| └ [이어 하기] | `open_sessions > 0`일 때만 보인다. 누를 때 `listSessions(id)`를 읽어 열린 것 중 가장 최근(`created_at` 큰 것)으로 간다. 읽기 실패는 줄 안 오류 한 줄 | 가장 최근 열린 세션으로 | `world-continue-<id>`(새) |
| └ [새 세션] | 시작 지역을 고르는 `NewSessionForm`을 연다. 월드가 바뀌면 지역 선택을 비운다(RE-F03) | 새 세션 → `/play/:id` | `world-start-<id>`(유지) |
| └ [편집] | | `/editor/:id` | `world-edit-<id>`(유지) |
| [자료로 새 월드 만들기] | "내 월드" 머리에 하나만 둔다(UX-15) | `BuildPanel` | `home-build`(유지) |
| BuildPanel 월드 id | 칸 아래 안내 "영문 소문자·숫자·-만, 40자까지"(UX-15). 칸은 BuildPanel에 있다(V8 소유, 한 줄만 V4가 더한다) | — | (유지) |
| 상태 | 첫 읽기는 스켈레톤 카드 둘, 오류는 `InlineError` + [다시 시도], 월드 0개는 빈 상태. 데모 목록 오류는 데모 칸에만 보인다 | | `status-loading`, `home-empty`(유지) |

- 빌드가 끝나면(교체 포함) 목록을 다시 읽는다(UX-16).
- 데모 불러오기가 끝나면 두 목록을 다시 읽는다.

## 3. 플레이 `/play/:sessionId` (FR-S2, UX-28~33)

### 3.1 배치 — 1280

```
┌ AppShell (GM은 메뉴로만) ─────────────────────────────────────────────────────────┐
│ ┌ 장면 열 (minmax(0,1fr)) ───────────────────────┐ ┌ 오른쪽 열 360px (sticky) ──┐ │
│ │ 엠버리프 섬 › 솔트마치            (경로, 작게) │ │ ┌ 작은 지도 (WorldMap play)┐│ │
│ │ 솔트웨이크 항구 (h1)   마을 · 4턴째            │ │ │ 지금 위치 확대, 갈 수 있음 ││ │
│ │ ┌ 결과 띠 (턴 뒤에만, role=status) ────────┐  │ │ │ 점선, 막힘 ×   [섬 전체]  ││ │
│ │ │ 4턴이 지났어요                    [닫기] │  │ │ └──────────────────────────┘│ │
│ │ │ · 이곳에 새 소문 1                       │  │ │ 범례: 지금 위치 · 갈 수 있음 │ │
│ │ │ · 당신 이야기가 거터라이트에 닿았어요    │  │ │ 갈 수 있는 곳 (h2)           │ │
│ │ │ ┃ GM: 당신은 여관 구석에 앉아 …          │  │ │ 앰버메도  강을 따라 · 1턴 [이동]│ │
│ │ └──────────────────────────────────────────┘  │ │ 거터라이트 길로 · 2턴   [이동]│ │
│ │ 장면 글 (지역 설명, story 글꼴)                │ │ 스톤브라우 막혀 있음 · 길이   │ │
│ │ ┌ 행동 상자 ───────────────────────────────┐  │ │   무너졌어요 (회색, 버튼 없음)│ │
│ │ │ 무엇을 할까요?                            │  │ │ 여정 기록 (h2)               │ │
│ │ │ [선언 입력………………] 0/300자            │  │ │ 4턴 당신 이야기가 …          │ │
│ │ │ [선언하기 · 1턴] (primary) [기다리기 · 1턴]│  │ │ 3턴 …   (최근 30줄)          │ │
│ │ └──────────────────────────────────────────┘  │ └─────────────────────────────┘ │
│ │ 이곳의 사람들 (h2)  ← 대화 중이면 대화 패널(Q5) │                                 │
│ │ 이곳 사람들이 아는 것 / 전해 들은 이야기 / 떠도는 소문                            │
│ └────────────────────────────────────────────────┘                                │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 배치 — 390

```
┌ Locus              [한] [≡] ┐
│ 엠버리프 섬 › 솔트마치        │
│ 솔트웨이크 항구  마을·4턴째    │
│ ┌ 결과 띠 ┐                  │
│ 장면 글                       │
│ ┌ 작은 지도 (16:10) [섬 전체]┐│
│ 이곳의 사람들 (카드, [말 걸기])│
│ 이곳 사람들이 아는 것 (3개 + 더 보기) │
│ 전해 들은 이야기 / 떠도는 소문 │
│ 여정 기록 (5줄 + 더 보기)     │
│ (아래 여백 = 띠 높이 + 안전 영역) │
├──────────────────────────────┤
│ [기다리기] [선언하기] [이동]   │ ← 고정 행동 띠 (Q3), 각 44px 이상
└──────────────────────────────┘
  [선언하기] → 아래 시트: 입력 상자, 글자 수, [선언하기 · 1턴]
  [이동]     → 아래 시트: 갈 수 있는 곳 목록(막힌 곳 포함)
  [말 걸기]  → 전체 시트: 대화(Q5), 뒤로 가기 = 닫기
```

### 3.3 요소와 동작

| 요소 | 내용 | 누르면 | testid |
|---|---|---|---|
| 경로 | `level_path_ids`를 이름표에서 찾아 ` › `로 잇는다. 없으면 `level_path` | — | `region-path`(유지) |
| 지역명·단계·턴 | 이름표 → `region_name`. 단계는 `enumLabel("regionLevel")`, 턴은 `turnLabel` | — | `region-title`(유지) |
| 닫힌 세션 띠 | 세션이 `closed`면 장면 위에 "이 세션은 끝났어요" + [홈으로]. 행동·이동·대화 입력이 꺼진다 | 홈 | `closed-banner`(새), `play-home-link`(새) |
| GM 작업 중 안내 | `view.gm_busy`가 참이면(V5 전에는 없음 = 거짓) "GM이 작업 중이에요. 잠시 뒤 다시 해 보세요" | — | `gm-busy-notice`(새) |
| 결과 띠(Q2) | 마지막 턴의 결과를 모은다. | [닫기]: 접음 | `result-band`(새), `result-band-close`(새) |
|  | - 제목: "N턴이 지났어요"(턴 없음은 "조용히 지나갔어요") |  |  |
|  | - 바뀐 지역 줄(`changeSummary`, 이름은 이름표) |  |  |
|  | - 선언의 GM 문장(`declaration.text`) |  |  |
|  | - 대화 끝의 판단 결과 |  |  |
|  | `role="status"`. 다음 행동을 시작하면 비운다 |  |  |
| 경고 알림 | 턴 실패(위험, 닫을 때까지), 예산 소진, LLM 실패만 Toaster로 보인다. 턴 결과는 알림으로 띄우지 않는다(Q2) | — | `notif-play:*`(유지) |
| 장면 글 | 이름표의 `description` → `view.description`. `font-story` | — | `region-scene`(유지) |
| 행동 상자(넓음·중간) | 선언 입력(라벨 있음, 초점 고리, 글자 수), [선언하기 · 1턴](primary), [기다리기 · 1턴]. 진행 중에는 "턴을 진행하고 있어요…"와 진행 표시가 나오고 버튼이 `aria-disabled`가 된다 | 선언·기다리기 | `action-bar`, `declare-input`, `declare-count`, `declare-btn`, `wait-btn`, `turn-progress`(유지) |
| 고정 행동 띠(좁음) | 세 버튼이다. `pb-[env(safe-area-inset-bottom)]`. 열려 있는 동안 페이지 아래 여백을 띠 높이만큼 둔다 | [기다리기]: 바로 / [선언하기]: 선언 시트 / [이동]: 이동 시트 | `action-dock`, `dock-wait`, `dock-declare`, `dock-move`(새) |
| 선언 시트·이동 시트 | V2 `Dialog`에 더하는 `variant="sheet"`(아래 고정, 너비 꽉 참, 위 모서리만 둥금, 최대 높이 85vh). 제목·초점 가둠·Esc·초점 복귀는 지금 Dialog 그대로다. 내용은 열렸을 때만 렌더한다. 선언 시트는 보내면 닫히고, 이동 시트는 고르면 닫힌다 | | `declare-sheet`, `move-sheet`(새) |
| 이곳의 사람들 | NPC 카드: 이름표의 이름·역할·설명, 나눈 말 수, [말 걸기]. ~~키가 없으면 [말 걸기]가 꺼지고 이유를 적는다~~ → 코드 리뷰 01 #28(a): 키가 없어도 [말 걸기]는 열리고, 목록 위에 "AI 키가 없어 지난 대화만 볼 수 있어요" 한 줄, 패널은 기록만 보이며 입력을 잠근다(BR-U5-29, BR-V4-18과 맞춤) | 대화 열기(Q5) | `npc-list`, `npc-<id>`, `npc-<id>-talk-btn`, `npc-<id>-talked`(유지) |
| 대화(넓음) | "이곳의 사람들" 자리를 `DialoguePanel`이 대신한다. [닫기]는 목록으로 돌아가고, [대화 끝내기]는 판단 턴을 시작해 결과 띠에 결과를 낸다 | | `dialogue-panel` 외 유지 |
| 대화(좁음·중간) | 같은 `DialoguePanel`을 `Dialog variant="full"`(화면 전체)에 담는다. 열림은 **라우터 상태**가 정한다(설계 리뷰 R-06, BLM § 2.5): `navigate(현재 경로, {state: {talk: npcId}})`로 열고, 뒤로 가기·[닫기]·Esc가 닫는다 | | `talk-sheet`(새) |
| 이곳 사람들이 아는 것 | 지식 `statement_ko` → `statement`. 좁음에서는 3개 + [N개 더 보기] | — | `knowledge-item-<id>`(유지) |
| 전해 들은 이야기 | 감쇠 단어(`decayWord`) 배지 + 문장. 안내 한 줄 | — | `hearsay-hint`, `hearsay-item-<id>`(유지) |
| 떠도는 소문 | 왜곡 단어(`degreeWord`)와 믿음 단어(`bandOf("support")`) 배지. 내 행적이면 "당신 이야기" 배지. 수치는 없다 | — | `rumor-<id>`, `deed-badge-<id>`(유지) |
| 작은 지도(Q4) | `WorldMap mode="play"`, `focus={지금 위치, 이웃}`, `reachableIds`(갈 수 있는 곳), `playerRegionId`. 이름은 이름표(지도에 넘기는 `regions`의 `name`을 바꿔 넘김). 바탕 그림은 viewBox를 따른다(V2 이월). 보기 전용이다 | 갈 수 있는 곳을 누르면 이동 목록의 그 줄을 강조하고 스크롤한다. 이동하지 않는다 | `play-map`(새) |
| 갈 수 있는 곳 | 줄마다 이름, 연결 단어(`enumLabel("travelBy", kind)`), "N턴", [이동]. 막힌 연결도 회색 줄로 두고 이유를 사전 문장으로 적는다(UX-32): "막혀 있음 · 지금은 지나갈 수 없어요"(`play.move.blocked`). 서버의 `reason`("blocked pass")은 코드 같은 영어라 보이지 않는다 | [이동] | `move-panel`, `move-<id>`, `move-<id>-btn`, `move-<id>-blocked`(유지) |
| 여정 기록 | 최근 30줄, 최신이 위. 기록 문장의 이름은 `payload`의 id로 이름표에서 찾고, 없으면 굳은 이름. 좁음에서는 5줄 + 더 보기 | — | `play-log`, `log-<kind>`(유지) |
| 빈 `/play` | "세션이 없어요" + [홈으로] + "홈의 데모 카드에서 바로 시작할 수 있어요" | 홈 | `play-empty`(유지), `play-home-link` |
| 진행 오류·느림 | 턴 확인이 실패하면 행동 자리에 `InlineError` + [다시 확인]. 상한을 넘으면 "턴이 오래 걸려요" + [다시 확인] | 다시 폴링 | `turn-error`, `turn-slow`, `turn-recheck`(새) |
| 오류 | `InlineError`(`describeError`) + [다시 시도] | 다시 읽기 | `play-error`(유지) |

**없어지는 것** (의도한 변경):
- `play-gm-btn`: GM은 메뉴로만 간다.
- `play-narration`·`narration-card`: 결과 띠로 옮긴다. `narration-card`는 띠 안 선언 문장의 testid로 남긴다.

## 4. 컴포넌트 트리와 props

```
routes/HomePage
  layout/AppShell
  features/home/HomeHero                      [새]
  features/home/DemoCards → DemoCard          [바뀜] 상태별 버튼, *_ko, 세션 읽기
  features/home/MyWorlds → WorldRow           [새] (HomePage의 목록을 옮김)
  features/play/NewSessionForm                [바뀜] RE-F03
  features/editor/BuildPanel                  [한 줄] 월드 id 안내
routes/PlayPage                               [다시 씀] 조립만
  layout/AppShell(sessionId, worldId, llmOff)  [한 줄] 월드 없는 "에디터" 항목은 NavLink가 아니라 Link(활성 표시 없음, UX-13)
  features/play/PlayLayout                    [새] 폭별 섹션 순서(§ 1 표). SplitView는 쓰지 않는다
  features/play/PlayHeader                    [새] 경로·지역명·단계·턴·닫힘 띠·GM 작업 중
  features/play/ResultBand                    [새] (NarrationCard 흡수)
  features/play/RegionScene                   [바뀜] 장면 글 + 사람 + 지식 3섹션, names
  features/play/ActionBar                     [바뀜] 넓음·중간의 행동 상자, 초점 고리
  features/play/ActionDock                    [새] 좁음의 고정 띠 + 선언·이동 시트
  features/play/DialoguePanel                 [바뀜] 폭에 따라 열 안 또는 TalkSheet 안
  features/play/TalkSheet                     [새] 전체 시트 + 뒤로 가기
  features/play/PlayMap                       [새] WorldMap play 래퍼(이름표, 강조 콜백)
  features/play/MovePanel                     [바뀜] 막힌 줄 이유, 강조, names
  features/play/PlayLog                       [바뀜] names, 좁음 접기
hooks/usePlaySession(sessionId)               [새] 세션·지역·기록 읽기, 늦은 답 버림, 다시 읽기
hooks/useTurnRun(sessionId)                   [새] act → 202 → 폴링(상한) → 결과
hooks/useWorldNames(worldId)                  [새] 이름표, 언어 따라 다시 읽기
hooks/useMedia(query)                         [새] matchMedia 구독
ui/Dialog                                     [바뀜] variant: "center"(지금) | "sheet" | "full"
ui/Button                                     [바뀜] busy → aria-disabled + 누름 무시(§ 4.1)
```

### 4.1 공유 프리미티브 변경 (설계 리뷰 R-05)

- **`ui/Dialog`**: `variant?: "center" | "sheet" | "full"`(기본 `center` = 지금). 나머지 동작(이름 붙이기, 초점 가둠, Esc, 초점 복귀, 알림 영역 누름 무시)은 변형과 무관하게 같다. `ui.primitives.test`에 변형마다 이름·Esc·초점 복귀를 하나씩 더한다.
- **`ui/Button`**
  - `busy`면 `disabled` 속성 대신 `aria-disabled="true"`를 두고, `onClick`은 감싸서 바쁜 동안 부르지 않는다(`if (busy) { e.preventDefault(); return; }`).
  - `disabled`(바쁨이 아닌 꺼짐)는 지금처럼 native `disabled`다.
  - 영향: 바쁜 버튼에 `toBeDisabled()`를 단언하는 테스트만 바뀐다(`ui.primitives.test`의 Button·ConfirmDialog 등). 코드 계획에서 수를 세어 고친다.
  - V6·V8에 넘기는 계약: "바쁜 버튼은 `aria-disabled`이고 누름을 무시한다. 단언은 `toHaveAttribute("aria-disabled", "true")`로 한다".

주요 props:

```ts
// hooks
usePlaySession(sessionId: string): {
  session: GameSession | null; view: RegionView | null; log: TimelineEntry[];   // 지금 sessionId의 것만 (BLM 2.1)
  state: "loading" | "ready" | "error"; error?: DescribedError; reload(): void;  // 같은 키로 다시, 화면 유지
}
useTurnRun(sessionId: string, opts: { pollMs?: number; maxPolls?: number; onSettled(): void }): {
  running: TurnRun | null; slow: boolean;          // slow = 상한을 넘음
  outcome: TurnOutcome | null;                     // 결과 띠에 들어갈 것
  act(action: PlayerAction): Promise<boolean>;     // 202면 true
  recheck(): void;                                 // slow일 때 [다시 확인]
  clearOutcome(): void;
}
type TurnOutcome = { turn: number; changes: RegionTurnChange[]; declaration?: Narration | null; quiet: boolean };
useWorldNames(worldId: string | null): { names: WorldNames | null; nameOf(kind: "regions"|"npcs"|"event_seeds", id: string, field: string, fallback: string): string }
// names.world_id !== worldId 이면 null로 다룬다 (옛 월드의 이름표를 쓰지 않음)
useMedia(query: string): boolean

// components
PlayHeader({ view, session, names })
ResultBand({ outcome, names, onClose })
RegionScene({ view, names, npcCounts, activeNpcId, onTalk, compact })   // compact = 좁음 접기
ActionBar({ running, disabled, closed, gmBusy, onWait, onDeclare, maxChars })
ActionDock({ running, disabled, closed, gmBusy, moves, names, onWait, onDeclare, onMove, maxChars })
PlayMap({ view, regions, connections, names, onPickReachable(regionId) })
MovePanel({ moves, names, disabled, highlightId, onMove })
TalkSheet({ open, title, onClose, children })
DemoCard({ demo, world, onChanged })        // world: 목록의 WorldInfo | null(안 불러옴). 열린 세션은 카드가 읽는다
PlayLayout({ wide, narrow, header, band, scene, actions, map, moves, people, knowledge, log, dock })
MyWorlds({ worlds, demoNames, onChanged })
```

## 5. 새 바탕 하나: `useMedia`

```ts
export function useMedia(query: string): boolean   // matchMedia + change 구독, SSR/테스트에서는 false
```

- 테스트는 `window.matchMedia`를 대역으로 바꿔 좁음·넓음을 고른다.
- 렌더가 갈리는 곳만 쓴다(고정 띠·시트·대화 자리). 배치는 CSS로 한다.

## 6. API 연결

| 화면 | 읽기 | 쓰기 |
|---|---|---|
| 홈 | 이렇게 읽는다(설계 리뷰 R-03). | `loadDemo`, `startSession` |
|  | - `listDemos()`, `listWorlds()`: 둘 다 `?lang=`, `useRequestLang` 키 |  |
|  | - 불러온 데모마다 `listSessions(name)`: 서버는 모든 세션을 오래된 순으로 준다. 카드가 `status === "open"`만 걸러 `created_at` 내림차순으로 쓴다 |  |
|  | - 불러온 데모마다 `worldNames(name)`: 시작 지역 이름 |  |
|  | - 내 월드 행은 목록의 `open_sessions`만 보고, [이어 하기]를 누를 때 `listSessions`를 읽는다 |  |
|  | - 새 세션 폼을 열 때만 `exportWorld`(지역 목록, 지금과 같음) |  |
|  | - 홈에서 월드 전체 내보내기를 미리 받지 않는다 |  |
| 플레이 | `getSession`, `getRegion`(`?lang=`), `getLog(30)`, `worldNames(session.world_id)`, `exportWorld(world_id)`(작은 지도의 지역·연결, 한 번), `listNpcs`(나눈 말 수), `listTurnRuns(running)`(재진입), `getTurnRun` | `act`(기다리기·선언·이동·대화 끝내기), 대화 `say` |

## 7. testid 정리

- **유지**
  - 홈: `demo-card-*`, `demo-play-*`, `demo-edit-*`, `demo-reload-*`, `demo-*` 확인 흐름, `world-row-*`, `world-start-*`, `world-edit-*`, `home-build`, `home-empty`
  - 플레이: `region-scene`, `region-title`, `region-path`, `npc-*`, `knowledge-item-*`, `hearsay-*`, `rumor-*`, `deed-badge-*`, `action-bar`, `declare-*`, `wait-btn`, `turn-progress`, `move-*`, `play-log`, `log-*`, `play-empty`, `play-error`
  - 대화: `dialogue-*`, `notif-*`, `new-session-*`
- **새로**
  - 홈: `home-hero`, `my-worlds`, `world-continue-*`, `demo-continue-*`, `demo-new-session-*`, `demo-fresh-*`, `demo-sessions-error-*`
  - 플레이: `closed-banner`, `play-home-link`, `gm-busy-notice`, `result-band`, `result-band-close`, `action-dock`, `dock-wait`, `dock-declare`, `dock-move`, `declare-sheet`, `move-sheet`, `talk-sheet`, `play-map`, `turn-error`, `turn-slow`, `turn-recheck`
- **바뀜**
  - `demo-ask`·`demo-keep`·`demo-reload`는 409 경로(목록이 모르던 월드)에만 남는다.
  - 불러온 카드의 교체는 `demo-fresh-<name>` → `demo-confirm`이다.
- **없앰**: `play-gm-btn`, `play-narration`, 플레이의 턴 알림 카드(`notif-turn:*`, `notif-play:turn`).

### 7.1 고치는 기존 테스트 (의도한 변경, 설계 리뷰 R-04)

| 테스트 | 왜 | 고치는 방향 |
|---|---|---|
| `home.test.tsx` EX-2 "a held world with open sessions — reload asks twice" | 불러온 카드는 [바로 플레이]에서 묻지 않는다 | `demo-fresh-<name>` → `demo-confirm` 두 번(교체, N개 닫기)으로 같은 흐름을 본다 |
| `home.test.tsx` "a held world — [play this world]" | `demo-keep` 질문 없이 새 세션으로 간다 | 불러온 카드의 [바로 플레이]가 묻지 않고 `startSession`을 부르는지 본다. 질문 경로는 "before the list arrives"(409) 테스트가 맡는다 |
| `home.test.tsx` EX-13 "a held world without its start region" | 같은 이유 | `demo-start-missing`은 그대로다. 진입만 `demo-keep` 없이 바뀐다 |
| `home.test.tsx` "lists worlds … open sessions" | 데모 id 줄이 빠진다(Q1), 열린 세션 배지 클래스가 바뀐다 | 데모가 아닌 월드로 본다. 배지는 중립 클래스다 |
| `play.test.tsx:138-144` | 턴 결과가 알림이 아니라 결과 띠다 | `result-band`에 지역 변화 문장이 있고, 알림 영역에는 예산 경고만 있다 |
| `play.test.tsx:142-143` `play-narration` | 결과 띠로 옮김 | `result-band` |
| `play.test.tsx` 409 진행 중(154), 실패(268) | 남는 알림(BR-V4-04 허용 목록) | 그대로 |
| `deeds.test.tsx:125` `narration-card` | 결과 띠 안에 남는다 | 그대로 |
| `deeds.test.tsx:138` 진행 중 알림 | 남는 알림 | 그대로 |
