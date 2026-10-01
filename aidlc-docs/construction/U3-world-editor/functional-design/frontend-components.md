# U3 월드 에디터 — Frontend Components

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U3 기능 설계 중 화면입니다. 다음을 정합니다.
- `/` 월드 목록
- `web/src/features/editor/`의 지도 편집(도구 모드, Q5=A)
- 지역 인스펙터(지식·스코프·NPC·연결)와 스코프 없음 목록
- 빌드·World File·보강 Q&A·wiki 패널

## 1. 컴포넌트 트리
```
/                     routes/HomePage.tsx (새)            월드 목록 + [편집] [세션 시작], 빈 목록이면 [데모] [자료로 만들기]
/editor/:worldId      routes/EditorPage.tsx (다시 씀)
  ├─ WorldFileBar     features/editor/WorldFileBar.tsx    이름 · [저장(내려받기)] [불러오기] [자료로 만들기] · "열린 세션 N개" 띠
  ├─ MapCanvas        features/editor/MapCanvas.tsx       도구 [선택·이동] [지역 추가] [연결 긋기] + MapOverlay
  ├─ 오른쪽 탭        [지역] [스코프 없음] [보강] [wiki]
  │   ├─ RegionInspector   features/editor/RegionInspector.tsx   지역 폼 · 연결 목록 · 지식 목록(+스코프) · NPC 목록(+초안)
  │   ├─ UnscopedPanel     features/editor/UnscopedPanel.tsx     스코프 없는 지식 + 지역 지정
  │   ├─ AugmentPanel      features/editor/AugmentPanel.tsx      run 유지 · 대상 표시 · 고정 선택지 · 바뀐 것 · 되돌리기
  │   └─ WikiPanel         features/editor/WikiPanel.tsx         prior 목록 · 참조 · 끊긴 근거
  ├─ BuildPanel (Modal)    features/editor/BuildPanel.tsx        업로드 폼 → BuildReportPanel
  └─ ConfirmDelete (Modal) features/editor/ConfirmDelete.tsx     삭제 계획/확인
옛 파일: Toolbar.tsx, RegionPanel.tsx(에디터 쪽), AugmentPanel.tsx(루트) → features/editor로 옮기거나 지운다
```
- `RegionPanel`은 GM 화면에서도 쓴다(세션 지식 보기). ✕는 없앤다(BR-U3-33). 이름은 `features/gm/RegionKnowledgePanel.tsx`로 옮긴다.

## 2. 컴포넌트별 정의

### 2.1 `HomePage` (BR-U3-34)
- `api.listWorlds()`로 줄마다 이름·지역 수·마지막 수정(상대 시각)·열린 세션 수를 보인다.
- [편집]은 `/editor/:id`로 간다.
- [세션 시작]은 누를 때 `api.exportWorld(w)`로 지역을 읽어 `NewSessionForm`(U4, `regions` prop)에 넘긴다. 시작은 `api.startSession(w, {name, start_region_id})`(U4의 `POST /api/play/worlds/{w}/sessions`, 본문 있으면 201 `SessionStartOut`)이고, 그 뒤 `/play/:sid`로 간다(검토 01 R-10).
- 빈 목록이면 [데모 불러오기](`api.loadDemo("aldermoor", ...)` → `/editor/aldermoor`)와 [자료로 만들기](새 world id 입력 → BuildPanel)를 보인다.
- `App.tsx`에서 `/`와 `*`의 넘김을 없앤다. `*`는 `/`로 간다.

### 2.2 `MapCanvas` (Q5=A, BR-U3-30)
- 도구 버튼(`map-tool-select`, `map-tool-add-region`, `map-tool-connect`)과 현재 도구 표시
- **선택·이동**
  - 지역을 누르면 선택한다.
  - 4px 넘게 끌었을 때만 `onMove` → `PUT region`(position)이다. 누르기만 하면 저장하지 않는다.
- **지역 추가**
  - 빈 곳을 누르면 그 정규화 좌표로 "새 지역" 폼(이름·레벨·부모·설명)이 모달로 뜬다.
  - 저장하면 `POST regions`다.
- **연결 긋기**
  - 지역 A를 누르고 B를 누르면 연결 폼(종류 adjacent/route/river/blocked, 가중치 0~1)이 뜬다.
  - 저장하면 `PUT connections`다. 같은 지역을 두 번 누르면 취소다.
- 선은 지금처럼 종류·가중치로 모양이 정해진다(`edgeStyle`).
- 선을 누르면 연결을 선택하고, 인스펙터가 연결 상세(근거·prior, 편집·삭제)를 보인다.
- 연결의 종류를 바꾸면 `saveConnection({..., previous_kind})` 한 번이다. 서버가 가중치·근거·prior를 옮긴다(BR-U3-11).
- `MapOverlay`에 선택 콜백 `onSelectConnection`과 빈 곳 콜백 `onBackground`를 더한다. 끌기 판정은 거리 임계로 한다(4px).

