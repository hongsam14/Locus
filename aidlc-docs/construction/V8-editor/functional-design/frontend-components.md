# V8 에디터 화면 — Frontend Components

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**지금 하는 것**: V8 Functional Design. 이 문서는 에디터의 배치, 요소, 컴포넌트 트리, API 연결, testid를 정한다.
- 흐름은 `business-logic-model.md`에, 규칙과 시험은 `business-rules.md`에 있다.

결정(계획 `construction/plans/V8-editor-functional-design-plan.md`)
- Q1 = A: GM과 같은 틀. 지도 왼쪽 + 오른쪽 400px 패널에 탭 넷.
- Q2 = A: 플레이만. [이 월드로 플레이] + 열린 세션 수. `SessionBar`는 지운다.

---

## 1. 폭과 나뉨

| 폭 | 배치 |
|---|---|
| 넓음(≥ 1024px, V4·V6와 같은 `WIDE`) | 머리가 폭 전체를 쓴다. 그 아래 지도(남는 폭) + 오른쪽 패널(400px). 패널은 위에 붙어 있고 자체 스크롤을 가진다(`sticky top-4`, `max-h-[calc(100vh-2rem)]`). 본문 폭은 GM처럼 `max-w-[1240px]` 가운데다 |
| 좁음(< 1024px) | 한 열: 머리 → 지도 → 패널. 각 부분은 한 번만 놓인다 |

- 틀은 GM과 같다. `GmLayout`의 넓음·좁음 꼴을 공유 부품 `layout/MapPanelLayout`으로 뽑는다(props는 § 5.3).
  - `GmLayout`은 얇은 래퍼로 남는다. GM 시험은 `GmLayout`을 바로 렌더하므로 그대로 돈다. 래퍼는 `testId="gm-layout"`, `panelLabel=t("label.gmPanel")`, `panelTop`(턴 도구·오류·결과 띠, `gm-panel-top`), `narrowOrder=["head","panelTop","map","panel"]`을 넘긴다.
  - 에디터는 `testId="editor-layout"`, `panelLabel=t("label.editorPanel")`, `panelTop` 없음, `narrowOrder=["head","map","panel"]`을 넘긴다.
  - 뽑기는 GM의 DOM과 testid(`gm-layout`, `gm-panel-top`, 패널 이름)를 바꾸지 않는다.
- 390px에서 가로 스크롤이 없다(FR-D5). 지도는 열 폭을 따른다(지금의 `min(800px, …)` 고정 폭을 없앰). `min-w-80`을 없애고, 줄은 감긴다.

## 2. 배치 — 1280

```
┌ AppShell 머리(메뉴·언어) ─────────────────────────────────────────────────┐
│ [LLM 꺼짐 띠 — AppShell이 하나만]                                         │
├──────────────────────────────────────────────────────────────────────────┤
│ 에메랄드 섬 (h1)   지역 12 · 연결 18 · 지식 40      [파일 ▾]              │
│                    열린 세션 2개 · 교체하면 닫혀요   [이 월드로 플레이]    │
│ (파일 ▾을 열면 그 아래 한 줄: [저장(내려받기)] [불러오기] [자료로 만들기])│
├───────────────────────────────────────────┬──────────────────────────────┤
│ [선택·이동] [지역 추가] [연결 긋기]  도움말 │ [지역] [범위 없는 지식 3]     │
│ 범례: ● 마을 ■ 구역 ▲ 지형 · ─ 길 ┄ 강 …  │ [보강] [상식 근거]            │
│                          지도 그림 [고르기]│ ┌ 지역 고르기 [솔트웨이크 ▾] ┐│
│                                           │ ▾ 기본 정보                  │
│                                           │   이름 / 단계 / 상위 / 설명  │
│                  지 도                    │   [저장]                     │
│              (남는 폭, 16:10)              │ ▸ 연결 3                     │
│                                           │ ▸ 이곳 지식 7                │
│                                           │ ▸ 주민 2                     │
│                                           │ ┄┄ 위험 ┄┄                   │
│                                           │   [이 지역 지우기]           │
└───────────────────────────────────────────┴──────────────────────────────┘
```

