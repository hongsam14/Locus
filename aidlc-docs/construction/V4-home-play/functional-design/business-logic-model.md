# V4 홈·플레이 화면 — Business Logic Model

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V4 Functional Design. 홈과 플레이가 무엇을 읽고, 무엇을 하고, 결과를 어떻게 한 곳에 보이는지 흐름으로 정한다.

배치와 요소는 `frontend-components.md`, 규칙 번호(BR-V4-*)는 `business-rules.md`에 있다.

---

## 1. 홈

### 1.1 읽기

```
HomePage
  lang = useRequestLang()                          # 표시 언어가 바뀌면 다시 읽는다 (V3 리뷰 #6)
  demos  = useResource(["demos", lang],  api.listDemos)
  worlds = useResource(["worlds", lang], api.listWorlds)
  demoNames = demos.data.map(d => d.name)
  mine = worlds.data.filter(w => !demoNames.includes(w.id))          # Q1=A
  loadedDemos = demos.data.filter(d => worlds.data has id d.name)
  for each loaded demo (DemoCard 안에서):
      sessions = useResource(["sessions", name], () => api.listSessions(name))
          → open = sessions.filter(s => s.status === "open").sort(created_at 내림차순)   # 서버는 전부, 오래된 순
      names    = useWorldNames(name)          → 시작 지역 이름 (없으면 "시작 …"을 뺀다)
  내 월드 행: 목록의 open_sessions만 본다. [이어 하기]를 누를 때 listSessions(id)를 읽는다
  월드 전체 내보내기(exportWorld)는 새 세션 폼을 열 때만 읽는다 (지금과 같음)
```

- 데모 목록이 비거나 오류이면 데모 칸만 빈 상태·오류이고, "내 월드"는 그대로 읽는다.
- 월드 목록 오류는 "내 월드" 칸만 `InlineError`이고, 데모 카드는 "불러왔는지 모름"으로 그린다.
  - 이때 [바로 플레이]는 지금처럼 `replace=false`로 불러온다.
  - 이미 있으면 409이고, "이 월드로 / 새로" 질문을 띄운다(지금 흐름).

### 1.2 데모 카드 상태

```
state = !there                          → "new"      : [바로 플레이], [에디터에서 보기]
        there && sessions 읽는 중        → "loaded"의 버튼을 꺼 둔 채(스켈레톤 한 줄)
        there && sessions 실패           → "loaded"의 버튼 + "세션을 읽지 못했어요 [다시 시도]" ([이어 하기]는 숨김)
        there && open.length > 0         → "resume"   : [이어 하기], [새 세션], [에디터에서 보기], [데모 다시 불러오기]
        there && open.length === 0       → "loaded"   : [바로 플레이](= 새 세션), [에디터에서 보기], [데모 다시 불러오기]
there = worlds has demo.name || foundThere(409를 받음)
```

| 버튼 | 흐름 |
|---|---|
| [바로 플레이] new | `loadDemo(replace=false)` → `startSession(start_region_id)` → `/play/:id`. 409(이미 있음, 목록이 몰랐던 월드)면 질문 "이 월드로 할까요, 새로 불러올까요?"(`demo-ask`)를 띄운다(지금). [이 월드로](`demo-keep`) = 새 세션, [새로](`demo-reload`) = 아래 교체 확인 흐름 |
| [이어 하기] | `/play/<가장 최근 열린 세션>` |
| [새 세션]·[바로 플레이] loaded | `startSession(start_region_id)` → `/play/:id`. 시작 지역이 없으면(고친 월드) 안내와 [에디터에서 보기]를 보인다(지금의 `demo-start-missing`) |
| [에디터에서 보기] | 있으면 바로 에디터, 없으면 불러온 뒤 에디터(다시 불러오지 않음, BR-U8-21) |
| [데모 다시 불러오기] | 보이는 ghost 버튼이다(새 메뉴 없음). "교체할까요?" → 열린 세션이 있으면 "N개 닫고 교체할까요?"(지금의 `useReplaceConfirm`, `demo-confirm`) → `loadDemo(replace=true, confirm)` → 목록·세션 다시 읽기 |

### 1.3 내 월드

