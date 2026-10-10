## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — V7 월드·지식 정확성
**Reviewed artifact:** `aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-08T13:50:24Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 2.2 `WorldCache.get` 3단계; domain-entities.md § 2; business-rules.md BR-V7-07 | "버전이 `None`이면 캐시하지 않는다"가 두 경우를 가리지 않는다. (a) 로더가 `version()`을 아예 갖지 않거나 `check_version=False`인 캐시(`cache.py` `_current_version`이 `getattr(loader,"version",None)` 없으면 `None`을 돌려준다), (b) WorldMeta가 없어 `version()`이 `None`을 돌려주는 월드. 규칙을 그대로 쓰면 (a)도 영영 캐시되지 않는다. `tests/knowledge/test_cache.py`의 `_Loader`(version 없음)로 만든 EX-18(`test_get_caches_until_invalidated`), EX-19(`is_cached(\"w\") is True`)가 깨지고, 같은 파일 96행 근처의 "메타 없는 월드는 무효화만"을 단언하는 시험도 뜻이 바뀐다. 설계는 어느 기존 시험이 바뀌는지도, (a)를 어떻게 다루는지도 적지 않았다. | 3단계를 "마커를 지원하는 로더가 `None`을 돌려준 경우"로 한정하고, 마커 미지원 로더·`check_version=False`는 지금처럼 명시적 invalidate만으로 캐시한다고 적는다. 바뀌는 기존 시험(test_cache.py의 메타 없는 월드 단언)과 그대로여야 할 시험(EX-18/19)을 BR-V7-07 또는 TP-V7-4에 이름으로 밝힌다. | New |
| R-02 | Major | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 6 표 `editor/writes.py delete_held`; business-rules.md BR-V7-19, TP-V7-11 | `delete_held`는 지금 라벨 없이 읽어 노드가 없으면 `unindex(world_id,[node_id])`를 부르고, 다른 라벨 노드면 `False`만 돌려주고 검색 문서를 건드리지 않는다(`writes.py` 108~118). 읽기를 `label=label`로 바꾸면 "같은 id를 다른 라벨이 쓰는" 경우 읽기가 `None`이 되어 `node is None` 가지로 들어가고, 다른 라벨 노드의 검색 문서를 지운다(색인 문서는 맨 id로 키가 잡힌다 — `persistence.py` 주석과 `SearchRepository.delete(world_id, ids)`). 설계는 "다른 라벨의 같은 id 노드와 그 검색 문서는 건드리지 않는다"고 쓰지만 그 가지가 이를 어긴다. TP-V7-11은 그래프 노드만 확인한다. 지금은 지켜지던 보호가 새로 깨진다. | `delete_held`의 "노드 없음" 가지에서, 같은 id를 다른 라벨이 쓰고 있으면 `unindex`를 하지 않는다(라벨 없는 존재 확인 한 번, 또는 `own_label` 성격의 질의)고 흐름을 적는다. TP-V7-11에 "다른 라벨 노드의 검색 문서가 남는다"를 단언으로 더한다. | New |
| R-03 | Major | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 7 3항 (확인은 이미 그 값이면 거절); business-rules.md BR-V7-22, TP-V7-13 | WIKI_CONFLICT 질문의 확인(CONFIRM)은 "유지한다"는 뜻이다(`questions.py` 템플릿 "Keep or fix it?"). 탐지는 확신도와 무관하다(`engine.py` 111~121, 지형과 설명의 충돌 판정). 확신이 이미 0.9 이상인 지식에 CONFIRM하면(`apply._confirm_or_edit`: `max(k.confidence,0.9)`) 값이 같아 설계대로면 400 "the answer changes nothing"이다. 제작자는 "유지"를 고를 길이 막히고 무시(IGNORE)만 남는다. LOW_CONFIDENCE는 정의상 0.5 미만이라 이 문제가 없다. 설계는 이 경우를 따져 보지 않았다. 요구사항 FR-C12는 "빈 변경이 기록되지 않는다"이지 "유지를 거절한다"가 아니다. | WIKI_CONFLICT의 CONFIRM은 변경 기록 없이 성공으로 처리(또는 IGNORE와 같은 결과)하거나, 거절한다면 그 문장과 화면 안내를 정한다. 어느 쪽이든 "이미 그 확신이면 거절"의 적용 범위를 이슈 종류별로 적고 TP-V7-13에 WIKI_CONFLICT·확신 0.9 이상 사례를 더한다. 또 §7 2항의 검사가 `_write`에서 쓰기 전에 값을 비교하는지, 쓴 뒤 `changed` 집합이 비어서 던지는지를 정한다(후자면 그래프·색인·WorldMeta가 이미 바뀐 뒤다). | New |
| R-04 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 3 마지막 항, § 4 "세션"; business-rules.md "알려진 제약" 2번째 | "세션 닫기는 API·CLI 층이 빌드 앞에서 한다 … 백업 실패로 멈추면 세션은 이미 닫혀 있을 수 있다"는 코드와 반대다. `api/routers/world.py` `_after_replace`/`_close_if_replaced`는 빌드 **뒤**, `report.replaced`가 참일 때만 세션을 닫고(149행), CLI(`__main__.py` 127~130)도 같다. 앞에서는 열린 세션 수를 점검만 한다. 그래서 백업·옛 스냅샷 읽기 실패(`replaced=false`)로 멈추면 세션은 열린 채이고, 알려진 제약으로 적은 "닫힌 채 남는다"는 생기지 않는다. 반대로 교체 직후 세션을 닫기 전까지의 틈은 문서에 없다. | 두 곳의 서술을 실제 순서(교체 뒤 `replaced`일 때만 닫음)로 고치고, 쓸모없어진 알려진 제약을 지우거나 "중단 시 세션은 그대로"로 바꾼다. 중단 경로에서 세션을 닫지 않는 것이 맞다는 점을 시험(TP-V7-7)에 한 줄 더한다. | New |
| R-05 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > BR-V7-20, TP-V7-12; business-logic-model.md > § 6 | 호출부 수가 어긋난다. 코드의 `get_node`/`delete_node` 호출은 12줄이다(apply.py 160·195·210·256, regions.py 112·117·120, writes.py 44·56·110·117, bundle.py 54). 상류 설계 리뷰 R-05가 센 11은 한 줄 덜 센 것이고, 설계의 "8곳 + 3곳 = 11"도 같은 오차를 이어받았다. § 6 표대로면 라벨을 넘기는 호출은 9줄(writes 44·110·117, regions 3줄, apply 160·195·210)이고 라벨 없는 호출은 3줄(bundle 54, writes 56, apply 256)이다. `apply.py:210`은 "스냅숏 없는 id는 라벨 없이"여서 라벨 없는 가지가 하나 더 있다. 구현자가 "8곳"을 기준으로 시험을 쓰면 한 곳이 빠진다. | 수를 줄 단위로 다시 세어 BR-V7-20·TP-V7-12에 적고, 호출부를 표의 행이 아니라 파일:줄로 나열한다. `apply.py:210`의 라벨 없는 가지를 라벨 없는 목록에 넣는다. | New |
| R-06 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 1 "이 결과를 쓰는 곳"; business-rules.md BR-V7-05 | "쓰는 쪽은 다시 정렬하지 않는다"가 사실과 다르다. `play/npc/scope.py` `pick_facts`는 `_fact_key`(범위 순위, -확신도, id)로 다시 정렬한다(키가 같아 결과는 같지만 재정렬은 한다). 또 `play/rumor/service.py` 417행은 `view.direct + view.propagated`의 차례로 소문 씨앗을 고르므로, 합의의 정렬이 바뀌면 소문 초안의 씨앗 차례가 바뀐다. 설계는 이 소비처를 "이 결과를 쓰는 곳" 목록에 넣지 않았고 기존 시험(소문 씨앗 차례를 단언하는 것)에 영향이 있는지도 밝히지 않았다. 또 "GM 지식 접힘, 에디터 미리보기"는 합의를 직접 부르지 않고 `QueryEngine`을 거치는 것으로 보이는데 그 경로가 적혀 있지 않다. | BR-V7-05를 "재정렬이 있어도 같은 키라 같은 결과"로 고치고, 소문 씨앗 차례가 바뀌는 영향과 소비처의 실제 경로(`QueryEngine`, `SessionKnowledgeService`, `RumorService`)를 적는다. | New |
| R-07 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-rules.md > PBT-V7-1; domain-entities.md § 1.2 | PBT-V7-1은 스코프 목록 순열에 대해 결과가 같다고 단언하지만, `compute_consensus`의 1~2단계는 `assigned` 때문에 같은 (지식, 지역) 스코프가 둘이면 목록의 먼저 나온 것의 확신도를 쓴다. 생성기가 같은 (지식, 지역) 쌍을 확신도를 달리해 두 번 낼 수 있으면 속성이 거짓이 된다. 저장소는 엣지를 쌍으로 MERGE하므로 실제 월드에는 없으나, 설계는 생성기가 쌍을 유일하게 내야 한다고도, 중복 시 규칙(예: 최댓값)도 적지 않았다. | 생성기가 (지식, 지역) 쌍을 유일하게 낸다고 적거나, 중복 스코프의 확신도 규칙을 BR-V7-02에 더한다. | New |
| R-08 | Minor | aidlc-docs/construction/V7-world-knowledge/functional-design/business-logic-model.md > § 4 1항; domain-entities.md § 4 | 빌더가 옛 스냅샷을 `WorldLoader.load`로 읽는다고 하나 `WorldBuilder`는 로더를 가지고 있지 않다(생성자는 `graph_repo, search_repo, cache`와 팩터리만 받는다). `WorldLoader(self._graph)`를 안에서 만드는지, 생성자 인자로 주입하는지가 없다. 주입이면 `WorldBuilder(` 호출 5곳(wiring.py, __main__.py, 시험 3곳)이 영향받는다. 사용자 메모리의 DI 선호와도 관련된다. | 로더를 어떻게 얻는지(내부 생성 또는 `from_factory`/생성자 인자 추가)와 영향받는 조립 지점을 한 줄로 정한다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `consensus.py` 4단계가 설계 서술(dict 순회 첫 출처, 쌍마다 `unknown_count`)과 같은가 | 125~152행이 서술과 일치 | RE-W01 재현 서술 OK |
| `persist_graph` 노드 일괄에 WorldMeta 포함, 엣지 뒤 색인 | 62~70, 85~98행 확인 | § 2.1 재정렬 설명 OK |
| `WorldCache`에 버전 없는 로더·`check_version=False` 경로 | `_current_version`이 `None` 반환, `test_cache.py` `_Loader`는 `version` 없음 | R-01 |
| `get_node`/`delete_node` 호출부 grep | production 12줄, 정의 4곳(base, neo4j_repo, fakes, test_services) | R-05 |
| `delete_held` 현재 흐름 | 노드 없음→unindex, 다른 라벨→`False` | R-02 |
| 세션 닫기 순서 | `_close_if_replaced`는 `replaced`일 때만, 빌드 뒤 | R-04 |
| WIKI_CONFLICT 탐지와 CONFIRM 적용 | 확신도 무관 탐지, CONFIRM은 `max(conf,0.9)` | R-03 |
| `WorldBuilder(`·`WorldFileImporter(` 생성 지점 | builder 5곳, importer 5곳 | R-08 |
| 데모 World File 중복 id | emberleaf.world.json 절 사이·안 중복 0 | § 5 검사가 데모를 막지 않음, OK |
| 요구사항·RE ID 해소 (FR-C6/7/8/9/10/12, RE-W01~W04·W18, R-02/05/06/08) | follow-up-requirements.md, code-quality-assessment.md, 설계 리뷰 01에서 모두 확인 | OK |
| 경계 행렬 (`carry_over.py`는 world, 로더는 knowledge) | shared ← knowledge ← world 안 | OK |
| 백업 설정 | `wiring.py`·`__main__.py`가 항상 `backup_dir` 주입 | "미설정은 통과"가 운영에서 조용한 비백업이 되지 않음, OK |

### Summary

핵심 흐름(합의 출처 고르기, 쓰기 순서, 백업 게이트, 이어 붙이기, 중복 id)은 코드와 상류 산출물에 잘 맞고 ID도 모두 풀린다. 다만 세 곳은 지금 동작을 새로 깬다: 마커 없는 캐시를 아예 캐시하지 않게 하는 규칙(R-01), `delete_held`가 라벨을 좁히면서 다른 라벨의 검색 문서를 지우게 되는 가지(R-02), WIKI_CONFLICT "유지"가 400이 되는 막다른 길(R-03). Major 셋이 닫히기 전에는 구현이 물어야 할 틈이 남는다. 제안(심사 사유 아님): 세션 닫기 서술(R-04)은 알려진 제약 절과 함께 한 번에 고치는 편이 좋다.
