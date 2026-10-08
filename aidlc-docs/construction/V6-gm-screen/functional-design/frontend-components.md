# V6 GM 화면 — Frontend Components

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**지금 하는 것**: V6 Functional Design. 이 문서는 GM 화면의 다음을 정한다.
- 배치(1280·390)
- 요소
- 컴포넌트
- API 연결
- testid

결정(계획 `construction/plans/V6-gm-screen-functional-design-plan.md`):

| 질문 | 답 | 내용 |
|---|---|---|
| Q1 | A | 지도는 왼쪽에 둔다. 오른쪽 열 맨 위에는 턴 도구를 늘 두고, 그 아래에 탭 다섯 개([지역] [사건] [씨앗] [기록] [행적])를 둔다. 지도에서 지역을 누르면 [지역] 탭이 열린다 |
| Q2 | A | 턴 결과는 턴 도구 바로 아래 결과 띠 하나에 담는다. 기록 탭은 그 턴의 줄에 "새로"를 붙인다. 턴 결과에는 알림을 띄우지 않는다 |

바탕
- V2: `ui/`(Tabs, ConfirmDialog, Select, StatusView, Toaster, CommitRange, Badge, Card, Field, Button), `layout/`(AppShell, Section), `map/WorldMap`, `format/`, `errors/`, `hooks/`
- V4: `useMedia`, `useWorldNames`, `useMounted`, `ResultBand`의 꼴, `PlayLayout`의 "폭마다 한 번" 규칙

---

## 1. 폭과 나뉨

| 이름 | 폭 | GM |
|---|---|---|
| 넓음 | `lg` 1024px 이상 | 머리 두 줄(세션·플레이어)은 위에 가로로 둔다. 그 아래가 2열이다. 왼쪽 지도는 `minmax(0,1fr)`, 오른쪽 열은 `400px`이다. 오른쪽 열은 붙박이(sticky)이고 자체 스크롤이 있다 |
| 중간·좁음 | 1023px 이하(390 기준) | 1열로 쌓는다. 순서: 머리 → 플레이어 → 턴 도구 → 결과 띠 → 지도 → 탭 |

- 넓음인지는 `useMedia(WIDE)`가 정한다(V4와 같은 상수). GM은 중간과 좁음의 순서가 같아서 `narrow`를 쓰지 않는다.
- **각 부분은 한 폭에 한 번만 렌더한다**(V4 BR-V4-25와 같은 규칙). 같은 testid가 DOM에 둘 생기지 않는다.
- 배치는 `features/gm/GmLayout`이 폭별 순서로 정한다. V2 `SplitView`는 휴대폰 순서가 섞여(턴 도구가 지도보다 위) 쓰지 않는다.
- jsdom에는 `matchMedia`가 없어 테스트의 기본은 1열이다. 넓음은 대역으로 고른다(V4와 같음).

| 부분 | 넓음(≥1024) | 1열(<1024) |
|---|---|---|
| `GmHeader`(세션 고르기·새 세션·끝내기) | 맨 위 가로 | 맨 위 |
| `PlayerStrip` | 머리 아래 가로 | 머리 아래 |
| `MapPane`(상태 토글·범례·바탕 그림·지도) | 왼쪽 열 | 결과 띠 아래 |
| `TurnTools`(턴 진행·사건 제안·일괄) | 오른쪽 열 맨 위 | 플레이어 아래 |
| `TurnBand`(결과 띠, Q2) | 턴 도구 아래 | 턴 도구 아래 |
| `GmTabs`(지역·사건·씨앗·기록·행적) | 오른쪽 열, 띠 아래(자체 스크롤) | 지도 아래 |

## 2. 배치 — 1280