### 2.3 `RegionInspector` (US-2.2·2.3·2.4·2.5)
- `GET regions/{r}/editor`로 연다. 표시 언어가 바뀌면 다시 읽는다.
- **지역 폼**
  - 이름·레벨·부모(같은 월드 지역 선택, 자기·자손 제외)·설명
  - [저장]은 `PUT region`이다.
  - [삭제]는 `GET delete-plan` → `ConfirmDelete`(계획 표시, `blocked_by_sessions`가 있으면 확인 버튼 꺼짐) → `DELETE region`이다.
- **연결 목록**: 상대 지역·종류·가중치·근거(prior 또는 "저장되지 않은 근거")와 [편집]·[삭제]
- **지식 목록**
  - 제목·진술(번역 + 원문 토글)·붙은 지역 칩
  - [편집]은 제목·진술 → `PUT knowledge`다.
  - [스코프]는 지역 다중 선택 → `PUT scopes`다.
  - [삭제]는 확인을 거쳐 `DELETE knowledge`다.
  - [지식 추가]는 제목·진술 → `POST regions/{r}/knowledge`다.
- **NPC 목록**
  - 이름·역할·설명(원문, 번역 없음 — BR-U3-37)과 [편집]·[삭제](확인)
  - [NPC 추가]는 이름·역할·설명·traits 폼이다.
  - [NPC 제안]은 `POST npc-drafts`다.
    - 초안 카드 0~3장마다 [받아들이기]를 둔다. 누르면 `POST npcs`이고, 그 카드는 사라진다.
    - `failed`면 "제안을 받지 못했어요" 안내를 보인다.

### 2.4 `UnscopedPanel` (BR-U3-14)
- `GET knowledge/unscoped` 목록을 보인다. 줄마다 지역 선택 + [지정](`PUT scopes`)과 [삭제]를 둔다.
- 탭 이름에 개수 배지를 단다.

### 2.5 `AugmentPanel` (BR-U3-24~28)
- [빈틈 찾기]는 `POST runs`다. 화면은 그 run을 보관한다.
- **질문 카드**
  - 대상(종류 배지·이름·지역 이름·끊긴 속성)과 질문 문장을 보인다.
  - 선택지는 서버가 준 `actions`만 버튼으로 보인다(문구는 i18n `augment.action.*`).
  - edit·add는 필요한 입력을 받는다: 진술·제목·신뢰도, 지역 선택(orphan·unscoped·dangling-지역), 대상 id 선택(dangling-prior).
- 답하면 `POST answer` → `AnswerResult`다. 같은 run의 다음 질문으로 바꾸고, "바뀐 것" 목록에 `changed`와 [되돌리기]를 쌓는다.
- [되돌리기]는 `POST revert`다. 아직 되돌리지 않은 **가장 나중** 변경에만 버튼이 켜진다(BR-U3-27). 이미 되돌린 것은 "되돌림"으로 보인다. 409면 안내한다.
- run을 다시 읽다가 404(서버 재시작)면 "보강 기록이 사라졌어요" 안내와 [새로 찾기]를 보인다(BR-U3-42).
- run이 converged·stopped이면 그렇다고 보이고 [다시 찾기]를 둔다.

### 2.6 `WikiPanel` (BR-U3-31)
- `GET priors` + `GET prior-refs`
  - 표: 조건 → 효과, 도메인 칩, 신뢰도, 참조 수(펼치면 연결 "A–B route"·지식 제목)
- "저장되지 않은 근거" 절: 끊긴 참조의 목록과 그 연결·지식
- prior 삭제는 확인을 거친다(P2 편집은 범위 밖).

### 2.7 `BuildPanel` + `BuildReportPanel` (BR-U3-35)
- **폼**
  - world id(새 월드면 입력, 지금 월드면 고정)·이름·설명
  - 메모 여럿(텍스트 영역 + 파일 .txt/.md)
  - 구조화 지도 JSON 파일 여럿, 지도 이미지 여럿(png/jpg), 컨셉 아트 여럿
- **[빌드]**
  - 월드가 있으면 "교체" 확인을 받는다(`replace=true`).
  - 409(열린 세션)면 "세션 N개를 닫고 진행" 확인 뒤 `confirm=true`로 다시 보낸다.
- 빌드 중에는 진행 표시를 보이고 폼을 잠근다. 빌드는 LLM이라 수십 초다.
- **리포트**
  - 수(지역·연결·엔티티·지식·보강·prior)
  - 경고(severity별 색, 단계·항목)
  - 스코프 없음 수(누르면 UnscopedPanel)
  - LLM·임베딩 호출 수, 교체 여부·닫힌 세션·백업 경로
  - `ok`가 거짓이면 빨간 머리말을 보인다.

### 2.8 `WorldFileBar` (BR-U3-36)
- [저장]은 `GET file`을 받아 `<world>.world.json`으로 내려받는다.
- [불러오기]는 파일을 고른다 → 같은 id 월드가 있으면 교체 확인 → 409(열린 세션)면 닫기 확인 → `confirm=true`다. 422(버전)는 서버 문구를 보인다.
- "열린 세션 N개" 띠(BR-U3-15)를 보인다. 누르면 세션 목록 → GM 화면이다.

