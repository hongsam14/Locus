## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 — V4 홈·플레이 화면
**Reviewed artifact:** `aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-08T00:45:28Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 6 (6.3~6.9) vs Step 7.3 | Step 6은 `RegionScene`·`NpcList`·`MovePanel`·`PlayLog`·`ActionBar`·`DialoguePanel`을 바꾸고(이름표, 막힌 줄 회색, `turn-progress`, `compact`, 사람 카드, 키 없음 안내 등) 그대로 커밋한다. 그러나 이 컴포넌트를 쓰는 옛 `routes/PlayPage.tsx`는 Step 7에서야 다시 쓰이고, 이를 거치는 `play.test`·`dialogue.test`·`deeds.test`는 7.3에서야 고친다. 6.11은 "부품 단위" 테스트만 말한다. 그래서 Step 6 커밋 시점에 옛 PlayPage가 바뀐 props·DOM과 맞는지, 기존 테스트가 GREEN인지 계획에 없다(`ActionBar`가 `useTurnRun` 출력을 받게 되면 옛 PlayPage는 타입부터 깨진다). "각 단계는 게이트 GREEN으로 끝난다"는 단계 표기와 어긋난다 | 부품 변경이 옛 PlayPage와 호환(새 props는 선택, 기존 testid·DOM 유지)임을 Step 6에 못박거나, 호환 불가 부품(ActionBar·NpcList·DialoguePanel 등)은 Step 7과 한 커밋으로 묶거나 그 부품의 기존 테스트 수정을 Step 6에 옮긴다. 어느 쪽이든 Step 6 끝의 vitest·tsc GREEN 근거를 적는다 | New |
| R-02 | Major | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 3.1~3.3, § 1.2 "사전 키" | `nav.gmLocked`를 `hint.gmLocked`로 옮기고 LEGACY에서 뺀다고 했지만, 현재 문장은 "세션을 선택하면 열립니다"(`web/src/i18n/ko.ts:9`)로 `i18n.style.test.ts`의 NOTICE 규칙(`HAEYO = /요[.?]?$/`)에 걸린다. 문장을 해요체로 고친다는 말이 계획에 없어 Step 3 커밋이 RED가 된다. 또 `layout.test.tsx:60`이 `t("nav.gmLocked")`를 직접 쓰는데 3.3은 이 호출 수정을 말하지 않고, `en.ts:9`의 대응 키도 언급이 없다. 같은 이유로 `log.*` 두 줄은 STORY가 `다\.$`를 요구하므로 마침표를 더해야 하는데, `deeds.test.tsx:169-170`은 `t()`로 비교하므로 안전하다는 확인도 계획에 없다 | 3.1~3.3에 (a) `hint.gmLocked`의 ko 문장을 해요체로 쓰고(예: "…열려요") en도 옮기는 것, (b) `layout.test.tsx`·AppShell의 키 이름 교체(호출 지점 `AppShell.tsx:71`, `layout.test.tsx:60`), (c) `log.*` 소비처(`deeds.test.tsx:169-170`)가 `t()`로 비교해 영향 없음을 적는다 | New |
| R-03 | Major | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 2.3, § 1 "테스트" 행 | `Button`은 공유 프리미티브로 `busy={...}`를 쓰는 곳이 비테스트 파일 28곳이다(에디터 12개 파일, GM `GmHub`·`DeedPanel`, `SessionBar`, `ConfirmDialog`, `HomePage`, `PlayPage` 등). 2.3은 "`toBeDisabled()` 단언하던 테스트를 grep으로 찾아 고친다"고만 하고, § 1 "테스트" 행에는 `gm.test`·`editor.test`·`components.test`가 없어 V6·V8 소유 테스트를 V4가 고친다는 범위가 드러나지 않는다(`gm.test.tsx:622,634`, `editor.test.tsx:434,469,569`, `components.test.tsx:244-247` 등 후보). 또 "`onClick`을 막는다"만으로는 `type="submit"` 버튼(`NewSessionForm.tsx:57`, `ActionBar.tsx:93`, `DialoguePanel.tsx:189`)의 암묵적 제출이 막히지 않는다(폼 `onSubmit`은 따로 `!busy` 가드를 가진 곳만 안전). 어느 단언이 busy 때문이고 어느 것이 native `disabled`인지 가르는 기준도 없다 | 2.3에 (a) busy를 쓰는 버튼에 대해 무엇을 바꾸는지(submit이면 `preventDefault`, `aria-busy` 유지), (b) 영향 테스트 파일 목록을 `grep`으로 미리 확정해 § 1에 넣고 busy 단언과 `disabled` 단언을 구별하는 규칙을, (c) V6·V8 코드 쪽에 `disabled={busy}`로 둔 호출이 있으면 그대로 둔다는 판단을 적는다 | New |
| R-04 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 5.1~5.4, 6.10 | 사전 키를 더하는 단계가 6.10 하나뿐이고 "(ko·en) 플레이용"이다. Step 5의 홈이 쓰는 키(`label.homeKicker`, `story.homeTagline`, `story.homeLead`, 카드·월드 행·배지 문구, `hint.worldIdChars`, `action.showMore`)를 더하는 단계가 없다. 또 6.1~6.9 컴포넌트가 6.10보다 먼저 키를 쓴다. 키 집합 일치 테스트(ko·en 동일 키)와 문체 테스트가 단계 중간에 깨질 수 있다 | 키는 쓰는 단계에서 같은 커밋에 ko·en 함께 더한다고 정하고, Step 5에 홈 키 추가 항목을 만든다. 6.10은 "단계마다 더한 키를 모아 확인"으로 바꾼다 | New |
| R-05 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 5.5, § 1 "웹: 바뀜" | `NewSessionForm`에 `worldId` prop을 더한다고 했지만 호출처가 둘이다: `routes/HomePage.tsx:94`와 `web/src/SessionBar.tsx:122`. SessionBar는 `web/src/SessionBar.tsx`가 바뀜 목록에 없고, prop이 필수면 tsc가 깨진다. 또 `NewSessionForm`은 `if (!open) return null`이 훅 뒤에 있어 상태가 닫혀도 남으므로 "worldId가 바뀌면 비운다"는 effect/key 방식 선택이 필요하다 | `SessionBar.tsx`를 바뀜 목록에 넣거나 `worldId`를 선택 prop으로 한다고 적는다. 비우는 방식(`key={worldId}` 또는 effect)을 정한다 | New |
| R-06 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > § 1.1 〔실행 메모 R-11〕 | R-11 처리는 구체적이다(언마운트에서 `navigate` 금지, 열기 전 `{sessionId,regionId,npcId}` 검사, replace는 같은 페이지의 지역·폭 변화만). 남는 빈틈: (a) 승인된 FD `business-logic-model.md` § 2.5(`state.talk`가 npcId, 언마운트 시 replace)와 `business-rules.md` BR-V4-21·TP-V4-8은 그대로여서 계획이 이를 덮어쓴다는 사실을 한 줄로 명시하지 않았다. (b) 넓음→좁음 전환의 `navigate(location, {state:{talk}})`와 넓음 전환의 `activeNpcId = state.talk`가 새 객체 모양과 검사를 어떻게 쓰는지 적혀 있지 않다. (c) 7.3은 "목적지 유지·어긋난 state.talk 무시"를 말하지만 "세션 변경 시 닫힘"과 [닫기]의 `navigate(-1)`가 검사 실패 시 어떻게 되는지(이미 어긋난 칸에서 -1) 테스트가 없다 | § 1.1에 "이 메모가 BLM § 2.5·BR-V4-21·TP-V4-8의 해당 줄을 덮어쓴다"를 적고, 폭 전환 두 줄을 새 모양으로 다시 쓰고, 7.3에 세션 변경·어긋난 칸에서의 닫기 케이스를 더한다 | New |
| R-07 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 6.6, § 1 "웹: 바뀜" | `map/WorldMap.tsx`의 바탕은 `mode`와 무관한 `<img alt="world map">`(`WorldMap.tsx:205-207`)다. 계획은 "play 모드 바탕을 svg `<image>`로 옮긴다"고 하는데, 분기를 만들지 edit/gm에도 적용할지 불명하고 (에디터·GM이 같은 컴포넌트를 쓴다) `map.worldmap.test.tsx`가 테스트 목록에 없다. 에디터 화면은 V8, GM은 V6 소유다 | play 모드에만 적용하는지 전 모드 공통인지 정하고, 공통이면 `map.worldmap.test`의 영향과 V6·V8 화면 영향(캡처 확인)을 적는다 | New |
| R-08 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 4.2~4.3, § 1 "웹: 바뀜" | (a) `useResource.ts`는 합쳐진 로더(`Promise.all`)와 `reload()`(같은 키, 화면 유지, 에러였다면 loading)를 계획 가정대로 지원한다(확인함). 단 `api/play.ts`의 `getSession`·`getRegion`·`getLog`는 `signal`을 받지 않아 abort는 결과 버림으로만 작동한다(현재 설계상 문제는 아니나 4.2에 한 줄 필요). (b) 행동 뒤 `reload()`가 실패하면 같은 키 data가 남은 채 `state="error"`가 되는데, "data 있음이면 그린다"와 "error면 오류 화면" 중 무엇이 이기는지 4.2에 없다. (c) `gm_busy`는 `web/src/types.ts`에 아직 없는데(`turn_running`·`declare_max_chars`만 있음) 타입 추가 파일이 § 1 목록에 없다 | 4.2에 (b)의 우선 규칙(data가 있으면 화면 유지 + 알림)을 정하고, `types.ts`에 `gm_busy?: boolean`을 선택 필드로 더한다고 § 1에 넣는다 | New |
| R-09 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 5.6, 8.2, § 3 | TP-V4-12의 후반(열린 세션 배지 렌더 클래스에 `danger` 없음, BR-V4-06)과 BR-V4-22(대화 끝내기 판단 결과가 결과 띠에 나옴)에 이름 붙은 테스트 단계가 없다. 5.6은 TP-V4-1~4, 8.2는 정규식 검사만 말한다. BR-V4-20(`play-gm-btn` 없음)도 7.2 구현 줄뿐 7.3 테스트가 없다 | 5.6에 배지 클래스 테스트를, 7.3에 BR-V4-20·BR-V4-22 테스트를 명시한다 | New |
| R-10 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 1.2, Step 9.1 | (a) 기준선 숫자(vitest 424+skip 1, pytest 1048)는 Step 1.2가 재측정하므로 문제 없으나 `CLAUDE.md` Status의 수치(948·202)와 달라 어느 쪽이 기준인지 code-summary § 1에서 확인한다고 적으면 좋다. (b) 캡처 도구는 세션 scratchpad `v2/cap/server-v2.mjs`에 의존하는데(현 세션 scratchpad에 존재함을 확인) `shoot-v2.mjs`·브라우저 도구 요건과 scratchpad가 사라질 때의 대비는 없다. 9.3의 "고친 것은 그 Step의 파일에서 커밋" 도 이미 지난 단계를 되돌아가므로 "별도 fix 커밋" 중 어느 쪽인지 모호하다 | 9.1에 사본 원본 경로와 필요 도구(브라우저 자동화)를 적고, 9.3은 "별도 `fix(web)` 커밋으로 현 단계에 쌓는다"로 정한다 | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 계획이 이름 붙인 기존 웹 경로 존재 | `hooks/{index,useAction,useResource}.ts`, `features/home/{DemoCard,DemoCards}.tsx`, `features/play/*` 9개, `ui/{Button,Dialog}.tsx`, `layout/AppShell.tsx`, `map/WorldMap.tsx`, `i18n/{ko,en}.ts`, 계획의 테스트 파일 대부분 존재. 새 파일(`useMedia` 등)은 계획이 새로 선언 | OK |
| `useResource` 의미 | 키 JSON 비교, 새 키 동안 옛 data 유지, `reload`는 같은 키·화면 유지, `key=null` 지원, 늦은 답은 `seq`로 버림 | 계획 가정(R-01 FD, `session.id` 가드, `exportWorld` 키 `[worldId]`)과 일치. R-08에 세부 |
| `api/play.ts`·`api/world.ts` 심볼 | `getSession`·`getRegion(withLang)`·`getLog(limit)`·`listTurnRuns(status)`·`getTurnRun`·`act`·`listSessions`·`listNpcs`·`exportWorld`·`loadDemo`·`worldNames` 존재, `useRequestLang`는 `i18n`에서 export | OK |
| `gm_busy` 타입 | `web/src/types.ts`에 없음(`turn_running`, `level_path_ids`, `declare_max_chars`는 있음) | R-08 (c) |
| `busy={` 호출 수 | 비테스트 28곳(에디터·GM·SessionBar·ConfirmDialog·Home·Play) | R-03 |
| `type="submit"` 버튼 | NewSessionForm, ActionBar, DialoguePanel | R-03 |
| `nav.gmLocked` 소비처 | `AppShell.tsx:71`, `layout.test.tsx:60`, `ko.ts:9`, `en.ts:9`, `i18n.style.test.ts:12`; 문장이 해요체 아님 | R-02 |
| `log.*` 소비처·키 수 | ko 2줄(`ko.ts:188-189`), 테스트 `deeds.test.tsx:169-170`는 `t()` 비교 | 마침표 추가는 안전 |
| `NewSessionForm` 호출처 | `HomePage.tsx:94`, `SessionBar.tsx:122` | R-05 |
| `WorldMap` 바탕 | `<img alt="world map">` 모든 모드 공통(`WorldMap.tsx:205`) | R-07 |
| BR-V4-01~26 / TP-V4-1~15 단계 대응 | 대부분 Step 2~8에 대응. BR-V4-06 배지 테스트·BR-V4-20/22 테스트 누락 | R-09 |
| R-11 실행 메모 | 구체적이며 실행 가능. BLM § 2.5·BR-V4-21·TP-V4-8 덮어쓰기 명시 및 폭 전환 줄 빠짐 | R-06 |

### Summary

계획은 단계 구성과 FD 추적성이 대체로 좋고 R-11 메모도 실행 가능하지만, 커밋마다 GREEN이라는 주장이 세 곳에서 지켜지지 않는다: Step 6이 옛 PlayPage와 기존 플레이 테스트를 고치지 않은 채 부품을 바꾸고(R-01), Step 3의 `hint.gmLocked`가 문체 테스트에서 RED가 되며(R-02), Step 2의 `Button busy` 변경이 V6·V8 소유 화면과 submit 버튼에 미치는 영향이 목록에 없다(R-03). 이 셋(Major 3건)을 고치고 Minor를 정리하면 2차에서 READY가 된다.