```
┌ Locus · 홈 · 플레이 · [GM] · 에디터                             한국어 | EN ┐
├────────────────────────────────────────────────────────────────────────────┤
│ GM · 엠버리프 섬   세션 [4턴 · 진행 중 · 10월 8일 14:05 ▾]                    │
│                    [플레이어 없는 새 세션]  [세션 끝내기]                      │
│ 여행자 아린 · 솔트웨이크 항구 · 4턴                      [플레이로 돌아가기]   │
├──────────────────────────────────────────────┬─────────────────────────────┤
│ [세계 상태 ✓]  색: 왜곡 낮음 ▢▢▢▢▢ 높음        │ [턴 진행]  사건 제안 [1▾][제안]│
│ 숫자: 지금 도는 소문 · ✦ 플레이어 이야기        │ [빈 지역 소문 만들기]          │
│                          [지도 그림 고르기]    │ [모든 지역 소문 다시 만들기]   │
│ ┌──────────────────────────────────────────┐ │ ┌ 5턴이 지났어요 ─────── [닫기]┐│
│ │                                          │ │ │ 솔트웨이크 항구: 새 소문 1   ││
│ │            지도 (GM 모드)                  │ │ │ 거터라이트: 사건 1 적용      ││
│ │   ◎ 플레이어   ● 고른 지역   색 = 왜곡      │ │ └─────────────────────────────┘│
│ │   배지 "3 ✦1"                             │ │ [지역][사건 ②][씨앗][기록][행적]│
│ │                                          │ │ ─────────────────────────── │
│ │                                          │ │ 솔트웨이크 항구 · 마을         │
│ └──────────────────────────────────────────┘ │ 도는 소문 3 · 굳은 소문 1 ·    │
│                                              │ 플레이어 이야기 1 · 사건 1      │
│                                              │ 왜곡 0.40 · 조금 비틀림 ━━○━━ │
│                                              │ 소문이 더한 몫 0.05 · 조금      │
│                                              │ 소문  [만들기] [다시 만들기]    │
│                                              │  ┌ 굳음 · 0.42 · 많이 비틀림 ┐ │
│                                              │  │ "항구 창고가 불탔대"       │ │
│                                              │  │ 공신력 0.72 · 널리 믿음 ━○ │ │
│                                              │  └───────────────────────────┘ │
│                                              │ ▸ 이 지역에 사건 만들기         │
│                                              │ ▸ NPC가 아는 것 (12)            │
└──────────────────────────────────────────────┴─────────────────────────────┘
```

- 오른쪽 열의 높이는 `calc(100vh - 머리 높이 - 여백)`을 넘지 않는다. 넘치는 것은 열 안에서 스크롤된다. 턴 도구와 결과 띠는 열 맨 위에 붙어 있다.
- 다른 탭들의 모습
  - **[사건]**: "제안 2"(승인·버리기), "진행 중 1"(해소), "끝남 4"(접힘, 10개씩 더 보기)
  - **[씨앗]**: 씨앗 카드(제목·지역·분류·규모·[시작] 또는 "진행 중")
  - **[기록]**: 최신부터 20줄, 마지막 턴의 줄에 "새로", [더 보기]
  - **[행적]**: 행적 카드(지금 `DeedPanel`의 내용, 라벨 바뀜)

## 3. 배치 — 390

```
┌ Locus             [≡]  한국어|EN ┐
├─────────────────────────────────┤
│ GM · 엠버리프 섬                   │
│ 세션 [4턴 · 진행 중 · 10월 8일 ▾]  │
│ [플레이어 없는 새 세션]            │
│ [세션 끝내기]                      │
│ 아린 · 솔트웨이크 항구 · 4턴        │
│ [플레이로 돌아가기]                │
├─────────────────────────────────┤
│ [턴 진행]                          │
│ 사건 제안 [1▾] [제안]              │
│ [빈 지역 소문 만들기]              │
│ [모든 지역 소문 다시 만들기]        │
│ ┌ 5턴이 지났어요 ──── [닫기] ┐     │
│ │ 솔트웨이크 항구: 새 소문 1  │     │
│ └─────────────────────────┘     │
│ [세계 상태 ✓] 범례(줄바꿈)          │
│ ┌───────── 지도 ─────────┐       │
│ │  (폭에 맞춰 줄어듦)       │       │
│ └────────────────────────┘       │
│ [지역][사건②][씨앗][기록][행적]     │
│ (탭 줄이 넘치면 줄바꿈)             │
│ 솔트웨이크 항구 …                  │
└─────────────────────────────────┘
```