### 2.9 GM 화면의 지식 패널 (BR-U3-33)
- 옛 `RegionPanel`의 ✕와 `deleteNode` 호출을 없앤다. 세션 지식 보기만 남긴다.

## 3. API·타입 (`web/src/api/world.ts`, `types.ts`)
- **더할 것**
  - `getEditorRegion`, `createRegion`, `updateRegion`, `getDeletePlan`, `deleteRegion`
  - `saveConnection`, `deleteConnection`
  - `createKnowledge`, `updateKnowledge`, `setScopes`, `deleteKnowledge`, `listUnscoped`
  - `createNpc`, `updateNpc`, `deleteNpc`, `draftNpcs`
  - `listPriors`, `priorRefs`, `deletePrior`
  - `getRun`, `answer`(→ `AnswerResult`), `revert`
  - `buildUpload`(concept arts 포함)
- **없앨 것**: `deleteNode`
- **타입**
  - 새로: `EditorRegionView`, `ConnectionKey`, `RegionDeletePlan/Report`, `NpcDraftResult`, `QuestionTarget`, `AnswerResult`, `PriorUsage`, `PriorRefView`
  - 고침: `WorldExport.npcs`, `BuildReport.backup_path`·`priors_created`

## 4. i18n (ko·en 같은 키 집합)
| 묶음 | 키 |
|---|---|
| 홈 | `home.title`, `home.empty`, `home.edit`, `home.startSession`, `home.loadDemo`, `home.buildFromSources`, `home.regions`, `home.updated`, `home.openSessions` |
| 지도 도구 | `map.tool.select`, `map.tool.addRegion`, `map.tool.connect`, `map.hint.*` |
| 인스펙터 | `editor.region.*`, `editor.connection.*`, `editor.knowledge.*`, `editor.scopes`, `editor.npc.*`, `editor.npcDraft.*`, `editor.unscoped.*` |
| 삭제 | `delete.region.title`, `delete.region.children`, `delete.region.connections`, `delete.region.npcs`, `delete.region.unscope`, `delete.region.scopeRemoved`, `delete.region.entities`, `delete.region.blocked` |
| 보강 | `augment.find`, `augment.target.*`, `augment.action.{confirm,edit,remove,add,ignore}`, `augment.changed`, `augment.revert`, `augment.reverted`, `augment.converged`, `augment.stopped` |
| wiki | `wiki.title`, `wiki.condition`, `wiki.effect`, `wiki.domains`, `wiki.refs`, `wiki.broken` |
| 빌드 | `build.*`, `build.report.*` |
| World File | `file.save`, `file.load`, `file.replaceConfirm`, `file.closeSessionsConfirm`, `file.openSessions` |

## 5. 상태 흐름 (지역 하나 지우기)
```
RegionInspector [삭제] → GET delete-plan → ConfirmDelete(수와 이름, blocked면 확인 꺼짐)
  → 확인 → DELETE region → RegionDeleteReport → 토스트("자식 1 옮김 · NPC 2 · 연결 2 · 스코프 없음 1")
  → EditorPage: 월드 다시 읽기(export) · 선택 해제 · 스코프 없음 배지 갱신
409(세션) → ConfirmDelete에 세션 목록과 "GM 화면에서 세션을 닫거나 플레이어를 옮기세요"
```

## 6. 테스트 (vitest)
| 테스트 | 확인 |
|---|---|
| HomePage | 줄의 수·이름·열린 세션, [편집] → `/editor/w`, [세션 시작] → `exportWorld` → 폼 → `startSession(w, body)` → `/play/sid`, 빈 목록 → 데모·만들기 버튼 |
| MapCanvas 도구 | 선택 모드 클릭 → `updateRegion` 0회, 10px 끌기 → 1회(EX-11). 지역 추가 모드 빈 곳 → 폼. 연결 모드 A·B → 연결 폼 → `saveConnection` |
| RegionInspector | 지식 추가 → `createKnowledge(region)`. 스코프 지정 → `setScopes`. NPC 제안 → 카드 3장, 하나 받아들이기 → `createNpc` 1회. `failed` → 안내 |
| ConfirmDelete | 계획의 수를 보인다. `blocked_by_sessions`면 확인 꺼짐. 확인 → `deleteRegion` |
| UnscopedPanel | 지정 → `setScopes`, 목록에서 빠짐 |
| AugmentPanel | 대상 이름 보임. 서버 `actions`만 버튼. 답 → 같은 run 유지(`startRun` 1회). 되돌리기는 가장 나중 변경에만 켜짐 → `revert(run, change)`. 되돌린 뒤 꺼짐. run 404 → 새로 찾기 안내 |
| WikiPanel | prior 줄, 참조 펼침, 끊긴 근거 절 |
| BuildPanel | 파일들이 FormData로, 409 → 확인 → `confirm=true` 재요청, 리포트 표시 |
| WorldFileBar | 저장 → 내려받기 링크. 불러오기 409 → 확인 → 재요청 |
| GM 지식 패널 | ✕ 없음 |
