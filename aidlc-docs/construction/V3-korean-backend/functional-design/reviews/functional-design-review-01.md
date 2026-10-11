## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — V3 한국어 표시 백엔드
**Reviewed artifact:** aidlc-docs/construction/V3-korean-backend/functional-design/business-logic-model.md (함께: business-rules.md, domain-entities.md)
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-07T14:31:48Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | business-logic-model.md > § 4 CLI; business-rules.md > BR-V3-28, TP-V3-9 | "PostgreSQL 닿음? (assemble_localization이 서비스를 만들었나)"로 DB 도달 여부를 가른다고 적었으나, 실제 `assemble_localization`은 SQL 엔진이 있으면 곧바로 `pg.ensure_schema()`를 부르고(locus/localization/wiring.py:40-41), 엔진은 `make_engine`으로 게으르게 만들어져(locus/shared/wiring.py `_sql`) DB가 안 닿아도 `sql_engine`은 None이 아니다. 닿지 않으면 `None`이 아니라 예외가 난다. CLI는 `assemble_shared(..., llm=False)`를 strict로 부르고 `_try` 감싸개가 없으므로(api/main.py의 `_try`와 다름) 예외가 `world demo`를 죽인다. 그러면 BR-V3-28의 "skipped (database unreachable) 한 줄, 종료 코드 0"이 구현될 수 없다. 이미 불러오기는 끝난 뒤라 종료 코드도 거짓이 된다. TP-V3-9는 서비스를 주입하므로 이 경로를 잡지 못한다. | CLI가 `assemble_localization`(또는 `ensure_schema`)의 예외를 잡아 "skipped" 한 줄로 바꾸는 규칙을 BLM § 4와 BR-V3-28에 적는다. `sql_engine`이 None인 경우("off"와 구별)도 정한다. TP-V3-9에 "저장소가 예외를 던지면 skipped, 종료 코드 0" 사례를 더한다. | New |
| R-02 | Major | business-rules.md > BR-V3-21; domain-entities.md > 결정 표 Q5, § 2, § 6; 상류 component-dependency.md:109, components.md:79, component-methods.md:96-97·167-169·221-225, unit-of-work.md > V3 코드·완료 조건 | 승인된 설계에서 벗어난 것이 한 문장(BR-V3-21 "Q5=A")과 § 2 일부로만 적혀 있고 추적이 불완전하다. (1) V3→V4 계약(component-dependency.md:109: `region_name_ko`, `npcs[].name_ko`…)과 component-methods.md:221-225의 `RegionViewOut.region_name_ko`·`SeedViewOut.title_ko`·`NpcOut` 칸이 더 이상 만들어지지 않는데, 어느 줄이 무효가 되는지 나열하지 않는다. V4·V6·V8 설계가 옛 계약을 읽으면 존재하지 않는 칸을 쓴다. (2) unit-of-work.md V3의 코드 목록(`api/routers/{play,gm,world_editor}.py` "번역 칸")과 완료 조건("API 응답의 지역·NPC·지식·씨앗·월드·데모 카드가 ko로 나온다")은 이제 "이름표와 목록 칸으로 나온다"로 바뀌는데 이 변경이 적혀 있지 않다. (3) § 2는 `TranslationEntry`의 `lang`·`source_hash` 제거만 밝히지만, 같은 설계 문서와 달라진 다른 점도 있다: `SeedReport`의 `missing`→`unknown`(component-methods.md:169), `seed`에 `world_id` 추가, `DemoWorlds.translations(name, lang)`에 `target_world_id`·`remapped` 추가(component-methods.md:155), component-dependency.md:18이 api가 `remapped_id`를 쓴다고 한 것과 달리 world 안(`DemoWorlds`)에서 쓰는 것. | domain-entities.md(또는 BLM 머리)에 "승인된 설계와 달라지는 것" 표를 한 개 둔다. 각 줄에 상류 파일·줄, 달라지는 내용, 근거(Q5=A, 계획의 스스로 정한 것), 영향받는 유닛(V4/V6/V8)을 적는다. 위 (1)~(3)을 모두 담고, unit-of-work.md V3 완료 조건을 이름표 기준으로 바꿔야 한다는 점을 Units/요구 쪽 후속 조치로 명시한다. | New |
| R-03 | Minor | business-logic-model.md > § 8 이름표; domain-entities.md > § 6.1 | 이름표는 `world.cache.get(w)`를 쓰는데 `WorldContainer.cache`는 `SnapshotCache \| None`이고(locus/world/wiring.py:28) 캐시가 없을 때의 응답이 없다. 또 한 번 읽을 때마다 월드 전체(지역·NPC·씨앗 모든 필드)의 미스를 warm에 넘기므로, 키가 있고 큰 월드면 첫 읽기 한 번이 수백 건의 LLM 번역을 예약한다. 상한이 없다. | 캐시 없음일 때 응답(503 또는 빈 맵)을 정한다. warm 예약 건수 상한 또는 "시딩된 월드는 예약하지 않음" 중 하나를 정하고 한 줄 적는다. | New |
| R-04 | Minor | business-rules.md > BR-V3-15; business-logic-model.md > § 3 | "데모 번역은 예전 LLM warm 결과보다 앞선다"고 하나 보장하는 것은 시딩 시점의 덮어쓰기뿐이다. 키가 있을 때 시딩 전에 이미 `_in_flight`에 있던 같은 키의 warm이 시딩 뒤에 끝나면, 원문이 같아 해시가 맞는 한 LLM 번역이 손으로 다듬은 행을 덮는다(`purge(world_id=…)`는 in-flight 키를 잊지 않는다: service.py `purge`는 `ids`가 있을 때만 정리). | 규칙을 "시딩은 그 시점의 행을 덮는다"로 좁히거나, 시딩이 해당 키를 in-flight에서 빼는 한 줄을 더한다. 어느 쪽이든 알려진 한계로 적는다. | New |
| R-05 | Minor | domain-entities.md > § 1 첫 줄 | 캐시 키에 `world_id`가 없는 근거를 "source id는 UUID"(locus/localization/models.py 독스트링)에 두었다. 재매핑하지 않은 데모·World File은 `region-saltwake`·`npc-brisa` 같은 비UUID id를 그대로 쓴다. 파일의 `world.id`가 서로 다른 두 월드가 같은 항목 id를 쓰면 키가 충돌해 서로의 행을 덮는다(해시가 어긋나 화면은 영어로 떨어질 뿐 틀린 말은 안 보이지만, 번갈아 덮는다). 이 전제가 더 이상 참이 아니라는 말이 없다. | "id는 월드 안에서만 유일, 월드 사이 충돌은 해시가 막고 번갈아 덮는 비용만 남는다"를 알려진 한계로 적는다. | New |
| R-06 | Minor | business-rules.md > BR-V3-12 vs BR-V3-10, Q3=A | Q3=A는 "실행은 너그러움, 번역 문제로 데모를 잃지 않는다"인데, BR-V3-12는 `translations`·`i18n` 키 형식이 틀리면 항목 전체를 목록에서 뺀다. 같은 번역 문제인데 한 가지는 항목을 빼고 나머지는 남긴다. 구현자가 어느 쪽인지 추측해야 한다. 또 `_check`는 지금 `str \| None` 하나를 돌려주는 구조라(locus/world/demo/__init__.py:150) 항목을 남기면서 문제만 여럿 더하는 `_check_translations`가 `_read_manifest`의 어디에 끼는지(`if problem: … elif`) 적혀 있지 않다. | BR-V3-12가 Q3=A의 예외임을 밝히고 까닭을 적거나, 키 형식도 problem만 더하고 그 언어만 버리게 한다. `_read_manifest` 흐름 변경(항목 유지 + problems 추가)을 BLM § 6.1에 한 줄 적는다. | New |
| R-07 | Minor | business-logic-model.md > § 10, § 3 끝 | `carry`의 시그니처가 domain-entities.md에 없고 BLM § 10 의사코드에만 있다. `carry` 실패(저장소 오류)를 삼키는지, 시작 응답을 깨는지도 적혀 있지 않다(시딩·purge는 "기록만 남김"으로 적혀 있음). `start_seed`는 `create_event` 뒤에 `carry`를 부르므로 예외가 나면 사건은 만들어졌는데 5xx가 나간다(api/routers/gm.py:287-298). | `carry`를 domain-entities § 5에 시그니처와 함께 적고, 실패는 기록만 하고 응답을 깨지 않는다고 BR-V3-17에 더한다. TP-V3-10에 실패 사례를 더한다. | New |
| R-08 | Minor | business-rules.md > TP-V3-12, TP-V3-7, BR-V3-02 | 테스트 계획의 빈틈이다. (a) TP-V3-12 "그래프·검색 저장소에 쓰기 호출이 없다"는 불러오기 자체가 그래프를 쓰므로 그대로는 거짓이다. 시딩 단계의 쓰기만 센다고 해야 한다. (b) 시딩·purge 실패가 불러오기 응답을 깨지 않는다(BLM § 3 항목 5)는 규칙이 TP에 없다. (c) LLM이 있을 때 이름표가 빠진 항목을 warm에 넘기는 경로(BR-V3-22 끝)와 BR-V3-02의 "LLM 있으면 지금처럼"이 TP-V3-6에서 한쪽만 확인된다. (d) 키 없는 서비스에서 `enrich`가 스케줄을 부르지 않는 것은 코드 변경이 필요한데(`_warm_inner`가 `self._translator.try_translate`를 부른다, service.py) 생성자 시그니처(`translator: Translator`)를 `Translator \| None`으로 바꾼다는 말이 모델에 없다. | TP-V3-12 문구를 바로잡고, 실패 주입 사례와 LLM 있음 사례를 TP-V3-7·6에 더한다. `TranslationService`의 생성자 변경을 BLM § 2에 한 줄 적는다. | New |