- [이어 하기]: 목록의 `open_sessions > 0`일 때만 보인다. 누르면 `listSessions(id)`를 읽어 열린 것 중 `created_at`이 가장 큰 세션으로 간다. 읽기 실패는 그 줄 안의 오류 한 줄이다.
- [새 세션]: `NewSessionForm`을 그 월드의 지역(`exportWorld`)으로 연다.
  - 폼은 `worldId`가 바뀌면 이름은 두고 지역 선택을 비운다(RE-F03).
  - 열 때마다 새 월드의 지역만 보인다.
- [편집] → 에디터.
- [자료로 새 월드 만들기] → `BuildPanel`.
  - 끝나면(성공·교체·실패 모두) 두 목록을 다시 읽는다(UX-16).
  - 교체가 아닌 성공이면 지금처럼 에디터로 간다.

## 2. 플레이

### 2.1 읽기와 늦은 답

```
usePlaySession(sessionId)
  key = [sessionId, requestLang]                   # rev는 키에 넣지 않는다 (설계 리뷰 R-01)
  r = useResource(key, signal => Promise.all(getSession, getRegion(lang), getLog(30)))  # 늦은 답 버림
  data = r.data && r.data.session.id === sessionId ? r.data : null    # 옛 세션의 data는 버린다
  state: data 없음 + loading → 스켈레톤 | data 있음 → 그린다(다시 읽는 중에도) | error → describeError + [다시 시도]
  reload() = r.reload()                            # 행동 뒤: 같은 키, 화면 유지, 스켈레톤 없음
useWorldNames(worldId)
  key = [worldId, requestLang]                     # 세션 안에서는 한 번, 언어가 바뀌면 다시
  names = r.data && r.data.world_id === worldId ? r.data : null       # 옛 월드의 이름표는 버린다
  nameOf(kind, id, field, fallback) = names?.[kind][id]?.[field] ?? fallback
exportWorld(session.world_id)                      # 작은 지도의 지역·연결. 한 번 (key = [worldId])
listNpcs(sessionId)                                # 나눈 말 수. 실패해도 화면은 그대로
```

- 세션을 바꾸면(`/play/a` → `/play/b`) 키가 바뀐다. 옛 요청은 abort되고, 늦게 와도 버린다(V2 `useResource`).
- `useResource`는 새 키를 읽는 동안 옛 키의 data를 그대로 둔다. 그래서 화면은 `session.id`(이름표는 `world_id`)가 지금 것과 같을 때만 data를 쓴다. 다르면 스켈레톤이다(BR-V4-16).
- 행동 뒤 다시 읽기는 `reload()`다(같은 키). 화면은 그 사이 지금 data를 유지하고 스켈레톤으로 돌아가지 않는다.

### 2.2 행동 → 턴 → 결과

```
useTurnRun(sessionId)
  act(action):
      outcome = null                               # 결과 띠를 비운다 (다음 행동 시작)
      run = await api.act(sid, action)             # 202 | 409 | 400(선언 길이)
          409 turn_running/gm_busy → toast(play:busy, "턴을 진행하고 있어요") ; false
          409 session_closed       → reload() (닫힘 띠가 나온다) ; 알림 없음 ; false
          400                      → 입력을 되살리고 이유를 보인다 ; false
      reload()                                     # 플레이어는 이미 도착했다 (BR-U4-10). 기다리지 않는다
      poll(run.id)                                 # reload와 나란히 시작한다 (설계 리뷰 R-01 (c))
  poll(id):
      for n in 1..maxPolls (기본 120, pollMs 700 → 약 84초):
          wait pollMs; if 세션이 바뀜/떠남 → 멈춤
          r = getTurnRun(id)
              예외 → error = describeError ; running 유지 해제 ; reload() ; 끝 ([다시 확인]으로 다시 폴링)
          running → 계속
          failed  → toast(play:run, 위험, 닫을 때까지) ; reload ; 끝
          done    → outcome = { turn, changes, declaration, quiet: changes 없음 } ; 경고 toast(예산·LLM 실패) ; reload ; 끝
      상한을 넘음 → slow = true ("턴이 오래 걸려요" + [다시 확인]) ; 버튼은 계속 꺼 둠
  recheck(): slow = false ; poll(같은 id)
  재진입: 화면을 열 때 listTurnRuns(running)이 있으면 그 run을 poll한다 (지금과 같음)
```

