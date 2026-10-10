## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — V7 월드·지식 정확성
**Reviewed artifact:** `aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-08T13:55:46Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 2.2 3항; aidlc-docs/construction/V7-world-knowledge/functional-design/domain-entities.md > § 2; aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-07, TP-V7-5 | 고쳐졌다. 무캐시 규칙이 "버전을 읽을 수 있는 캐시 + 로더가 이 월드에 `None`"으로 한정됐고, `_current_version`이 `UNVERSIONED` 표식으로 두 경우를 가른다. `version()` 없는 로더와 `check_version=False`는 지금처럼 캐시한다(`cache.py`의 `getattr(loader,"version",None)` 분기와 맞다). EX-18·EX-19 유지가 명시됐다. | 없음 | Resolved |
| R-02 | Major | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 6 `delete_held` 행; aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-19, TP-V7-11 | 고쳐졌다. 라벨 읽기 → 없으면 라벨 없는 읽기 → 노드 전무면 unindex만, 다른 라벨 노드면 False(문서도 그대로)로 흐름이 정해졌고 TP-V7-11이 검색 문서를 단언한다. | 없음 | Resolved |
| R-03 | Major | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 7 2·3항; aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-22, TP-V7-13 | 거의 고쳐졌다. CONFIRM은 거절하지 않고, 고치기·더하기·다시 가리키기의 무변경 검사는 쓰기 전에 한다고 정해졌다. 남은 것은 새 R-09(확신이 이미 목표값인 CONFIRM이 빈 변경 기록을 남기는지 정해지지 않음)로 옮겼다. 이 행의 원래 결함(유지 길이 막힘, 검사 시점)은 닫혔다. | 없음 | Resolved |
| R-04 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 3 마지막 항, § 4 "세션"; aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > 알려진 제약 | 고쳐졌다. 세션 닫기는 교체 뒤 `replaced`일 때만(`api/routers/world.py` `_close_if_replaced`와 일치), 중단 시 세션은 열린 채라고 적혔고 잘못된 알려진 제약은 지워졌다. TP-V7-9에 세션이 닫히지 않음이 있다. | 없음 | Resolved |
| R-05 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-20, TP-V7-12; aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 6 | 고쳐졌다. 12곳 = 9 라벨 + 3 라벨 없음, 그리고 `apply.py` 더한 노드 삭제의 스냅숏 없는 갈래가 적혔다. grep 결과(writes 44/56/110/117, regions 112/117/120, bundle 54, apply 160/195/210/256)와 일치한다. | 없음 | Resolved |
| R-06 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-05; aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 1 "이 결과를 쓰는 곳" | 고쳐졌다. `pick_facts`의 재정렬(`_fact_key`)은 같은 뜻의 키라고 바로잡았고 소문 씨앗 차례 변화가 적혔다(`rumor/service.py` 419행 `view.direct + view.propagated` 확인). 메서드 이름은 `_sources`가 아니라 `_collect_sources`이나 구현에 지장 없다. | 없음 | Resolved |
| R-07 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-02, PBT-V7-1; aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 1 0항 | 고쳐졌다. 같은 (지역, 지식) 직접 스코프는 최대 확신 하나, 생성기가 중복을 낸다. | 없음 | Resolved |
| R-08 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 4 1항; aidlc-docs/construction/V7-world-knowledge/functional-design/domain-entities.md > § 4 | 고쳐졌다. `self._cache.invalidate` 뒤 `self._cache.get`으로 새로 읽고 생성자·생성 지점 5곳은 그대로다. `WorldBuilder.__init__`이 `SnapshotCache`(get·invalidate)를 받으므로 가능하다. 읽기 실패는 교체하지 않는다. | 없음 | Resolved |
| R-09 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 7 3항; aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-22 | FR-C12는 "빈 변경이 기록되지 않는다"인데, 확신이 이미 목표값인 CONFIRM은 "지금처럼 기록되고 질문을 닫는다"로 적혀 있다. 이때 `apply_answer`의 `changed`가 비어 변경 내용 없는 ChangeSet(되돌리기 목록에 뜨는 빈 항목)과 불필요한 색인·`touch_world_meta` 쓰기가 남을 수 있다. 어느 쪽인지 정해지지 않아 구현자가 추측해야 한다. | CONFIRM이 값을 바꾸지 않을 때 (a) 변경 기록 없이 질문만 닫고 성공을 돌려주는지, (b) 빈 ChangeSet을 남기는지(FR-C12 예외로 밝힘)를 한 줄로 정하고 TP-V7-13에 단언을 더한다. | New |
| R-10 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/domain-entities.md > § 4 경고 문장 마지막 항; aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > PBT-V7-4 | `WorldLoader.load`는 집 지역이 없는 NPC와 지역이 없는 씨앗을 스냅샷에서 `load_warnings`로만 버린다(`loader.py` `_keep`). 그래서 `carry_over`가 받는 옛 스냅샷에는 그 항목이 없고 "옛 집 지역이 옛 스냅샷에 없으면" 경고 갈래는 닿지 않는다. 이미 깨진 NPC·씨앗은 이어 붙지도, 경고로 보고되지도 않고 교체와 함께 사라진다(백업도 스냅샷에서 나온다). PBT-V7-4의 "붙인 + 경고 = 옛 수"는 스냅샷 안의 항목에만 참이다. | 그 갈래를 지우거나 "스냅샷에 오른 항목만 센다"로 PBT-V7-4 문장을 좁히고, 로더가 버린 항목을 리포트 경고로 올릴지(`old.load_warnings` 중 stage `load`)를 정한다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `cache.py` `_current_version`, hit·miss 분기와 R-01 서술 | `getattr(loader,"version",None)` 없으면 `None`; `check_version=False`는 별도 분기 | `UNVERSIONED` 구분으로 구현 가능, EX-18/19 유지 |
| 교체 중 읽기 경로 추적(옛 버전 읽기 → 부분 로드 → 캐시) | 교체 뒤 버전이 달라 다음 읽기에 무효화됨; 지운 틈은 `None`이라 무캐시 | BR-V7-08 성립 |
| `persist_graph` 노드·엣지·색인 구조와 메타 마지막 | 노드 일괄에 meta 포함(62~70행), 실패 시 early return | 재정렬은 메타를 별도 호출/단계로 빼야 함. § 2.1이 이를 서술, OK |
| `get_node`/`delete_node` 호출부 grep | production 12줄: 라벨 9, 라벨 없음 3 (+apply 갈래) | R-05 Resolved |
| `delete_held` 현재 코드 대 새 흐름 | 현재는 라벨 없이 읽음; 새 흐름이 다른 라벨 문서를 보존 | R-02 Resolved |
| `apply._confirm_or_edit`·`apply_answer` 변경 집합 계산 | 확신 같은 CONFIRM은 `changed`가 비는 ChangeSet을 만든다 | R-09 |
| `WorldLoader.load`의 `_keep`(NPC 집 지역, 씨앗 지역) | 끊긴 항목은 스냅샷에서 빠짐 | R-10 |
| `WorldBuilder.__init__`의 `cache: SnapshotCache`, `test_build.py`의 실제 `WorldCache` | get·invalidate 둘 다 있음; 기존 시험에 스텁 캐시 없음 | R-08 방식이 기존 시험을 깨지 않음 |
| `rumor/service.py` `_collect_sources`, `scope.py` `pick_facts` | 419행 `direct + propagated`; `_fact_key` 재정렬 | BR-V7-05 서술과 일치(이름만 다름) |
| FR-C6~C12, V7 unit-of-work 완료 조건과 설계 대응 | 완료 조건 6개 모두 TP·BR에 대응 | OK |
| 경계(`carry_over.py`는 world, 로더·캐시는 knowledge) | shared ← knowledge ← world 안 | OK |

### Summary

1차의 Major 셋과 Minor 다섯이 모두 코드와 맞게 닫혔고, 남은 것은 FR-C12의 빈 변경과 CONFIRM의 관계(R-09), 로더가 버린 끊긴 NPC·씨앗의 보고(R-10)라는 Minor 둘뿐이다. Critical 0, Major 0이라 READY다.