### Checks Run

| Check | Result |
|---|---|
| 리맵 규칙 vs 실제 코드 (`locus/world/worldfile/remap.py` `new()`/`file_ids`, `import_.py:56-57`) | 일치. `new()`가 `old not in known`이면 그대로 두므로 BLM § 5의 "파일 안 id만"과 같고, `remapped = force_remap or source != target`이라 `ImportReport.remapped`를 그대로 쓰는 판단도 맞다. `world` 종류는 `file_ids`에 없으므로 별도 규칙(BR-V3-19)이 필요한 것도 맞다 (R-07 설계 리뷰 종결 확인) |
| 해시 규칙 vs `locus/localization/service.py` `source_hash`/`_cached` | `sha256(strip)`와 행의 `source_hash` 대조가 그대로이고, 이동 후 값이 같아 기존 행이 맞는다 |
| purge 필터 의미 (`postgres_repo.py purge`) | 모든 필터 AND, 필터 없음 ValueError, 빈 `ids` 0행. `purge(world_id=w)`는 `kind` 없이 전 종류를 지우고, 세션 내용(rumor·event)은 `enrich`가 `session_id`만 적으므로(api/schemas.py `localize_query_result`, gm.py `_events_out`) 걸리지 않는다. BR-V3-13과 일치 |
| 순서 import → purge → seed | `_after_replace`(api/routers/world.py:90-104)가 세션 닫기 뒤 purge이고 데모 경로(world.py:386)도 이를 부른다. 시딩을 그 뒤에 두는 것이 가능하다 |
| 경계 | `tests/test_boundaries.py`: world는 shared·knowledge·world만, localization은 shared만, `__main__`·`__init__`은 합성 루트로 면제. shared `models/i18n.py`를 두 경계가 쓰는 구조는 규칙에 맞는다. api는 `locus/**` 밖이라 제약이 없다 |
| 에뮬리프 123개 계산 | `emberleaf.world.json`에서 지역 12, NPC 15, 씨앗 3, 지식 23, 지식 `title` 23/23 비어 있지 않음, 빈 필드 없음을 확인했다. 2+24+45+6+46=123 일치 |
| 시간선 payload의 id 동반 주장 | player_moved·waited·npc_talked·session_started·set_distortion·deed_spread는 `region_id`(·`npc_id`)가 이미 있다. `deed_seeded`(advancer.py:885)만 `npc_name`뿐이라 `npc_id` 추가는 맞다. `RegionView.level_path`(play/models.py:391)도 이름뿐이라 맞다. 같은 이름 목록을 가진 `RegionBrief.level_path`(io.py:191, `GET /worlds/{w}/briefs`)는 설계가 다루지 않는다(화면 사용 여부 미확인, 질문으로 남김) |
| 에디터 purge 지점 | `RegionDeleteReport.deleted_ids`(editor/models.py:44)가 있고, `delete_npc` 라우터(world_editor.py:272)는 지금 `loc` 의존이 없어 추가가 필요하다(설계가 "NPC 삭제는 그 NPC를 지운다"고 적어 구현 가능) |
| 씨앗 → 사건 | `seeds.py:62`가 `description=seed.description or seed.title`이고 `start`의 호출처는 gm.py:295 하나라 carry 지점이 한 곳이면 된다 |
| 패키지 데이터 | pyproject `world/demo/worlds/*.json` 글롭이 `emberleaf.ko.json`을 덮는다 |
| 상류 ID 해소 | FR-L2·L3·L4·FR-C11·NFR-5·6·8·9, A-1·A-2, S3, 설계 리뷰 R-07 모두 존재한다. R-02의 상류 줄 번호 확인함 |
| Mermaid (BLM § 3) | participant·alt/loop/end 구문 정상 |
| 키 없는 NFR-9 경로 | 서비스가 LLM 없이 만들어지면 `loc.translations`를 쓰는 곳은 `api/schemas.py`뿐이라 다른 소비처의 가정 위반은 없다. 단 R-01(CLI)과 R-08(d) 참조 |

