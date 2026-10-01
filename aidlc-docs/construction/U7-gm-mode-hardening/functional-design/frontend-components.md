# U7 GM 모드·안정화 — Frontend Components

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U7 기능 설계 중 화면입니다.
- 플레이↔GM 전환(Q1=B)을 정합니다.
- god component `SessionPanel`을 기능별 패널로 나눕니다.
- 세계 상태 오버레이와 슬라이더 저장을 정합니다.

## 1. 컴포넌트 트리 (바뀌는 곳만)
```
/play/:sid  PlayPage
  └─ 머리 줄: [GM 모드] 버튼 (새)                         → /gm/:sid
/gm/:sid    GmPage
  ├─ PlayerStrip (새, features/gm/PlayerStrip.tsx)      이름·지역·턴·진행 중 + [플레이로 돌아가기]
  ├─ MapOverlay (+ markerId, regionFill, regionBadge)  플레이어 지역 표시, 오버레이 색·배지
  │    └─ WorldStateOverlay (새, features/gm/WorldStateOverlay.tsx)  켜기/끄기 + 범례
  ├─ RegionPanel (그대로)
  └─ GmHub (새, features/gm/GmHub.tsx; SessionPanel.tsx를 대신함, data-testid="session-panel" 유지)
       ├─ ManualTurnPanel   턴 진행·사건 제안·전체 생성·전체 재생성·진행률
       ├─ EventPanel        사건 목록(승인·해소·폐기) + EventForm
       ├─ DistortionPanel   선택 지역 왜곡도 (CommitRange)
       ├─ RumorPanel        선택 지역 소문 + 지지도 (CommitRange) + 생성·재생성
       ├─ TimelinePanel     GM 타임라인 (이름 템플릿)
       └─ DeedPanel         (U6, 위치만 GmHub 안으로)
ui/CommitRange.tsx (새)     Range + 저장 시점 규칙
```

## 2. 컴포넌트별 정의

### 2.1 플레이↔GM 전환 (Q1=B, BR-U7-21·22)
- **`PlayPage` 머리 줄**
  - `[GM 모드]` 버튼(`data-testid="play-gm-btn"`)을 둔다. 누르면 `navigate("/gm/" + sid)`다.
  - 진행 중 실행이 있어도 갈 수 있다. 폴링은 언마운트 때 멈추고(`genRef`, 그대로), 서버의 실행은 계속된다.
- **`GmPage`**
  - `PlayerStrip`이 `api.getPlayer(sid)`와 `api.listTurnRuns(sid)`(가장 최근 하나)를 읽는다.
  - 플레이어가 404면 띠와 돌아가기 버튼을 그리지 않는다(GM 세션).
  - 띠(`gm-player-status`): `"{name} · {지역 이름} · 턴 {turn}"`, 실행 중이면 `"(진행 중)"`
  - `[플레이로 돌아가기]`(`gm-back-to-play`) → `navigate("/play/" + sid)`
  - 지도: `markerId = player.region_id`. 그 지역에 굵은 테두리와 "●" 표시를 둔다.
  - 띠는 GM 쓰기·턴 진행 뒤(`sessionRev`)에 다시 읽는다.
- **돌아오면**: `PlayPage`가 새로 마운트되어 지역·로그·NPC를 다시 읽는다. GM에서 바꾼 것이 보인다(US-5.1 둘째).
- **`AppNav`**: 링크는 그대로 둔다(같은 이동의 다른 입구).

### 2.2 `GmHub`와 패널 (NFR-7, BR-U7-25)
- **`GmHub`(상태 담당)**
  - `SessionPanel`의 상태와 동작을 옮긴다. 상태: 타임라인·사건·왜곡도·소문 병렬 읽기 한 번, `readSeq` 최신 응답만 반영, `run` 래퍼, 전체 생성·재생성(`mapLimit` 5), 확인 모달, 알림.
  - 패널에는 값과 콜백만 내린다.
