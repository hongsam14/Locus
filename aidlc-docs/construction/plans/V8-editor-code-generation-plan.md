# V8 에디터 화면 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**지금 하는 것**: Construction V8(실행 8/9, P1), Code Generation 1부(계획).
- 승인된 V8 기능 설계대로 에디터를 다시 짠다. GM과 같은 틀(지도 + 400px 패널, 탭 넷)을 쓰고, 세션은 [이 월드로 플레이] 하나만 둔다.
- 이 계획이 V8 코드 생성의 유일한 기준이다.

**근거**
- 요구사항 `inception/requirements/follow-up-requirements.md`
  - FR-S4(P1)
  - 이 화면의 FR-S5·S6·FR-L1, FR-D5·D8·D9
  - FR-C12의 카드 쪽
- 유닛 `inception/application-design/follow-up/unit-of-work.md` V8
- 승인된 FD `construction/V8-editor/functional-design/*`
  - BR-V8-01..34, TP-V8-1..18, frontend-components § 1~7
  - FD 리뷰 02의 R-15·R-16·R-17은 Accepted risk다. § 1.1이 다룬다.
- 이어받는 것: V7 code-summary § 8, V6 이월(`SessionBar` 정리, 월드 교체의 `sessions` 경고), V2 이월(`MapOverlay` 어댑터 없애기)

**단계 표기**
- 단계마다 체크박스를 고친다.
- 단계는 웹 게이트(tsc + vitest)가 GREEN인 상태로 끝낸다. 서버는 바뀌지 않으므로 pytest는 처음과 끝에만 돌린다.
- Step 2~4는 새 파일과 호환되는 변경만 한다. 지금 에디터는 그대로 동작한다. 화면 조립, 옛 부품 없애기, 옛 시험 고치기는 Step 5 한 커밋에서 한다(V6와 같은 꼴).
- 단계마다 `feat/follow-up`에 커밋한다. **이 계획의 승인이 이 커밋들의 허락이다.** 푸시·PR은 사람이 한다.

---

## 1. 단위 맥락

| 항목 | 내용 |
|---|---|
| 웹: 새로 | `layout/MapPanelLayout.tsx` |
|  | `features/editor/{EditorHeader,FileActions,PlayThisWorld,EditorMapPane,MapTools,MapLegend,NewRegionDialog,NewConnectionDialog,RegionTab,RegionPicker,DangerZone,useEditorWorld,useAugmentation,augmentNames,dragSaves,buildStages}.ts(x)` |
| 웹: 바뀜 | `routes/EditorPage.tsx`(다시 씀) |
|  | `features/editor/{RegionInspector,RegionForm,ConnectionList,KnowledgeList,NpcEditorList,NpcDraftCards,ConfirmDelete,UnscopedPanel,AugmentPanel,AugmentQuestion,WikiPanel,BuildPanel,BuildReportPanel}.tsx` |
|  | `features/gm/GmLayout.tsx`(얇은 래퍼) |
|  | `format/enums.ts`(`augmentationIssue`), `types.ts`, `i18n/{ko,en}.ts` |
| 웹: 없앰 | `MapOverlay.tsx`, `SessionBar.tsx`, `features/editor/{WorldFileBar,MapCanvas}.tsx` |
| 시험: 고침 | `editor.test.tsx`, `components.test.tsx`, `play.test.tsx`, `gm.test.tsx`(쓰지 않는 import 한 줄), `format.enums.backend.test.ts`, `fr-d8.test.tsx`, `design.grep.test.ts` |
| 시험: 새 파일 | `editor.layout.test.tsx`, `editor.parts.test.tsx`, `editor.data.test.tsx`, `editor.augment.test.ts`(열쇠 읽기·변경 설명, 속성 시험 포함) |
| 바꾸지 않는 것 | 서버 전부, `WorldMap` 그리기 규칙, `NewSessionForm`(홈과 공유, 바꾸지 않음), GM 동작 |

### 1.1 실행 메모 (FD 리뷰 02, 승인 때 Accepted risk)