- 가로 스크롤은 없다. 탭 줄은 V2 `Tabs`처럼 `flex-wrap`으로 줄을 바꾼다.
- 슬라이더는 라벨 아래 줄로 내려 폭을 다 쓴다.
- 지도 머리의 컨트롤(토글·범례·바탕 그림)은 줄을 바꾼다.

## 4. 요소와 동작

| 요소 | 보이는 것 | 누르면 |
|---|---|---|
| 세션 고르기 + [열기] | 아래 "세션 라벨" 규칙을 따른다. 열린 세션이 먼저 오고, 그 뒤에 "끝난 세션" 묶음(`optgroup`)이 온다. 고르기만으로는 옮기지 않는다(코드 리뷰 01 #9, 사람이 고름) | [열기]를 누르면 `/gm/:id`로 가고, 새 화면의 세션 고르기가 초점을 받는다. 옛 세션 화면은 곧바로 비운다(BLM § 1.3) |
| [플레이어 없는 새 세션] | 버튼(보조) | `startSession(worldId)` → 새 세션으로 간다. 요청 중에는 꺼진다 |
| [세션 끝내기] | 위험 버튼. 이 세션이 끝났으면 없다 | 확인 대화상자(위험): "이 세션을 끝낼까요? 끝낸 세션은 다시 열 수 없어요. 플레이어도 더 행동할 수 없어요." → `closeSession` → 세션을 다시 읽는다. 쓰기 컨트롤이 모두 꺼지고 "끝난 세션" 띠가 보인다 |
| 끝난 세션 띠 | 머리 아래 "이 세션은 끝났어요. 기록은 볼 수 있어요." | — |
| 플레이어 띠 | "이름 · 지역 · N턴". 턴이 진행 중이면 "· 턴 진행 중"을 붙인다. 플레이어가 없는 세션에서는 띠가 없다 | [플레이로 돌아가기] → `/play/:id`. [다시 확인](진행 중일 때만) → 플레이어와 진행 중 run을 다시 읽는다 |
| 세계 상태 토글 | `aria-pressed`. 처음에는 켜져 있다 | 지도 색·배지를 켜고 끈다. 상태 읽기는 토글과 무관하게 늘 한다(지역 탭 요약이 쓴다) |
| 범례 | "색: 왜곡 낮음 → 높음 · 숫자: 지금 도는 소문 · ✦: 플레이어 이야기" | — |
| 지도 | `WorldMap mode="gm"`. 끌리지 않는다. 플레이어 고리, 고른 지역, 상태 색·배지 | 지역을 누르면 고르고 [지역] 탭을 연다 |
| [지도 그림 고르기] | V2 `FileInput`. 고른 파일 이름을 보인다 | 로컬 그림을 지도 바탕으로 쓴다(서버로 가지 않음) |
| [턴 진행] | 주 버튼 | `advanceTurn` → 결과 띠. 요청 중, 일괄 생성 중, 세션이 끝났을 때 꺼진다 |
| 사건 제안 개수 + [제안] | `Select` 1..상한 + 버튼. LLM이 없으면 꺼지고 `title`로 까닭을 알린다 | `suggestEvents(n)` → [사건] 탭 배지가 는다. 탭은 옮기지 않는다 |
| [빈 지역 소문 만들기] | 버튼. 진행 중에는 진행 막대와 "N/M · 실패 K"를 보인다 | 일괄 생성(BLM § 4) |
| [모든 지역 소문 다시 만들기] | 위험 버튼 | 확인 → 일괄 다시 만들기 |
| 결과 띠 | "N턴이 지났어요" 또는 "조용한 턴이었어요". 바뀐 지역 줄마다 지역 이름(버튼)과 바뀐 내용. 예산이 바닥났거나 LLM이 실패했으면 그 줄을 덧붙인다 | 지역 이름 → 그 지역을 고르고 [지역] 탭을 연다. [닫기] → 띠를 접는다. 다음 턴 진행이 띠를 바꾼다 |
| [지역] 탭 | § 4.1 | — |
| [사건] 탭 | § 4.2 | — |
| [씨앗] 탭 | 씨앗마다 제목·지역·분류 라벨·"규모 0.50 · 보통"을 보인다. 진행 중이면 "진행 중"이고, 아니면 [시작]이 있다 | [시작] → `startSeed` → 씨앗과 사건을 다시 읽는다 |
| [기록] 탭 | 최신부터 20줄. 줄 머리는 "N턴"이다. 마지막 턴 진행이 만든 줄에는 "새로" 배지를 붙인다 | [더 보기] → 20줄 더 |
| [행적] 탭 | 지금 `DeedPanel` 내용 | [없던 일로 하기] → 확인 → `voidDeed` |

**세션 라벨**: "N턴 · 진행 중 · 10월 8일 14:05"
- 상태는 `enumLabel("sessionStatus", …)`로 쓴다.
- 날짜는 `formatDateTime(created_at)`으로 쓴다.
- `created_at`이 없으면 날짜 대신 id 앞 8자를 쓴다.
- 같은 라벨이 둘이면 뒤에 " · " + id 앞 4자를 붙인다.

### 4.1 [지역] 탭

고른 지역이 없으면 빈 상태를 보인다: "지도에서 지역을 누르면 그 지역의 소문과 왜곡을 손볼 수 있어요."

| 순서 | 내용 | 동작 |
|---|---|---|
| 0 | 지역 고르기(`Select`, 단계별 묶음). 고른 지역이 없을 때도 있다(코드 리뷰 01 #10: 지도 밖에서 어느 지역이든 고르는 길) | 고르면 그 지역을 보인다 |
| 1 | 지역 이름(이름표)과 단계 라벨 | — |
| 2 | 요약 한 줄: "도는 소문 3 · 굳은 소문 1 · 플레이어 이야기 1 · 진행 중 사건 1"(세계 상태의 그 지역 행) | — |
| 3 | 왜곡: 라벨 "왜곡 0.40 · 조금 비틀림"은 끄는 값을 따라간다. `CommitRange`. 되먹임 몫이 0보다 크면 "소문이 더한 몫 0.05 · …"을 보인다 | 놓거나 키보드로 바꾸면 `setDistortion` → 돌아온 행으로 바로 고치고, 상태를 다시 읽는다(BLM § 3) |
| 4 | 소문 머리: [이 지역 소문 만들기] [다시 만들기]. LLM이 없으면 꺼진다 | 만들기 → `generateRumors`. 다시 만들기 → 확인 → `regenRumors`. 둘 다 끝나면 이 지역 소문과 상태를 다시 읽는다 |
| 5 | 소문 카드: 배지("굳음", "플레이어 이야기"), "0.42 · 많이 비틀림", 문장(`LocalizedText`), 공신력 라벨(끄는 값을 따라감) + `CommitRange` | 공신력 저장 → `setSupport` → 돌아온 소문으로 그 카드를 고친다. `rumor_inactive` 409면 문장을 보이고 이 지역 소문을 다시 읽는다 |
| 6 | 빈 소문: "이 지역에는 아직 도는 소문이 없어요." | — |
| 7 | ▸ 이 지역에 사건 만들기(`Section` 접힘, 처음에는 닫힘) | § 4.3 |
| 8 | ▸ NPC가 아는 것 (N)(`Section` 접힘, 처음에는 닫힘). 지금 `RegionKnowledgePanel`의 내용이다. 스코프는 라벨로, 수치는 "0.80 · 확실함"으로 보인다 | 펼칠 때 처음 읽는다. 펼친 상태는 지역을 바꿔도 유지된다 |

### 4.2 [사건] 탭

- 세 묶음: "제안"(suggested), "진행 중"(active), "끝남"(resolved).
  - 끝남은 접혀 있고, 펼치면 최신 10개와 [더 보기]가 있다.
  - 빈 묶음은 한 줄 빈 문장이다. 예: "기다리는 제안이 없어요".
- 카드에 보이는 것
  - 상태 배지(라벨, 톤: 제안 `neutral`, 진행 중 `event`, 끝남 `neutral`)
  - 지역 이름(버튼: 누르면 그 지역을 고르고 [지역] 탭을 연다)
  - 분류 라벨
  - "규모 0.50 · 보통"
  - 수명 라벨
  - 설명(`LocalizedText`)
- 버튼
  - 제안 카드에는 [승인] [버리기]가 있다. [버리기]는 위험 톤이다.
  - 진행 중 카드에는 [해소]가 있다.
  - 버튼마다 그 카드의 요청 중에는 꺼진다.
- 탭 배지는 제안 수다. 0이면 없다.

### 4.3 사건 만들기 폼 (UX-38)

| 칸 | 라벨(보임) | 규칙 |
|---|---|---|
| 분류 | "분류" | `Select`. 라벨은 `enumLabel("eventCategory")`. 처음 값은 war |
| 설명 | "무슨 일이 일어났나요" | `Field`. 앞뒤 공백을 뺀 길이가 0이면 [사건 만들기]가 꺼진다. 최대 길이는 서버 검증과 같게 코드 계획에서 확인한다 |
| 규모 | "규모 0.50 · 보통"(끄는 값을 따라감) | `Range` 0..1, 0.05 단위 |
| 수명 | "수명" | `Select`: "분류에 따름"(빈 값) / "한 번 일어남"(one_shot) / "이어짐"(persistent) |
| [사건 만들기] | 주 버튼 | `createEvent` → 성공하면 설명 칸만 비운다(분류·규모·수명은 남김). [사건] 탭 배지는 그대로이고, 진행 중 묶음에 카드가 는다. 실패하면 칸을 비우지 않는다 |

## 5. 컴포넌트 트리와 props

```
routes/GmPage                                  [다시 씀] 조립만
  layout/AppShell(worldId, sessionId)
  features/gm/GmLayout                         [새] 폭별 순서(§ 1 표)
  features/gm/GmHeader                         [새] (SessionBar의 GM 몫을 옮김)
  features/gm/ClosedBanner                     [새] 끝난 세션 띠
  features/gm/PlayerStrip                      [바뀜] useResource, [다시 확인], 이름표
  features/gm/MapPane                          [새] WorldStateOverlay(토글·범례) + 바탕 그림 + WorldMap gm
  features/gm/TurnTools                        [새] (ManualTurnPanel을 바꿈) 턴·제안·일괄
  features/gm/TurnBand                         [새] 결과 띠 (play ResultBand와 같은 꼴)
  features/gm/GmTabs                           [새] V2 Tabs 다섯 개, 지도 선택 → 지역 탭
    features/gm/RegionTab                      [새] 요약 + DistortionPanel + RumorPanel + EventForm + RegionKnowledgePanel
      features/gm/DistortionPanel              [바뀜] 수치+뜻, 되먹임 몫 뜻
      features/gm/RumorPanel                   [바뀜] 공신력 라벨 따라감, 배지 라벨, 빈 상태
      features/gm/EventForm                    [새] (EventPanel의 폼을 떼어 냄) 라벨·검증·비우기
      features/gm/RegionKnowledgePanel         [바뀜] 접힘 안, reload로 다시 읽기(다시 마운트 없음), 라벨·뜻
    features/gm/EventPanel                     [바뀜] 세 묶음, 라벨, 지역 이름 버튼
    features/gm/SeedPanel                      [바뀜] useResource, 라벨·뜻
    features/gm/TimelinePanel                  [바뀜] 최신부터, 20줄 + 더 보기, "새로"
    features/gm/DeedPanel                      [바뀜] 라벨 "없던 일로 하기", slant 라벨, 수치+뜻
features/gm/useGmSession(sessionId)            [새] 세션·월드·이름표 읽기, 다시 시도(둘 다)
features/gm/useGmData(sessionId, regionId)     [새] (GmHub의 읽기를 옮김) 키별 useResource + 다시 읽기 표
features/gm/useBulkRumors(sessionId)           [바뀜] 세션이 바뀌면 멈춤, 503 → LLM 안내
features/gm/WorldStateOverlay                  [바뀜] 배지·범례 말, 상태는 늘 읽음
api/http.ts conflictKind                       [바뀜] closed | turn_running | gm_busy | rumor_inactive | null
ui/Select                                      [바뀜] option.group → optgroup
SessionBar.tsx                                 [없앰] 쓰는 곳이 GmPage뿐이다. GmHeader로 옮긴다
features/gm/GmHub.tsx, ManualTurnPanel.tsx     [없앰] GmTabs·TurnTools·useGmData로 나뉜다
MapOverlay.tsx                                 [그대로] GM은 더 쓰지 않는다. 어댑터 삭제는 V8
```

### 5.1 공유 바탕 변경

- **`ui/Select`**
  - 옵션에 `group?: string`을 더한다. 같은 group이 이어지는 옵션은 `<optgroup label>`으로 묶는다. group이 없는 옵션은 지금처럼 그린다.
  - 영향: 기존 호출은 바뀌지 않는다. `ui.primitives.test`에 묶음 하나를 더한다.
- **`api/http.ts` `conflictKind`**
  - 돌려주는 값을 `"closed" | "turn_running" | "gm_busy" | "rumor_inactive" | "conflict" | null`로 넓힌다.
    - code가 있으면 code로 가른다.
    - code가 없는 옛 서버는 지금처럼 문장을 본다: "session is closed"면 closed, 나머지는 turn_running.
  - 지금 `"busy"`를 쓰는 곳은 셋이다: `useTurnRun`, `DeedPanel`, `GmHub`.
    - `"busy"`는 `turn_running | gm_busy`를 함께 뜻하는 도우미 `isBusy(kind)`로 바꾼다. 그래서 동작이 그대로다.
    - 다만 플레이어 알림 문장은 갈린다(BR-V6-20).
- **`errors/describeError`**: 키를 둘 더한다. `error.gm_busy.{title,action}`, `error.rumor_inactive.{title,action}`(ko/en).

### 5.2 주요 props

```ts
// hooks
useGmSession(sessionId: string): {
  session: GameSession | null;           // 지금 sessionId의 것만 (옛 세션은 null)
  world: WorldExport | null;             // session.world_id의 것만
  names: WorldNames | null;              // useWorldNames(session?.world_id)
  state: "loading" | "ready" | "error"; error?: DescribedError;
  retry(): void;                         // 세션과 월드를 모두 다시 읽는다 (RE-F01)
  reloadSession(): void;                 // 화면 유지
}
useGmData(sessionId: string, regionId: string | null): {
  events: Resource<SessionEvent[]>;      // 키 [sid, lang]
  timeline: Resource<TimelineEntry[]>;   // 키 [sid]
  worldState: Resource<WorldState>;      // 키 [sid]
  rumors: Resource<SessionRumor[]>;      // 키 [sid, regionId, lang], regionId null이면 읽지 않음
  seeds: Resource<SeedView[]>;           // 키 [sid]
  deeds: Resource<DeedViewOut[]>;        // 키 [sid, lang]
  after(write: GmWrite): void;           // 다시 읽기 표(BLM § 3)대로 해당 자원만 reload
  patchRumor(r: SessionRumor): void;     // 공신력 저장의 답으로 그 카드를 바로 고침
  patchDistortion(row: RegionDistortion): void;
}
type GmWrite = "turn" | "suggest" | "approve" | "discard" | "resolve" | "create" | "seed"
             | "distortion" | "support" | "generate" | "regen" | "bulk" | "void" | "close";

// components
GmLayout({ wide, header, closed, player, map, tools, band, tabs })
GmHeader({ session, sessions, names, onPick, onNew, onClose, busy })   // sessions: 이 월드의 세션 목록
PlayerStrip({ sessionId, turn, nameOf, rev, onPlayer })
MapPane({ world, names, selectedId, playerRegionId, state, overlayOn, onToggle, onSelect })
TurnTools({ closed, llmOff, advancing, bulk: BulkProgress | null, suggestN, maxSuggest,
            onSuggestN, onAdvance, onSuggest, onGenerateAll, onRegenAll })
TurnBand({ outcome: GmTurnOutcome | null, nameOf, onPickRegion, onClose })
GmTabs({ tab, onTab, regionTab, eventsTab, seedsTab, timelineTab, deedsTab, suggestedCount })
RegionTab({ session, regionId, nameOf, regionState, distortion, rumors, closed, llmOff, bulkBusy, ... })
EventForm({ regionId, closed, onCreate(body): Promise<boolean> })   // true면 설명을 비운다
TimelinePanel({ timeline: TimelineEntry[] | undefined, newTurn: number | null, state, error, onRetry })
type GmTurnOutcome = { turn: number; changes: RegionTurnChange[]; quiet: boolean;
                       budgetExhausted: boolean; llmFailed: boolean };
```

- 이름표: 지역·씨앗 이름은 `useWorldNames(session.world_id).nameOf`로 찾고, 없으면 응답의 영어 이름 → id 순이다(V4 BR과 같음).
- `GmPage`는 `selected`(고른 지역)와 `tab`(열린 탭)을 가진다. 지도 선택과 결과 띠·사건 카드의 지역 이름이 둘을 함께 바꾼다.

## 6. API 연결

| 무엇 | 읽기 | 쓰기 |
|---|---|---|
| 세션·월드 | `getSession`, `listSessions(world_id)`, `exportWorld(world_id)`(월드가 바뀔 때 한 번), `worldNames(world_id)` | `startSession(world_id)`, `closeSession` |
| 플레이어 | `getPlayer`, `listTurnRuns(sid, "running")` | — |
| 턴 | — | `advanceTurn`(동기, `TurnResult`) |
| 지역 탭 | `getWorldState`(요약·지도), `listDistortions`(되먹임 몫), `listRumors(sid, region)`(`?lang=`), `sessionKnowledge(sid, region)`(펼칠 때) | `setDistortion`(저장한 행을 돌려줌), `setSupport`(소문을 돌려줌), `generateRumors`, `regenRumors` |
| 사건 | `listEvents`(`?lang=`) | `suggestEvents(n)`, `approveEvent`, `discardEvent`, `resolveEvent`, `createEvent` |
| 씨앗 | `listSeeds` | `startSeed` |
| 기록 | `getTimeline`(전부; 자르기는 화면) | — |
| 행적 | `listDeeds`(`?lang=`) | `voidDeed` |

- 서버 API는 바꾸지 않는다. V6는 웹만 바꾼다.
- `listDistortions`와 `getWorldState`는 같은 왜곡을 담는다. 지역 탭의 왜곡과 몫은 `getWorldState`의 행(`distortion`, `feedback_share`)에서 읽는다. 그래서 `listDistortions`는 더 부르지 않는다(읽기 하나 줄임). 일괄 다시 만들기의 대상도 상태의 지역 목록이다.

## 7. testid 정리

- **유지**(같은 뜻의 요소에 둔다)
  - `session-select`, `session-new-btn`, `session-close-btn`, `gm-error`, `gm-retry-btn`, `busy`
  - `gm-player-status`, `gm-player-error`, `gm-back-to-play`
  - `gm-state-toggle`, `gm-state-legend`, `gm-state-error`, `map-file-input`
  - `advance-turn-btn`, `suggest-events-btn`, `suggest-n`, `generate-all-btn`, `regen-all-btn`, `generate-progress`
  - `events`, `event-<id>`, `event-status-<id>`, `event-desc-<id>`, `approve-<id>`, `discard-<id>`, `resolve-<id>`
  - `event-form`, `event-category`, `event-description`, `event-magnitude`, `event-lifecycle`, `event-create-btn`
  - `seed-panel`, `seed-row-<id>`, `seed-start-<id>`, `seed-running-<id>`
  - `gm-region`, `gm-no-region`, `distortion-label`, `distortion-slider`, `distortion-feedback`
  - `generate-btn`, `regen-btn`, `rumor-<id>`, `rumor-text-<id>`, `promoted-<id>`, `deed-badge-<id>`, `support-<id>`
  - `region-panel`, `knowledge-item-<id>`, `knowledge-text-<id>`, `region-empty`
  - `timeline`
  - `deed-panel`, `deed-<id>`, `deed-none`, `deed-notice`, `deed-appraisals-<id>`, `deed-reached-<id>`, `deed-voided-<id>`, `void-<id>`, `void-confirm`
  - 지도: `region-marker-<id>`, `player-marker-<id>`, `region-badge-<id>`(V2 WorldMap)
- **새로**
  - 머리와 띠: `gm-header`, `gm-closed-banner`, `session-close-confirm`, `gm-player-recheck`
  - 지도와 턴: `gm-map`, `turn-tools`, `turn-band`, `turn-band-close`, `turn-band-region-<id>`
  - 탭: `gm-tabs`, `gm-tab-region`, `gm-tab-events`, `gm-tab-seeds`, `gm-tab-timeline`, `gm-tab-deeds`
  - 지역 탭: `region-summary`, `support-label-<id>`, `rumors-empty`, `event-form-toggle`, `knowledge-toggle`
  - 사건 탭: `events-suggested`, `events-active`, `events-resolved`, `events-empty-<group>`, `event-region-<id>`
  - 기록 탭: `timeline-more`, `timeline-new-<id>`, `timeline-empty`
- **바뀜**
  - `session-panel`(허브 Panel)은 없어진다. 그 자리의 단언은 `turn-tools`·`gm-tabs`로 옮긴다.
  - `gm-hub-error`는 쓰기 오류 줄로 남는다. 턴 도구 아래, 결과 띠 위에 두고 `describeError` 문장을 보인다.
  - `llm-required`(버튼 옆 글)는 없앤다. AppShell의 LLM 띠 하나만 남는다(BR-V2-20). `llm-notice`는 AppShell 것이다.
  - 턴 알림 카드(`notif-turn:*`)는 없앤다(Q2). `notif-gm:bulk`는 남는다.

### 7.1 고치는 기존 테스트 (의도한 변경)

코드 계획에서 줄 번호를 세어 고친다. 방향은 이렇다.

| 테스트 | 왜 | 고치는 방향 |
|---|---|---|
| `gm.test.tsx` 턴 알림 단언 | 턴 결과가 알림이 아니라 결과 띠다(Q2) | `turn-band`에 지역 줄이 있고, 알림 영역에는 일괄 알림만 있다 |
| `gm.test.tsx`·`components.test.tsx`의 `session-panel` | 허브가 탭으로 나뉜다 | 해당 탭을 열고 단언한다 |
| `components.test.tsx` GmHub 12개 | GmHub가 없어진다 | `GmTabs`·`TurnTools`·`useGmData` 단위로 옮긴다. 단언하는 동작은 그대로다 |
| `gm.test.tsx` `llm-required` | 버튼 옆 글을 없앤다 | 버튼이 꺼지고 `title`이 있는지, AppShell 띠가 하나인지 본다 |
| `deeds.test.tsx` "취소" 라벨 | 라벨이 "없던 일로 하기"로 바뀐다 | 라벨 문장을 바꾼다 |
| `gm.test.tsx` 세션 닫기 | 확인을 거친다 | `session-close-btn` → `session-close-confirm` |
| 타임라인 순서 단언 | 최신부터다 | 첫 줄이 가장 최근 턴이다 |
