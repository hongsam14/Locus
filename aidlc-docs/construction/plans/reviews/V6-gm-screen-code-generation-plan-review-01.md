## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (계획) — V6 GM 화면
**Reviewed artifact:** `aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-08T10:59:34Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1 "웹: 없앰", Step 5.4 | 계획은 `SessionBar.tsx`를 "쓰는 곳은 GmPage뿐"이라며 지운다. 그러나 `web/src/features/editor/WorldFileBar.tsx:5,106`이 `<SessionBar variant="picker" regions onPlay …>`를 쓴다(에디터의 "세션 시작" 띠, `start-session-band`). `web/src/__tests__/play.test.tsx:11,304-343`(`SessionBar player start (US-3.1)`)도 쓴다. 지우면 `tsc`가 깨지고 에디터가 세션 고르기·플레이어와 시작을 잃는다(에디터는 V8 몫이다). 계획의 Step 5.4 grep은 `components.test.tsx`만 짚고 `play.test.tsx`와 `WorldFileBar`는 놓쳤다. FD(`business-logic-model.md` § 1.5 "에디터는 이제 세션 띠가 없다", `frontend-components.md:223`)의 전제도 현재 코드와 다르다. 또 GmHeader는 "플레이어와 시작"(`onPlay`, `regions`)을 맡지 않는다. | `SessionBar`를 V6에서 지우지 않는다(GM 머리만 `GmHeader`로 옮기고 `SessionBar`는 에디터 picker 변형으로 V8까지 남긴다). 아니면 V8이 에디터를 정리한 뒤 지운다고 쓴다. 어느 쪽이든 FD의 틀린 전제를 이탈로 code-summary § 5에 적고, 4.9의 `session.close` 값 바꿈이 남는 `SessionBar`에 미치는 영향을 정한다. `play.test.tsx`를 고치는 테스트 목록에 넣는다(지우는 쪽을 택할 때). | New |
| R-02 | Major | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > 단계 표기, Step 3.4, 4.2, 4.3, 4.5~4.7, 4.9, 5.5 | "단계는 웹 게이트가 GREEN인 상태로 끝낸다"가 Step 3~4에서 성립하지 않는다. 옛 소비자(`GmHub`, `GmPage`)는 Step 5.4까지 남는데, Step 3.4는 `PlayerStrip`이 자기 읽기를 버리고 props를 받게 바꾼다(현 시그니처 `sessionId, turn, regionNames, rev, onPlayer`; `GmPage.tsx:136`, `gm.test.tsx:124,555`가 씀). Step 4는 `SeedPanel`(현 props `sessionId, closed, busy, reloadKey, onStart`, 자기 `listSeeds`)을 "자원을 받는다"로, `EventPanel`·`TimelinePanel`·`DeedPanel`·`WorldStateOverlay`·`DistortionPanel`·`RumorPanel`을 새 계약으로 바꾼다. `GmHub.tsx`는 옛 props로 그대로 부른다 → `tsc`가 깨진다. 값 바꿈(4.9)과 `llm-required` 글 제거(4.3)는 `gm.test.tsx:650`, `components.test.tsx`의 `GmHub` 묶음을 깬다. 이 테스트들은 5.5에서야 고친다. 계획은 일시적으로 깨지는 곳을 밝히지 않는다. | 둘 중 하나로 정한다. (a) 3.4·4.x가 옛 소비자와 호환되게 새 props를 선택적으로 두고 `GmHub`가 5.4에서 지워질 때 옛 경로를 걷는다. (b) Step 3~5를 하나의 "깨질 수 있는 구간"으로 묶고, 어디서 `tsc`·vitest가 다시 GREEN인지(Step 5.6) 명시하고 그 사이 커밋은 게이트 없이 한다고 쓴다. 단계 표기의 문장을 그에 맞게 고친다. | New |
| R-03 | Minor | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1 "웹: 바뀜", § 1.1 R-05 표 | `features/play/DialoguePanel.tsx`가 "바뀜" 목록에 있고 Step 2.2는 "타입만 맞춘다"인데, R-05 표는 "DialoguePanel은 `=== "closed"`만 보므로 바뀌지 않는다"고 한다. `DialoguePanel.tsx:94,134`는 `=== "closed"`만 비교하므로 새 반환형에서도 컴파일된다. 서로 맞지 않는다. | 목록과 Step 2.2에서 `DialoguePanel`을 뺀다(또는 바꿀 이유를 쓴다). | New |
| R-04 | Minor | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > Step 3.5(TP-V6-4), Step 8.1 | TP-V6-4는 "쓰기 14종"이라 하나 BLM § 3 표의 쓰기는 13행(소문 만들기·다시 만들기, 일괄 둘이 한 행에 묶임)이라 세는 법이 다르다. 개발자가 어떤 14인지 추측해야 한다. 또 Step 8의 "완료" 검증에 vitest 목표 수(기준 550 + 새 테스트)나 새 테스트 수의 하한이 없다. | 14종을 나열하거나 표와 맞춘다. 8.1에 vitest 기대 수의 하한과 `ruff`·`black`을 건드리지 않음(백엔드 불변)을 적는다. | New |
| R-05 | Minor | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1 "웹: 바뀜"(`WorldStateOverlay`), Step 3.2, 5.5 | `useWorldState`(`WorldStateOverlay.tsx:33`)는 `GmPage.tsx:34`와 `gm.test.tsx:18,167`이 쓴다. 계획은 `useGmData.worldState`가 이를 대신하는지, `useWorldState`를 지우는지 남기는지, 그 테스트를 어떻게 고치는지 말하지 않는다. | `useWorldState`의 운명(삭제 또는 `overlayOf`만 유지)과 그 호출부(`GmPage`, `gm.test.tsx`)를 Step 3.2 또는 4.2에 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 계획이 바꾸는 웹 경로 존재(`features/gm/*`, `routes/GmPage.tsx`, `api/http.ts`, `hooks/{useTurnRun,useWorldNames}.ts`, `ui/Select.tsx`, `layout/Section.tsx`, 테스트 10개) | 모두 존재. 새 파일 14+3개는 새로 선언됨 | OK |
| `conflictKind` 호출부 grep | `GmHub`(2, `"closed"`만), `DialoguePanel`(2, `"closed"`만), `useTurnRun:165`(`"busy"`), `DeedPanel:57`(`"busy"`), 테스트 `gm.test.tsx:272-277`, `errors.describe.prop.test.ts:83-84` | 계획의 호출부 표와 단언 고침(`gm.test:271-279`, `errors.describe.prop:83-84`)은 맞다. `DialoguePanel`은 바꿀 필요 없음(R-03) |
| `SessionBar` 호출부 grep | `GmPage`, **`features/editor/WorldFileBar.tsx:5,106`**, 테스트 `components.test.tsx`, **`play.test.tsx:11,304-343`** | "쓰는 곳은 GmPage뿐"은 거짓 → R-01 |
| `BulkProgress` 호출부 | `ManualTurnPanel.tsx:4`(정의), `useBulkRumors.ts:4` | 계획의 2.7 이동이 두 곳을 덮음 OK |
| `mapLimit`·`useWorldNames`·`Select`·`Section` 현황 | `mapLimit`은 `bulk.ts`, `useWorldNames`는 `reload`를 돌려주지 않음 | 계획의 변경 전제와 맞음 OK |
| R-01(FD 리뷰) slant | `format.enums.test.ts:34` "slant is not an enum" 확인, `component-methods.md:61`의 `EnumKind`에는 있음 | 실행 메모대로 정하고 이탈로 적는 것은 구체적. BR-V6-24·TP-V6-12 이탈은 계획이 명시함 OK |
| R-09(FD 리뷰) "could not be closed" | `api/routers/world.py:174` 빌드 경고. GM 화면에 안 나옴 | V8 이월 근거가 맞음 OK |
| FD 리뷰 R-01..R-10 실행 메모 | § 1.1에 각각 구체적 규칙·테스트가 있고 FD와 다른 곳(R-01 slant, R-02 소유 표, R-08 BLM § 7 줄)은 이탈로 명시 | 구체적으로 다뤘고 숨은 모순은 찾지 못함 OK |
| 단계별 게이트 GREEN 가능성(3.4, 4.2~4.9 vs `GmHub`/`GmPage`/`gm.test`) | 옛 소비자와 테스트가 5.4~5.5까지 남음 | R-02 |
| 백엔드 불변 주장 | 계획이 건드리는 서버 파일 없음 | OK |

### Summary

SessionBar 삭제의 근거("쓰는 곳은 GmPage뿐")가 거짓이다. 에디터 `WorldFileBar`와 `play.test.tsx`가 쓰므로 그대로 실행하면 `tsc`가 깨지고 V8 몫인 에디터의 세션 시작이 사라진다(R-01, Critical). 또 Step 3~4가 옛 소비자를 두고 계약을 바꾸어 "단계마다 GREEN"이 성립하지 않는다(R-02, Major). FD 리뷰 R-01..R-10의 실행 메모와 `conflictKind` 호출부 처리는 구체적이고 맞다. 이 둘을 고치면 나머지(Minor 3건)는 막지 않는다.