- 지도 위 띠는 머리 하나다(UX-17). 월드 id는 머리에 보이지 않는다. 이름이 없는 월드만 id를 제목으로 쓴다.
- 오류 줄은 일어난 자리에 둔다: 머리 쓰기는 머리 아래, 지도 쓰기는 지도 머리 아래, 패널 쓰기는 그 섹션 안.

## 3. 배치 — 390

```
┌ AppShell 머리 ─────────────┐
│ 에메랄드 섬 (h1)           │
│ 지역 12 · 연결 18 · 지식 40 │
│ [파일 ▾] [이 월드로 플레이] │
│ 열린 세션 2개              │
├────────────────────────────┤
│ [선택·이동][지역 추가]      │
│ [연결 긋기]                │
│ 범례(감김)                  │
│ 지도 그림 [고르기]          │
│ ┌ 지도 (열 폭, 16:10) ┐    │
│ └────────────────────┘    │
├────────────────────────────┤
│ [지역][범위 없는 지식 3]    │
│ [보강][상식 근거]  (감김)   │
│ 지역 고르기 [▾]             │
│ ▾ 기본 정보 …               │
└────────────────────────────┘
```

- 한 열이다. 탭 줄과 도구 줄은 감긴다. 지도는 열 폭을 쓴다.
- 지도를 누르면 [지역] 탭이 열리고 패널 머리로 스크롤한다(좁음에서만, 지도 아래가 보이지 않으므로).

## 4. 요소와 동작

### 4.1 머리 (`EditorHeader`)

| 요소 | 동작 |
|---|---|
| 월드 이름 `h1` | `world.name`(이름표 번역이 있으면 그것), 없으면 월드 id |
| 수 | "지역 12 · 연결 18 · 지식 40"(`graph-status`를 지킴) |
| [파일 ▾] | `aria-expanded` 단추. 열면 바로 아래 한 줄에 세 단추가 나온다. Esc, 바깥 누름, 동작 시작에 닫히고 초점은 [파일 ▾]로 돌아간다. 숨은 파일 input은 줄 밖에 늘 있다. 새 의존성 없이 만든다(드롭다운 메뉴 부품이 없음). BLM § 7.1 |
| [저장(내려받기)] | World File을 내려받는다(지금과 같음) |
| [불러오기] | 파일 고르기 → 교체 확인 → 열린 세션이 있으면 닫기 확인(지금과 같은 두 단계) → 성공 알림 |
| [자료로 만들기] | 빌드 대화상자를 연다(§ 4.6) |
| 열린 세션 수 | "열린 세션 N개 · 교체하면 닫혀요". 0이면 보이지 않는다(Q2 = A) |
| [이 월드로 플레이] | 홈과 같은 `NewSessionForm`(이름 + 시작 지역, 평면 목록)을 연다. 시작하면 `/play/:sessionId`로 간다. 월드가 없거나 지역이 없으면 꺼진다. props는 BLM § 8 |

### 4.2 지도 칸 (`EditorMapPane`)

| 요소 | 동작 |
|---|---|
| 도구 줄 `role="toolbar"` | [선택·이동] [지역 추가] [연결 긋기]. 화살표 키로 옮긴다(로빙 tabindex). 고른 도구는 `aria-pressed`. 옆에 도움말 한 줄(`map-hint`) |
| 범례 | 단계 모양(● 마을, ■ 구역, ▲ 지형, 큰 글씨 = 대륙·지방)과 연결 종류의 선. 사전 라벨이다 |
| 지도 그림 | GM `MapPane`과 같은 `FileInput`, 도움말 "이 브라우저에서만 쓰여요"(`map-file-input` 지킴) |
| 지도 | `WorldMap mode="edit"`를 바로 쓴다(`MapOverlay` 어댑터 없앰). 4px 넘게 끌면 옮긴다. 추가 도구는 빈 곳 누름 → 새 지역 대화상자. 연결 도구는 두 지역 → 새 연결 대화상자 |
| 첫 읽기 | 지도 자리에 로딩 판(GM과 같은 `aspect-[16/10]` 회색 판) |