- 〔R-15〕 **보강 호출의 주인은 페이지가 쥐는 훅이다.**
  - 새 훅 `features/editor/useAugmentation.ts`가 맡는 것
    - 상태: run, busy, error(`DescribedError`), `changed`(변경 기록의 대상 이름), `drafts`(`issue_key` 열쇠)
    - 동작: start, answer, revert, unignore, `lost`(404)
  - `EditorPage`가 그 훅을 쥐고, `AugmentPanel`은 보이기만 한다(props: `aug`, `regions`, `entities`, `knowledge`, `connections`).
  - 답을 보내고 응답을 받은 자리에서 훅이 그 카드의 초안을 지운다. 패널이 내려가도 훅은 살아 있으므로 빠지지 않는다.
  - busy는 훅의 것이다. 요청 중에 탭을 바꿨다 돌아와도 busy가 이어지고, 같은 답이 두 번 나가지 않는다(BR-V8-23, TP-V8-4에 넣음).
  - 월드가 바뀌는 일(FD BLM § 1의 4 표)에 훅의 `reset()`을 부른다.
- 〔R-16〕 **같은 지역의 끌기는 줄을 선다.**
  - 새 파일 `features/editor/dragSaves.ts`에서 지역마다 저장을 하나씩만 보낸다. 앞 저장이 도는 동안 온 끌기는 "다음 자리"로만 남기고, 앞 저장이 끝나면 마지막 자리 하나를 보낸다.
  - 덮개(`moved`)의 칸은 "그 지역에 마지막으로 보낸 자리"와 다시 읽은 월드의 자리가 같아지면 지운다.
  - 저장이 실패하면 그 지역의 대기를 버리고, 덮개 칸을 지우고, 월드를 다시 읽는다.
  - 다른 지역의 끌기는 서로 막지 않는다.
- 〔R-17〕 **기다리는 선택의 근거.**
  - 만들기 성공 직후, 같은 틈에서 월드 `reload()`를 부른다. `useResource`는 앞서 나간 읽기를 버린다(abort와 `seq`). 그래서 만들기 전에 시작한 읽기는 판정에 오지 않는다. `worldGen`은 이 `reload()` 뒤에 도착한 답에서만 늘어난다.
  - 이 의존을 `useEditorWorld`의 주석에 적는다.
  - TP-V8-3에 "앞서 나간 읽기가 만들기 응답 뒤에 도착함 → 판정되지 않고, 다시 읽기의 답으로 선택됨"을 더한다.

### 1.2 코드를 읽고 정한 것 (FD에 없던 사실)

- **빌드 단계는 닫힌 enum이 아니다.** 서버의 `BuildWarning.stage`는 자유 문자열이다. 그런데 `format.enums.backend.test.ts`는 `ENUM_VALUES`의 모든 종류를 서버 enum 클래스와 맞춰 본다.
  - 그래서 빌드 단계 라벨은 `ENUM_VALUES`에 넣지 않는다. 대신 `features/editor/buildStages.ts`(알려진 단계 → 사전 키, 모르면 "기타")에 둔다.
  - `augmentationIssue`만 `ENUM_VALUES`에 넣고, backend 시험에 `enumClass(aug, "IssueType")`를 더한다.
- **에디터는 이미 지연 청크다**(`App.tsx:11`, `lazy`). 그래서 V8 부품은 첫 화면 크기에 들지 않는다. `ui/Tabs`도 에디터 청크에만 든다(GM처럼 `ui/Tabs`에서 바로 가져옴).
- **`gm.test.tsx:13`의 `MapOverlay` import는 쓰이지 않는다.** 어댑터를 지울 때 이 줄만 지운다.
- **칸 라벨**(끊긴 참조의 `field`)은 사전 키 `field.{parent_id,located_in,wiki_prior_ref,derived_from_prior_ids,about_entity_ids}`로 둔다. 모르는 칸은 "칸"이다.

### 1.3 이 계획이 정한 것

- **게이트**: `scratchpad/v8gate.sh`를 새로 만든다(이전 세션 도구는 사라짐).
  - 웹: `cd web && npx tsc --noEmit && npx vitest run`
  - 끝에서만: `npm audit --omit=dev`(0), `vite build`(스크래치 출력)로 첫 화면 JS gzip과 에디터 청크 gzip을 잰다.
