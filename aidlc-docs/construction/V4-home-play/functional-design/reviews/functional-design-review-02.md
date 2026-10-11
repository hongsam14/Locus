## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — V4 홈·플레이 화면
**Reviewed artifact:** aidlc-docs/construction/V4-home-play/functional-design/business-logic-model.md (함께: business-rules.md, frontend-components.md)
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-08T00:37:33Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | business-logic-model.md > 2.1, 2.2; business-rules.md > BR-V4-16, TP-V4-10; frontend-components.md > 4 (`usePlaySession`) | 고쳐졌다. `session.id === sessionId`일 때만 data를 쓰고(이름표는 `world_id`), 키에서 `rev`를 빼 `reload()`로 바꿨으며, `reload`는 void라 폴링을 기다리지 않고 나란히 시작한다고 적었다. `useResource`(옛 data 유지, `reload()` 같은 키)와 맞고, TP-V4-10에 "B를 읽는 동안 A의 data가 안 보인다"가 들어갔다 | 없음 | Resolved |
| R-02 | Major | frontend-components.md > 1, 4 (`PlayLayout`), BR-V4-25, TP-V4-8 | 고쳐졌다. `SplitView`를 플레이에서 빼고 `PlayLayout`이 폭별 목록으로 순서를 정하며, 폭별 DOM 표와 "같은 testid가 DOM에 둘 생기지 않는다"(BR-V4-25, TP-V4-8)가 생겼다 | 없음 | Resolved |
| R-03 | Major | frontend-components.md > 2.3, 6; business-logic-model.md > 1.1, 1.2 | 고쳐졌다. 시작 지역 이름은 `worldNames`(없으면 줄을 뺌), 숫자는 `region_count`(`types.ts:298`에 있음), NPC·씨앗 수와 미니 지도는 뺐고 홈이 전체 내보내기를 받지 않는다고 적었다. 열린 세션은 클라이언트가 걸러 최근순으로 쓰고, 세션 읽기 실패 상태도 정했다 | 없음 | Resolved |
| R-04 | Major | business-rules.md > 기존 테스트, TP-V4-15; frontend-components.md > 2.3, 7, 7.1 | 고쳐졌다. 깨지는 테스트를 § 7.1 표에 이름으로 나열하고, `demo-ask/keep/reload`는 409 경로에만 남기며 "⋯ 메뉴"를 버리고 ghost 버튼 `demo-fresh-*`로 바꿨다. `home.test.tsx`의 `demo-ask`/`demo-keep` 사용(149·168·204·208·253행)과 표가 맞는다 | 없음 | Resolved |
| R-05 | Minor | business-rules.md > BR-V4-24, BR-V4-26; frontend-components.md > 4.1 | 고쳐졌다. `Dialog variant`와 `Button busy`(aria-disabled, `onClick` 가로채기, V6·V8 계약)가 코드 목록 수준으로 적혔다 | 없음 | Resolved |
| R-06 | Minor | business-logic-model.md > 2.5; business-rules.md > BR-V4-21 | 라우터 상태 방식으로 바뀌어 대부분 고쳐졌으나, 정리 규칙에 새 문제가 있다(R-11) | R-11에서 다룬다. 이 행은 뒤로 가기·닫기 판정 부분이 해소되어 닫는다 | Resolved |
| R-07 | Minor | business-rules.md > BR-V4-09; business-logic-model.md > 3 | 고쳐졌다. `AppShell`의 월드 없는 에디터 항목을 `Link`로 바꾸고 `layout.test.tsx` 검사를 더했으며 `AppNav.tsx` 표기를 바로잡았다(현재 `AppShell.tsx`에서 `nav-editor`가 `NavLink`임을 확인) | 없음 | Resolved |
| R-08 | Minor | business-rules.md > BR-V4-04, BR-V4-17, BR-V4-19 | 고쳐졌다. 알림 허용 목록에 409 진행 중을 넣고 닫힘은 띠로 보내며, 폴링 예외 경로와 `gm_busy` 다시 읽기 상한이 적혔다 | 없음 | Resolved |
| R-09 | Minor | business-rules.md > BR-V4-10, BR-V4-01, TP-V4-14 | 고쳐졌다. TP-V4-14가 `ENUM_VALUES`(`regionLevel`·`travelBy`·`sessionStatus`·`rumorOrigin`, 모두 `format/enums.ts`에 있음)를 순회하고, BR-V4-01은 자동 테스트가 없음을 명시했다 | 없음 | Resolved |
| R-10 | Minor | frontend-components.md > 1; business-rules.md > 캡처 계획, TP-V4-8 | 고쳐졌다. 768px 캡처와 TP-V4-8의 중간 폭 항목이 생겼다 | 없음 | Resolved |
| R-11 | Major | business-logic-model.md > 2.5 대화 ("지역이 바뀜(이동)·세션이 바뀜·언마운트" 줄); business-rules.md > BR-V4-21, TP-V4-8 | 언마운트 때 `navigate(location, {replace:true, state:null})`로 정리한다고 했다. 사용자가 시트를 연 채 [홈으로]·상단 메뉴로 라우트를 떠나면 PlayPage가 언마운트되면서 클로저의 옛 `location`으로 replace가 불려, 방금 간 곳이 `/play/...`로 덮이거나 되돌려진다. 세션 변경(`/play/a`→`/play/b`)에서도 `location`이 어느 쪽인지 정해져 있지 않다. 같은 라우트 안에서 일어나는 이동·폭 변경과 라우트를 떠나는 경우를 한 줄로 묶어 놓아 개발자가 그대로 짜면 탈출이 막힌다 | 언마운트·라우트 이탈 때는 `navigate`를 부르지 않는다고 정한다(남은 기록 칸은 두고, 되돌아오면 `state.talk`로 시트가 다시 열려도 된다고 받아들이거나, 열기 전에 `state.talk`가 현재 `regionId`·`sessionId`와 맞는지 검사해 어긋나면 열지 않는다). replace 정리는 같은 PlayPage 안에서 지역·폭이 바뀔 때만 둔다. TP-V4-8의 "언마운트하면 칸이 남지 않는다"를 "라우트를 떠난 뒤 위치가 목적지로 남는다"로 바꾼다 | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `web/src/hooks/useResource.ts` 의미 | 새 키 동안 옛 data 유지, `reload()`는 void·같은 키·화면 유지 | R-01의 `session.id` 검사와 `reload()` 설계가 현실과 맞음 |
| `GameSession.id/world_id`, `WorldNames.world_id` 존재 | `types.ts:456-459`, `309-310` | 옛 data 판별 키가 실재 |
| `WorldInfo.region_count` | `types.ts:298` | 카드 숫자 출처 유효 |
| `ENUM_VALUES`의 네 종류 | `format/enums.ts:7,9,14,20` | TP-V4-14 순회 가능 |
| `AppShell.tsx` `nav-editor` | `NavLink`, `end` 없음 | UX-13 원인·수정 위치 맞음 |
| `ui/Button.tsx` busy | `disabled={disabled \|\| busy}` 현행 | § 4.1 변경은 실제 코드의 변경이며 영향 범위가 적혔음 |
| `home.test.tsx`의 `demo-ask`/`demo-keep` | 149·168·204·208·253행 | 7.1 표가 영향 테스트를 덮음 |
| 라우터 정리 규칙 시뮬레이션 | 언마운트 시 옛 `location`으로 replace | R-11 |

### Summary

이전 R-01~R-10은 모두 설계에서 해소되었다. 새로 Major 1건(R-11)이 남았다. 대화 시트의 라우터 상태 정리가 라우트를 떠날 때 옛 위치로 되돌릴 수 있어, 구현 전에 한 줄로 정해야 한다. Major 1건이라 READY이고, 코드 계획에서 반영해도 된다.
