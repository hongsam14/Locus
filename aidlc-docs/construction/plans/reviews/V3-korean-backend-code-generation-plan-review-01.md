## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 — V3 한국어 표시 백엔드
**Reviewed artifact:** `aidlc-docs/construction/plans/V3-korean-backend-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-07T14:43:03Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/V3-korean-backend-code-generation-plan.md > Step 5.2·5.5 (FR-C11) | 5.2가 "`file.world.id != info.name` → 항목 빠짐"을 더하면 지금 있는 테스트가 깨진다. `tests/world/test_demo.py`의 `_entry()`는 `file="emberleaf.world.json"`(world.id=`emberleaf`)에 `name="isle"`·`"no-start"`·`"cut-off"`·`"escape"`·`"lost-source"`·`"imaged"`를 붙이고(94-107행, 사용 12곳), `test_ex11_*`는 `demos.list() == ["isle"]`와 `len(problems) == 6`을 단언한다. FR-C11 뒤에는 이 항목들이 모두 이름 불일치로 빠지고 문제 문장이 늘어 5단계 커밋이 RED가 된다. 5.5는 새 테스트만 적고 기존 `_entry`/`_workdir` 보정은 없다. 개발자가 추측해야 한다. | 5.5에 기존 `tests/world/test_demo.py` 보정을 단계로 적는다. 예: `_workdir`가 World File 사본의 `world.id`를 항목 `name`에 맞춰 다시 쓰거나, 각 항목에 쓰는 파일을 이름별 사본으로 둔다. ex11의 문제 개수·문구 단언이 어떻게 바뀌는지(FR-C11 문제가 하나 더 생기는 항목은 따로 만든다)도 적는다. "단계는 그 단계의 테스트가 GREEN으로 끝난다"(계획 머리)와 맞춘다. | New |
| R-02 | Major | aidlc-docs/construction/plans/V3-korean-backend-code-generation-plan.md > Step 9.1·9.2, § 1.1 R-01 | CLI가 불러오기 뒤에 "한 줄을 찍는다"고만 적고 출력 채널이 없다. `_print_report`는 JSON 보고서를 stdout에 찍고(`locus/__main__.py` 약 110행), `tests/test_cli.py::test_demo_export_import_roundtrip_and_list`는 `json.loads(capsys.readouterr().out)`로 stdout 전체를 읽는다. 이 테스트의 fake_env는 `Settings.model_construct`(`translation_enabled` 기본 True)에 `sql_engine`이 없어 R-01의 "skipped (no database configured)" 갈래를 타고, 그 줄이 stdout에 붙으면 `Extra data`로 깨진다. `world demo`의 JSON-only stdout을 쓰는 호출자도 같은 위험이 있다. 9단계 커밋이 RED가 된다. | 9.1에 번역 줄은 **stderr**로 찍는다(stdout은 JSON 한 덩이로 유지)고 못 박고, 9.2에 "기존 `test_cli`의 stdout 파싱이 그대로 통과한다"를 검증으로 더한다. stdout에 두려면 기존 테스트를 어떻게 고치는지 적는다. | New |
| R-03 | Minor | aidlc-docs/construction/plans/V3-korean-backend-code-generation-plan.md > Step 8.1·9.1 | CLI는 `locus/__main__.py`이고 `tests/test_boundaries.py`의 `_violations()`는 `locus/**` 전체(`__main__` 포함)에서 `api` import를 위반으로 센다. 그래서 CLI는 8.1의 `purge_world_translations`·`seed_demo_translations`(`api/schemas.py`)를 쓸 수 없다. 9.1은 "지우기, 이어서 시딩"이라고만 하고 CLI가 무엇을 부르는지(`service.purge(world_id=w)` + `purge(kind="world", ids=[w])`, `demos.translations/texts`, `service.seed`, 언어 집합은 `settings.supported_langs`)를 적지 않는다. TP-V3-9의 "서비스 주입"이 `cli.assemble_localization`을 monkeypatch하는 것이라면 `__main__`이 그 이름을 모듈 수준으로 import한다는 말도 없다. | 9.1에 CLI가 직접 부르는 호출을 나열하고 api 도우미를 import하지 않는다고 적는다. TP-V3-9의 주입 지점(monkeypatch 대상 이름)을 적는다. R-01의 네 갈래를 검사하는 순서(설정 꺼짐 → 엔진 없음 → assemble 예외)도 한 줄로 정한다. | New |
| R-04 | Minor | aidlc-docs/construction/plans/V3-korean-backend-code-generation-plan.md > Step 8.2·8.5 | (a) 8.2의 데모 불러오기는 "`ok`면 시딩"인데 `loc`가 없거나 `loc.translations`가 `None`일 때 `demo.translations/texts`를 부르지 않는다는 말이 없다. `tests/api/test_world_api.py`의 가짜 `_Demo`(100-127행)에는 `translations`·`texts`·`card`가 없어, 시딩이 `loc` 확인 앞서 `demo`를 부르면 기존 테스트가 깬다. (b) 8단계는 커밋이 둘인데 테스트는 8.5 한 덩이이고 TP-V3-7은 시딩 결과(이름표 전부 ko)를 전제한다. 첫 커밋(이름표·목록 칸)의 테스트는 시딩 없이 저장소에 행을 직접 넣어야 하는데 이 구분이 없다. | 8.2에 "`loc`·번역 서비스가 없으면 `demo`의 새 메서드를 부르지 않는다"를 적고, 가짜 `_Demo` 보정이 필요한지 적는다. 8.5의 테스트를 두 커밋에 나눠 배정한다. | New |
| R-05 | Minor | aidlc-docs/construction/plans/V3-korean-backend-code-generation-plan.md > Step 3.4 | `wiring.py`는 지금 `shared.llm is None`이면 `translations=None`을 돌려준다(`locus/localization/wiring.py` 40-46행). 3.4는 이 분기를 "키 없는 서비스"로 바꾸지만, 어느 줄을 어떻게 고치는지(`store`가 주입돼도 LLM이 없으면 `None`이던 지금 동작, 실행기 `None`, `LocalizationContainer.close`) 적지 않았다. 실제로는 바뀌는 것이 한 분기라 위험은 작다(`assemble_localization`을 부르는 테스트가 없음은 확인). `api/main.py:88`의 기동에서 키 없는 서버도 이제 `ensure_schema`를 부르게 되는 행동 변경은 code-summary 알려진 한계에 한 줄 필요하다. | 3.4에 "LLM이 없어도 같은 분기에서 `Translator` 없이 서비스를 만든다, 기동 때 키 없는 서버도 `translations` 테이블을 만든다"를 적고 12.2 § 6에 올린다. | New |
| R-06 | Minor | aidlc-docs/construction/plans/V3-korean-backend-code-generation-plan.md > § 2 머리, "규모" | "커밋 13개 안팎"이라고 하나 단계별 커밋을 세면 1.1·1.3·2·3·4·5·6·7·8(둘)·9·11·12·10 = 14개다. 10단계(웹)는 11단계(불변) 앞에 있다. 승인이 이 커밋들의 허락이라고 했으므로 수가 어긋나면 사람이 승인 범위를 잘못 읽는다. | 수를 14로 고치거나 "안팎"을 뺀다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 계획이 가리키는 파일·심볼 존재 (`locus/localization/{service,models,wiring,__init__}.py`, `locus/world/worldfile/remap.py`, `locus/world/demo/{__init__.py,worlds/manifest.json}`, `knowledge/query.py`, `play/models.py`, `play/player/service.py`, `play/turn/advancer.py`, `api/{schemas.py,routers/world.py,world_editor.py,gm.py}`, `locus/__main__.py`, `web/src/{types.ts,api/world.ts}`) | 모두 존재. 새 파일(`shared/models/i18n.py`, `worldfile/texts.py`, `emberleaf.ko.json`)은 아직 없고 계획이 [새]로 밝힘 | OK |
| `tests/{shared,localization,world,api,play}/`, `tests/test_cli.py`, `tests/test_demo_as_data.py`, `web/src/__tests__/` | 존재 | OK |
| 상류 줄 참조 `component-dependency.md:18`·`:109`, `component-methods.md:221-225`, `components.md:79`, `unit-of-work.md` V3 | 줄 내용이 계획 § 1.1 R-02의 설명과 일치 | OK |
| FR-L2·L3·L4·FR-C11·NFR-5·6·8·9·A-1·A-2 해소 | `follow-up-requirements.md`에 모두 존재, § 3 대응표 완전 | OK |
| Emberleaf 123 항목 (`emberleaf.world.json`) | 월드 2·지역 24·NPC 45·씨앗 6·지식 46 = 123, 빈 필드 없음 | 일치 |
| `remap_ids.new()` · `file_ids` · `set_world_id` | `new()`가 `uuid5(NAMESPACE_LOCUS, f"{target}:{old}")`, 파일 안 id만 옮김. 4.2의 공개 함수 추출은 값을 바꾸지 않음 | 일치 |
| `purge` 필터 의미 (`memory_repo`·`postgres_repo`) | 필터 AND, 무필터 ValueError, `purge(world_id=w)`는 kind 없이 전 종류 삭제, `ids`가 있어야만 in-flight 키 정리 | 8.2·BR-V3-13과 일치. R-04(in-flight) 해소 방식(`seed`가 키를 뺌)도 실행 가능 |
| `enrich`/`_warm_inner`가 `self._translator`를 부름 | `translator=None`이면 예약 안 하는 가드가 필요(3.1이 명시) | OK, mypy 가드 필요 |
| 단계 순서 의존 (shared→localization→world→demo→ko 파일→api→CLI→web) | 앞 단계가 뒤 단계에 필요한 것을 먼저 만든다. 5단계 커밋 시점 매니페스트에는 `translations` 칸이 아직 없어 `check_packaged()`가 통과 | OK (단 R-01) |
| FR-C11 영향: `grep -rn "DemoWorlds(\|DemoInfo(" tests`, `tests/world/test_demo.py` 94-130행 | `_entry(name="isle")` 등이 `emberleaf.world.json`을 가리킴(world.id 불일치), ex11이 `problems == 6`을 단언 | R-01 확인 |
| CLI stdout 계약: `tests/test_cli.py` 52-56행, `_print_report` | `json.loads(capsys.readouterr().out)`로 stdout 전체를 읽음. fake settings는 `translation_enabled` 기본 True, `sql_engine=None` | R-02 확인 |
| 경계: `tests/test_boundaries.py` `_violations()` | `locus/**`는 `__main__` 포함 `api` import 금지. world↔localization 금지, `__main__`은 locus 내 경계 import 면제 | R-03 확인. `models/i18n.py`는 shared 안이라 안전 |
| `level_path` 호출 위치 | `query.py:51` 정의, `player/service.py:72`·`query.py:85`(RegionBrief)·`npc_drafts.py`. 계획은 `RegionView`만 바꾸고 `RegionBrief`는 안 건드림 | OK (가산, `level_path_ids`는 `RegionView`만) |
| `deed_seeded` 기록 (`advancer.py` 약 885행) | payload에 `npc_name`뿐, `npc_id`는 `appraisal.npc_id`로 바로 채울 수 있음. `npc_name`을 정확히 비교하는 테스트는 `test_dialogue`(`npc_talked`)·`test_deeds_api`(appraisals) 뿐 | 가산 안전 |
| `need_service`·`display_lang`·`WorldContainer.cache`·`WorldSnapshot`(`meta`·`npcs`·`event_seeds`·`topo.regions`) | 모두 존재, `cache`는 `SnapshotCache \| None` | 이름표 구현 가능 (R-03 FD 실행 메모와 일치) |
| 웹 `withLang`·`listDemos`·`listWorlds` | `withLang`은 서버 기본 언어와 같으면 쿼리를 붙이지 않음. 두 목록 함수는 지금 `withLang` 없음. URL 정확 비교하는 기존 vitest는 찾지 못함 | OK |
| FD 리뷰 01 R-01..R-08 → § 1.1 실행 메모 매핑 | R-01 → Step 9 네 갈래(출력 채널은 R-02), R-02 → Step 1.3·12.2 § 5 표, R-03 → Step 8·12.2 § 6, R-04 → Step 3·§ 6, R-05 → Step 3.4·§ 6, R-06 → Step 5 `_read_manifest` 흐름, R-07 → Step 3.3·8.4, R-08 → Step 3·8·11 | 구체적이고 실행 가능. 빠진 매핑 없음 |
| 5단계·9단계 GREEN 여부 | 5단계(R-01)와 9단계(R-02)는 기존 테스트가 깨질 수 있어 계획대로면 RED | 위 두 Major |

### Summary

접근과 근거는 타당하다. 파일·심볼·요구 ID·123 항목 수·FD 리뷰 R-01..R-08의 실행 메모 매핑이 모두 실제와 맞고, 단계 순서와 경계 규칙도 지켜진다. 다만 5단계(FR-C11이 기존 `tests/world/test_demo.py`의 이름 ≠ world.id 항목을 모두 빼 버림)와 9단계(번역 한 줄이 stdout JSON을 깨 `tests/test_cli.py`가 실패)는 계획 그대로면 커밋이 RED이므로, 승인 전에 두 Major를 단계에 적어야 개발자가 추측하지 않는다. Major가 둘이라 판정은 READY이지만 둘 다 고친 뒤 승인할 것을 권한다. 제안(판정과 무관): 이름표 첫 읽기의 warm 예약 비용은 FD 실행 메모대로 감수한 것이라 이 계획에서 다시 지적하지 않았다.