- **돌연변이 확인**: 고친 결함마다(UX-25 선택, UX-24 입력 유지, R-15 두 번 보내기, R-16 끌기 대기, 변경 설명 라벨) 되돌린 코드에서 새 시험이 실패하는지 본다. 결과는 code-summary에 적는다.
- **푸시·PR**: 하지 않는다(사람의 일).

### 1.4 실행 메모 (코드 계획 리뷰 01, 승인 2026-10-11 때 Accepted risk)

- 〔R-01〕 Step 5.4 첫머리에서 고칠 시험 표를 grep으로 다시 만든다. 대상은 § 7.1 표에 더해 `AugmentPanel`, `UnscopedPanel`, `NpcDraftCards`, `BuildPanel`, `KnowledgeList`를 렌더하거나 그 문장을 단언하는 시험 전부다. 결과는 code-summary § 4에 싣는다.
  - `AugmentPanel` 시험(`editor.test.tsx` 288-345, 745-824, `components.test.tsx:143-163`)은 시험용 호스트로 렌더한다. 호스트는 `useAugmentation`을 쥐고 `AugmentPanel`에 넘긴다. "run id를 넘기고 돌아오면 다시 읽음"은 "탭을 바꿨다 돌아와도 run이 남음"으로 뜻을 옮긴다.
  - `UnscopedPanel` 시험(257-285, 665-675)은 `reloadKey`를 `reload()`·`picks`로 바꾼다.
  - `NpcDraftCards`(466-480), `BuildPanel`(370-430, 826-900), `KnowledgeList`(679)는 새 문장으로 단언한다.
- 〔R-02〕 `useEditorWorld.onReplaced()`(불러오기·빌드 성공, `replaced`)는 비우기 표에 더해, 등록된 인스펙터 `reload()`와 열려 있는 범위 없는 지식·상식 근거 패널의 `reload()`를 부른다.
  - 빌드 리포트의 [범위 없는 지식 보기]는 탭을 열면서 그 목록의 `reload()`도 부른다.
  - TP-V8-18에 둘을 더하고 Step 5.5에 넣는다: 선택한 지역이 교체 뒤에도 남으면 인스펙터가 새 내용을 읽는다. 범위 없는 지식 탭이 열린 채 빌드가 끝나면 목록을 다시 읽는다.
