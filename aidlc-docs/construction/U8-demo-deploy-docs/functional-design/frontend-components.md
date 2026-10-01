# U8 데모·배포·문서 — Frontend Components

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 기능 설계 중 화면입니다. 다음을 정합니다.
- `/`의 데모 카드(원클릭)
- 키가 없을 때의 안내와 끄기
- GM 화면의 사건 씨앗 패널
- 진행 중 표시
- 데모 이름 상수 걷어 내기

## 1. 컴포넌트 트리 (바뀌는 곳만)
```
src/capabilities.ts (새)            useCapabilities(): { llm, vlm, embedding } | null  — 앱에서 한 번 읽어 모듈에 둔다
src/ui/LlmNotice.tsx (새)           한 줄 안내. features/play/LlmBanner를 이것으로 바꾼다
/                routes/HomePage.tsx (고침)
  ├─ LlmNotice                       capabilities.llm === false 일 때
  ├─ DemoCards   features/home/DemoCards.tsx (새)   listDemos() 항목마다 DemoCard
  │    └─ DemoCard features/home/DemoCard.tsx (새)  제목·설명·credits · [바로 플레이] [에디터에서 보기]
  └─ (월드 목록, 그대로)
/editor/:worldId routes/EditorPage.tsx (고침)        LlmNotice
  ├─ BuildPanel (고침)               [만들기] llm 없으면 끔 + 까닭 · 컨셉 아트 칸에 InProgressBadge
  └─ NpcDraftCards (고침)            [초안] llm 없으면 끔 + 까닭
/gm/:sessionId   features/gm/GmHub.tsx (고침)       LlmNotice · SeedPanel 자리
  ├─ SeedPanel   features/gm/SeedPanel.tsx (새)      씨앗 목록 · [시작] · "진행 중" 표시
  ├─ ManualTurnPanel (고침)          [사건 제안] llm 없으면 끔
  └─ RumorPanel·GmHub 일괄 (고침)    [생성]·[전체 생성]·[재생성]·[전체 재생성] llm 없으면 끔
routes/AppNav.tsx (고침)             worldId가 없으면 에디터 링크는 "/"
src/ui/InProgressBadge.tsx (새)     "진행 중" 작은 표지(title에 한 줄 설명)
```

## 2. 컴포넌트

### 2.1 `useCapabilities` (`src/capabilities.ts`)
- 첫 호출 때 `api.capabilities()`를 한 번 부르고 결과를 모듈 변수에 둡니다. 구독자는 결과가 오면 다시 그립니다.
- 실패하면 `null`(모름)입니다. `null`이면 안내와 끄기를 하지 않습니다(BR-U8-26).
- 헬퍼 `llmOff(caps) = caps?.llm === false`를 둡니다.

### 2.2 `LlmNotice` (`src/ui/LlmNotice.tsx`)
- props: `visible: boolean`, `text?: string`(기본 `t("llm.offNotice")`).
- `data-testid="llm-notice"`. 지금 `LlmBanner`의 모양(sketch-border, highlight)을 그대로 씁니다.
- `PlayPage`는 지금처럼 세션 보기의 `llm_available`로 `LlmNotice`를 씁니다. 문구는 `play.noLlm` 그대로입니다.

### 2.3 `DemoCards` / `DemoCard` (`features/home/`)
| 상태 | 내용 |
|---|---|
| `demos` | `listDemos()` 결과. 실패하면 카드 영역에 한 줄 오류 |
| `worlds` | `HomePage`가 이미 읽은 `listWorlds()`를 받는다(world id가 있는지 판단) |
| `busy` | 카드별. 진행 중이면 두 버튼을 끈다 |
| `ask` | `null` \| `"existing"`(지금 월드로 / 새로 불러와) \| `{ sessions: n }`(열린 세션 닫기 확인) |
| `error` | 카드별 한 줄 |

- [바로 플레이] 흐름은 business-logic-model §2.2를 따릅니다.
  - 불러오기: `api.loadDemo(worldId, name, { replace: true, confirm })` — 서명은 §3과 같은 `(worldId, name, options)`다. vitest가 인자 순서를 단언한다 〔검토 01 R-08〕
  - 세션: `api.startSession(worldId, { name: t("demo.playerName"), start_region_id })`
  - 이동: `navigate("/play/" + id)`
- [에디터에서 보기]: 월드가 있으면 바로 `navigate("/editor/" + id)`, 없으면 불러온 뒤 갑니다.
- 409 본문의 `open_sessions` 수는 `WorldFileBar`와 같은 방식으로 읽습니다(공용 도우미 `openSessionsOf(err)`를 `api/http.ts`에 둡니다). `busy_sessions`가 있으면 확인 없이 `t("demo.busy")`를 보입니다 〔검토 01 R-03〕.
- 불러오기 응답이 `ok=false`이면 error 경고 앞 3개와 `backup_path`를 카드에 보이고 세션을 시작하지 않습니다. [지금 월드로 플레이]의 세션 시작이 404·400이면 `t("demo.startMissing")`와 [새로 불러와 플레이]를 보입니다 〔검토 01 R-03〕.
- 확인 창은 기존 `Modal`을 씁니다(`confirmTone="danger"`).
- testid: `demo-card-<name>`, `demo-play-<name>`, `demo-edit-<name>`, `demo-ask`, `demo-keep`, `demo-reload`, `demo-error-<name>`.

