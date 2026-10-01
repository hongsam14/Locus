## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — U3 월드 에디터
**Reviewed artifact:** `aidlc-docs/construction/U3-world-editor/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-01T07:10:13Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/U3-world-editor/functional-design/business-logic-model.md > §5.1 | 단계별 저장 시점(커밋 순서 2·4·5), 정규화 질의 중복 키, 빌드당 40개 상한, 참조 규칙 "증류 ∪ created"가 모두 명시됐다. DERIVED_FROM의 MATCH가 늘 끝점을 찾는다. | 없음 | Resolved |
| R-02 | Major | business-rules.md > BR-U3-37, domain-entities.md > §2.3·§8-7 | NPC 번역을 버리고 이탈 7로 기록했다. BR-U3-3·19, frontend §2.3과 일관된다. | 없음 | Resolved |
| R-03 | Major | domain-entities.md > §4.2, BLM §4.1·4.2 | `AugmentationAnswer.ref_id`, `Issue.field`·`key`, `ignored_keys`가 생겼고 dedup 키에 속성이 들어갔다. 남은 모호함은 새 R-11로 옮긴다. | 없음 | Resolved |
| R-04 | Major | business-rules.md > BR-U3-28, BLM §4.3 | `answers`/`MAX_ANSWERS=30`과 되돌리기 포함 상태 전이 표가 있다. 20개 질문 대비 5개 문제가 해소됐다. | 없음 | Resolved |
| R-05 | Minor | BLM §4.1, BR-U3-41 | 다듬기 5개·wiki_conflict 20개 상한과 run 안 캐시가 명시됐다. | 없음 | Resolved |
| R-06 | Minor | BR-U3-23, domain-entities §4.1 | NPC dangling을 뺐고 옛 relation 분기를 지운다고 명시했다. | 없음 | Resolved |
| R-07 | Minor | domain-entities.md > §8-0 | W4~W8 계약 변경 목록이 있다(클래스 분할, 시그니처, 반환형). | 없음 | Resolved |
| R-08 | Minor | BLM §4.3 revert, §4.2 ignore 행, domain-entities §4.3, TP-U3-4 | 나중 것부터 규칙, run 수명(BR-U3-42)은 생겼다. 남은 것은 셋이다. (a) ignore는 "빈 변경"을 남기는데, LIFO라서 이 빈 변경을 먼저 되돌려야 앞선 실제 변경을 되돌릴 수 있는지, 그리고 되돌리면 `ignored_keys`가 복원되는지 정해지지 않았다(`ChangeSet`에 ignored 키 필드가 없다). (b) run 밖의 에디터 편집이 사이에 끼면 `nodes_before` 교체 되돌리기가 그 편집을 덮어쓴다. 충돌 규칙이 없다. (c) TP-U3-4는 여전히 답 1~5개이고 ignore·converged/stopped 전이·run 밖 편집을 덮지 않는다. | ignore가 ChangeSet을 남기는지와 되돌리기 효과(`ignored_keys` 복원)를 정하거나 ignore는 LIFO에서 제외한다. 외부 편집 충돌은 거절(409)이나 감수로 한 줄 적는다. TP-U3-4에 ignore 섞은 열과 상태 전이 속성을 넣는다. | Unresolved |
| R-09 | Minor | BLM §2, §1.4, BR-U3-16 | 열린 세션 전부의 GM 리스(`TurnGuard.hold`, locus/play/turn/guard.py에서 확인)를 쥔 채 보호 집합을 읽고 지운다. 턴 중이면 409다. 종류 바꾸기는 `change_connection_kind` 한 연산이다. | 없음 | Resolved |
| R-10 | Minor | frontend-components.md > §2.1, BLM §6 | `exportWorld`로 지역을 읽고 `startSession(w, {name, start_region_id})`를 부른다. `GET /worlds/{w}/export`는 api/routers/world.py:263에 있다. | 없음 | Resolved |
| R-11 | Minor | BLM §4.2 dangling 행, domain-entities §4.2 `Issue.key` | 새 발견. 이슈 키는 속성 이름까지만 구분한다. `derived_from_prior_ids`·`about_entity_ids`는 목록인데 한 노드에 끊긴 id가 둘이면 같은 키로 한 이슈가 되고, edit(`ref_id` 하나)·remove("그 id만 뺌")가 어느 id인지 정하지 못한다. 또 connection 대상의 `wiki_prior_ref` 수정은 두 방향 엣지에 모두 적용해야 한다는 말이 없고, `Region.parent_id` edit에 BR-U3-7의 순환 검사가 적용되는지도 없다. | 목록 속성의 키에 끊긴 id를 포함하거나 한 이슈로 목록 전체 처리 규칙을 적는다. connection 쌍 양방향 갱신과 parent 순환 검사 적용을 한 줄씩 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `TurnGuard.hold`·`assert_idle` 존재와 의미 | locus/play/turn/guard.py, 턴 중이면 즉시 예외, GM 보유 중 턴 `acquire`도 거절 | R-09 해소 근거 OK |
| `InMemoryRunStore` 존재 | locus/world/augmentation/run_store.py | BR-U3-42의 전제 OK |
| `GET /worlds/{w}/export` 라우트 | api/routers/world.py:263 | R-10 OK |
| 이전 지적 ID가 산출물에서 해소됐는지 | R-01~R-07·R-09·R-10 확인, R-08 일부 | 위 표 |
| 산출물 간 BR/EX/TP 번호 해석 | BR-U3-3·16·23·28·29·37·41·42, EX-8·11, TP-U3-4 모두 존재 | OK |

### Summary

열 개 중 아홉 개는 해소됐고 구현자가 되묻지 않고 만들 수 있다. 남은 것은 모두 Minor다. ignore와 LIFO 되돌리기의 상호작용, 외부 편집 충돌(R-08), 목록 속성 dangling 처리(R-11)이다. Major 0, Critical 0이라 READY다.
