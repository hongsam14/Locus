## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (계획) — V6 GM 화면
**Reviewed artifact:** `aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-08T11:03:36Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1 "웹: 남김", § 1.3 R-01, Step 5.6 | `SessionBar`를 지우지 않고 남긴다. `WorldFileBar.tsx`(`SessionBar`를 import)와 `play.test.tsx`·`components.test.tsx`의 묶음은 그대로다. 호출부 grep(`GmPage`, `WorldFileBar`, 테스트 2개)과 맞는다. `session.close`는 바꾸지 않고(`ko.ts:40`) GmHeader가 `session.end`를 쓴다(Step 4.9). FD의 틀린 전제는 code-summary § 5에, `variant="full"` 정리는 § 7(V8)에 적는다. | - | Resolved |
| R-02 | Major | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > 단계 표기, Step 3~5 | 방식 (a)로 고쳤다. Step 2~4는 새 파일과 호환 변경만 하고, 기존 부품의 계약 변경·`GmHub`/`ManualTurnPanel`/`useWorldState` 삭제·사전 값 바꿈·옛 테스트 고치기는 Step 5 한 커밋에 모은다. 확인한 것: `conflictKind` 호출부는 `GmHub`(`=== "closed"`만)·`DialoguePanel`(같음)·`DeedPanel`·`useTurnRun`이고 2.2가 새 반환형에 맞춘다. `BulkProgress`는 `ManualTurnPanel`에서 `bulk.ts`로 옮기고 `useBulkRumors`가 따라간다(2.7). `useBulkRumors`는 선택 콜백만 더해 `GmHub`와 호환되며 바뀐 끝 알림 단언은 3.3에서 고친다. `deed.void` 값은 `DeedPanel` 외에 쓰는 곳이 없다(grep). 일시적 깨짐 구간이 없다. | - | Resolved |
| R-03 | Minor | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1 "웹: 바뀜", Step 2.2, § 1.3 R-03 | "바뀜" 목록에서 `DialoguePanel`이 빠졌고 Step 2.2·§ 1.3이 "바꾸지 않는다"로 일치한다. | - | Resolved |
| R-04 | Minor | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1.2 "쓰기 감싸기", Step 3.5, Step 8.1 | 14종을 나열하고 BLM 표가 13줄인 까닭(`generate`·`regen`이 한 줄을 나눔)을 적었다. 8.1은 vitest를 기준선 이상으로 정하고, 백엔드가 불변이라 pytest는 1138 그대로로 한정한다. | - | Resolved |
| R-05 | Minor | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1.3 R-05, Step 5.1·5.6·5.7 | `useWorldState`는 Step 5에서 지우고 호출부(`GmPage.tsx:34`, `gm.test.tsx:18,167`)를 5.6·5.7에 적었다. `overlayOf`는 "badgeOf로 바꾸거나 없앤다"인데 `gm.test.tsx:204`의 사용은 5.7의 `gm.test` 고침이 덮는다. | - | Resolved |
| R-06 | Minor | aidlc-docs/construction/plans/V6-gm-screen-code-generation-plan.md > § 1.2 "사전 접두어" (줄 176) vs § 1.3 R-01, Step 4.9 | § 1.2는 "있는 키 `session.close` '닫기'는 '세션 끝내기'로 바꾼다"고 쓰는데, § 1.3 R-01과 Step 4.9는 값을 바꾸지 않고 새 키 `session.end`를 쓴다고 한다. 계획 안에서 서로 어긋나 개발자가 줄 176을 따르면 에디터 `SessionBar`(`ko.ts:40`, `SessionBar.tsx:137`)의 닫기 라벨이 바뀐다. | § 1.2의 해당 문장을 "`session.close`는 그대로 두고 새 키 `session.end` '세션 끝내기'를 쓴다"로 맞춘다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `SessionBar` 호출부 grep | `GmPage`, `features/editor/WorldFileBar`, `components.test`, `play.test` | 남기는 결정과 맞음 (R-01 Resolved) |
| `conflictKind` 호출부 grep | `GmHub`×2, `DialoguePanel`×2, `DeedPanel`, `useTurnRun`, 테스트 `gm.test`·`errors.describe.prop` | 계획의 호출부 표와 단언 고침과 일치 |
| `BulkProgress` / `useMounted` / `WorldMap mode="gm"` 존재 | 각각 `ManualTurnPanel`·`useBulkRumors`, `hooks/useMounted.ts`, `map/WorldMap.tsx:34` | Step 2.7·3.3·4.3의 전제가 성립 |
| `useWorldState`·`overlayOf` 호출부 | `GmPage`, `gm.test`(18,167,204) | Step 5.1·5.6·5.7이 덮음 |
| `deed.void`·`deed.voided` 사용처 | `DeedPanel`만 (`deed.voidConfirmBtn`은 이미 "없던 일로 하기"이나 대화상자 안에서만 조회) | 5.5의 값 바꿈이 다른 곳을 깨지 않음 |
| 단계별 tsc·vitest GREEN 가능성 | Step 2~4 호환, 계약 변경은 Step 5 단일 커밋 | 성립 |
| 문서 내부 일관성 | § 1.2 줄 176 vs § 1.3 R-01 / Step 4.9 | R-06 |

### Summary

이전 Critical 1건·Major 1건·Minor 3건이 모두 해소됐다(SessionBar 유지, Step 2~4 호환 변경 + Step 5 단일 커밋, 호출부 정리). 새로 찾은 것은 § 1.2의 `session.close` 문장이 § 1.3·Step 4.9와 어긋난 Minor 1건뿐이라 막지 않는다.