### 2.4 `SeedPanel` (`features/gm/SeedPanel.tsx`)
| 항목 | 내용 |
|---|---|
| props | `sessionId`, `closed: boolean`, `busy: boolean`, `onStart(seedId)`(GmHub의 `run` → 성공 뒤 `refreshRef.current()`), `reloadKey` |
| 읽기 | `api.listSeeds(sid)`. `reloadKey`가 바뀌면 다시 읽는다 |
| 줄 | 제목 · 지역 이름 · 분류 · 크기 · 상태(`running_event_id`가 있으면 "진행 중", 없으면 [시작]) |
| 끄기 | 세션이 닫혔거나 `busy`면 [시작]을 끈다. LLM과는 상관없다 |
| 빈 목록 | "이 월드에는 사건 씨앗이 없습니다" |
| testid | `seed-panel`, `seed-row-<id>`, `seed-start-<id>`, `seed-running-<id>` |

- 오류(409·404)는 GmHub의 오류 줄에 보입니다(지금 `run`의 방식).

### 2.5 LLM 버튼 끄기
| 컴포넌트 | 버튼 | 까닭 표시 |
|---|---|---|
| `BuildPanel` | [만들기] | 버튼 옆 작은 글 `t("llm.required")`. World File 불러오기는 이 패널 밖이라 그대로다 |
| `NpcDraftCards` | [초안] | 같음 |
| `ManualTurnPanel` | [사건 제안] | 같음 |
| `RumorPanel` | [생성]·[재생성] | 같음 |
| `GmHub` | [전체 생성]·[전체 재생성] | 같음 |

- 버튼에는 `disabled`와 `title={t("llm.required")}`를 줍니다.
- 503을 받은 오류 문구는 `t("llm.required")`로 바꿉니다. 바꾸는 곳은 위 버튼과 `DialoguePanel`의 기존 503 처리입니다(BR-U8-27).

### 2.6 `InProgressBadge` (`src/ui/InProgressBadge.tsx`)
- props: `note: string`. 모양은 "진행 중" 작은 표지이고, `title`에 note를 둡니다.
- 쓰는 곳: `BuildPanel`의 컨셉 아트 칸. note는 `t("build.conceptArtsWip")`("올린 그림은 아직 월드 구성에 쓰이지 않거나 일부만 쓰입니다")입니다.

## 3. API 클라이언트 (`src/api/*`)
| 바뀜 | 내용 |
|---|---|
| `api.capabilities()` | 새로. `GET /api/capabilities` |
| `api.listDemos()` | 응답 타입 `DemoInfo`에 `start_region_id`, `credits`, `has_sources`를 더한다 |
| `api.loadDemo(worldId, name, options)` | `name` 기본값(`"aldermoor"`)을 지운다. 이제 필수다 |
| `api.buildWorldDemo` | 지운다(쓰는 곳 없음, 이름이 박혀 있음) |
| `api.listSeeds(sid)` | 새로. `GET /api/gm/sessions/{sid}/seeds` → `SeedView[]` |
| `api.startSeed(sid, seedId)` | 새로. `POST /api/gm/sessions/{sid}/seeds/{seedId}/start` → `SessionEvent` |
| `types.ts` | `Capabilities`, `SeedView`, `EventSeed`, `DemoInfo` 확장, `RegionDeletePlan.seed_ids`, `RegionDeleteReport.seeds_deleted` |

## 4. i18n (ko·en 같은 집합)
- 새 키
  - `demo.play`, `demo.edit`, `demo.playerName`, `demo.existing`, `demo.keep`, `demo.reload`, `demo.closeSessions`, `demo.loadFailed`, `demo.busy`, `demo.startMissing`
  - `llm.offNotice`, `llm.required`
  - `seed.title`, `seed.start`, `seed.running`, `seed.none`, `seed.category`, `seed.magnitude`
  - `timeline.seedStarted`("씨앗 사건 시작: {title}")
  - `build.conceptArtsWip`, `wip.badge`
- 지우는 키: `toolbar.loadDemo`, `editor.noWorld`(쓰는 곳 없음)
- `timelineText`: `event_created` 줄에 `seed_title`이 있으면 `timeline.seedStarted`를 씁니다(U7 #10 폴백 규칙 그대로).

## 5. 테스트 (vitest)
| 파일 | 내용 |
|---|---|
| `home.test.tsx` | EX-1·2·3·12·13·14(`loadDemo` 인자 순서 단언 포함). 데모가 둘이면 카드도 둘. 월드가 있어도 카드가 보임. 단계 실패 시 카드 오류. `llm=false`면 안내가 보이고 [바로 플레이]는 켜져 있음 |
| `gm.test.tsx` | SeedPanel 목록·[시작]·"진행 중"·409 오류 줄·닫힌 세션에서 끔. `llm=false`면 [사건 제안]·[생성]이 꺼지고 수동 사건은 켜짐 |
| `editor.test.tsx` | `llm=false`면 [초안]·[만들기]가 꺼짐. 컨셉 아트 칸의 "진행 중" 표지. 삭제 계획에 씨앗 수 |
| `components.test.tsx` | App 라우팅: `AppNav`의 에디터 링크가 월드 없이 `/`. 데모 불러오기 의도된 변경(`# U8 intended change`) |
| `capabilities.test.ts` | 한 번만 읽음, 실패 → `null` → 끄지 않음 |
| 이름 상수 검사 | TP-U8-6은 백엔드 테스트가 `web/src`도 함께 훑는다 |