새 지역 대화상자: 이름, 단계(사전 라벨), 상위 지역(단계별 묶음), 설명(`Textarea`).

새 연결 대화상자
- 두 지역 이름과 종류(사전 라벨)를 고른다.
- 가중은 `CommitRange` 하나로 다루고, 라벨은 "0.60 · 잘 다님"이다. 폼에서는 값만 정하고 [저장]이 쓴다(BLM § 4).
- 같은 쌍·종류가 이미 있으면 "연결 고치기"로 바뀌고 지금 가중을 보인다(지금 동작을 지킴, U3 #15).

### 4.3 패널 탭 (`ui/Tabs`)

| 탭 | 라벨(ko) | 내용 |
|---|---|---|
| `region` | 지역 | § 4.4 |
| `unscoped` | 범위 없는 지식 N | 범위 없는 지식과 지역 정하기(지금 `UnscopedPanel`) |
| `augment` | 보강 | § 4.5 |
| `wiki` | 상식 근거 | 사전 목록, 참조, 끊긴 참조, 지우기(지금 `WikiPanel`) |

- `ui/Tabs`는 안 보이는 탭을 내린다(unmount). 그래서 탭의 입력 상태는 페이지가 쥔다(§ 5.2). 탭을 오가거나 지도를 눌러도 보강 답과 범위 없는 지식의 고른 지역이 남는다(UX-24).
- `editor-tab-*` testid를 탭 단추에 남긴다.

### 4.4 [지역] 탭 (`RegionTab`)

1. **지역 고르기**: `Select`로 단계별 묶음을 보인다(GM `RegionTab`과 같은 꼴, 키보드 접근). 지도와 같은 선택을 가리킨다.
2. 고른 지역이 없으면 "지도에서 지역을 고르거나 위에서 고르세요"를 보인다.
3. **인스펙터 섹션**(`Section collapsible level=3`)

| 섹션 | 처음 | 머리 | 내용 |
|---|---|---|---|
| 기본 정보 | 펼침 | "기본 정보" | 이름, 단계, 상위 지역, 설명(`Textarea`), [저장] |
| 연결 | 접힘 | "연결 N" | 상대 지역 · 종류 · 가중(`CommitRange`, 놓으면 저장) · 근거 사전 · [연결 지우기](이름 있는 ✕) |
| 이곳 지식 | 접힘 | "이곳 지식 N" | 지식 목록(번역 보기), [고치기], [범위 고치기], [지우기], [지식 더하기] |
| 주민 | 접힘 | "주민 N" | NPC 목록, [고치기](자기 사전 키), [지우기], [NPC 더하기], [NPC 제안](LLM, 꺼지면 안내) |

4. **위험 칸**: 섹션들 아래, 구분선 뒤에 [이 지역 지우기]. 삭제 계획 확인(`ConfirmDelete`)을 거친다. [저장]과 다른 칸이다(UX-19).

- 섹션의 펼침은 페이지가 쥔다. 처음 들어올 때만 기본 정보를 펼치고 나머지는 접는다. 그 뒤로는 사용자가 정한 대로이며, 지역을 바꾸거나 새 지역을 만들어도 바뀌지 않는다(설계 리뷰 01 R-08).
- 섹션을 접거나 탭을 바꾸면 그 안의 폼이 내려간다(`Section`·`ui/Tabs`는 안 보이는 것을 내림). 저장하지 않은 기본 정보·지식 더하기·NPC 폼의 글은 그때 사라진다. 이것은 알려진 제약이다(BR 알려진 제약). 페이지가 쥐는 것은 보강 초안, 범위 없는 지식의 고른 지역, 펼침 상태뿐이다.
- 연결 줄의 상대 지역 이름을 누르면 그 지역을 고른다.

### 4.5 [보강] 탭 (`AugmentPanel`)

| 요소 | 지금 | 바뀜 |
|---|---|---|
| 상태 줄 | "상태: open · 답 3/30" | "진행 중 · 답한 질문 3개". 멈추면 "답 한도에 닿아 멈췄어요", 수렴하면 "더 물을 것이 없어요"(사전 라벨, "/30" 없앰) |
| 질문 카드 | 대상 칸이 `<code>` 원문 | 대상 이름 + 종류 라벨(예: "지식 · 물고기") + 문제 종류 라벨(예: "낮은 확신"). 연결은 두 지역 이름과 종류 라벨이다. 질문 문장은 화면이 문제 종류마다 사전 문장으로 만든다. 서버 문장은 보이지 않는다(코드 리뷰 01 #3, 사람이 고름 A: LLM이 없으면 서버 문장은 영어 틀이고 칸 원문이 든다) |
| 입력 칸 | 서버의 `needs` | 그대로(FR-C12, V7에서 서버가 맞춤) |
| 변경 기록 | `low_confidence:confirm` 원문 | "낮은 확신 · 확인"처럼 문제 종류 + 행동 라벨 |
| 무시한 질문 | 내부 열쇠 `<code>` | 대상 이름(열쇠의 id를 월드 이름으로), [다시 보기] |
| 이대로 둔 질문 | 없음 | "이대로 둔 질문 N개"(접힘): 대상 이름. 되살리기 없음(V7) |
| 오류 | `String(e)` | `describeError` 문장, 원문은 접음 |

- 쳐 둔 답은 페이지가 쥔다. 다른 탭에 갔다 와도, 다른 카드에 답해도 남는다(지금 S28 시험을 지킴).

### 4.6 빌드 대화상자와 리포트 (`BuildPanel`, `BuildReportPanel`)

- 대화상자 동작은 지금과 같다(파일 고르기, 교체 확인, LLM 꺼짐, 닫았다 열기).
- 리포트

| 줄 | 보임 |
|---|---|
| 머리 | "빌드 끝" / "빌드에 문제가 있어요"(지금 키) |
| 수 | 지역·연결·엔티티·지식·보강·사전(지금 줄) |
| 이어 붙임 | "NPC 2명 · 사건 씨앗 1개를 새 지역으로 옮겼어요"(V7 `carried_npcs`·`carried_seeds`). 둘 다 0이면 숨김 |
| 범위 없는 지식 | "범위 없는 지식 3개 보기" 단추 → 대화상자를 닫고 [범위 없는 지식] 탭을 연다(UX-22). 0이면 숨김 |
| 교체·백업 | 지금 줄(교체로 닫은 세션 수, 백업 경로) |
| 경고 | 단계마다 사전 라벨과 수: "이어 붙이지 못함 2", "백업 실패", "중복 id", "세션을 닫지 못함 1"… 각 줄을 펼치면 서버 문장(영어 원문)이 보인다. 단계 라벨 표는 BR-V8-15 |

### 4.7 빈 상태와 로딩

- 첫 읽기: 머리는 월드 id, 지도 자리는 로딩 판, 패널은 로딩 표시(`StatusView loading`).
- 월드 없음(404): "아직 이 월드가 없어요" + [자료로 만들기](지금 `empty-hint`, 도구는 꺼짐). 홈 문장을 빌려 쓰지 않는다.
- 읽기 실패: `InlineError`(문장 + [다시 시도] + 원문 접음).

## 5. 컴포넌트 트리와 props

```
EditorPage (routes) — 월드 읽기, 선택, 탭, 탭 상태를 쥔다
└ AppShell
  └ MapPanelLayout (layout, GM과 공유) wide={useMedia(WIDE)}
    ├ head:  EditorHeader
    │         ├ FileActions (파일 ▾ → 저장·불러오기·자료로 만들기, 교체·닫기 확인)
    │         └ PlayThisWorld (NewSessionForm 재사용)
    ├ map:   EditorMapPane
    │         ├ MapTools (toolbar)  ├ MapLegend  ├ FileInput(지도 그림)
    │         ├ WorldMap mode="edit"
    │         ├ NewRegionDialog     └ NewConnectionDialog
    └ panel: EditorTabs (ui/Tabs)
              ├ RegionTab → RegionPicker, RegionInspector
              │               ├ Section 기본 정보 → RegionForm
              │               ├ Section 연결 → ConnectionList (CommitRange)
              │               ├ Section 이곳 지식 → KnowledgeList
              │               ├ Section 주민 → NpcEditorList (+ NpcDraftCards)
              │               └ DangerZone → ConfirmDelete
              ├ UnscopedPanel
              ├ AugmentPanel → AugmentQuestion × n
              └ WikiPanel
BuildPanel (Dialog) → BuildReportPanel
```

### 5.1 지우는 것과 옮기는 것

| 대상 | 처리 |
|---|---|
| `web/src/MapOverlay.tsx` | 지운다. `MapCanvas`가 `WorldMap`을 바로 쓰는 `EditorMapPane`이 된다 |
| `web/src/SessionBar.tsx` | 지운다(Q2 = A). `variant="full"`·`"picker"` 모두 쓸 곳이 없다(V6 이월) |
| `WorldFileBar.tsx` | `EditorHeader` + `FileActions`로 나뉜다. 교체 확인 흐름은 그대로 옮긴다 |
| `GmLayout` | 넓음·좁음 꼴을 `layout/MapPanelLayout`으로 뽑고, GM은 그 위에서 순서를 정한다 |
| `MapCanvas`의 `LEVELS`·`KINDS` | `format/enums`의 `ENUM_VALUES`를 쓴다 |
| `types.ts` | `BuildReport.carried_npcs?`·`carried_seeds?`, `AugRun.kept_keys?`, `ChangeSet.kept_key?`를 더한다(V7 이월) |
| `format/enums` | `augmentationIssue`(gap, low_confidence, wiki_conflict, orphan, dangling, unscoped)와 `buildStage`(ingestion, topology, wiki, ontology, persist-graph, persist-search, persist-meta, embed, import, load, backup, carry-over, duplicate-ids, commit, sessions)를 더한다. 사전에 ko/en 라벨을 둔다 |

### 5.2 페이지가 쥐는 상태 (`EditorPage`)

| 상태 | 뜻 |
|---|---|
| `world` | `useResource(["world", worldId])`로 읽은 `WorldExport` |
| `selected` | 고른 지역 id. 추가한 지역은 다시 읽은 뒤 정한다(BLM § 3) |
| `pendingSelect` | 추가 직후 고를 `{id, gen}`. 풀리는 때는 BLM § 3 표 |
| `worldGen` | 월드 답이 올 때마다 1씩 늘어남(BLM § 3) |
| `moved` | 끌기 덮개 `{[regionId]: {x, y}}`(BLM § 4) |
| `connection` | 고른 연결(지도에서 선을 누름) |
| `tab` | 열린 탭 |
| `inspectorOpen` | 섹션별 펼침 `{basic, connections, knowledge, npcs}` |
| `augDrafts` | 보강 카드별 쳐 둔 답 `{[issueKey]: AnswerDraft}`(질문 id가 아님, BLM § 6) |
| `augRunId` | 지금 run id(지금과 같음) |
| `unscopedPick` | 범위 없는 지식별 고른 지역 `{[knowledgeId]: regionId}` |
| `mapUrl`, `mapName` | 지도 그림(이 브라우저만) |
| (`rev` 없음) | 쓰기 뒤에는 각 읽기의 `reload()`를 부른다. 키를 바꾸지 않으므로 화면이 로딩으로 돌아가지 않는다(BLM § 2) |

### 5.3 주요 props(새 것과 바뀐 것)

```ts
MapPanelLayout({
  wide,            // useMedia(WIDE)
  testId,          // "gm-layout" | "editor-layout"
  panelLabel,      // 패널 section의 aria-label: t("label.gmPanel") | t("label.editorPanel")
  head, map, panel,
  panelTop?,       // 넓음: 패널 맨 위에 붙음(sticky). GM만 넘김(gm-panel-top)
  narrowOrder?,    // 좁음의 차례. 기본 ["head","map","panelTop","panel"]; GM은 ["head","panelTop","map","panel"]
})  // 넓음·좁음의 바깥 여백과 max-w-[1240px]는 GmLayout과 같다
EditorHeader({ world, info, onLoaded, onBuild, onPlay })
EditorMapPane({ world, selectedId, selectedConnection, busy, disabled, mapUrl, mapName,
                onSelect, onSelectConnection, onMove, onCreateRegion, onCreateConnection, onMapFile })
RegionTab({ worldId, regions, selected, onSelect, open, onOpenChange, onChanged, onDeleted })  // 인스펙터는 자기 useResource의 reload()를 페이지에 등록(ref)
AugmentPanel({ worldId, regions, entities, knowledge, runId, onRunId, drafts, onDrafts, onChanged })
UnscopedPanel({ worldId, regions, picks, onPicks, onChanged })
BuildReportPanel({ report, onShowUnscoped })
```

## 6. API 연결

바뀌는 호출은 없다. 지금 호출을 그대로 쓴다.
- 월드: `exportWorld`, `listWorlds`(열린 세션 수)
- 지역: `createRegion`, `updateRegion`, `getEditorRegion`, `getDeletePlan`, `deleteRegion`
- 연결: `saveConnection`, `deleteConnection`
- 지식: `createKnowledge`, `updateKnowledge`, `deleteKnowledge`, `setScopes`, `listUnscoped`
- NPC: `createNpc`, `updateNpc`, `deleteNpc`, `draftNpcs`
- 보강: `startRun`, `getRun`, `answer`, `revert`, `unignore`
- 사전: `listPriors`, `priorRefs`, `deletePrior`
- 파일·빌드: `getWorldFile`, `importWorldFile`, `uploadBuild`

`startSession`은 플레이어 폼만 부른다. 이름과 시작 지역을 넘기고 → `/play/:id`로 간다(홈과 같음). 이름 없는 `startSession(worldId)`와 `listSessions`·`closeSession`은 에디터에서 사라진다.

## 7. testid 정리

- **지킴**(같은 뜻의 요소에 남김)
  - 탭과 머리: `editor-tab-*`, `graph-status`, `world-name`, `file-save`·`file-load`·`file-input`·`file-confirm`·`file-error`·`file-build`
  - 지도: `map-file-input`, `map-tool-*`, `map-hint`, `map-canvas`
  - 지역 추가·연결: `new-region-*`, `connection-kind`·`connection-weight`·`connection-save`·`connection-exists`·`connection-form`
  - 인스펙터: `region-*`, `connection-*`(목록), `knowledge-*`, `npc-*`, `scope-*`, `delete-*`, `confirm-delete`, `inspector-error`
  - 탭 내용: `unscoped-*`, `augment-*`, `prior-*`, `wiki-*`
  - 빌드: `build-*`
  - 빈 상태와 오류: `empty-hint`, `editor-error`
- **새로**
  - 머리와 배치: `editor-header`, `file-menu`(파일 ▾), `play-this-world`, `open-sessions`, `editor-layout`
  - 지도와 패널: `map-legend`, `region-picker`, `inspector-section-{basic,connections,knowledge,npcs}`, `danger-zone`
  - 보강: `augment-kept`
  - 빌드 리포트: `build-report-carried`, `build-report-stage-{stage}`
- **없앰**: `world-file-bar`, `session-bar`, `session-*`(에디터 쪽: `session-select`·`session-status`·`session-new-btn`·`session-play-btn`·`session-close-btn`), `start-session-band`, `open-sessions-band`
- **[파일 ▾] 안으로 들어가는 것**: `file-save`, `file-load`, `file-build`는 펼친 줄 안에 있다. 시험은 도우미 `openFileMenu()`(`file-menu` 누름)를 먼저 부른다. `file-input`은 줄 밖에 늘 있으므로 바로 만진다(설계 리뷰 01 R-05, R-09).

### 7.1 고치는 기존 시험(의도한 변경)

grep으로 다시 만든 표다(설계 리뷰 01 R-05). 대상은 `MapOverlay`, `SessionBar`, `WorldFileBar`, `RegionInspector`, `MapCanvas`, `file-*`, `graph-status`, `session-*`의 시험 쪽 사용처 전부다.
- `editor.test.tsx`는 `it` 49개와 `it.each` 1개(경우 2)로, 도는 시험이 51개다.

| 파일:줄 | 지금 | 바뀜 |
|---|---|---|
| `gm.test.tsx:13` | `MapOverlay` import(쓰지 않음) | import 줄을 지운다. GM 단언은 바뀌지 않는다 |
| `components.test.tsx:6,78-91` | `MapOverlay` 시험 둘(표식·선 수, 누르면 `onSelect`) | `WorldMap mode="edit"`를 바로 렌더하는 같은 단언으로 옮긴다(`map.worldmap.test`에 같은 뜻이 있으면 지움) |
| `components.test.tsx:11,165-174` | `SessionBar` full의 `session-new-btn` | 지운다(Q2 = A) |
| `components.test.tsx:239-240` | `/editor/aldermoor`의 `graph-status`, `session-close-btn` 없음 | `graph-status`는 지킨다. `session-close-btn` 단언은 `play-this-world`가 있음으로 바꾼다 |
| `components.test.tsx:327,353-356,392` | `file-input`, `map-file-input` | 그대로(둘 다 늘 마운트) |
| `play.test.tsx:11,304-345` | `SessionBar` picker의 플레이 폼·`session-new-btn` | 지운다. 플레이어 폼 시험은 홈(`home.test`)과 새 TP-V8-13에 있다 |
| `editor.test.tsx:13,85-91` | `MapCanvas` 단독 렌더(누름은 저장 없음, 끌기 `onMove` 한 번, 추가·연결 대화상자) | `EditorMapPane` props로 같은 단언 |
| `editor.test.tsx:15,711,727` (S24) | `WorldFileBar` 단독 렌더, `file-input` 값 비움, 교체 → 닫기 → 확인 | `EditorHeader`(+`FileActions`) 렌더. `file-input`은 그대로 만지고, 버튼은 `openFileMenu()` 뒤 |
| `editor.test.tsx:16,694` (S23) | `MapOverlay` 끌기 취소 | `EditorMapPane`(또는 `WorldMap mode="edit"`)으로 같은 단언 |
| `editor.test.tsx:18,145-171,225,632,658` | `RegionInspector` 단독 렌더(번역 글, 사전 참조, 지식 더하기, `reloadKey`로 다시 읽기, 범위 고르기, NPC 제안, 삭제·차단, S31) | 같은 부품을 새 props로 렌더한다. `reloadKey` 단언은 "쓰기 뒤 `reload()`로 다시 읽어 끌기 자리를 지킨다"로 바꾼다. 섹션은 `open` prop으로 펼친 채 렌더 |
| `editor.test.tsx:561-567` | `file-build` 바로 누름 | `openFileMenu()` 뒤 |
| `editor.test.tsx:619-620` (S01) | `start-session-band` → `session-new-btn` | `play-this-world` → 플레이어 폼(TP-V8-13) |
| `editor.test` ConfirmDelete S25 | "Hollow (route)" | "Hollow (길)"(사전 라벨) |
| `editor.test` WikiPanel | "Riverton–Hollow route" | 종류 라벨 |
| `editor.test` #15 | `connection-exists` "0.35", `connection-weight` 값 "0.35" | 숫자 + 뜻 라벨, `CommitRange` 값 |
| `editor.test` 연결 가중 | 숫자 칸이 빈칸·"abc"·"1.5" 뒤 "0.6"으로 돌아옴 | 목록의 `CommitRange`: 끄는 동안(`onDraft`)은 저장 없음, 놓을 때 한 번 저장(설계 리뷰 01 R-12) |
| `editor.test` 끌기 실패 | `editor-error`에 "graph down" | `describeError` 문장. 원문은 접힌 칸에 있음 |
| `editor.test` 보강 오류 | `augment-error` 글이 정확히 "region not found: gone" | 사람 말 문장 + 접힌 원문 |
