## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation — Part 1 (unit plan) — U1 경계 재정리
**Reviewed artifact:** `aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-09-29T13:52:54Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 2.6, 8.1, 10.4 | 2.6이 `SharedContainer`·`assemble_shared`를 `locus/shared/wiring.py`로 못박고 Step 2로 앞당겼으며, 8.1은 `api/containers.py`를 만들지 않는다고 명시. 10.4는 `locus/** → api` import를 위반으로 검사하고 "api 제외"가 api가 import하는 쪽 한정임을 밝힌다. | 없음. | Resolved |
| R-02 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > 유닛 컨텍스트 '바뀌는 외부 계약', Step 2.2, 15.1 | 저장된 `prov_source` 옛 값 때문에 기존 Neo4j 월드 재빌드가 필요하다는 위험을 명시(옵션 a)했고, Q4=A를 근거로 매핑 미도입을 선언, code-summary·operations 기록과 15.1 데모 재빌드까지 적었다. "의미 불변" 주장도 저장 데이터 예외를 달았다. | 없음. | Resolved |
| R-03 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 5.1, 5.3, 7.1, 7.2, 실행 원칙 | 5단계는 번역 부분을 지우지 않고 7단계가 "복사 후 원본에서 삭제"하도록 순서를 고쳤다. `play_metadata`/`localization_metadata` 분리, `ALTER TABLE ... active`의 `ensure_play_schema` 귀속, FK 없음 확인이 적혔다(`translations`는 UniqueConstraint만 있고 FK 없음을 코드로 확인). | 없음. | Resolved |
| R-04 | Major | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 5.4, 10.5 | `ON CONFLICT` upsert가 5.4로 들어갔다(방언별 helper, 계약 테스트 멱등 케이스). 대상 키가 PK(`session_rumors.id`, `region_distortions`(session_id, region_id))라 `index_elements`가 성립한다. | 없음. | Resolved |
| R-05 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 2.6, 9.1 | `assemble_shared`가 켠 자원만 연결하고 스키마 초기화를 조립 밖(`ensure_*_schema`)으로 뺐으며, CLI 플래그별 부분 조립을 명시. | 없음. | Resolved |
| R-06 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 4.5, 10.2 | `parents[3]`로 수정(`locus/world/demo/__init__.py` 기준 저장소 루트로 맞음)하고 `test_demo_map_image_path_exists`를 추가. | 없음. | Resolved |
| R-07 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 11.2 | `git mv web/src/api.ts web/src/api/index.ts` 명시, `/api/` 호출 파일이 `api.ts` 하나뿐임을 grep으로 재확인(현 워크스페이스에서도 1개). | 없음. | Resolved |
| R-08 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 8.5, 10.3, 10.6, 15.1, 스토리 추적 | 옛→새 경로표가 8.5에 추가되었고 실제 라우터 경로(advance-turn, suggest-events, augment/session 등)와 일치. 오타 수정, US-5.1·US-7.3 추적 추가, mypy 기준선은 1.1 실측, 15.1은 `compose --profile service` 기준을 유지하고 낮출 때 게이트에 드러내도록 함. | 없음. | Resolved |
| R-09 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 2.5, 13.1, 실행 원칙, 10.6 | 삭제 테스트를 이름으로 나열(`test_traverse_respects_min_weight_param`, 다른 참조 없음 grep 확인)하고 10.6 기대치를 −1로 조정, 실행 원칙에서 설계 명시 예외로 규칙을 정리. | 없음. | Resolved |
| R-10 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 7.1, 7.3, 10.2 | 설계 L2 이름(`get_many`/`upsert_many`) 채택, `purge`는 U5임을 명시, `enrich` 시그니처 변경에 따른 번역 테스트 갱신을 10.2에 추가. | 없음. | Resolved |
| R-11 | Minor | aidlc-docs/construction/plans/U1-boundary-restructure-code-generation-plan.md > Step 7.3 vs Step 6.2, 8.4~8.5 | 7.3이 `enrich` 호출부로 `play/region_knowledge.py`를 든다. 그러나 6.2는 `SessionKnowledgeService`에서 번역 인자·`_localize`를 제거하고 8.5가 라우터에서 `enrich`를 부르도록 정했다. 또 play가 localization 서비스를 부르면 10.4 경계 행렬(`play → localization` 위반)과 충돌한다. | 7.3의 호출부 목록에서 `play/region_knowledge.py`를 빼고(`api/routers`만) 문구를 6.2·8.5와 맞춘다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 8.5 옛→새 경로표 vs `api/routers/{session,authoring,query}.py` 실제 데코레이터 | 경로·메서드 일치(advance-turn, suggest-events, augment/session 등 확인) | R-08 OK |
| `traverse`/`get_region_subtree`/`get_region_ancestors`/`TraversalSpec` 사용처 grep | 테스트 참조는 `tests/storage/test_storage.py:95` 하나 | R-09 OK |
| `locus/demo.py:15` `parents[1]` → 새 위치 `parents[3]` | 저장소 루트가 맞음 | R-06 OK |
| `postgres_session_repo.py` MetaData/PK/FK | 단일 `_metadata`, FK 없음, PK로 ON CONFLICT 가능 | R-03·R-04 OK |
| `grep /api/ web/src` | `web/src/api.ts` 하나 | R-07 OK |
| 단계 순서(2.6 wiring이 3.3·4.7·6.4·7.4보다 앞) | 충족 | R-01 OK |

### Summary

이전 Major 4건과 Minor 6건이 모두 계획에 반영되어 코드·경로로 확인되었다. 남은 것은 7.3의 호출부 목록이 6.2·8.5와 어긋나는 Minor 1건뿐이라 Critical 0, Major 0으로 READY.