- **결과는 한 곳**(Q2, BR-V4-04)
  - 성공한 턴의 결과는 `ResultBand`에만 나온다. 턴 알림 카드("턴이 지났어요", 지역별 카드)는 플레이에서 띄우지 않는다.
  - 기록(여정 기록)에는 서버 기록이 다시 읽히며 줄로 쌓인다. 강조하지 않는다.
- **결과 띠의 문장**
  - 지역 변화 줄은 지금의 `changeSummary`(사전 문장)를 쓰고, 이름은 이름표로 바꾼다(`rc.region_id`).
  - 선언 문장은 `declaration.text`이고, 표시 언어로 생성된다(대화 규칙과 같다).
  - 대화 끝내기의 판단 결과는 그 턴의 `changes`와 같은 띠에 들어간다.
- **[닫기]**는 띠만 접는다. 다음 결과가 오면 다시 펼친다.
- **reload와 poll의 순서**
  - `reload()`는 void이고 기다리지 않는다.
  - 폴링은 행동이 202를 받은 즉시 시작한다. 폴링에는 도착한 화면이 필요 없다.
  - 도착은 reload가 오는 대로 그려지고, 턴이 끝나면 폴링이 한 번 더 reload한다. 두 읽기가 겹쳐도 `useResource`의 번호가 마지막 것만 남긴다.
- **진행 중**: `view.turn_running`이거나 `running`이 있으면 행동 버튼이 `aria-disabled`이고 진행 표시가 보인다.
- **GM이 잡고 있음**: run 없이 `turn_running`이면, GM의 짧은 쓰기나 에디터가 세션을 잡고 있는 것이다. 지금처럼 1초마다 최대 5번 다시 읽는다(U3 S02).
  - V5가 `gm_busy`를 더하면 이 경우를 `gm_busy`로 구별해 안내한다(BR-V4-19). 다시 읽기 상한(1초 × 5번)은 `gm_busy`에도 같다.

### 2.3 이동

- 목록 `MovePanel`이 유일한 이동 길이다(Q4).
  - 갈 수 있는 줄의 [이동] → `act({type: "move", to_region_id})`.
  - 막힌 줄은 버튼이 없다.
