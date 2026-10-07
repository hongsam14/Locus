## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — U2 World File·캐노니컬 기반
**Reviewed artifact:** `aidlc-docs/construction/U2-worldfile-foundation/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-09-29T16:44:00Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | business-logic-model.md > §7 도입부·§7.1·§7.2; business-rules.md > BR-U2-1/4; domain-entities.md > §1.4 | 수정 확인. §7.2 `WorldFile.parse` 가 v0 의 `world.id` 를 최상위 `world_id` 에서 채우고, `remapped = force_remap or source != target` 이 되어 교차 월드 v0 import 가 재매핑된다. `world_id` 없는 dict 는 422. 유일 제약 충돌은 `MERGE (n:{label} {id, world_id})` + `id` 유일 제약(neo4j_repo.py:69,83)이라 다른 월드와 같은 id 면 제약 위반으로 실제 실패하므로 "error 경고 + ok=False" 규칙이 성립한다. TP-U2-6 이 교차 월드 v0 를 다룬다. | 없음. (강제 재매핑 경로의 결함은 R-12 로 별도 등록) | Resolved |
| R-02 | Major | business-rules.md > TP-U2-2; business-logic-model.md > §7.1 | 수정 확인. `NAMESPACE_LOCUS` 고정 값 정의, 성질을 결정성 + "재매핑 뒤 world.id==T 이면 항등" 으로 고쳤고 `remap_ids` 가 world.id/world_id 를 T 로 갱신한다고 명시했다. TP-U2-2 가 참인 명제가 되었다. | 없음. | Resolved |
| R-03 | Major | business-logic-model.md > §4.1; business-rules.md > BR-U2-9; `locus/shared/models/enums.py` > `RegionLevel` | 수정 확인. `LEVEL_RANK` 이 실제 enum 값(continent/province/town/district)을 명시 표로 고정하고 TERRAIN 은 표 밖으로 두어 모호성 해소에서 제외했다. BR-U2-8/9·TP-U2-5·EX-8 이 일치한다. | 없음. | Resolved |
| R-04 | Major | business-logic-model.md > §5; business-rules.md > BR-U2-11 | 수정 확인. 준비/커밋 단계로 분리, 백업 export 후 삭제, `finally` invalidate, 존재 판정을 `list_world_ids` 로 통일했다. 커밋 단계 실패는 부분 저장이 남으나 백업 + `ok=False, replaced=True` 로 드러내는 것이 명시된 수용 결정이다. EX-10/11 이 검증한다. | 없음. | Resolved |
| R-05 | Major | business-logic-model.md > §6; business-rules.md > BR-U2-3; domain-entities.md > §1.4 | 수정 확인. §6 정렬 키 표가 전 절(regions/entities/knowledge/priors/npcs/relations=id 등)을 덮고 필드명이 models/graph.py 와 일치한다(Relation.id, WikiPriorLink.source_id/target_id/relation, ConnectionEdge, ScopeLink). BR-U2-3·§1.4 가 같은 표를 가리키고 TP-U2-1 에 섞인 순서 조건이 있다. | 없음. | Resolved |
| R-06 | Minor | business-logic-model.md > §1·BR-U2-16 대 domain-entities.md > §1.3 | 수정 확인. `load_warnings` 가 §1.3 표에 있고 확장 필드가 명기되었다. | 없음. | Resolved |
| R-07 | Minor | business-logic-model.md > §5·§8; domain-entities.md > §4 | 수정 확인. `count_nodes` 를 제거하고 `list_world_ids` 하나만 쓴다. | 없음. | Resolved |
| R-08 | Minor | domain-entities.md > §1.2; BR-U2-21 | 수정 확인. `label="NPC"` 로 통일되었다. | 없음. | Resolved |
| R-09 | Minor | business-rules.md > §8 / §8.1 | 수정 확인. §8.1 이 BR-U2-1~29 를 TP/EX 로 매핑한다(BR-U2-18 만 코드 리뷰 항목으로 명시). BLM 의 잘못된 BR-U2-14 참조도 제거됐다. | 없음. | Resolved |
| R-10 | Minor | business-logic-model.md > §4.1 `resolve_region` | 수정 확인. 단일 후보에도 부모 순위 검사를 하고, 입력은 `by_name` dict, 반환은 `tuple[Region\|None, BuildWarning\|None]` 로 명시했다. | 없음. | Resolved |
| R-11 | Minor | business-logic-model.md > §2 `WorldCache` | 수정 확인. 락 밖 로드 + 월드별 세대 번호로 로드 중 무효화 시 캐시 저장을 막는다. EX-19 가 검증한다. | 없음. | Resolved |
| R-12 | Major | business-logic-model.md > §7.1 첫 줄(`if file.world.id == target_world_id: return file`) 대 §7 `remapped = force_remap or …`; business-rules.md > BR-U2-4, EX-3 | `force_remap`/`?remap=true` 가 실제로는 동작하지 않는 경로가 있다. `remap_ids` 는 `file.world.id == T` 이면 항등을 반환하므로, 같은 world_id 로 import 하다가 다른 월드와 id 가 충돌한 경우(충돌 메시지가 안내하는 `retry with remap=true` 복구 시나리오)에도 `force_remap=True` 는 아무 것도 바꾸지 않고 같은 충돌이 되풀이된다. `ImportReport.remapped=True, forced=True` 가 참으로 기록돼도 id 는 그대로다. EX-3 도 `world.id != T` 인 파일이면 강제 여부와 무관하게 통과해 이 결함을 못 잡는다. BR-U2-4 의 "결정적 항등" 과 "강제" 가 서로 모순된다. | `remap_ids` 의 항등 단락(shortcut)을 호출부 조건으로 옮겨라: 항등 판정은 `not force_remap and world.id == T` 일 때만(§7 의 `remapped` 조건이 이미 그 역할이므로 §7.1 첫 줄을 삭제하거나 `force` 인자를 받게 한다). 단 TP-U2-2 의 "재매핑 뒤 재적용 항등" 은 `world.id==T` 이고 force 가 아닐 때로 한정해 서술하고, EX-3 을 "world.id == T 인 파일 + remap=true → 모든 id 가 바뀐다" 로 구체화한다. | New |
| R-13 | Minor | business-logic-model.md > §7.1 (`provenance.refs` 재매핑) | `Provenance.refs` 는 "WikiPrior / ChangeSet / input 의 id"(models/graph.py) 라서 파일 안에 없는 id(ChangeSet, 입력 참조)가 섞일 수 있다. 전부 uuid5 로 바꾸면 해석되지 않는 새 id 가 생기고, TP-U2-2 의 "재매핑 뒤에도 모든 참조가 해석된다" 와 충돌한다. | 파일 안에 존재하는 id 만 재매핑하고 나머지 refs 는 그대로 둔다고 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| §7.2 v0 파서 vs 옛 export 키 | `world_id` → `world.id`, 누락 시 422 | R-01 해소 |
| neo4j_repo.py `upsert_nodes` MERGE 키·`ensure_schema` 유일 제약 | `MERGE (n:L {id, world_id})` + `id` 유일 제약 → 타 월드와 id 충돌 시 제약 위반 | 충돌 감지 규칙 성립 |
| `remap_ids` 항등 단락 vs `force_remap` | `world.id == T` 이면 강제해도 항등 | R-12 |
| `RegionLevel` 값 vs `LEVEL_RANK` | continent/province/town/district + terrain 제외, 일치 | R-03 해소 |
| 정렬 키 표 필드명 vs graph.py 모델 | Relation.id, WikiPriorLink(source_id,target_id,relation), ConnectionEdge, ScopeLink 일치 | R-05 해소 |
| 저장 포트 변경 | `list_world_ids` 하나(S4)만 사용, `count_nodes` 잔존 없음 | R-07 해소 |
| `SearchDoc.label` | `NPC` 추가로 통일 | R-08 해소 |
| `Provenance.refs` 의미 | id 이나 외부 참조 포함 가능 | R-13 |
| §8.1 BR→검증 매핑 | BR-U2-1~29 전부 매핑됨 | R-09 해소 |

### Summary

이전 Critical 1건(R-01)과 Major 4건, Minor 6건이 모두 문서상 해소되었고 근거(유일 제약 동작, enum 값, 모델 필드명)도 코드와 일치한다. 새로 찾은 것은 강제 재매핑이 `world.id == T` 인 파일에서는 항등 단락 때문에 무효가 되는 모순(R-12, Major)과 provenance.refs 의 외부 id 재매핑(R-13, Minor)이다. 열린 항목은 Major 1건으로 READY 기준(Critical 0, Major ≤ 2) 안이며, R-12 는 구현 전 §7.1 한 줄과 EX-3 수정으로 닫을 수 있어 게이트에서 함께 인용할 것을 권한다.
