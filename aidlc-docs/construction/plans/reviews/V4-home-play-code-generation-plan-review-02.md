## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 — V4 홈·플레이 화면
**Reviewed artifact:** `aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-08T00:52:40Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 6 머리말(GREEN 규칙) | 해결됨. Step 6은 새 부품은 새 파일이고 기존 부품(RegionScene·NpcList·MovePanel·PlayLog·ActionBar·DialoguePanel)에는 기본값이 지금 동작인 선택 prop만 더하며, 보이는 변경은 Step 7.1a로 미뤄 `play`·`dialogue`·`deeds`가 Step 6에서 그대로 통과한다고 못박았다. 다만 6.7이 `Field` 라벨과 `outline-none` 제거를 Step 6에서 하는데 7.1a는 "ActionBar의 라벨·초점 고리"를 Step 7에서 켠다고 해 서로 어긋난다(R-12로 이관) | 없음(R-12에서 정리) | Resolved |
| R-02 | Major | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 3.1~3.3 | 해결됨. `hint.gmLocked` ko를 해요체("세션을 고르면 열려요", `HAEYO` 통과)로 쓰고 en도 옮기며, `nav.gmLocked`를 두 사전에서 지우고 LEGACY에서 빼고, `layout.test.tsx:60`·`AppShell.tsx:71` 키 교체를 적었다. `log.*` 두 줄은 마침표를 더하고 STORY에 `log`를 넣으며 `deeds.test.tsx:169`가 `t()` 비교라 안전하다는 확인도 `grep` 단계로 적었다. 소스에서 소비처 `AppShell.tsx:71`, `layout.test.tsx:60`, `deeds.test.tsx:169`만임을 확인했다 | 없음 | Resolved |
| R-03 | Major | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 2.3 | 해결됨. 시험 결과(깨지는 테스트 둘)를 읽어 본 판단: `ui.primitives.test.tsx:8`은 `Button busy`에 `toBeDisabled()`를 걸고 `gm.test.tsx:315`는 busy 확인 버튼에 `waitFor(toBeDisabled)`를 걸어 `aria-disabled` 전환에서 깨지는 것이 맞다. 그 밖의 `toBeDisabled` 단언(`gm.test` 622·634, `editor.test` 434, `components.test` 244-247, `deeds.test` 60-70, `dialogue.test` 322)은 `disabled=`·`closed`·native 입력에 거는 것이라 busy 전환의 영향을 받지 않는다는 주장이 그럴듯하다. submit 버튼은 `onClick`의 `preventDefault`로 암묵 제출을 막고 Enter 테스트도 계획에 있으며, 규칙(busy 단언은 `aria-disabled`, `disabled`는 `toBeDisabled`)도 적혔다. 남는 사소한 점은 R-12 | 없음 | Resolved |
| R-04 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 5.5a, 6.10 | 해결됨. 키를 쓰는 단계의 같은 커밋에 ko·en을 함께 더하도록 5.5a(홈 키)와 6.10(플레이 키)으로 나눴다 | 없음 | Resolved |
| R-05 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 5.5 | 해결됨. `worldId?` 선택 prop, `SessionBar.tsx:122` 호출처는 그대로임, `useEffect`로 지역을 비우는 방식을 정했다. 구현 때 `useEffect`는 `if (!open) return null` 앞에 둔다(훅 순서) | 없음 | Resolved |
| R-06 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > § 1.1 | 해결됨. 메모가 BLM § 2.5·BR-V4-21·TP-V4-8의 해당 줄을 대신한다고 명시하고, code-summary § 5 이탈 기록을 적었고, 두 폭 전환을 새 `{talk:{sessionId,regionId,npcId}}` 모양으로 다시 쓰고, 7.3에 세션 변경·어긋난 `state.talk`·폭 전환 테스트를 더했다 | 없음 | Resolved |
| R-07 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 6.6 | 해결됨. play 모드에서만 svg `<image>`로 그리고 edit·gm은 `<img>` 그대로이며 `map.worldmap.test`에 테스트를 더한다. `getByAltText("world map")`(`components.test.tsx:554`)은 `MapOverlay` 경유(edit·gm)라 영향이 없다 | 없음 | Resolved |
| R-08 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 4.2, 4.2a | 해결됨. data가 있으면 오류가 와도 data를 그리고 `InlineError`+[다시 시도]를 두는 우선 규칙을 정했다(`useResource`가 같은 키 data를 오류 때도 남기므로 구현 가능). `types.ts`에 `gm_busy?`를 더하는 4.2a가 생겼고 § 1 바뀜 목록에도 있다 | 없음 | Resolved |
| R-09 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 5.6, 7.3 | 해결됨. 배지 클래스(BR-V4-06), BR-V4-20, BR-V4-22 테스트가 각 단계에 이름 붙었다 | 없음 | Resolved |
| R-10 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 9.1, 9.3 | 해결됨. 캡처 도구의 원본·node·headless chrome 요건을 적었고 고침은 별도 `fix(web)` 커밋으로 정했다. 기준선 숫자는 1.2가 다시 재므로 충분하다 | 없음 | Resolved |
| R-11 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > § 1 "테스트" 행, Step 7.3 | `gm.test.tsx`는 `PlayPage`를 직접 렌더하는 시험을 둘 가진다. `:96-113`은 `play-gm-btn`을 눌러 `/gm/:sid`로 가는 시험이고(BR-V4-20으로 버튼이 사라진다), `:326` 이후 "PlayPage after U7"는 다시 쓴 `PlayPage`와 새 `getRegion` 합친 읽기로 렌더한다. 그런데 § 1은 `gm.test`의 변경을 "Button busy 단언 하나"로 말하고 7.3은 `play`·`dialogue`·`deeds`만 고친다고 해, V6 소유 파일의 PlayPage 시험 수정이 범위에 드러나지 않는다. Step 7 커밋이 이 때문에 RED가 될 수 있다 | § 1 테스트 행과 7.3에 `gm.test.tsx`의 두 PlayPage 시험(`play-gm-btn` 시험은 메뉴 `nav-gm` 경로로 바꾸거나 BR-V4-20 테스트로 옮김, "PlayPage after U7" 블록은 새 화면에 맞게 수정)을 적는다. `grep -rln PlayPage web/src/__tests__`로 대상 파일을 확정한다 | New |
| R-12 | Minor | aidlc-docs/construction/plans/V4-home-play-code-generation-plan.md > Step 6.7 vs 7.1a, Step 2.3 | (a) 6.7은 ActionBar의 `Field` 라벨과 `outline-none` 제거를 Step 6 안에 두고, 7.1a는 같은 "라벨·초점 고리"를 Step 7에서 켠다고 해 둘 중 어느 쪽인지 모호하다(GREEN 규칙은 선택 prop만 허용). (b) `Button`의 `base`는 `disabled:` 변형으로 비활성 모양을 내므로 `busy`가 `aria-disabled`로 바뀌면 바쁜 버튼이 활성처럼 보일 수 있다. 2.3에 `aria-disabled:` 스타일 처리가 없다 | (a) ActionBar 라벨·초점 고리를 한 단계로 정하고(Step 6이면 기존 테스트가 testid 기반이라 안전함을 적고, 7.1a에서 뺌) 두 줄을 맞춘다. (b) 2.3에 바쁜 버튼의 모양(스피너 유지, `aria-disabled:` 변형으로 `disabled:`와 같은 모양)을 한 줄 더한다 | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `i18n.style.test.ts` 규칙 대 새 문장 | NOTICE는 `요[.?]?$`, STORY는 `다\.$`, CONTROL은 어미 금지. "세션을 고르면 열려요", `log.*`+마침표가 통과 | R-02 해결 |
| `nav.gmLocked`·`log.*` 소비처 | `AppShell.tsx:71`, `layout.test.tsx:60`, `ko.ts:9`, `en.ts:9`, `i18n.style.test.ts:12`; `deeds.test.tsx:169`는 `t()` 비교 | 계획이 모두 덮음 |
| `Button` 소스와 busy 단언 | `disabled={disabled || busy}`; busy 의미의 `toBeDisabled`는 `ui.primitives:8`, `gm.test:315`(DeedPanel 확인 버튼). 나머지 `toBeDisabled`는 `disabled=` 또는 입력 | 시험 결과 주장 그럴듯함 |
| `useResource` 오류 시 data | 같은 키면 data 유지 | 4.2 우선 규칙 구현 가능 |
| `NewSessionForm` 호출처 | `HomePage.tsx:94`, `SessionBar.tsx:122` | 선택 prop이라 tsc 안전 |
| `WorldMap` 배경과 테스트 | `<img alt="world map">` 전 모드 공통, 테스트는 `components.test:554`(MapOverlay) | play 한정 변경은 영향 없음 |
| `gm.test.tsx`의 PlayPage 사용 | `:21`, `:105`, `:110`(play-gm-btn), `:326`, `:351` | R-11 |
| 8.2 정규식 대상 | `toFixed`(RegionScene 2곳), `String(e)`(DemoCards·DemoCard·HomePage·DialoguePanel·PlayPage), `outline-none`(ActionBar:83) 모두 이 계획 단계가 다시 쓰는 파일 | 8.2 통과 가능 |

### Summary

1차 Major 셋(R-01~R-03)과 Minor 일곱이 모두 해결됐다. 남은 것은 Minor 둘이다. `gm.test.tsx`의 PlayPage 시험 둘이 Step 7에서 영향을 받는데 범위에 없고(R-11), ActionBar 라벨·초점 고리가 Step 6과 7.1a 중 어디인지 모호하며 busy 버튼의 비활성 모양이 빠졌다(R-12). 둘 다 구현 중 테스트가 바로 드러내는 성격이라 막지 않는다. 승인 전에 R-11·R-12 한 줄씩 고치기를 권한다. Critical 0, Major 0이므로 READY.