- 작은 지도에서 갈 수 있는 지역을 누르면 `highlightId`를 둔다. 그 줄이 강조되고, 넓은 화면에서는 줄로 스크롤한다. 좁은 화면에서는 이동 시트를 연다.
- 이동하면 결과 띠는 비고, 장면은 새 지역이다. 대화 중이면 대화를 닫는다(지금 규칙, U5 #8).

### 2.4 선언

- 넓음·중간에서는 행동 상자의 입력이다. 좁음에서는 선언 시트다.
  - 같은 `ActionBar` 입력 컴포넌트를 쓴다.
  - 글자 수 상한은 `view.declare_max_chars`다.
- 서버가 거절하면(400 길이, 409 진행 중) 입력을 되살리고 이유를 보인다(지금 규칙).
- 좁음에서는 보내면 시트를 닫고, 거절이면 시트를 연 채 둔다.

### 2.5 대화 (Q5)

```
넓음(lg+):  talkNpc = 화면 상태(activeNpcId). 열기 = 설정, 닫기 = null. 기록(history)을 쓰지 않는다
그 밖:      talkNpc = location.state?.talk   (react-router가 소유하는 기록, 직접 pushState 하지 않음)
  열기:     navigate(location, { state: { talk: npcId } })          # 기록 한 칸 push
  닫기([닫기]·Esc): location.state?.talk 이 있으면 navigate(-1)     # 그 칸을 되돌림
  뒤로 가기: 라우터가 이전 칸으로 → state.talk 없음 → 시트 닫힘   # 따로 판정하지 않는다
  지역이 바뀜(이동)·세션이 바뀜·언마운트: state.talk 이 있으면 navigate(location, {replace: true, state: null})
                                                                    # 코드 리뷰 01 #12: 이 화면이 넣은 칸이면 navigate(-1)로 되돌린다(칸이 쌓이지 않게). 넣지 않은 칸(복원된 탭)만 replace. 언마운트·세션 변경 때는 하지 않는다(R-11)
  그 NPC가 지역에 없음: 위와 같이 칸을 치운다(코드 리뷰 01 #11)
  넓음으로 바뀜(시트가 열린 채): activeNpcId = state.talk ; navigate(location, {replace: true, state: null})
  넓음에서 좁아짐(열 안 대화 중): navigate(location, {state: {talk: activeNpcId}}) ; activeNpcId = null
[대화 끝내기]: act({type: "end_talk", npc_id}) → 2.2 흐름 → 결과 띠에 판단 결과 ; 위 규칙으로 닫기
```

- ~~키가 없으면 [말 걸기]가 꺼지고 "AI 키가 없어 대화를 쉬어요"를 보인다~~ → 코드 리뷰 01 #28(a)로 바뀜: 키가 없어도 [말 걸기]는 열린다. 목록 위에 "AI 키가 없어 지난 대화만 볼 수 있어요"가 있고, 패널은 지난 대화만 보이며 입력을 잠근다(`dialogue-no-llm`). 키 없는 닫힌 세션도 기록을 읽는다(BR-V4-18).
- 닫힌 세션은 기록만 읽는다(`readOnly`).
- 대화 중에는 사람 목록이 없으므로, 다른 NPC로 바꾸려면 [닫기] 뒤 다시 고른다.

### 2.6 닫힌 세션과 빈 `/play`

- `session.status === "closed"`이면 세 가지를 한다.
  - 닫힘 띠와 [홈으로]를 보인다.
  - 행동 상자·띠·이동 버튼·대화 입력이 꺼진다(대화 기록은 읽힌다).
  - 결과 띠는 마지막 것을 둔다.
- `/play`(세션 없음)이면 빈 상태 문장, [홈으로], 데모 안내를 보인다. 읽기를 하지 않는다.

### 2.7 이름 대체 (V3 이름표)

| 자리 | id | 대체 |
|---|---|---|
| 경로 | `view.level_path_ids[i]` → `regions` `name` | `view.level_path[i]` |
| 지역명·장면 글 | `view.region_id` → `regions` `name`·`description` | `view.region_name`·`view.description` |
| NPC | `npc.id` → `npcs` `name`·`role`·`description` | 응답의 영어 |
| 이동·지도 | `move.region_id`, 지도 `regions[].id` | `move.region_name`, 내보내기의 이름 |
| 결과 띠 | `rc.region_id` | `rc.region_name` |
| 기록 | `payload`의 `region_id`, `from_/to_region_id`, `npc_id`, `seed_id` | `payload`의 굳은 이름, 그다음 `summary` |

- `nameOf`는 렌더마다 계산한다(맵 조회). 이름표가 늦게 오면 영어로 그렸다가 바뀐다. 이때 깜빡임은 허용한다(첫 읽기에는 둘이 거의 함께 온다).

## 3. 바꾸지 않는 것

- 서버 계약은 그대로다. 플레이 요청·응답, 오류 `code`, 이름표·`*_ko`(V3)를 쓰며, V4가 서버를 바꾸지 않는다.
- 대화 한 줄마다 LLM 한 번, 표시 언어로 생성(U5)도 그대로다.
- 에디터 화면(V8)과 GM 화면(V6)은 V4가 바꾸지 않는다. V4가 만지는 남의 파일은 셋이다.
  - **`layout/AppShell.tsx`**(V2 소유, UX-13)
    - 월드가 없을 때의 "에디터" 항목을 `NavLink to="/"` 대신 `Link to="/"`로 둔다. 활성 표시가 생기지 않는다. 지금 링크는 `end`가 없어 모든 경로에서 활성이었다.
    - 월드가 있으면 지금처럼 `NavLink`다.
    - `layout.test.tsx`에 "홈에서 에디터는 활성 아님"을 더한다.
  - **`features/editor/BuildPanel.tsx`**(V8 소유): 월드 id 안내 한 줄.
  - **`ui/Dialog`·`ui/Button`**(V2 소유): frontend-components § 4.1.
- unit-of-work.md V4 코드 목록의 `AppNav.tsx`는 V2에서 `layout/AppShell.tsx`로 합쳐졌다. V4는 AppShell을 고친다.
