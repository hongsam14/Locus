## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — U2 World File·캐노니컬 기반
**Reviewed artifact:** `aidlc-docs/construction/U2-worldfile-foundation/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-09-29T16:36:58Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | business-logic-model.md > §7 도입부(`version` 처리)·§7.1; business-rules.md > BR-U2-1/BR-U2-4; domain-entities.md > §1.4 | v0(옛 export) 수용이 다른 월드의 데이터를 덮어쓴다. 옛 export 는 최상위 `world_id` 키와 항목별 `world_id` 를 가진다(`locus/world/worldfile/export.py`). 그런데 v0 은 `world={id: 대상 world_id}` 로 채운다고 정했으므로 `remapped = file.world.id != world_id` 가 항상 false 가 되어 재매핑이 일어나지 않는다. 월드 A 에서 export 한 v0 파일을 월드 B 로 import 하면 A 의 id 가 그대로 남는다. 저장은 id 기준 upsert 이고 Neo4j 유일 제약은 `id` 이므로 A 의 노드를 B 가 빼앗거나 제약 위반이 난다. 이는 Q1=A 의 근거(id 충돌 방지) 자체를 v0 경로에서 무효로 만든다. 또 §7 는 v0 를 `WorldFile` 로 만드는 주체(파서 위치)를 정하지 않았다: `WorldFile.format_version: int` 는 필수 필드라 v0 dict 를 그대로 검증하면 실패한다. | (1) v0 파서를 명시한다(어느 모듈, 입력 dict → `WorldFile`). v0 의 `world.id` 는 최상위 `world_id` 에서 가져오고 없을 때만 대상 world_id 로 둔다. (2) 재매핑 여부는 "파일 원본 world id ≠ 대상" 으로 판정한다. (3) 저장 전에 "이 id 가 다른 world_id 에 이미 있는가" 방어 검사(또는 충돌 시 강제 재매핑)를 규칙으로 추가한다. (4) 이를 BR-U2-1/4 와 TP-U2-6 에 반영하고, 교차 월드 v0 import 예제를 넣는다. | New |
| R-02 | Major | business-rules.md > TP-U2-2; business-logic-model.md > §7.1 | TP-U2-2 `remap_ids(remap_ids(f,T),T)==remap_ids(f,T)` 는 현재 정의로 거짓이다. `new(old)=uuid5(T:old)` 를 두 번 적용하면 id 가 다시 바뀐다. §7.1 의 "멱등" 은 실제로는 "결정성"(같은 입력 → 같은 출력)이다. 재매핑 뒤 `file.world.id` 를 T 로 바꾼다는 문장도 없다. 없으면 export→import 왕복(TP-U2-1)에서 재매핑이 중복 발생한다. `NAMESPACE_LOCUS` 상수도 정의되지 않았다(값이 바뀌면 재현성이 깨진다). | 성질을 "결정성 + 재매핑 후 `world.id==T` 이면 `remap_ids` 는 항등(no-op)" 으로 고쳐 쓰고, `remap_ids` 가 `world.id` 를 T 로 갱신한다고 명시한다. `NAMESPACE_LOCUS` 의 고정 값·위치를 정한다. | New |
| R-03 | Major | business-logic-model.md > §4.1 마지막 줄(rank); business-rules.md > BR-U2-9; `locus/shared/models/enums.py` > `RegionLevel` | 순위 전제가 실제 enum 과 다르다. 문서는 `continent < region < province < district < town` 이라 적지만 `RegionLevel` 은 CONTINENT, PROVINCE, TOWN, DISTRICT, TERRAIN 이고 `region` 값이 없다. "선언 순서 = 넓은 것부터" 를 따르면 town(2) < district(3) 이 되어 문서 예시와 반대이고, 계층상 district 가 town 을 포함하는지 여부도 어디에도 없다. TERRAIN(마지막) 은 위계 레벨이 아니라 VLM 승격 지형인데, 연결·지식 힌트 역할(가장 구체적 = 최대 rank)이 동명 후보 중 TERRAIN 을 항상 고르게 된다. `resolve_region` 을 그대로 구현하면 오해석되고, TP-U2-5 도 이를 못 잡는다. 문서 예시와 BR-U2-9 가 서로 모순이다. | rank 표를 실제 enum 값으로 명시 고정한다(town/district 순서 결정 포함, TERRAIN 취급: 힌트에서 제외/최하위 등). 순위표를 enum 선언 순서에 의존시키지 말고 `naming.py` 의 명시 dict 로 두며, enum 에 값이 추가되면 실패하는 테스트를 둔다. | New |
| R-04 | Major | business-logic-model.md > §5 빌드 의사코드; business-rules.md > BR-U2-11 | 교체 빌드가 삭제 후 작업한다. 의사코드는 `delete_world`(그래프·검색) 를 `ingest_all`·LLM 호출·저장보다 먼저 한다. 수집 실패(§5 의 "저장 없이 리포트 ok=False")나 LLM/persist 실패가 나면 기존 월드는 이미 사라졌고 새 월드도 없다(A3 수정이 데이터 유실을 만든다). 예외 시 `cache.invalidate` 도 호출되지 않아 삭제된 월드의 낡은 스냅샷이 남는다. 또 `count_nodes(world_id, any)` 는 라벨 `any` 의미가 정의돼 있지 않다. | 순서를 "수집·토폴로지·온톨로지 완료 → (replace 면) 삭제 → 저장" 으로 바꾸고, 저장 실패 시 상태(부분 저장)와 리포트 규칙을 적는다. `cache.invalidate` 는 `finally` 에서 호출하도록 한다. "월드 존재" 판정 방법(`list_world_ids` 사용 등)을 정한다. | New |
| R-05 | Major | business-logic-model.md > §6 export 의사코드; business-rules.md > BR-U2-3; domain-entities.md > §1.4 마지막 줄 | 결정적 순서가 일부 절에만 적혀 있다. §6 은 regions/connections/scopes/prior_links 만 정렬하고 entities, relations, knowledge, priors, npcs 는 정렬하지 않는다. BR-U2-3 과 domain-entities §1.4 는 "절마다" 라 하고 `relations`·`npcs` 의 키는 정의하지 않았다. Neo4j `find_nodes` 는 순서를 보장하지 않으므로 TP-U2-1 이 리스트 비교라면 flaky 하다. "바이트 단위로 같게" 는 §6 에서 지켜지지 않는다. | 모든 절의 정렬 키를 표로 확정한다(예: relations=id, npcs=id, priors=id). 문장(§1.4, BR-U2-3, §6)을 하나로 통일하고 TP-U2-1 에 "입력을 섞어도 export 가 같다" 를 추가한다. | New |
| R-06 | Minor | business-logic-model.md > §1·BR-U2-16 대 domain-entities.md > §1.3 | `snapshot.load_warnings` 를 로더와 BR-U2-16 이 쓰지만 `WorldSnapshot` 필드 표에 없다. 또 승인된 component-methods 의 `WorldSnapshot` 은 `world_id,kg,topo,npcs,regions_by_id,npcs_by_region` 뿐이라 `meta`, `regions_by_name`, `unscoped_knowledge_ids` 는 확장이다(모순은 아니나 명시 없음). | `load_warnings: list[BuildWarning\|str]` 를 §1.3 에 추가하고, 확장 필드를 component-methods 대비 확장으로 표시한다. | New |
| R-07 | Minor | business-logic-model.md > §5·§8, domain-entities.md > §4 | `GraphRepository.count_nodes(world_id, label)` 는 승인된 S4(component-methods) 에 없다(거기엔 `list_world_ids` 만 신규). 프로토콜 확장이므로 인메모리/가짜 저장소 갱신을 포함해 확장임을 표시해야 한다. | 확장으로 명기하고, 필요하면 `list_world_ids` 로 대체 가능한지 결정한다. | New |
| R-08 | Minor | domain-entities.md > §1.2 (`npc_doc`); `locus/shared/models/io.py` > `SearchDoc` | NPC 검색 문서를 `kind="npc"` 로 적었으나 `SearchDoc` 필드는 `label`(값: Knowledge/Entity/WikiPrior)이고 검색 필터 키도 `label` 이다. 그대로 구현하면 필드가 없고, 기존 두 호출(`world/wiki`)이 `label` 필터를 써서 오염은 없지만 `SearchDoc.label` 주석에 `NPC` 를 더해야 한다. BR-U2-21 도 `kind=npc`. | `label="NPC"` 로 고치고 BR-U2-21 을 맞춘다. | New |
| R-09 | Minor | business-rules.md > BR-U2-9~12, 15, 19~24, 26, 28, 29 | 검증 수단이 없는 규칙이 있다. §8 은 TP·예제 목록에 BR-U2-11(replace 교체), 12(NPC home 검증), 15(호출 계수), 19(title), 20(briefs), 21~24(NPC 저장·메타·목록), 26(CLI --force), 28(데모 LLM 0 은 예제로 언급) 을 규칙별로 매핑하지 않는다. BLM §8 의 "BR-U2-14" 참조도 스냅샷 불변 규칙(BR-U2-18)을 가리켜야 한다(BR-U2-14 는 미해석 지식). | BR 별 예제/속성 매핑 열을 추가하고, 위 교차 참조 오류를 고친다. | New |
| R-10 | Minor | business-logic-model.md > §4.1 `resolve_region` | (a) 후보가 1개일 때 role=parent 라도 순위 검사 없이 반환해 자식보다 하위 레벨이 부모가 된다. (b) 시그니처 `snapshot_or_regions` 가 모호하다(수집 단계엔 스냅샷이 없다). (c) 경고 반환형(`warning(...)` 가 `BuildWarning` 인지)이 없다. | 단일 후보에도 부모 순위 검사를 적용하고, 입력 타입을 하나로 정하며 반환 타입을 명시한다. | New |
| R-11 | Minor | business-logic-model.md > §2 `WorldCache` | `get` 이 락을 잡은 채 `loader.load` 를 실행해 다른 월드 조회까지 막고, `invalidate` 가 `load` 진행 중에 호출되면 낡은 스냅샷이 저장된다(단일 워커라도 동기 라우터는 스레드풀). 편집(U3) 동시성에서 드러난다. | 월드별 락 또는 세대 번호로 "load 중 invalidate → 결과 폐기" 를 규칙으로 적는다(Minor: 구현 세부). | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `RegionLevel` 값 목록 vs §4.1 rank 문장 | enum 은 continent/province/town/district/terrain, `region` 없음 | R-03 확인 |
| 옛 export 키(`export.py`) vs v0 처리 | 최상위 `world_id` 존재, 설계는 이를 무시 | R-01 확인 |
| `GraphRepository`(base.py) 메서드 vs 설계가 부르는 것 | `count_nodes` 없음, `list_world_ids` 없음(신규 예정) | R-04, R-07 |
| component-methods 의 K3/K4/K5·W9·W10 시그니처 vs BLM | `WorldCache(loader)`, `get/invalidate/clear`, `region_briefs(world_id,*,top_k)`, `import_(..., replace=True)`, `build(..., replace)` 일치 | 모순 없음(필드 확장만) |
| tests/test_boundaries.py 행렬 vs 설계 | world→shared/knowledge, play 금지. 세션 닫기는 라우터/CLI 에 둠(BR-U2-27) | OK. `WorldCache` 를 `knowledge` 에 둠 = 허용 |
| RE A1/A2/A3/A4/A7/A8/A11/A13 → BR | A1=6, A2=7, A3=11, A4=14, A7=10, A8=19, A11=8, A13=13 모두 규칙 존재 | 규칙은 있으나 A3(R-04)·A11(R-03) 는 결함 |
| `SearchDoc` 필드 | `label` 이며 `kind` 없음 | R-08 |
| `hybrid_search` 호출처 | 2곳 모두 `label` 필터 사용, NPC 문서가 기존 검색을 오염시키지 않음 | OK |
| Neo4j `delete_world` | `MATCH (n {world_id}) DETACH DELETE n` → `:WorldMeta`/`:NPC` 도 지움 | OK(world_id 속성 필수 준수) |
| ID 해석 (Q1~Q7, A1~A8, K3~K5, W6/W9/W10, RE) | 플랜·상위 산출물에서 모두 해석됨 | 자료 없음 |

### Summary

Q1=A 의 id 재매핑 규칙이 v0 경로에서 성립하지 않아(R-01) 다른 월드 데이터를 덮어쓸 수 있고, TP-U2-2 와 RegionLevel 순위(R-02, R-03), 삭제 후 작업 순서(R-04), 부분 정렬(R-05)이 구현자에게 추측을 요구한다. 경계 준수·approved 시그니처와의 정합은 대체로 양호하나 Critical 1건과 Major 4건으로 NOT-READY.