- **패널**: 받은 값을 그리고 콜백을 부른다. 자기 상태는 폼 입력뿐이다.
- 기존 `data-testid`는 모두 같은 요소에 남긴다. 기존 vitest가 그대로 통과해야 한다.
  - `advance-turn-btn`, `suggest-events-btn`, `generate-all-btn`, `regen-all-btn`, `generate-progress`, `events`, `event-<id>`, `gm-no-region`, `gm-region`, `distortion-slider`, `generate-btn`, `regen-btn`, `event-form`, `event-*`, `rumor-<id>`, `timeline`
- **`EventPanel`**
  - SUGGESTED 사건에는 `[승인]`·`[폐기]`만 그린다. `[해소]`는 ACTIVE에만 그린다.
  - 서버도 막는다(BR-U7-7). 화면은 같은 규칙을 보일 뿐이다.
- **`ManualTurnPanel`**
  - `[사건 제안]` 옆에 개수 선택(1~5, 기본 1, `suggest-n`)을 둔다. 서버 상한과 같다.
- **`DistortionPanel`**
  - 슬라이더 아래에 "되먹임 몫 {share}"를 작게 보인다(`distortion-feedback`). 몫이 0이면 숨긴다.
- **이름**: 사건·소문 줄의 지역은 이름으로 보인다. 이름표는 `GmPage`가 이미 읽은 월드 내보내기의 `regions`에서 만든다.

### 2.3 `WorldStateOverlay` (US-5.5, BR-U7-23)
- 지도 위 토글이다(`gm-state-toggle`, 기본 끔).
- **켜면**
  - `api.getWorldState(sid)`를 읽는다. `sessionRev`가 바뀔 때마다 다시 읽는다.
  - `MapOverlay`에 `regionFill`과 `regionBadge`를 넘긴다.
    - `regionFill`: 왜곡도 5단계 색. `[0,.2)` 종이색, `[.2,.4)`·`[.4,.6)`·`[.6,.8)` 붉은 잉크 농도 3단계, `[.8,1]` 진한 붉은색. 디자인 토큰만 쓴다.
    - `regionBadge`: `"{active}/{promoted}"` 숫자 배지. 행적 소문이 있으면 `"✦{deed}"`를 덧붙인다.
  - 범례(`gm-state-legend`)를 보인다: 색 5칸 + "활성/승격" 설명.
- **끄면**: 색·배지를 지우고 원래 지도로 돌아온다.
- 읽기 실패는 오버레이 자리에 한 줄 오류로 보이고 지도는 그대로 둔다.

### 2.4 `CommitRange` (`ui/CommitRange.tsx`, BR-U7-24)
```ts
interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "value"> {
  value: number;                       // 서버 값
  onCommit: (v: number) => void;       // 저장
}
```
- 안쪽에 `draft` 상태를 둔다. `onChange`는 `draft`만 바꾼다.
- 저장 시점은 `onPointerUp`, `onKeyUp`, `onTouchEnd`, `onBlur`다.
  - `onKeyUp`은 화살표·Home·End·PageUp·PageDown일 때만 저장한다.
- 마지막으로 저장한(또는 서버에서 받은) 값과 같으면 보내지 않는다(ref).
- `value` prop이 바뀌면 `draft`와 ref를 그 값으로 맞춘다.
- 왜곡도·지지도 슬라이더가 이것을 쓴다. 기존 `onMouseUp` 경로는 `onPointerUp`이 대신한다.

### 2.5 `PlayLog`
- `GM_ONLY_KINDS` 필터를 없앤다. 서버가 플레이어 시점으로 거른다(BR-U7-12, 이탈 3).
- 최근 30줄, 최신이 위인 것은 그대로다.
- 새로 보이는 줄의 템플릿(`deed_seeded`·`rumor_spread`)은 플레이어 시점 문장이다(§3).

### 2.6 `DialoguePanel`·`PlayPage` (U5 이월)
- `say`가 503이면 오류 한 줄(`dialogue.failed`)을 보이고, 입력칸의 글은 지우지 않는다.
- `say`가 성공하면 NPC 목록을 다시 읽지 않는다. `npcCounts[npcId] += 2`를 로컬로 한다(U5 C1).

