## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Application Design — Follow-up cycle
**Reviewed artifact:** `aidlc-docs/inception/application-design/follow-up/application-design.md`
**Class:** advisory
**Iteration:** 1
**Date:** 2026-10-07T06:58:49Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/inception/application-design/follow-up/component-methods.md > 6 `TurnAdvancer.recover_interrupted`; services.md > S5; components.md > 7 lifespan | 끊긴 run 복구가 어떤 저장소 호출로 `running` run 목록을 얻는지 적혀 있지 않다. `PlayRepository`의 `TurnRunStore`(locus/play/ports.py:104-112)에는 세션 단위 `list_runs(session_id, status)`와 일괄 `fail_stale_runs(reason)`뿐이다. `recover_interrupted`는 세션을 가리지 않고 `running` run 전체를 읽어 `_fail`(advancer.py:508)과 같은 보상을 해야 하므로, 새 포트 메서드(예: 전 세션 `running` run 조회) 없이는 구현할 수 없다. 설계는 `fail_stale_runs`를 "대신" 부른다고만 하고(components.md §7) 그 메서드를 어떻게 할지(제거·유지, postgres_repo/memory_repo/계약 테스트 영향)도 말하지 않는다. | `TurnRunStore`에 추가할 조회 메서드의 시그니처를 component-methods에 적고, `fail_stale_runs`의 처리(제거 또는 유지)와 두 구현체·계약 테스트 영향을 밝힌다. `_fail`이 `exc`를 받는 점(`interrupted`를 어떻게 넘기는지)도 한 줄 적는다. | New |
| R-02 | Major | aidlc-docs/inception/application-design/follow-up/component-methods.md > 4 `WorldBuilder.build` / `BackupFailedError`; services.md > S4 | "백업이 실패하면 교체하지 않는다"의 판정 기준이 모호하다. 지금 `_backup`(build.py:364-381, import_.py:123-135)은 백업 미설정(`exporter`/`backup_dir`가 None)과 실패를 모두 `None` 반환으로 처리한다. 미설정까지 실패로 보면 `backup_dir` 없이 만드는 기존 빌더·테스트와 CLI 경로가 모두 깨지고, 실패만 보면 `_backup`이 둘을 구별해 돌려줘야 한다. 설계는 이 구별을 정하지 않았다. 또 S4는 옛 스냅샷을 `WorldCache`에서 읽는다고 하는데, 캐시는 WorldMeta 버전 일치 시 오래된 스냅샷을 줄 수 있어(cache.py:56-61) 직접 편집 직후의 NPC·씨앗을 놓칠 수 있다. 읽는 곳이 캐시인지 로더인지 정해야 한다. `WorldFileImporter`도 같은 `_backup`을 가진다. | (a) 미설정은 지금처럼 통과, 실패만 `BackupFailedError`로 중단하는지 아니면 미설정도 거절하는지를 밝히고, 빌더·임포터가 공유하는 `_backup`의 반환 계약(경로 / 미설정 / 예외)을 적는다. (b) 옛 스냅샷은 캐시를 무효화하거나 로더로 직접 읽는다고 명시한다. | New |
| R-03 | Minor | aidlc-docs/inception/application-design/follow-up/components.md > 6 "GM 쓰기 서비스들"; component-dependency.md > 4 | GM 쓰기 서비스가 `short_write`를 쥐려면 `TurnGuard`를 가져야 하는데, 지금 `EventService`, `SeedService`, `DistortionService`와 소문·행적 서비스는 guard 없이 만들어진다(play/wiring.py:125-148에서 guard를 받는 것은 `SessionService`, `PlayService`뿐). 생성자 변경(주입)이 설계 어디에도 없다. | 서비스에 guard를 주입한다고 component-methods §6에 적고, 영향받는 생성자(wiring 한 곳과 테스트 조립)를 밝힌다. | New |
| R-04 | Minor | aidlc-docs/inception/application-design/follow-up/component-methods.md > 6 `TurnGuard` ("is_running / running_run_id / assert_idle은 위 둘로 대체") | 대체되는 메서드의 호출부가 이름 없이 "V5에서 정리"로 넘어가 있다. 실제 호출부는 `play/player/service.py:78`(is_running), `play/session_service.py:115`(assert_idle), `api/routers/world.py:64`(is_running, 월드 교체 전 점검)이고 테스트 호출은 수십 곳이다. 특히 `world.py:64`는 GM 리스까지 "바쁨"으로 세던 점검인데, `turn_running`으로 바꾸면 GM 쓰기 중 월드 교체가 통과하고, 둘을 합치면 `gm_busy` 의미가 흐려진다. `api/errors.py`의 `http_error`는 `TurnInProgressError`를 isinstance로 409에 매핑하므로 서브클래스 `GmBusyError`가 별도 `code`를 받으려면 분기 순서(서브클래스 먼저)가 필요하다. 이 계약도 적히지 않았다. | `world.py` 점검이 어느 쪽 상태를 보는지, `close_session`이 GM 리스를 어떻게 다루는지(리스 공유 vs `short_write`만)를 한 줄로 정한다. 호출부 목록과 `ERROR_CODES`에서 서브클래스를 먼저 매기는 규칙을 component-methods에 더한다. | New |
| R-05 | Minor | aidlc-docs/inception/application-design/follow-up/components.md > 2 "그래프 포트"; component-methods.md > 2 | `get_node`/`delete_node`에 `label`을 더하고 "에디터와 삭제 경로는 늘 라벨을 넘긴다"고 하나 호출부를 세지 않았다. 코드에는 production 호출이 11곳(augmentation/apply.py:160,195,210,256; editor/regions.py:112,117,120; editor/writes.py:44,56,110,117; editor/bundle.py:54)이고 테스트용 구현체(`tests/shared/storage/fakes.py:134`, `tests/world/services/test_services.py:56`)의 시그니처도 바뀌어야 한다. | 호출부 수(11)와 테스트 대역 두 곳을 V7 영향 범위에 적는다. | New |
| R-06 | Minor | aidlc-docs/inception/application-design/follow-up/component-methods.md > 3 `compute_consensus` | 적힌 시그니처가 실제와 다르다. 실제는 `compute_consensus(region_id, *, snapshot=None, regions=None, connections=None, scopes=None, knowledge_by_id=None, params: ConsensusParams = DEFAULT_PARAMS)`(consensus.py:70-79)인데, 문서는 `snapshot_parts...`와 `params: KnowledgeTuning`으로 적었다. `best_origins`의 `region_direct`와 `exclude`가 어디서 나오는지도 호출부에 연결되지 않는다. | 실제 시그니처로 고치고, `best_origins`를 `compute_consensus`의 어느 단계에서 부르는지 한 줄 적는다. | New |
| R-07 | Minor | aidlc-docs/inception/application-design/follow-up/component-methods.md > 4 `remapped_id`; services.md > S3 | `remapped_id(target, old)`는 `uuid5`를 무조건 계산하지만 실제 `remap_ids`는 파일 안에 있는 id만 바꾼다(remap.py:38-42, `known`). 데모 번역 항목 가운데 `world` 종류의 id는 월드 id 자체이고 파일 id가 아니라서, 같은 함수를 그대로 쓰면 틀린 id가 시딩된다. 또 S3와 FR-L2 목록(지역·NPC·씨앗·월드)에는 `knowledge`가 없지만 `TranslationEntry.kind`와 Emberleaf 번역 파일(지식 23)에는 있다. | 재매핑은 `file_ids`에 있는 id만 한다는 규칙과 `world` 종류는 제외한다는 규칙을 적고, S3·번역 종류 목록에 `knowledge`(기존 종류)를 함께 적는다. | New |
| R-08 | Minor | aidlc-docs/inception/application-design/follow-up/component-methods.md > 2 `persist_graph`; components.md > 2 "저장 순서" | `WorldMeta`를 엣지·색인 "뒤"에 쓴다고 하나, 지금은 노드 일괄 upsert에 meta가 함께 들어가고(persistence.py:62-70) 엣지 실패나 색인 실패 때 early return한다(persistence.py:85-98). 순서를 바꾸면 이 실패 경로에서 meta가 안 써진 월드가 생기는데, 그 월드가 `WorldCache`에서 어떻게 보이고(버전 None → 캐시 안 함), 빌더가 `ok`를 어떻게 정하는지가 적혀 있지 않다. | meta 쓰기가 실패·early return 경로에서 건너뛰는지, 그때 리포트가 `ok=false`인지 한 줄로 밝힌다. | New |
| R-09 | Minor | aidlc-docs/inception/application-design/follow-up/application-design.md > 3 마지막 행 (FR-T3) ; components.md > 9 | mypy CI 게이트의 유닛이 둘로 걸쳐 있다. 설계는 "V1에서 11건을 함께 고치지 않으면 V9에서 켠다"고 조건부로 적었고, 실행 계획(follow-up-execution-plan.md 유닛 표)의 V1은 FR-T1만, V9가 FR-T2~T7이다. 조건이 설계 단계에서 닫히지 않아 Units Generation이 다시 정해야 한다. | V9로 확정하고 V1은 기존 4잡 녹색만 맡는다고 적거나, V1 포함을 택한다면 실행 계획을 바꾼다는 점을 밝힌다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 경계 주장: world·localization·play 사이 새 import 없음, `TranslationEntry`를 shared에 둠, CLI는 합성 루트 | tests/test_boundaries.py의 ALLOWED 행렬과 `COMPOSITION_ROOTS={"__main__","__init__"}`가 설계 설명과 일치. api는 검사 대상 아님 | OK. 설계가 새 경계 화살표를 만들지 않는다는 주장은 맞다 |
| `TurnGuard` 현재 API와 설계 비교 (`acquire`, `hold`, `is_running`, `running_run_id`, `assert_idle`) | guard.py에 모두 존재. `hold`는 턴만 거절하고 GM끼리 공유, `acquire`는 GM 리스도 거절 | OK. Q1·Q2의 전제(GM 공유, 턴 배타)는 현재 동작과 맞다. 호출부 정리는 R-04 |
| `is_running`/`assert_idle`/`fail_stale_runs` 호출부 grep | production 4곳(player/service.py:78, session_service.py:115, routers/world.py:64, main.py:120), 테스트 다수 | R-04, R-01의 근거 |
| `get_node`/`delete_node` 호출부 grep | production 11곳, 테스트 대역 2곳 | R-05 |
| `WorldBuilder._build`·`_backup`·`persist_graph` 읽기 | `_backup`은 미설정과 실패를 모두 None으로 반환, `delete_world` 뒤 persist, WorldMeta는 노드 배치에 포함 | R-02, R-08 |
| `WorldSnapshot`에 `npcs`, `event_seeds` 있음 | shared/models/io.py:75-76 | OK. `carry_over`가 옛 스냅샷에서 읽을 수 있다 |
| `DemoWorlds._check` 현재 검사 | 파일 파싱, 소스 존재, 시작 지역, 통과 연결만 본다. `name == world.id`는 없다 | OK. FR-C11을 V3에 두는 조정이 코드와 맞다 |
| 요구사항 ID 해소 (FR-C1~C14, FR-D1~D10, FR-L1~L4, FR-S1~S6, FR-T1~T7, NFR-8, C-2, A-1~A-3) | follow-up-requirements.md에서 모두 확인 | OK |
| RE-W03/W04/W18, RE-P03/P12 내용 대조 | code-quality-assessment.md의 설명이 설계가 닫는다고 한 내용과 일치 | OK |
| 유닛 배치(V1~V9) 대조 | 설계 §3의 V 배치가 실행 계획과 같고, FR-C11의 V7→V3 이동은 명시됨 | OK (R-09의 조건부 문장 제외) |
| Mermaid 문법 점검 (flowchart TB/BT, sequenceDiagram 5개) | 노드·화살표 문법 이상 없음, subgraph 닫힘. 텍스트 대안 각각 있음 | OK |
| 순환 의존 점검 (백엔드 행렬, 웹 내부 의존) | 두 그래프 모두 비순환 | OK |
| 설계 질문 Q1~Q6 답과 결정 표 | 계획 파일의 답이 모두 A이고, 결정 표의 내용과 모순 없음 | OK |

### Summary

경계 행렬, 요구사항·RE ID, 유닛 배치, 순환 여부는 코드와 상류 산출물에 맞고, Q1~Q6 결정과도 어긋나지 않는다. 구현자가 물어야 할 빈틈은 둘이다. 끊긴 run 복구에 필요한 저장소 조회가 설계에 없고(R-01), 백업 "실패"와 "미설정"의 구별 및 옛 스냅샷 읽는 곳이 정해지지 않았다(R-02). 나머지는 호출부 목록과 시그니처 정정 수준의 Minor이며 FD나 코드 계획에서 닫을 수 있다.