### Summary

접근은 타당하다. 재매핑·해시·purge 필터·순서가 실제 코드와 맞고, 경계 규칙을 지키며, 123이라는 수도 맞다. 키 없는 서비스라는 빠진 전제를 스스로 찾아 계획과 BR-V3-02에 적은 점은 NFR-9에 필요한 일이었다. 막는 항목(Critical)은 없고 Major가 둘이어서 READY이지만, 둘 다 승인 전에 고쳐야 구현이 추측 없이 된다.

- R-01은 CLI의 "DB 안 닿음" 분기가 현재 wiring에서는 예외로 나타나므로 문서대로 구현하면 `world demo`가 불러온 뒤에 죽는다.
- R-02는 사람이 정한 Q5=A 이탈이 정당하지만, 상류의 어느 줄이 무효가 되는지와 V3 완료 조건 변경이 적혀 있지 않아 V4·V6·V8이 옛 칸(`region_name_ko` 등)에 기댈 위험이 있다.
- Minor R-03~R-08은 한 줄 규칙이나 테스트 문구 보강으로 닫힌다.

제안(판정과 무관): 이름표는 화면 쪽에서 한 번 받아 세션 동안 들고 있게 하면 읽기 부담이 작다. 이 점은 V4 FD에서 정할 일이다.
