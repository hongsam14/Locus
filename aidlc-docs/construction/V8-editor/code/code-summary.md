# V8 에디터 화면 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V8 코드 생성을 마쳤다(Step 1~8). 월드 에디터를 GM과 같은 틀로 다시 짰다.
- 넓은 화면은 지도 옆에 400px 패널과 탭 넷, 폰 폭은 한 열이다.
- 인스펙터는 접히는 섹션 넷이고, 지역 지우기는 위험 칸에 따로 있다.
- 연결 가중은 슬라이더 하나로 다룬다.
- 값과 오류는 모두 사람 말로 보인다.
- 에디터에서 바로 플레이를 시작한다.
- 지도로 지역을 만들면 그 지역이 골라진다. 탭을 오가도 쳐 둔 답이 남는다.

이 문서는 바뀐 것, 확인, 이탈, 알려진 한계, 다음에 넘기는 것을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V8-editor-code-generation-plan.md`(8단계, 승인 2026-10-11; 실행 메모 § 1.1~1.4 포함). 캡처: https://claude.ai/artifact/RGWSFsM26cNiZHeoUttVuN (비공개).

## 1. 기준선과 결과

| 항목 | 기준선 (Step 1.2, `835d1d6`) | 결과 (Step 8) |
|---|---|---|
| vitest | 664 | **741** (지운 시험 4, 새 시험 81) |
| tsc | clean | clean |
| npm audit `--omit=dev` | 0 | 0 |
| pytest | 1228 | 1228 (서버 코드 바뀜 없음: `git diff 835d1d6 -- locus api tests` 비어 있음) |
| ruff · black · mypy | clean · clean · 11 | 같음 |
| 첫 화면 JS gzip (`index`) | 117.19 kB | **119.21 kB** (+2.02, § 5 이탈 1) |
| 에디터 묶음 gzip | 10.12 kB | 13.59 kB (지연) |
| GM 묶음 gzip | 17.05 kB | 11.93 kB + 함께 쓰는 묶음 5.57 kB(`Tabs`·`MapPanelLayout`, 에디터와 공유) |

캡처 17장(장면 12 × 설계의 폭) 모두 `scrollWidth ≤ innerWidth`다. 머리 높이는 1280에서 64px, 390에서 112px이다. [파일 ▾]를 펼치면 108px·164px이다.

게이트 스크립트는 세션 scratchpad의 `v8gate.sh`(tsc + vitest)와 `v7gate.sh`(백엔드)다.

커밋(7개 + 이 요약):

| 단계 | 커밋 | 내용 |
|---|---|---|
| 2 | `07e2a34` | 공유 지도+패널 틀, 보강 문제 종류 라벨, 빌드 단계·칸 라벨 |
| 3 | `abe74ae` | 에디터 읽기·쓰기 훅: 만든 지역은 다시 읽은 뒤 고름, 같은 지역 끌기는 줄을 섬, 보강 호출은 페이지에 |
| 4 | `62d4109` | 새 부품: 머리와 [파일 ▾], 플레이 시작, 지도 칸(도구·범례), 지역 고르기, 위험 칸 |
| 5 | `c0abf6b` | 바꿔 끼우기: 화면 조립, 기존 부품, 옛 부품 넷 없앰, 옛 시험 고침, 새 화면 시험 |
| 6 | `caed0f3` | FR-D8·소스 검사를 에디터까지 |
| 7 | `0b76594` | 캡처에서 찾음: 펼친 파일 줄 자리, "상위 지역", 통하는 정도 한 이름 |
| 7 | `23a63de` | 캡처에서 찾음: 지도+패널 틀을 첫 화면 묶음에서 뺌 |

## 2. 바꾼 파일과 만든 파일

`web/src/` 아래만 바뀌었다.

- 만듦
  - `layout/MapPanelLayout.tsx`: GM과 에디터가 함께 쓰는 넓음·좁음 틀. `features/gm/GmLayout.tsx`는 이것을 쓰는 얇은 래퍼가 됐다.
  - `features/editor/useEditorWorld.ts`: 월드·열린 세션 수 읽기, 선택, 만든 지역 기다리기(만들기 표식, R-04), 끌기 덮개, 패널 다시 읽기 등록, 교체 뒤 비우기(R-02).
  - `features/editor/dragSaves.ts`: 지역마다 저장 하나씩, 기다리는 마지막 자리만 보냄(R-16).
  - `features/editor/useAugmentation.ts`: 보강 run·초안(`issue_key`)·쓰기 넷의 가드 하나, 404 가르기, 400 문장(R-05, R-15).
  - `features/editor/augmentNames.ts`(칸·변경·열쇠 이름), `buildStages.ts`(단계 라벨·묶음·세션 줄, `BUILD_STAGES`), `connections.ts`(도구·새 지역 꼴, 같은 연결 찾기, 단계·종류·지역 선택지).
  - `features/editor/EditorHeader.tsx`(+`PlayThisWorld`), `FileActions.tsx`, `EditorMapPane.tsx`, `MapTools.tsx`, `MapLegend.tsx`, `NewRegionDialog.tsx`, `NewConnectionDialog.tsx`, `RegionTab.tsx`(+`RegionPicker`, `DangerZone`).
  - `test/editor.tsx`: 시험 도우미 `openFileMenu`, `AugHost`, `ALL_OPEN`.
- 바꿈
  - `routes/EditorPage.tsx`: 다시 씀.
  - `features/editor/RegionInspector.tsx`: 섹션 넷, 머리의 수, `reload()` 등록, 위험 칸, 저장 뒤 1초 "저장했어요".
  - `features/editor/RegionForm.tsx`(지우기 단추 뺌, `Textarea`), `ConnectionList.tsx`(`CommitRange`, 이름 있는 ✕, 상대 이름 누르면 그 지역), `KnowledgeList.tsx`, `NpcEditorList.tsx`, `NpcDraftCards.tsx`, `ConfirmDelete.tsx`, `UnscopedPanel.tsx`(고른 지역은 페이지가 쥠), `WikiPanel.tsx`, `AugmentPanel.tsx`(보이기만), `AugmentQuestion.tsx`, `BuildPanel.tsx`, `BuildReportPanel.tsx`.
  - `format/enums.ts`(`augmentationIssue`), `types.ts`(V7 칸 넷), `i18n/{ko,en}.ts`(V8 낱말, 쓰지 않는 키 15개 뺌), `layout/index.ts`.
- 지움: `MapOverlay.tsx`, `SessionBar.tsx`, `features/editor/WorldFileBar.tsx`, `features/editor/MapCanvas.tsx`.

## 3. 요구·규칙·시험 대응

| 요구 | 규칙 | 시험 |
|---|---|---|
| 배치(FR-S4, Q1 = A) | BR-V8-01·02 | `layout.test` MapPanelLayout 셋, `editor.layout` TP-V8-1 둘, GM 시험 그대로(TP-V8-17) |
| 지도 위 띠 하나(UX-17) | BR-V8-03 | `editor.parts` TP-V8-2(머리, id 한 번, [파일 ▾]), 머리 줄 시험(펼친 줄 자리) |
| 390 가로 스크롤 없음(FR-D5) | BR-V8-04 | 캡처 17/17, `design.grep` 고정 폭·`min-w-80` 규칙 |
| `WorldMap` 바로 씀 | BR-V8-05 | `design.grep`(옛 지도 덮개·세션 띠 import와 파일 0) |
| 추가한 지역 선택(UX-25) | BR-V8-06 | `editor.data` TP-V8-3(늦은 읽기·실패·그 사이 선택·앞서 나간 읽기), `editor.layout` TP-V8-3(인스펙터가 열림) |
| 탭 상태 유지(UX-24) | BR-V8-07 | `editor.layout` TP-V8-4 셋, `editor.augment`(초안 정리, 두 번 보내기 없음) |
| 키보드로 지역 고르기 | BR-V8-08 | `editor.parts` TP-V8-5, `editor.layout` TP-V8-6 |
| 범례(UX-18) | BR-V8-09 | `editor.parts` 범례 라벨 |
| 끌기 저장 | BR-V8-10 | `editor.data`(저장 중 두 번째 끌기, 실패 뒤 덮개·다시 읽기), `editor.test` C1 둘, `editor.layout` 끌기 저장 뒤 인스펙터만 |
| 섹션·위험 칸(UX-19) | BR-V8-11·12 | `editor.layout` TP-V8-6 |
| 가중 하나(UX-20) | BR-V8-13 | `editor.test`(목록: 끄는 동안 0, 놓으면 1), `editor.parts` TP-V8-7(폼), #15 둘 |
| 이름 있는 단추(UX-21) | BR-V8-14 | `editor.layout` TP-V8-8 |
| 원문 enum·맨 숫자 없음(FR-D8) | BR-V8-15·16 | `fr-d8` TP-V8-9(ko·en), `design.grep` |
| 보강 표시(UX-23) | BR-V8-17·18 | `editor.augment`(열쇠·변경 이름, 속성 시험), `editor.layout` TP-V8-10 둘, `editor.test` 변경 라벨 |
| 탭 라벨 | BR-V8-19 | `editor.layout` TP-V8-15 |
| 사전 일치 | BR-V8-20 | 기존 사전 시험 |
| 상태·오류(FR-S5, FR-D9) | BR-V8-21~26 | `editor.layout` TP-V8-11 셋, TP-V8-12 둘, 알림 셋(불러오기·빌드·지역 지우기), `design.grep` `String(e)` |
| 플레이 시작(Q2 = A, UX-27) | BR-V8-27·28 | `editor.parts` TP-V8-13, `editor.test` S01, `editor.layout` 열린 세션 줄 |
| 빌드 리포트(UX-22) | BR-V8-29·30 | `editor.layout` TP-V8-14 둘, `editor.test` BuildPanel 시험 그대로 |
| 접근성(FR-S6) | BR-V8-31~34 | `editor.layout` TP-V8-15·BR-V8-33, `editor.parts` 도구 띠·[파일 ▾] |
| 월드가 바뀌는 일 | BLM § 1.4, R-02 | `editor.data` TP-V8-18, `editor.layout` TP-V8-18 둘 |

## 4. 바뀐 기존 시험과 지운 시험

`frontend-components.md` § 7.1 표와 실행 메모 R-01의 grep 목록대로 고쳤다.

- `editor.test.tsx`
  - 옛 지도 캔버스 셋 → `EditorMapPane` props로 같은 단언. 꺼진 칸은 끌리지 않는다는 시험 하나를 더했다.
  - `RegionInspector` 시험: 새 props(`open`, `onOpenChange`). `reloadKey` 단언 둘(S31, 끌기 지킴)은 페이지가 등록된 `reload()`를 부르는 것으로 옮겼다.
  - 연결 가중: 숫자 칸 단언 → `CommitRange`(끄는 동안 저장 0, 놓으면 1).
  - `ConfirmDelete` 막힘 줄·S05: 세션 id 대신 수(BLM § 9).
  - `UnscopedPanel` 둘: `reloadKey` → `picks`·`reload()`.
  - `AugmentPanel` 시험 전부: 시험용 호스트 `AugHost`로 렌더. "run id를 넘기고 돌아오면 다시 읽음" 둘은 "패널이 내려갔다 와도 run이 남음" 하나로 뜻을 옮겼다.
  - S06: 확인 답이 성공하면 그 카드의 초안이 지워진다(BLM § 6.2). 그 뒤 다시 쳐서 고치기를 단언한다. 원래 지키던 두 가지(확인에는 입력이 실리지 않음, 범위 밖 확신은 보내지 않음)는 그대로다.
  - #12 보강 오류: 서버 원문 → "질문의 대상이 월드에 없어요" 문장 + 접힌 원문.
  - 끌기 실패, WikiPanel 종류, S25 종류, #15 가중 라벨, #14 [파일 ▾], S01 플레이 폼, S23 `WorldMap`, S24·C8 `EditorHeader`.
- `components.test.tsx`: 옛 지도 덮개 둘 → `WorldMap mode="edit"`. 세션 띠 하나 지움. `/editor` 시험에 `play-this-world` 있음을 더함. 보강 하나는 `AugHost`.
- `play.test.tsx`: 세션 띠의 플레이어 폼 시험 둘을 지웠다. 같은 폼은 `home.test`와 `editor.parts` TP-V8-13이 본다.
- `gm.test.tsx`: 쓰지 않는 import 한 줄을 지웠다. GM 단언은 하나도 바뀌지 않았다.
- `layout.test.tsx`: `MapPanelLayout`을 파일에서 바로 가져온다.

지운 시험 4개(세션 띠 셋, run id 둘을 하나로)와 새 시험 81개:
- `editor.data` 17
- `editor.augment` 9
- `editor.parts` 16
- `editor.layout` 24
- `layout` 3
- `fr-d8` 2
- `design.grep` 2
- 기존 enum·사전 시험의 매개변수 경우 7(새 enum `augmentationIssue`와 새 키가 늘린 것)
- `editor.test` 1

## 5. 이탈

1. **첫 화면 JS가 2.02 kB(gzip) 늘었다**(117.19 → 119.21 kB). 플랜 Step 8.1은 "늘지 않는다"였다. 게이트 전에 여쭸고, 이탈로 기록하기로 정했다(2026-10-11, A).
   - 코드 쪽 원인(공유 틀이 `layout` 묶음 파일을 거쳐 첫 화면에 실림)은 고쳤다(`23a63de`, −0.26 kB).
   - 남은 것은 V8이 더한 ko/en 사전 낱말이다(소스 gzip +1.7 kB). 사전은 모든 화면이 쓰는 한 모듈이다. 홈의 빌드 대화상자도 V8 낱말을 쓴다.
   - 에디터 코드는 지연 묶음에 있다. 화면별 사전 나누기는 § 8로 넘긴다.
2. **빌드 단계는 `format/enums`가 아니다**(플랜 § 1.2). 서버의 `BuildWarning.stage`는 닫힌 enum이 아니라서, `buildStages.ts`가 아는 단계 목록을 쥐고 모르는 단계는 "기타"로 보인다.
3. **보강 run의 주인은 페이지의 훅이다**(실행 메모 R-15). FD § 5.2·5.3은 `runId`/`onRunId`와 `drafts`/`onDrafts`를 패널에 넘긴다고 했다. 대신 `useAugmentation`이 run·초안·쓰기를 쥐고, 패널은 보이기만 한다. 탭이 내려간 사이 끝난 답도 초안을 정리한다.
4. **기다리는 선택은 `worldGen` 대신 만들기 표식으로 가른다**(실행 메모 R-04). 결과는 BLM § 3 표와 같다.
5. **새 사전 키 이름**: 말투 시험이 키 앞머리로 말투를 가르므로 `label.stage.*`, `label.field.*`, `tab.*`, `notice.*` 등을 썼다. 플랜이 적은 `buildStage.*`, `field.*`는 쓰지 않는다.
6. **첫 읽기의 머리 제목**: FD § 4.7은 "월드 id"다. 월드 목록이 먼저 답하면 그 이름을 보인다. 둘 다 아직이면 id다(시험 있음).
7. **설계에 없던 작은 것**
   - 지도 대화상자가 닫히면 연 도구 단추로 초점을 돌린다(BR-V8-33). TP-V8-3을 쓰다 찾았다. 전에는 대화상자를 열 때 초점을 쥔 탭 단추로 돌아가, Radix 탭이 초점만으로 그 탭을 다시 열었다.
   - 지역 지우기 알림은 제목 "○○ 지역을 지웠어요"와 본문(옮긴 수)이다. `delete.region.done`은 본문이 됐다.
   - 연결 줄의 상대 이름을 누르면 그 지역을 고른다(FD § 4.4에 있음). 사전을 지우면 월드도 다시 읽는다(BLM § 5).
   - 새 testid: `editor-panel`, `world-error`, `region-not-found`, `connection-other-*`, `build-report-sessions`.

## 6. 알려진 한계

- FD에서 넘어온 것
  - 섹션을 접거나 탭을 바꾸면 저장하지 않은 기본 정보·지식 더하기·NPC 폼의 글이 사라진다(BR 알려진 제약). 페이지는 보강 초안, 고른 지역, 펼침만 쥔다.
  - 지도 자체는 키보드로 닿지 않는다. 지역은 패널의 지역 고르기로 고른다.
  - UX-18의 남은 부분(지도 위 라벨 겹침 등)은 지도 그리기 규칙이라 바꾸지 않았다(BLM § 10). 390px에서 지도 라벨이 작다.
- 캡처에서 찾은 것
  - **1024px 경계를 넘나들면** 머리·지도·패널이 새로 그려진다. `MapPanelLayout`이 넓음·좁음에서 다른 트리를 돌려주기 때문이다. GM도 V6부터 같다. 펼친 [파일 ▾], 열린 지도 대화상자, 저장하지 않은 인스펙터 글이 사라진다. 페이지가 쥐는 것(탭, 보강 초안, 고른 지역, 펼침, 선택)은 남는다.
  - 패널은 `sticky`이지만 지금 내용에서는 격자 줄만큼 길다. 그래서 페이지를 내리면 패널도 함께 올라간다(153px 내리면 위에서 8px). 패널은 화면 안에 남고, 나머지는 패널 자체 스크롤이 맡는다.
  - 예전 에디터 문장 일부가 합니다체다. 지도 도움말, `editor.*.none`, `editor.unscoped.none`, `delete.region.blocked` 등이다.

## 7. 돌연변이 확인

고친 곳마다 바꾸기 전 동작으로 되돌린 코드에서 시험이 실패하는지 봤다. **모두 잡혔다**(58개).
- 처음 실행에서 살아남은 것이 일곱이다. 시험을 더한 뒤 잡혔다.
  - Step 3: m25.
  - Step 5: p13, p16, i5, m2, m3.
  - Step 5의 i1은 잘못 만든 돌연변이였다(남는 인자가 무시됨). 다시 만들어 잡혔다.

| 단계 | 돌연변이 | 결과 |
|---|---|---|
| 3 훅 | 기다림 없음, 아무 읽기나 판정, 기다리는 중 없는 선택 지우기, 교체 뒤 패널 다시 읽기 없음, 쓰기 가드 따로, 초안 모두 지움, 404는 늘 lost | 7/7 |
| 5 화면 | 교체 뒤 run·고른 지역 남음, 만들기·지도 누름이 탭을 안 엶, 선 누름이 연결 섹션 안 엶, 펼침이 지역마다 처음으로, 범위 없는 지식 링크, 알림 셋, 지운 뒤 선택 남음, 빌드 교체 무시, 보강 뒤 월드 안 읽음, 404 빈 상태·읽기 실패 문장 없음, 인스펙터·범위 없는 지식 다시 읽기 등록 없음, 상대 이름 고르기 없음, 만든 지역 바로 고름 | 19/19 |
| 5 부품 | 위험 칸이 기본 정보 안, 저장했어요 없음, 섹션 수, 지운 지역 이름, 쓰기 뒤 다시 읽기 없음, 막힘 줄 없음, 리포트 다섯(범위 0, 이어 붙임 늘, 세션을 단계로, 펼친 채, 세션 줄 없음), 보강 넷(원문 변경·무시·이대로·"/30"), 지도 칸 셋(초점 돌림, 꺼진 칸 끌기, 로딩 판) | 18/18 |
| 6 검사 | 원문 변경·상태·이대로·단계·영역, 맨 확신, 삭제 계획 종류, 종류 선택지 원문, `min-w-80`, `String(e)`, 고정 폭 | 11/11 |
| 7 캡처 고침 | 머리 버튼 묶음이 다시 flex, 파일 줄이 끝으로 안 감 | 2/2 |

## 8. 다음에 넘김

- **V9 부채·문서**
  - 화면별 사전 나누기(첫 화면 낱말 무게, § 5 이탈 1).
  - 에디터·지도 문장의 합니다체를 해요체로(§ 6).
  - 1024px 경계에서 부품이 다시 그려지는 일(GM과 에디터 함께, § 6). 한 트리에서 CSS로 배치를 바꾸면 풀린다.
  - 데모 번역에 엔티티와 사전 하나의 한국어가 없다(캡처에서 영어로 보임).
- **B&T**
  - 실제 스택에서 에디터 한 바퀴를 돈다: 지역 추가 → 골라짐, 끌기, 빌드 교체 → 이어 붙인 수, 불러오기 알림.
  - 실제 서버의 빌드 경고 단계 이름이 `buildStages.ts`의 목록과 맞는지 본다. 모르는 단계는 "기타"로 보인다.
