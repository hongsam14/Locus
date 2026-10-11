## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — V8 에디터 화면
**Reviewed artifact:** `aidlc-docs/construction/V8-editor/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-11T01:52:46Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | business-logic-model.md > § 6.2; frontend-components.md > § 5.2 `augDrafts` | (1차) 쳐 둔 답의 열쇠가 질문 id로 적혀 S28과 어긋났다. 이제 열쇠는 `issue_key`이고, 답 성공 때 지우는 자리와 다른 카드 초안 유지, 사라진 키 유지가 적혔다. 열쇠와 정리 규칙 자체는 코드(`AugmentPanel.tsx` `input[q.issue_key]`)와 맞는다. 다만 "페이지의 답 보내기 함수"가 어디 있고 어떤 props로 패널에 닿는지는 적히지 않았다(R-15). | 열쇠 문제는 닫혔다. 남은 소유 문제는 R-15에서 다룬다. | Resolved |
| R-02 | Major | business-logic-model.md > § 4 끌기의 새 자리; business-rules.md > BR-V8-10 | (1차) 낙관적 자리와 겹친 끌기 처리가 `useResource`/`useAction`과 어긋났다. 이제 페이지 덮개 `moved`, 끌기의 `useAction` 우회, 성공·실패 때 비우는 때, "지금과 같음" 정정이 적혔다. `useResource`에 setter가 없다는 제약과 맞는 설계다. 겹친 PUT의 도착 순서 문제는 별건(R-16). | 닫혔다. | Resolved |
| R-03 | Major | business-logic-model.md > § 3 6단계 | (1차) `pendingSelect`가 풀리지 않는 경우가 있었다. 이제 `{id, gen}`과 다섯 경우 표가 있고, 다시 읽기 실패·id 없음·월드 교체·다른 지역 선택이 모두 풀림으로 이어진다. `useResource`의 `state: "error"`로 실패를 알 수 있어 구현 가능하다. `gen`이 가려내는 범위의 서술은 R-17. | 닫혔다. | Resolved |
| R-04 | Major | business-logic-model.md > § 1 4번 표, § 5 표; business-rules.md > BR-V8-24 | (1차) 월드가 바뀐 뒤 정리가 흐름마다 달랐다. 이제 한 표(id 바뀜·불러오기·빌드·편집)로 모든 상태의 비움을 정하고, run 404 안내까지 적혔다. | 닫혔다. | Resolved |
| R-05 | Major | frontend-components.md > § 7.1; business-rules.md > 시험 계획 끝 | (1차) 고칠 기존 시험 표가 불완전했다. 다시 grep으로 대조했다: `gm.test.tsx:13`, `components.test.tsx:11,165-174,239-240`, `play.test.tsx:11`, `editor.test.tsx:13,15,16,18,619-621`의 사용처가 표에 있고, `editor.test.tsx`의 `it(` 49개와 `it.each` 1개(2경우)도 맞다. GM의 `session-*` testid는 `GmHeader.tsx`가 따로 갖고 있어 에디터에서 없앤다는 서술과 충돌하지 않는다. | 닫혔다. | Resolved |
| R-06 | Minor | business-logic-model.md > § 6.6, § 9 | (1차) 보강 400이 원인이 여럿인데 한 문장으로 덮었다. 이제 일반 문장 + 접힌 원문으로 정하고 알려진 제약에 적었다. | 닫혔다. | Resolved |
| R-07 | Minor | business-logic-model.md > § 6.4 열쇠 읽기 표 | (1차) 열쇠 해석이 불명확했다. 이제 앞 둘/뒤 둘 분리, 종류별 이름 표, 연결 `a|b|kind` 일치, 칸 라벨, "이름 없는 항목"이 있다. | 닫혔다. | Resolved |
| R-08 | Minor | frontend-components.md > § 4.4; business-rules.md > BR-V8-11 | (1차) 펼침 규칙이 모순이었다. 이제 하나의 규칙과 알려진 제약(접거나 탭을 바꾸면 폼 글이 사라짐)이 적혔다. `Section`의 `open`/`onOpenChange` props가 이미 있어 구현 가능하다. | 닫혔다. | Resolved |
| R-09 | Minor | frontend-components.md > § 4.1; business-logic-model.md > § 7.1; BR-V8-34 | (1차) 파일 input 마운트, 닫힘 조건, 초점, 오류 위치가 비었다. 이제 모두 적혔다. | 닫혔다. | Resolved |
| R-10 | Minor | frontend-components.md > § 5.3 `MapPanelLayout` | (1차) 공유 틀 props가 비었다. 이제 `wide, testId, panelLabel, head, map, panel, panelTop?, narrowOrder?`와 GM·에디터 값이 적혔다. GM 현재 좁음 순서(머리 → 도구·오류·띠 → 지도 → 탭)와 `narrowOrder`가 같다. | 닫혔다. | Resolved |
| R-11 | Minor | business-logic-model.md > § 8 | (1차) `NewSessionForm`의 지역이 묶음이라 적혀 있었다. 이제 평면 목록이고 props 목록이 코드의 시그니처(`open, worldId, regions, nameOf?, error, busy, onSubmit, onCancel`)와 맞는다. | 닫혔다. | Resolved |
| R-12 | Minor | business-rules.md > BR-V8-13; business-logic-model.md > § 4 | (1차) 폼 가중의 `CommitRange` 의미가 비었다. 이제 폼은 값만 정하고 [저장]이 쓰며, 처음 값과 종류 변경 규칙이 있다. | 닫혔다. | Resolved |
| R-13 | Minor | business-logic-model.md > § 2; BR-V8-25 | (1차) `rev` 키 때문에 다시 읽을 때 로딩으로 돌아갔다. 이제 `reload()`를 쓴다. `useResource.reload`는 같은 키에서 이전 `data`와 `state: "ready"`를 유지하므로(`hooks/useResource.ts`) 설계 근거가 맞다. | 닫혔다. | Resolved |
| R-14 | Minor | business-rules.md > TP-V8-16 | (1차) 390px 가로 스크롤을 캡처로만 확인했다. 이제 `min-w-80`/고정 px 폭 grep 검사와 `scrollIntoView?.()`가 있다. | 닫혔다. | Resolved |
| R-15 | Major | frontend-components.md > § 5.3 `AugmentPanel({ worldId, regions, entities, knowledge, runId, onRunId, drafts, onDrafts, onChanged })`; business-logic-model.md > § 6.2, § 6.3; business-rules.md > BR-V8-23 | R-01의 수정이 "답을 보내는 일과 초안 정리를 페이지의 답 보내기 함수가 한다. 패널이 내려가도 빠지지 않는다"고 정했지만, 컴포넌트 계약이 이를 담지 않는다. 지금 코드(`AugmentPanel.tsx`)에서 `run`, `busy`, `error`, `changed`(변경 기록의 대상 이름), `call()`, `answer()`는 모두 패널 안 상태다. § 5.3의 패널 props에는 답 함수도 `busy`/`error`도 run도 없다. 그래서 (1) 답 함수가 패널에 남는다면 탭을 바꾼 사이 끝난 답의 초안 정리를 페이지가 할 수 없고(패널이 내려가면 `useAction`은 `onDone`을 부르지 않음) R-01의 약속이 지켜지지 않으며, (2) 페이지로 올린다면 응답의 run, `busy`, 오류, `changed`를 어디에 쥘지가 비어 있다. 또 요청 중 탭을 바꿨다 돌아오면 새로 마운트된 패널의 `busy`가 꺼져 있어 초안이 아직 남은 같은 답을 두 번 보낼 수 있다(BR-V8-23 "같은 쓰기가 두 번 나가지 않는다"와 TP-V8-4 "탭을 바꾼 사이 끝나도"가 서로 시험을 요구하는데 소유자가 정해지지 않음). | 답 보내기·되돌리기·다시 보기·시작을 페이지(또는 페이지가 쥐는 훅)가 소유할지, 패널이 소유하고 완료 때 `onAnswered(issueKey)` 같은 콜백을 페이지에 올릴지 하나로 정한다. 정한 쪽의 props(함수, `busy`, 오류, run, `changed`)를 § 5.3에 적고, 요청 중 탭을 바꿨다 돌아온 경우의 `busy` 값과 두 번 보내기 방지를 BR-V8-23/TP-V8-4에 한 줄로 넣는다. | New |
| R-16 | Minor | business-logic-model.md > § 4 "끌기는 `useAction`을 쓰지 않는다"; BR-V8-10 | 겹친 끌기를 줄 세우지 않고 "같은 지역의 겹친 저장은 서버에서 나중 것이 이긴다"고 적었다. 병렬 PUT은 보낸 순서가 아니라 도착 순서로 처리되므로, 첫 끌기의 요청이 늦게 도착하면 서버에는 첫 자리가, 덮개에는 둘째 자리가 남는다. 덮개는 "월드 답이 같아질 때"만 지워지므로, 그 뒤 월드를 다시 읽어도 둘이 달라 덮개가 서버 값을 가린 채 남는다. 또 첫 끌기가 실패해 덮개 칸을 지우고 월드를 다시 읽으면 둘째 저장이 아직 가는 중일 때 옛 자리로 되돌아 보일 수 있다. | 같은 지역의 끌기는 앞 저장이 끝난 뒤 마지막 자리만 보내거나(지역별 대기), 덮개를 지울 때 비교하는 값을 "마지막으로 보낸 자리"로 정해 어긋나면 다시 읽는다고 한 줄 적는다. 대안이 필요 없으면 알려진 제약으로 적는다. | New |
| R-17 | Minor | business-logic-model.md > § 3 6번 표 두 번째 행과 그 아래 "만들기 응답과 다시 읽기의 순서는 `gen`으로 가른다" | `worldGen`은 월드 "답이 올 때" 늘어나므로 `gen` 비교는 읽기를 "언제 시작했는지"를 가리지 못한다. 만들기 응답 전에 시작한 읽기가 응답 뒤에 도착하면 `worldGen > gen`이 되어 id가 없다는 이유로 풀린다는 표의 서술은 `gen`만으로는 성립하지 않는다. 실제로 막아 주는 것은 만들기 성공 뒤 부르는 `reload()`가 `useResource`의 이전 요청을 취소(abort, `seq`)하는 성질이다. 그 의존이 적혀 있지 않아, `reload()` 호출 순서가 바뀌면 오탐 "새 지역을 찾지 못했어요"가 난다. | `gen`의 정의와 판정을 맞춘다. "만들기 성공 직후 같은 틈에서 `reload()`를 부르고, 그 전에 나간 읽기는 `useResource`가 버린다"를 근거로 적거나, `gen`을 읽기 시작 시점에 세도록 고친다. TP-V8-3에 "이미 나간 읽기가 만들기 응답 뒤에 도착하는" 경우를 넣는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| R-01..R-14 수정이 세 산출물에 있는지 | 전부 "설계 리뷰 01 R-0x"/"리뷰 R-0x" 표식과 함께 있음 | 이전 지적은 해소 |
| `useResource`: `reload()`가 이전 요청을 취소하고 같은 키에서 data/ready 유지 | `hooks/useResource.ts` 확인, 일치 | R-13 근거 맞음, R-17의 보호 근거 |
| `useAction`: 실행 중이면 `undefined`, unmount 뒤 `onDone` 안 부름 | `hooks/useAction.ts` 확인 | 끌기 우회·R-01 서술 근거 맞음, R-15 근거 |
| `AugmentPanel` 현재 상태 소유(run·busy·error·changed·input) | `features/editor/AugmentPanel.tsx` 확인, 모두 패널 안 | 설계의 props 목록과 어긋남 → R-15 |
| `ui/Tabs`가 안 보이는 탭을 내림 | `Tabs.tsx`, Radix `Content` 기본 동작 | 페이지가 탭 상태를 쥐어야 한다는 전제 맞음 |
| `Section`의 `open`/`onOpenChange` props | `layout/Section.tsx` 확인 | 펼침을 페이지가 쥘 수 있음 |
| `NewSessionForm` props와 평면 목록 | `features/play/NewSessionForm.tsx` 확인 | BLM § 8 props 목록과 일치 |
| GM의 `session-*` testid 위치 | `GmHeader.tsx:59,64`, `SessionBar`는 `WorldFileBar`만 import | `SessionBar` 삭제가 GM 시험에 영향 없음 |
| `editor.test.tsx`의 `it(` 수와 `it.each` | 49 / 1(2경우) | 51 서술 일치 |
| `components.test.tsx:239-240`, `editor.test.tsx:619-621` 줄 번호 | 일치 | § 7.1 표 신뢰 가능 |
| 서버 변경 없음 주장 | 호출 목록이 기존 API뿐 | 모순 없음 |

### Summary

1차의 Major 5개와 Minor 9개는 모두 코드와 대조해 닫혔다. 새로 남은 Major는 하나(R-15: 보강 패널의 답 소유자와 props가 R-01의 수정 약속과 맞지 않음)이고 Minor 둘(R-16, R-17)이 있어 허용 범위(Major 2 이하, Critical 0)이므로 READY다. R-15는 코드 생성 계획 전에 페이지/패널 소유를 한 줄로 정해 두는 것이 좋다.