## 3. i18n (ko·en 같은 키 집합, U5 규칙)
| 키 | ko | en |
|---|---|---|
| `play.gmMode` | GM 모드 | GM mode |
| `gm.backToPlay` | 플레이로 돌아가기 | Back to play |
| `gm.playerStatus` | {name} · {region} · {turn}턴 | {name} · {region} · turn {turn} |
| `gm.running` | (진행 중) | (running) |
| `gm.stateToggle` | 세계 상태 | World state |
| `gm.stateLegend` | 왜곡도(색) · 활성/승격 소문(숫자) | Distortion (color) · active/promoted rumors (number) |
| `gm.feedbackShare` | 되먹임 몫 {share} | Feedback share {share} |
| `gm.suggestN` | 개수 | Count |
| `dialogue.failed` | 지금은 대답을 듣지 못했어요. 다시 말해 보세요. | No answer right now. Try again. |
| `timeline.event_suggested` | {region}에 {category} 사건이 제안되었다 | Suggested a {category} event in {region} |
| `timeline.event_approved` | {region}의 {category} 사건을 승인했다 | Approved the {category} event in {region} |
| `timeline.event_discarded` | {region}의 {category} 제안을 버렸다 | Discarded the {category} suggestion in {region} |
| `log.deed_seeded` | {region}에 당신에 대한 이야기가 돌기 시작했다 | Talk about you has started in {region} |
| `log.rumor_spread` | 당신에 대한 이야기가 {region}까지 왔다 | Talk about you has reached {region} |

- 기존 타임라인 템플릿은 `{region}` 자리에 `payload.region_name ?? payload.region_id`를 넣는다(D3). 대상은 생성·재생성·지지도·왜곡도·사건·승격·강등·가지치기다.
- `regenerate`는 `deactivated ?? deleted` 개수를 쓴다.
- 플레이어 로그는 `log.*` 키가 있으면 그것을, 없으면 `timeline.*`을 쓴다.

## 4. API·타입
- `api/gm.ts`
  - `getWorldState(sid): Promise<WorldState>` 새로 둔다.
  - `suggestEvents(sid, n)`은 그대로다(값 범위만 1~5).
- `types.ts`
  - `WorldState`, `RegionState`를 더한다.
  - `RegionDistortion.feedback_share`를 더한다.
  - 타임라인 종류 셋을 더한다.

## 5. 상태 흐름 (GM 왕복 한 번)
```
PlayPage [GM 모드] → /gm/:sid (PlayPage 언마운트, 폴링 정지)
GmPage: session · world export · player · last run 읽기 → PlayerStrip, 지도 표시
GM: 사건 승인 → run(): 쓰기 → GmHub refresh → onChanged → sessionRev++ → PlayerStrip·오버레이 다시 읽기
GM: [플레이로 돌아가기] → /play/:sid → PlayPage 마운트 → 지역·로그·NPC 새로 읽기
```

## 6. 테스트 (vitest)
| 테스트 | 확인 |
|---|---|
| `CommitRange` 키보드 | 화살표 `keyUp` 한 번 → `onCommit` 1회. 값이 같으면 0회. `blur` → 1회 |
| `CommitRange` 포인터·터치 | `pointerUp`·`touchEnd` → 저장 |
| GM 전환 | `play-gm-btn` → `/gm/sid` 경로. 플레이어 있으면 `gm-back-to-play`와 `gm-player-status`(지역 이름·턴), 404면 둘 다 없음 |
| 오버레이 | 토글 → `getWorldState` 1회, 배지 `"3/1"`, 범례. 끄면 배지 없음 |
| `EventPanel` | SUGGESTED에 해소 버튼 없음, ACTIVE에 승인·폐기 없음 |
| 타임라인 이름 | `event_suggested`·`promote` 줄이 `region_name`을 보인다. 이름 없는 지난 줄은 id |
| `PlayLog` | 서버가 준 `deed_seeded` 줄이 보인다(화면 필터 없음) |
| 대화 실패 | `say` 503 → `dialogue.failed`, 입력 유지. 성공 → `listNpcs` 재호출 없음 |
| 기존 GM 테스트 | `components.test.tsx`·`deeds.test.tsx`의 기존 `data-testid` 단언이 분할 뒤에도 GREEN |