- 〔R-03〕 Step 5.5에 TP-V8-10의 화면 쪽을 넣는다. BR-V8-17·19·26·28·33이 확인되는 시험은 § 3 표에 적는다.
- 〔R-04〕 `useEditorWorld`의 월드 로더 클로저는 읽기 시작 때의 "만들기 표식"(만들기 성공마다 1씩 느는 수)을 답에 실어 온다: `{world, createMark}`. 기다리는 선택은 `createMark ≥ pending.mark`인 답으로만 판정한다. 다시 읽기의 취소 시점에 기대지 않는다.
- 〔R-05〕 `useAugmentation(worldId, { onChanged })`의 계약
  - 반환: `run, busy, error, lost, changed, drafts, setDraft, priors, start, answer, revert, unignore, reset`
  - 쓰기 넷은 가드 하나를 공유한다(하나가 도는 동안 다른 것은 나가지 않음).
  - 쓰기가 404를 받으면 훅 안에서 `getRun`을 한다. run이 있으면 run을 유지하고 서버 사유를 오류로 보인다(지금 #12). run도 없으면 `lost`이고 "새로 시작" 안내다.
  - 사전 목록(`listPriors`, `ref_kind=prior` 질문용)도 훅이 읽는다.
  - 쓰기가 성공하면 `onChanged()`를 부른다(월드·인스펙터 다시 읽기).
- 〔R-06〕 `MapCanvas`가 내보내던 `sameConnection`, `NewRegion`, `MapTool`, `ConnectionForm` 꼴은 Step 4.2에서 새 파일 `features/editor/connections.ts`로 옮긴다. `MapCanvas`는 Step 5.3까지 그것을 다시 내보낸다. `RegionForm`·`ConnectionList`의 `LEVELS`·`KINDS`는 Step 5.2에서 `ENUM_VALUES`로 바꾼다.
- 〔R-07〕 Step 5.2에서 `min-w-80`을 다섯 곳 모두에서 없앤다: `EditorPage`, `RegionInspector`, `AugmentPanel`, `UnscopedPanel`, `WikiPanel`. 단계 5 끝에 Step 6.2의 소스 검사를 미리 돌린다. `String(e)`는 17곳이다(FD의 "21곳"을 바로잡음).
- 〔R-08〕
  - (a) 게이트 스크립트는 세션 스크래치 디렉터리의 `v8gate.sh`다.
  - (b) 완료 판정: vitest 수 ≥ 기준선 − 지운 수 + 새 수이고, 지운 단언이 모두 새 자리에 있다(code-summary § 4 대응 표).
  - (c) 속성 시험의 생성기는 이름과 id를 `[A-Za-z가-힣 ]` 글자로만 만든다(`_`·`:`가 없음). 단언은 "결과에 입력 열쇠 문자열과 enum 원문 값이 없음"이다.
  - (d) TP-V8-3의 "인스펙터가 열림"은 Step 5.5에서 확인한다.

---

## 2. 단계

### Step 1 — 진행 기록과 기준선
- [x] 1.1 진행 기록을 커밋한다: audit, state, V8 FD 계획(체크), FD 산출물·리뷰 01·02, 이 계획과 그 리뷰(`docs(aidlc): V8 functional design approved; V8 code plan`).
- [x] 1.2 기준선을 재서 code-summary § 1에 적는다(2026-10-11: vitest 664, tsc clean, pytest 1228, audit 0, 첫 화면 117.19 kB, 에디터 청크 10.12 kB): vitest(664), tsc, `pytest -q`(1228), `npm audit --omit=dev`(0), 첫 화면 JS gzip과 에디터 청크 gzip. `v8gate.sh`를 만든다.

### Step 2 — 공유 바탕 (frontend-components § 1·5.1, BR-V8-01·02·15, § 1.2)
- [x] 2.1 `layout/MapPanelLayout.tsx`(새): props는 FD § 5.3(`wide, testId, panelLabel, head, map, panel, panelTop?, narrowOrder?`). `features/gm/GmLayout.tsx`는 이것을 쓰는 얇은 래퍼가 된다. GM의 DOM·testid·패널 이름은 바뀌지 않는다.
- [x] 2.2 `format/enums.ts`: `augmentationIssue: ["gap","low_confidence","wiki_conflict","orphan","dangling","unscoped"]`. `format.enums.backend.test.ts`에 `IssueType`를 더한다.
- [x] 2.3 `types.ts`: `BuildReport.carried_npcs?`·`carried_seeds?`, `AugRun.kept_keys?`, `ChangeSet.kept_key?`.
- [x] 2.4 `i18n/{ko,en}.ts`: 새 키(사전 줄의 말투 규칙 때문에 키 머리를 `enum`·`label`·`tab`·`action`·`notice`·`hint`·`empty`로 둠: `label.stage.*`, `label.field.*`, `tab.unscoped`…)
  - 라벨: `enum.augmentationIssue.*`, `buildStage.*`, `field.*`
  - 머리·탭: `editor.tab.*`(라벨 고침: "상식 근거", "범위 없는 지식 {n}"), `editor.header.*`, `editor.file.*`, `editor.playThisWorld`, `editor.openSessions`
  - 지도·인스펙터: `editor.legend.*`, `editor.section.*`, `editor.danger.*`, `label.editorPanel`, `label.regionPicker`(있으면 재사용)
  - 보강: `augment.status.*`, `augment.kept`, `augment.unnamed`, `augment.cantSave`, `augment.worldChanged`
  - 빌드: `build.report.carried`, `build.report.stage.more`, `build.report.sessionsNotClosed`
  - ko/en 키 일치 시험이 지킨다.
- [x] 2.5 시험: `MapPanelLayout`(넓음·좁음·`narrowOrder`·패널 이름; GM 시험 전부 그대로), enums backend, 사전 일치.
- [x] 2.6 게이트 GREEN → 커밋 `feat(web): a shared map + panel layout, augmentation issue labels, build stage and field labels (V8)`

### Step 3 — 에디터 읽기·쓰기 훅과 순수 함수 (BLM § 1~6, § 1.1, TP-V8-3·4·10·12·18)
이 단계는 새 파일만 더한다. 지금 `EditorPage`는 그대로 동작한다.
- [x] 3.1 `features/editor/useEditorWorld.ts`(새)
  - 월드(`useResource`)와 열린 세션 수
  - `worldGen`, `pendingSelect {id, gen}`과 다섯 풀림 경우(BLM § 3), `selected`, `connection`
  - 끌기 덮개 `moved`와 `dragSaves` 연결(§ 1.1 R-16)
  - 월드가 바뀌는 일의 비우기 표(BLM § 1의 4)와 `onReplaced()`
  - `reload()`, `retry()`
- [x] 3.2 `features/editor/dragSaves.ts`(새): 지역별 하나씩, 마지막 자리 하나만, 실패 처리(§ 1.1 R-16).
- [x] 3.3 `features/editor/useAugmentation.ts`(새): § 1.1 R-15. run, busy, error, changed, drafts(`issue_key`), start/answer/revert/unignore, 404 → lost와 "새로 시작" 안내, `reset()`.
- [x] 3.4 `features/editor/augmentNames.ts`(새, 순수)
  - `issueKeyName(key, world)`: 앞 둘·뒤 둘을 떼고 가운데를 ids로 본다. 종류별로 이름을 찾는다(연결은 "작은 id|큰 id|종류"를 월드 연결에서). 못 찾으면 "이름 없는 항목"이다.
  - `changeLabel(description)`: `type:action`을 라벨로, 모르면 "변경"이다.
  - `fieldLabel(field)`
- [x] 3.5 `features/editor/buildStages.ts`(새, 순수): 단계 → 사전 키, 묶음과 수, `sessions` 단계의 수.
- [x] 3.6 시험
  - `editor.data.test.tsx`
    - TP-V8-3: 늦은 다시 읽기, 실패, 그 사이 다른 선택, 앞서 나간 읽기가 늦게 옴
    - TP-V8-12의 끌기: 같은 지역 겹침은 마지막 자리 하나, 실패하면 덮개 비우고 다시 읽기, 다른 지역은 막지 않음
    - TP-V8-18: 빌드 교체 뒤 비움
    - R-15: 탭이 내려간 사이 끝난 답의 초안 정리, 요청 중 두 번째 답 없음
  - `editor.augment.test.ts`
    - 열쇠 읽기(지역·지식·엔티티·연결, `|`나 `:`가 든 id, 못 찾음)
    - 변경 설명
    - 속성 시험: 어떤 열쇠·설명이 와도 결과에 열쇠 원문이나 `_`가 든 원문 값이 없음
  - 빌드 단계 묶음
- [x] 3.7 게이트 GREEN → 커밋 `feat(web): editor data hooks — a new region is selected after the re-read, drags of one region wait their turn, augmentation calls live on the page (V8, UX-25, UX-24)`

### Step 4 — 새 에디터 부품 (frontend-components § 4, BR-V8-03·08·09·12·13·14·27·28·31~34)
이 단계도 새 파일만 더한다(지금 부품은 그대로).
- [ ] 4.1 `EditorHeader`, `FileActions`
  - [파일 ▾] 펼침: 숨은 input은 줄 밖, Esc·바깥 누름·동작 시작에 닫힘, 초점 복귀, 오류는 머리 아래
  - 교체·닫기 확인(옛 `WorldFileBar` 흐름을 옮김)
  - `PlayThisWorld`(`NewSessionForm` 재사용)
- [ ] 4.2 `EditorMapPane`, `MapTools`(toolbar, 화살표 키, `aria-pressed`), `MapLegend`
  - `NewRegionDialog`(단계 라벨, 상위 묶음 `Select group`, `Textarea`)
  - `NewConnectionDialog`(`CommitRange`, 처음 값·종류 바꿈 규칙, "연결 고치기")
  - `WorldMap mode="edit"`를 바로 쓴다.
- [ ] 4.3 `RegionTab`, `RegionPicker`(단계 묶음 `Select`), `DangerZone`
- [ ] 4.4 시험 `editor.parts.test.tsx`: TP-V8-2(머리·파일 펼침), TP-V8-5, TP-V8-7(폼 쪽), TP-V8-13(플레이 시작), TP-V8-15(도구 띠 키보드), 지도 범례 라벨.
- [ ] 4.5 게이트 GREEN → 커밋 `feat(web): new editor parts — one head with a file menu and a play start, a map pane with tools and a legend, a keyboard region picker and a danger zone (V8, FR-S4)`

### Step 5 — 바꿔 끼우기: 화면 조립, 기존 부품, 옛 부품 없애기 (BLM 전부, BR-V8-01~34, frontend-components § 7.1)
- [ ] 5.1 `routes/EditorPage.tsx`를 다시 쓴다.
  - `MapPanelLayout` + `EditorHeader` + `EditorMapPane` + `ui/Tabs`(넷)
  - `useEditorWorld`, `useAugmentation`, `inspectorOpen`, `unscopedPick`
  - 지도 누름 → [지역] 탭(좁음에서 `scrollIntoView?.()`)
- [ ] 5.2 기존 부품
  - `RegionInspector`: 섹션 넷, 머리 수, `reload()` 등록, `describeError`
  - `RegionForm`: 위험 칸 분리, `Textarea`
  - `ConnectionList`: `CommitRange`, 놓을 때 저장, 이름 있는 ✕, 종류 라벨
  - `KnowledgeList`·`NpcEditorList`·`NpcDraftCards`: 이름 있는 ✕, NPC 자기 사전 키, `Textarea`, `describeError`
  - `ConfirmDelete`: 종류 라벨
  - `UnscopedPanel`: picks를 props로, `min-w-80` 없앰, 이름 있는 ✕
  - `AugmentPanel`·`AugmentQuestion`: 보이기만, 라벨·이름, "/30" 없앰, 이대로 둔 질문, 칸 라벨
  - `WikiPanel`: 영역·종류 라벨, 수치 + 뜻
  - `BuildPanel`·`BuildReportPanel`: 이어 붙인 수, 단계 묶음과 펼침, `sessions` 줄, [범위 없는 지식 보기] → 탭
  - 모든 `String(e)`를 `describeError`·`InlineError`로 바꾼다. 첫 읽기 로딩, 빈 상태 문장, 알림도 맞춘다.
- [ ] 5.3 없앤다: `MapOverlay.tsx`, `SessionBar.tsx`, `WorldFileBar.tsx`, `MapCanvas.tsx`. `gm.test.tsx:13` import 한 줄도 지운다.
- [ ] 5.4 옛 시험을 고친다(frontend-components § 7.1 표 그대로).
  - `editor.test.tsx`, `components.test.tsx`, `play.test.tsx`
  - 시험 도우미 `openFileMenu()`
- [ ] 5.5 새 시험 `editor.layout.test.tsx`: TP-V8-1, TP-V8-4(입력 유지), TP-V8-6(섹션), TP-V8-8(이름 있는 단추), TP-V8-11(상태), TP-V8-12(쓰기), TP-V8-14(빌드 리포트), TP-V8-15(탭 키보드)
- [ ] 5.6 돌연변이 확인: UX-25, UX-24, R-15, R-16, 변경 설명 라벨, 위험 칸 분리
- [ ] 5.7 게이트 GREEN → 커밋 `feat(web): editor rebuilt — map beside a 400 px panel of four tabs, a folding inspector with a separate danger zone, one weight control, words for every value and error, play from the editor (V8, FR-S4, UX-17..25, UX-27)`

### Step 6 — FR-D8 검사와 소스 검사 (BR-V8-15·16·22·05·27, TP-V8-9·16)
- [ ] 6.1 `fr-d8.test.tsx`: 에디터를 넣는다. 대상은 머리, 범례, 대화상자, 인스펙터, 보강, 사전, 빌드 리포트이고, 단계·종류·보강 값을 전부 돌린다. 원문 enum, `type:action`, 열쇠 글자가 없어야 한다.
- [ ] 6.2 `design.grep.test.ts`: 범위에 `features/editor/**`와 `routes/EditorPage.tsx`를 더한다.
  - 지금 규칙(`toFixed`, `String(e)`, `outline-none`)을 그대로 건다.
  - 새 규칙: `min-w-80`, 고정 px 폭(`min(\d+px`), `MapOverlay`·`SessionBar` import
- [ ] 6.3 게이트 GREEN → 커밋 `test(web): the editor shows no raw enum, bare number, error text or fixed width (V8, FR-D8)`

### Step 7 — 캡처 (사람 확인, BR-V8-04, 캡처 계획)
- [ ] 7.1 캡처 도구를 새로 만든다(`scratchpad/v8/cap/`)
  - 가짜 API 서버: 데모 한국어판 월드, 열린 세션 1개, 보강 run(질문 셋, 무시 하나, 이대로 둔 것 하나), 빌드 리포트(이어 붙임·경고 포함)
  - `vite build`(스크래치 출력)
  - `/usr/bin/google-chrome` headless + CDP 찍기 스크립트
  - 저장소에는 넣지 않는다.
- [ ] 7.2 FD 캡처 계획의 장면을 1280·390으로 찍는다. 장마다 `scrollWidth ≤ innerWidth`, 넓음에서 패널이 붙어 있는지, 머리 높이를 잰다.
- [ ] 7.3 비공개 Artifact 한 장에 올린다. 잰 값, 바뀐 것, 봐 주실 것을 함께 싣는다.
- [ ] 7.4 가로 스크롤이나 배치 결함이 보이면 그 자리에서 고치고 다시 찍는다. 커밋은 `fix(web): … (V8 captures)`다.

### Step 8 — 마무리
- [ ] 8.1 전체 게이트
  - tsc, vitest: Step 1.2 기준선 이상. 지운 시험(`SessionBar`·`MapOverlay` 묶음)과 새 시험 수를 code-summary § 4에 적는다.
  - `pytest -q`(1228, 바뀌지 않음), `npm audit --omit=dev`(0)
  - JS gzip: 첫 화면이 Step 1.2보다 늘지 않는다. 에디터는 지연 청크다.
- [ ] 8.2 `construction/V8-editor/code/code-summary.md`
  - § 1 기준선과 결과
  - § 2 파일
  - § 3 BR → 시험 표
  - § 4 고친 기존 시험과 지운 시험
  - § 5 이탈(§ 1.2의 빌드 단계, R-15의 소유)
  - § 6 알려진 제약(접힌 폼의 글, 지도 키보드, UX-18 남은 부분)
  - § 7 돌연변이 결과
  - § 8 넘기는 것(V9)
- [ ] 8.3 audit, state 갱신 → 커밋 `docs(aidlc): V8 code summary`

---

## 3. 요구 대응

| 요구·완료 조건 | 단계 | 규칙·시험 |
|---|---|---|
| 지도 위 띠 하나(UX-17) | 4.1, 5.1 | BR-V8-03, TP-V8-2 |
| 인스펙터 섹션 접힘, 위험 버튼 분리(UX-19) | 4.3, 5.2 | BR-V8-11·12, TP-V8-6 |
| 가중 컨트롤 하나(UX-20) | 4.2, 5.2 | BR-V8-13, TP-V8-7 |
| 아이콘 단추 이름(UX-21) | 5.2 | BR-V8-14, TP-V8-8 |
| 범위 없는 지식 링크(UX-22) | 3.5, 5.2 | BR-V8-29, TP-V8-14 |
| 보강 상태 사람 말(UX-23) | 3.4, 5.2 | BR-V8-17·18, TP-V8-10 |
| 탭 라벨, 지도를 눌러도 입력 유지(UX-24) | 2.4, 3.3, 5.1 | BR-V8-07·19, TP-V8-4 |
| 추가한 지역 선택(UX-25) | 3.1 | BR-V8-06, TP-V8-3 |
| 세션 라벨(UX-27) | 4.1, 5.3 | BR-V8-27·28, TP-V8-13 |
| 390px 가로 스크롤 없음(FR-D5) | 5, 6.2, 7 | BR-V8-04, TP-V8-16, 캡처 |
| 상태·오류(FR-S5, FR-D9) | 5.2 | BR-V8-21~26, TP-V8-11·12 |
| 접근성(FR-S6) | 4, 5 | BR-V8-31~34, TP-V8-15 |
| 원문 enum 없음(FR-D8) | 2, 6.1 | BR-V8-15·16, TP-V8-9 |
| V7·V6 이월 | 2.3, 3.5, 5.2 | BR-V8-30, TP-V8-14 |
| 캡처 Artifact | 7 | 캡처 계획 |
