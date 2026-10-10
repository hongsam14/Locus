# V7 월드·지식 정확성 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V7 코드 생성을 마쳤다(Step 1~10). 이제 다시 빌드하거나 월드를 불러와도 지식·NPC·사건 씨앗이 틀어지지 않는다.
- 지역 NPC가 아는 것은 가장 강한 출처에서 오고, 확실한 것부터 보인다.
- 교체 중인 반쪽 월드는 캐시되지 않는다.
- 백업이 실패하면 아무것도 지우지 않는다.
- 다시 빌드해도 NPC·씨앗이 남는다.
- 중복 id 파일은 거절한다.
- 노드는 종류(라벨)로 읽고 지운다.
- 보강 질문은 바꿀 수 있는 칸만 묻는다.

이 문서는 바뀐 것, 확인, 이탈, 알려진 한계, 다음에 넘기는 것을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V7-world-knowledge-code-generation-plan.md`(10단계, 승인 2026-10-11; 실행 메모 § 1.1~1.4 포함).

## 1. 기준선과 결과

| 항목 | 기준선 (Step 1.2, `c5601fc`) | 결과 (Step 10) |
|---|---|---|
| pytest | 1138 | **1194**(새 시험 56, 줄어든 시험 0). hypothesis 시드 둘(`3`, `21`)로 GREEN |
| ruff · black | clean | clean |
| mypy (`locus api`) | 11 | 11 |
| 웹 | vitest 664 | 바뀐 웹 없음(`git diff c5601fc..HEAD -- web` 비어 있음), vitest 664 그대로 |

게이트 스크립트는 이 세션의 scratchpad가 비워져 Step 1에서 다시 만들었다(`v7gate.sh`, 실행 메모 R-04의 명령 그대로).

커밋(8개 + 이 요약):

| 단계 | 커밋 | 내용 |
|---|---|---|
| 2 | `bc13544` | 합의: 가장 강한 출처, 모름은 지식마다 한 번, 목록마다 확실한 것부터 |
| 3 | `7e2c588` | WorldMeta는 마지막에 쓴다. 메타 없는 월드는 캐시하지 않는다. hit의 버전 읽기 실패는 miss로 다룬다 |
| 4 | `ed79465` | `get_node`·`delete_node`의 `label`, 호출부 9곳, 대역 셋 |
| 5 | `8ceefcc` | 중복 id World File 거절 |
| 6 | `2dfb923` | 백업 실패면 지우기 전에 멈춤(빌드·불러오기) |
| 7 | `c63d109` | 다시 빌드할 때 NPC·씨앗 이어 붙이기, 리포트 수, README 문장 |
| 8 | `4ae47d6` | 보강 입력 칸 (이슈, 대상) 열쇠, 무변경 답 거절, `kept_keys` |
| 9 | `aa64b3b` | 운영 문서 "Replace safety (V7)" |

## 2. 바꾼 파일과 만든 파일

**코드**

- 바꿈
  - `locus/knowledge/consensus.py`: `best_origins`, `_stronger`, `_confident_first`, 겹친 스코프의 최대 확신, `_TIE_DIGITS`.
  - `locus/knowledge/cache.py`: `UNVERSIONED`, 메타 없는 월드는 캐시하지 않음, hit 쪽 try.
  - `locus/knowledge/loader.py`: `NPC_HOME_DANGLING`, `SEED_REGION_DANGLING` 상수.
  - `locus/shared/storage/persistence.py`: WorldMeta를 마지막에 쓰고, 실패하면 `persist-meta` error.
  - `locus/shared/storage/base.py`, `neo4j_repo.py`: `label` 키워드, `_label_clause`.
  - `locus/shared/models/reports.py`: `BuildReport.carried_npcs`·`carried_seeds`, stage 주석.
  - `locus/world/build.py`: `BackupFailedError`, `backup_failed_warning`, 옛 월드를 새로 읽기, 이어 붙이기.
  - `locus/world/worldfile/import_.py`: 중복 id 검사, 백업 게이트, `_stopped`, `_duplicates`.
  - `locus/world/worldfile/remap.py`: `ID_SECTIONS`, `duplicate_ids`.
  - `locus/world/editor/{writes,regions,bundle}.py`: 라벨 있는 읽기·삭제. 라벨 없이 남는 곳에는 주석을 달았다.
  - `locus/world/augmentation/apply.py`: `UNCHANGED`, 무변경 검사를 쓰기 전에 함, 라벨.
  - `locus/world/augmentation/questions.py`: `NEEDS`를 (이슈, 대상) 열쇠로.
  - `locus/world/augmentation/types.py`: `AugmentationRun.kept_keys`.
  - `locus/world/augmentation/service.py`: 확인 답을 `kept_keys`에 넣고, 탐지에서 뺀다.
- 만듦: `locus/world/carry_over.py`(순수).

**시험**
- 새로 만든 파일
  - `tests/knowledge/test_consensus_props.py`
  - `tests/play/test_v7_order.py`
  - `tests/shared/storage/test_persist_order.py`
  - `tests/world/test_carry_over.py`
- 더한 파일
  - `tests/knowledge/{test_consensus,test_cache}.py`
  - `tests/shared/storage/test_port_contract.py`
  - `tests/world/editor/{test_region_delete,test_editors}.py`
  - `tests/world/augmentation/test_augmentation.py`
  - `tests/world/services/test_build.py`
  - `tests/world/worldfile/test_worldfile.py`
  - `tests/api/{test_world_api,test_world_editor_api}.py`
  - `tests/test_packaging.py`
- 대역
  - `tests/shared/storage/fakes.py`: (월드, 라벨, id) 열쇠와 라벨 인자.
  - `tests/world/services/test_services.py` `_GraphRepo`: 라벨 인자.
  - `tests/world/editor/helpers.py` `MeteredGraph`: 라벨 인자와 `calls_with`.

**문서**: `README.md` 7행, `aidlc-docs/operations/operations.md` "Replace safety (V7)".

## 3. 요구·규칙·시험 대응

| 요구 | 규칙 | 시험 |
|---|---|---|
| FR-C6 합의 | BR-V7-01~05 | TP-V7-1 (`test_tp_v7_1_*` 둘), TP-V7-2 (`test_tp_v7_2_*` 둘), TP-V7-3 (`test_tp_v7_3_each_list…`, `test_tp_v7_3_the_play_screens_facts…`), BR-V7-05 소문 씨앗 (`test_br_v7_05_rumor_seeds…`), PBT-V7-1~3 |
| FR-C7 캐시·저장 순서 | BR-V7-06~09 | TP-V7-4 (다른 프로세스 교체 중 읽기), TP-V7-5 (hit 버전 읽기 실패), R-02 (`check_version=False`), TP-V7-6 (쓰기 차례 넷) |
| FR-C8 백업 | BR-V7-10·11 | TP-V7-7 (빌드·불러오기), BR-V7-11 (백업 없는 빌더), 라우터 규칙 (`test_a_stopped_replace…`) |
| FR-C9 이어 붙이기 | BR-V7-12~16 | TP-V7-8 둘, TP-V7-9 둘, 규칙 시험 다섯, PBT-V7-4, PBT-02 (리포트 JSON 왕복), TP-V7-14 (README) |
| FR-C10 중복 id·라벨 | BR-V7-17~20 | TP-V7-10 둘, PBT-V7-5, TP-V7-11, TP-V7-12 (`calls_with`), 포트 계약 다섯 (Neo4j 질의 모양 포함) |
| FR-C12 보강 | BR-V7-21·22 | TP-V7-13 (서비스 둘, API 하나), R-09, S-1 둘, [두기]는 `ignored_keys`만 |

유닛 완료 조건:
- 연결 순서와 무관한 합의: PBT-V7-1.
- 교체 중 캐시: TP-V7-4.
- 백업 실패 뒤 옛 월드: TP-V7-7.
- 다시 빌드 뒤 NPC·씨앗: TP-V7-8.
- 중복 id 거절과 라벨 있는 삭제: TP-V7-10, TP-V7-11.
- 엔티티 질문의 제목 칸 없음: TP-V7-13.

## 4. 바뀐 기존 시험

- **1곳**: `tests/knowledge/test_cache.py::test_hit_is_refreshed_when_the_world_version_changes`의 끝부분(실행 메모 R-01).
  - 지금까지는 "메타 없는 월드는 무효화만"이어서, 메타 없는 월드를 캐시했다.
  - 이제는 "메타 없는 월드는 캐시하지 않음"이다. 두 번째 `get`도 새로 불러온다.
- 합의 차례가 바뀌었지만 기존 시험 가운데 깨진 것은 없다.
  - Step 2 뒤에도 1138건이 바뀌지 않고 통과했다.
  - 플랜이 걱정한 `test_npc_scope.py`, `test_dialogue.py`, `test_demo.py`, 소문 시험은 차례가 아니라 집합을 단언한다.
- 대역 셋이 라벨을 받게 바꿨고, 인메모리 그래프의 열쇠도 바꿨다. 이 때문에 깨진 시험은 없다.
  - `helpers.py`의 `_nodes.values()` 읽기는 그대로 돈다.
- `test_build.py`의 `_make`는 인자 `exporter`를 받는다. 기본값은 지금과 같다.

## 5. 이탈

1. **대역이 셋이다.** FD는 둘이라 했다. `MeteredGraph`가 셋째다(플랜 § 1.2).
2. **인메모리 그래프의 열쇠를 (월드, 라벨, id)로 바꿨다**(플랜 § 1.2).
   - 라벨 없는 삭제는 그 id의 모든 노드를 지운다. Neo4j와 같다.
   - 라벨 있는 삭제는 그 id의 노드가 하나도 남지 않을 때만 엣지를 지운다. Neo4j보다 느슨하다(§ 6).
3. **동률은 소수 9자리로 가른다**(`_TIE_DIGITS`, FD에 없음).
   - 같은 월드를 두 번 읽으면 경로곱과 확신이 마지막 비트에서 달라질 수 있다.
   - 출처 고르기와 목록 정렬이 이 잡음을 따르지 않게 한다.
   - 속성 시험의 연결 가중은 2의 거듭제곱이라 곱이 정확하다. 그래서 순서 무관을 정확한 같음으로 단언한다.
4. **`kept_keys`를 더했다**(세션 확인 S-1, FD에 없음, FD 승인 때 게이트에서 결정).
   - 위키 충돌의 확인 답과 값을 바꾸지 않은 확인 답은 같은 run에서 다시 묻지 않는다.
   - `ignored_keys`("무시한 질문")와는 따로 둔다.
5. **이어 붙이기를 계산하는 시점.** FD § 4는 온톨로지 뒤(⑤)에 계산한다고 했다.
   - 코드는 옛 월드를 읽은 직후, 백업 앞에서 순수 함수를 부른다.
   - 경고는 본체를 쓸 때(⑥) 리포트에 더한다. 그래서 백업이 실패해 멈춘 리포트에는 이어 붙이기 경고가 섞이지 않는다.
   - 결과(새 지역 id)는 같다. 새 지역은 준비 단계에서 이미 정해져 있다.
6. **멈춘 리포트를 만드는 곳.** 백업 실패와 중복 id 리포트는 불러오기의 `_stopped` 한 곳에서 만든다. 백업 실패 문장은 빌드와 불러오기가 `backup_failed_warning`을 함께 쓴다.

## 6. 알려진 한계

- FD에서 넘어온 것
  - WorldMeta가 없는 옛 월드(U2 이전)는 캐시되지 않아 읽을 때마다 불러온다(운영 문서에 적음).
  - 이미 저장된 옛 중복 id는 남는다. 라벨 없는 세 곳이 그 경우 모호하다.
  - 이름이 바뀐 지역의 NPC·씨앗은 이어 붙지 않는다. 경고로 알리고, 백업에 남는다.
- 인메모리 대역의 엣지는 라벨이 없다. 라벨 있는 삭제가 지운 노드의 엣지를, 같은 id의 다른 노드가 남아 있으면 지우지 않는다. 실제 Neo4j의 동작은 운영자 확인으로 넘긴다(§ 8).
- 옛 월드 읽기와 백업 사이의 편집
  - 다시 빌드의 커밋 단계는 옛 월드를 읽은 뒤 백업한다.
  - 그 짧은 틈에 에디터로 더한 NPC는 이어 붙지 않고 백업에만 남는다.
  - 빌드는 몇 분의 LLM 작업 뒤에 커밋하므로, 틈 자체는 커밋 순간의 수 밀리초다.
- `kept_keys`
  - 되살리기가 없다.
  - 낮은 확신 지식을 같은 값으로 확인하면 그 run 동안 다시 묻지 않는다. 새 run은 다시 묻는다.

## 7. 돌연변이 확인

고친 곳마다 고치기 전 동작으로 되돌린 코드에서 새 시험이 실패하는지 봤다. **36개 모두 잡혔다.**
- 둘(Step 4의 g, h)은 첫 실행에서 살아남았다. 시험을 조인 뒤 잡혔다.
- 단계별 결과

| 단계 | 돌연변이 | 결과 |
|---|---|---|
| 2 합의 | 처음 만난 출처, 쌍마다 세기, 직접 목록 정렬 빼기, 겹친 스코프 먼저 온 것, 동률 id 빼기 | 5/5 |
| 3 저장·캐시 | 메타를 노드 묶음에, `None` 캐시, hit try 빼기, `check_version=False`에 `None` 저장 | 4/4 (TP-V7-4 혼자서도 옛 순서를 잡음) |
| 4 라벨 | 씨앗·NPC·지역 삭제, `delete_held` 읽기·삭제·뒷정리, `node()`, 다시 가리키기, 되돌리기 검사, 더한 노드 삭제, Neo4j 읽기·삭제 | 12/12 (g `node()`, h 다시 가리키기: 첫 실행 생존 → 시험 조임 → 잡힘) |
| 5 중복 id | 검사 빼기, 절 안만 보기 | 2/2 |
| 6 백업 | 빌드가 실패를 삼킴, 일반 except가 받음, 불러오기가 실패를 삼킴 | 3/3 |
| 7 이어 붙이기 | 무효화 없이 캐시 읽기, 부모 가르기 빼기, 로더가 버린 것 숨김, 붙인 것 안 씀, 읽기 실패에도 진행 | 5/5 |
| 8 보강 | 같은 값 걸러내기 빼기, `kept_keys` 안 씀, 엔티티에 제목, 확인 없이 keep, 엔티티 `needs`에 제목 | 5/5 |

## 8. 다음에 넘김

- **V8 에디터**
  - 빌드 리포트에 이어 붙인 수(`carried_npcs`, `carried_seeds`)를 보이고, `web/src/types.ts`에 두 칸을 더한다.
  - 경고 stage(`backup`, `carry-over`, `duplicate-ids`, `persist-meta`)의 한국어 이름을 정한다. 지금은 `[stage] message` 원문 그대로 보인다.
  - 보강 패널에서 `kept_keys`를 보일지 정한다.
  - V6에서 넘어온 둘: 월드 교체의 "busy" 경고 문장, `SessionBar` `variant="full"` 정리.
- **B&T 운영자 확인**
  - 실제 Neo4j에서 라벨 있는 삭제를 본다. 같은 id의 지역과 씨앗을 손으로 만든 뒤, 지역 삭제 경로로 씨앗만 지워지는지 확인한다.
  - CLI로 다시 빌드하는 동안 API가 읽어도 반쪽 월드를 캐시하지 않는지 본다. 다시 빌드 뒤의 첫 읽기에 연결이 있어야 한다.
  - 백업 디렉터리를 쓰기 금지로 둔 채 교체하면 `stage backup`으로 멈추고 옛 월드가 남는지 본다.
