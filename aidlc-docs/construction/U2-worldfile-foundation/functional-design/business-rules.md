# U2 World File·캐노니컬 기반 — Business Rules

번호는 `BR-U2-n`. 근거 열의 Q는 FD-U2 답, A는 플랜의 가정, RE는 `reverse-engineering/code-quality-assessment.md`.

## 1. World File
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U2-1 | 파싱 입구는 `WorldFile.parse(raw)` 하나다. 지원 버전은 `format_version=1`. `format_version`이 없으면 v0(옛 export)으로 읽는다: `world.id`는 파일의 최상위 `world_id`(없으면 "월드 파일이 아님"으로 422), `name=world.id`, 빠진 절은 빈 목록. 그 밖의 버전 값은 거절(422, 지원 목록 포함) | Q1=A, 버전 가정, R-01 |
| BR-U2-2 | 알 수 없는 필드는 무시한다(상위 호환). 절 안 항목의 필수 필드가 빠지면 그 파일은 거절(422)한다 — 절반만 읽지 않는다 | 버전 가정 |
| BR-U2-3 | export는 모든 절을 BLM §6의 정렬 키 표(regions·entities·knowledge·priors·npcs·relations=`id`; connections=`(source_region_id, target_region_id, kind)`; scopes=`(knowledge_id, region_id)`; prior_links=`(source_id, target_id, relation)`)로 정렬하고 `json.dumps(sort_keys=True, indent=2)`로 쓴다. 저장소의 반환 순서에 기대지 않는다. `exported_at`은 비교에서 제외한다 | PBT-02, R-05 |
| BR-U2-4 | `file.world.id == 대상 world_id`이고 `force_remap`이 아니면 모든 id를 보존한다. 다르면 `uuid5(NAMESPACE_LOCUS, f"{target}:{old}")`로 **모든 id와 참조**를 재매핑하고 `world.id`와 모든 `world_id`를 대상으로 바꾼다. 재매핑은 결정적이며 재매핑된 파일에 다시 적용하면 항등이다. 저장 중 다른 월드와의 id 충돌(유일 제약 위반)은 error 경고 `id collision with another world; retry with remap=true`로 리포트한다(`ok=False`). `ImportReport.remapped/forced`에 기록 | Q1=A, R-01, R-02 |
| BR-U2-5 | import 전 참조 검증: 없는 대상을 가리키는 스코프·연결·관계·NPC(`home_region_id`)·`parent_id`는 항목을 버리고 error 경고를 남긴다(그 항목만; 파일 전체는 진행). `ok=False` | Q4=A |

## 2. 수집·병합·해석
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U2-6 | `merge_regions`: 키 (정규화 이름, 레벨). 리스트 속성(`adjacent_names`, `connections`)은 순서 보존 합집합, 스칼라 속성은 첫 값 유지 + 다르면 warning. 연결 후보와 `parent_name`은 병합 뒤에 남는다 | A1, RE A1 |
| BR-U2-7 | `merge_entities`: 키 (정규화 이름, entity_type). `id_map`을 돌려주고, 관계·`about_entity_ids`·`located_in`은 `id_map`으로 재작성한다. 재작성 뒤에도 끊긴 참조는 warning + 제거 | A2, RE A2 |
| BR-U2-8 | 이름 해석은 `resolve_region` 하나로: (a) 레벨이 주어지면 (이름, 레벨) 정확 일치, 없으면 붙이지 않음; (b) 후보가 하나면 그것; (c) 부모 역할이면 자식보다 상위 레벨 후보 중 가장 가까운 레벨; (d) 힌트 역할(연결·지식)이면 가장 구체적인 레벨; (e) 동률은 (이름, id) 정렬의 첫 항목. (c)(d)(e)는 warning을 남긴다 | Q3=A, RE A11 |
| BR-U2-9 | 지역 레벨 순위는 `topology/naming.py`의 명시 표 `LEVEL_RANK = {continent: 0, province: 1, town: 2, district: 3}`다(enum 선언 순서에 기대지 않는다; district는 town 안의 구역). `terrain`은 위계 레벨이 아니라 표에 없고, 모호성 해소에서 제외되며 정확 일치·유일 후보일 때만 붙는다. 부모 해석은 후보가 하나여도 상위 레벨 검사를 한다. enum에 위계 값이 추가되면 `test_level_rank_covers_every_hierarchy_level`이 실패한다 | Q3=A, R-03, R-10 |
| BR-U2-10 | base64 이미지가 유효하지 않으면 그 입력만 error 경고로 남기고 나머지 입력은 처리한다 | A7 |

## 3. 빌드
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U2-11 | 월드 존재 여부는 `world_id in graph.list_world_ids()`. `replace=False`이고 월드가 있으면 아무것도 쓰지 않고 `WorldExistsError`(409). `replace=True`면 **준비 단계(수집·토폴로지·prior 증류)를 그래프를 건드리지 않고 먼저 끝내고**, 커밋 단계에서 옛 월드를 `backup_dir/{world_id}-{UTC timestamp}.world.json`으로 내보낸 뒤(실패는 warning) 그래프·검색의 그 `world_id`를 지우고 저장한다(`replaced=True`). 준비 단계 실패는 옛 월드를 건드리지 않는다. 커밋 단계 실패는 부분 저장을 남기며 리포트가 `ok=False, replaced=True`로 드러낸다; 캐시 무효화는 `finally`로 항상 한다 | A3, RE A3, R-04 |
| BR-U2-12 | 빌드는 NPC를 만들지 않는다. NPC의 `home_region_id`는 저장 시점의 스냅샷에 존재하는 지역이어야 한다(import·편집이 검증) | FR-F3, Q7 |
| BR-U2-13 | 경고 등급: **error** = persist-graph/persist-search 실패, 입력 하나가 통째로 안 읽힘, 지역 0개; **warning** = 항목 단위 거절, 미해석 힌트·지식, 임베딩 실패, 계층 경고, 속성 충돌. `ok = error 없음`. CLI는 ok가 아니면 종료 코드 1 | Q4=A, RE A13 |
| BR-U2-14 | 스코프 못 한 지식은 저장하고 `unscoped_knowledge_ids`에 싣는다. 어떤 합의 뷰에도 나오지 않지만 스냅샷과 에디터에는 보인다 | A4, RE A4 |
| BR-U2-15 | `llm_calls`는 그 빌드의 LLM·VLM 호출 수, `embedding_calls`는 임베딩 호출 수. 카운터는 빌드마다 새로 만든다 | NFR-5 |

## 4. 로더·캐시·질의
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U2-16 | 로더는 매핑에 실패한 노드·엣지를 건너뛰고 경고(`load_warnings`)로 남긴다. 한 노드가 월드 전체 로드를 막지 않는다 | U1 리뷰 #2 |
| BR-U2-17 | `WorldCache`는 프로세스 메모리, 명시적 무효화만. 무효화 호출점은 빌드·import·데모 로드·에디터 쓰기·증강 적용/되돌리기(빌드·import는 `finally`). 로드는 락 밖에서 하고 월드별 세대 번호로 "로드 중 무효화 → 결과를 캐시에 넣지 않음"을 지킨다. 단일 워커 전제(문서·compose) | Q6=A, R-11 |
| BR-U2-18 | 스냅샷은 공유 불변 객체다. 읽는 쪽은 바꾸지 않는다; 쓰기는 그래프에 하고 무효화한다 | Q6=A |
| BR-U2-19 | `KnowledgeView.title`은 `Knowledge.title`을 그대로 넣는다(비어 있으면 `fallback_title`) | A8 |
| BR-U2-20 | `region_briefs`: 지역마다 이름·레벨 경로·설명·DIRECT 지식 title 상위 k(확신도 내림차순, 동률 id 순). 지식 없는 지역도 포함 | briefs 가정 |

## 5. NPC·메타·검색
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U2-21 | NPC는 `:NPC` 노드 + `LIVES_IN` 엣지로 저장하고, 검색 문서(`SearchDoc.label="NPC"`, 텍스트 = 이름·역할·설명)로도 색인한다. `delete_world`는 둘 다 지운다 | Q7=B, R-08 |
| BR-U2-22 | `traits`는 짧은 영어 태그 목록. 비어 있어도 된다 | Q7 |
| BR-U2-23 | `WorldMeta`는 월드당 1개(`id=world_id`). 빌드·import·편집이 `updated_at`·`last_writer`를 갱신한다. 없으면 export가 기본값으로 채운다 | Q2=A |
| BR-U2-24 | 월드 목록은 `list_world_ids` ∪ WorldMeta id. 메타 없는 월드는 `name=id`, `updated_at=None` | Q2=A |

## 6. 교체와 세션 (경계를 잇는 규칙)
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U2-25 | 월드를 교체(빌드·import·데모)하기 전에 라우터가 play 경계에 열린 세션 수를 묻는다. 1개 이상이고 `confirm=true`가 아니면 409 `{open_sessions: n}`. confirm이면 세션을 닫고(`SessionService.close`) 진행하며 닫은 id를 리포트에 싣는다. play 경계가 없으면 묻지 않는다 | NFR-9, services §3.1 |
| BR-U2-26 | CLI는 같은 상황에서 `--force` 없이는 종료 코드 1과 안내를 낸다 | NFR-9 |
| BR-U2-27 | world 경계는 play를 import하지 않는다. 세션 닫기는 라우터·CLI(조립 루트)만 한다 | 경계 행렬 |

## 7. 데모
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U2-28 | 데모 월드는 패키지 안의 World File v1에서 로드한다. 로드 경로는 LLM을 호출하지 않는다(임베딩은 제공자가 있을 때만; 없으면 텍스트 색인만) | Q5=A, FR-B3, NFR-4 |
| BR-U2-29 | 데모 파일은 손으로 작성한 결정적 내용이다(Aldermoor: 지역 5, 연결 1, 지식 8~10, NPC 지역당 1~2). TRPG 규모 확장은 U8 | Q5=A |

## 8. Testable Properties (NFR-2, PBT Partial)
| id | 속성 | 규칙 | 생성기 |
|---|---|---|---|
| TP-U2-1 (PBT-02) | `export(import(export(w))) == export(w)`(`exported_at` 제외), 같은 world_id. 저장소가 항목을 섞어 돌려줘도(가짜 저장소가 순서를 뒤섞음) export 바이트가 같다 | BR-U2-3/4 | `tests/world/strategies.py::world_files()` — 지역 계층(사이클 없음)·연결·엔티티·관계·지식·스코프·prior·NPC를 참조 일관되게 생성 |
| TP-U2-2 (PBT-02) | `remap_ids`는 결정적이고(같은 입력 → 같은 출력), 결과의 `world.id == T`이며, 재매핑된 파일에 다시 적용하면 항등이다(`remap_ids(remap_ids(f,T),T) == remap_ids(f,T)`). 재매핑 뒤에도 모든 참조가 해석된다 | BR-U2-4 | 같은 생성기 |
| TP-U2-3 (PBT-03) | `merge_regions` 뒤 모든 입력 힌트의 `connections`·`adjacent_names`·`parent_name`이 결과 어딘가에 남는다 | BR-U2-6 | `region_hints()` |
| TP-U2-4 (PBT-03) | `merge_entities` 뒤 재작성한 관계·ABOUT의 모든 참조가 결과 엔티티 id에 있다 | BR-U2-7 | `entities_with_refs()` |
| TP-U2-5 | `resolve_region`은 후보 순서를 섞어도 같은 답을 주고, 레벨이 명시되면 그 레벨만 돌려주며, 부모 역할의 답은 항상 자식보다 상위 레벨이고, 지형은 후보가 여럿일 때 선택되지 않는다 | BR-U2-8/9 | `same_name_regions()` |
| TP-U2-6 | v0 파일(옛 export dict, 최상위 `world_id`=A)을 대상 B로 읽어 import하면 `remapped=True`이고 어떤 id도 원본과 같지 않으며, 대상 A로 읽으면 `remapped=False`이고 export 결과의 절별 항목 수가 원본과 같다 | BR-U2-1/4 | 생성기의 v1 → 옛 키만 남긴 dict |
| TP-U2-7 (PBT-07) | 위 생성기는 `tests/world/strategies.py`에 두고 U3·U4·U8이 재사용한다 | — | — |
| TP-U2-8 (PBT-08) | hypothesis 기본 설정(seed 출력) 유지 | — | — |

### 8.1 규칙별 검증 수단 (예제 = `EX-n`, 인메모리·가짜 저장소로 오프라인)
| 규칙 | 검증 |
|---|---|
| BR-U2-1 | TP-U2-6; EX-1 버전 2 파일·`world_id` 없는 dict → 422 |
| BR-U2-2 | EX-2 모르는 필드가 있는 v1 파일이 읽힌다; 지역에 `name`이 없는 파일은 422 |
| BR-U2-3 | TP-U2-1 |
| BR-U2-4 | TP-U2-2, TP-U2-6; EX-3 `remap=true` 강제 재매핑; EX-4 유일 제약 위반을 흉내 낸 가짜 저장소 → error 경고·`ok=False` |
| BR-U2-5 | EX-5 없는 지역을 가리키는 스코프·NPC가 든 파일 → 그 항목만 빠지고 error 경고 |
| BR-U2-6 | TP-U2-3; EX-6 `parent_name`이 다른 두 힌트 → 첫 값 + warning |
| BR-U2-7 | TP-U2-4; EX-7 재작성 뒤에도 끊긴 관계 제거 + warning |
| BR-U2-8/9 | TP-U2-5; EX-8 `test_level_rank_covers_every_hierarchy_level`(enum 값 집합 − {terrain} == 표의 키) |
| BR-U2-10 | EX-9 잘못된 base64 하나 + 정상 메모 → error 경고 1, 메모는 처리 |
| BR-U2-11 | EX-10 준비 단계에서 실패하는 수집기(가짜) → 옛 월드 노드 그대로, `replaced=False`; EX-11 커밋 단계 persist 실패(가짜 저장소) → `ok=False, replaced=True`, 백업 파일 존재, 캐시 무효화됨; EX-12 `replace=False` + 존재 → 409 |
| BR-U2-12 | EX-13 없는 `home_region_id`의 NPC를 import → 항목 제거 + error 경고 |
| BR-U2-13 | EX-14 세 가지 error 경로(persist 실패·통째로 안 읽히는 입력·지역 0)에서 `ok=False`, 그 외 경고만 있으면 `ok=True`; CLI 종료 코드 |
| BR-U2-14 | EX-15 `region_hint`가 안 풀리는 지식 → 저장되고 `unscoped_knowledge_ids`에 있고 스냅샷 `unscoped_knowledge_ids`에도 있다 |
| BR-U2-15 | EX-16 카운팅 제공자로 빌드 → 리포트의 `llm_calls`·`embedding_calls`가 호출 수와 같다; 데모 로드는 `llm_calls == 0` |
| BR-U2-16 | EX-17 깨진 속성의 노드 하나 → 나머지는 로드되고 `load_warnings` 1개 |
| BR-U2-17 | EX-18 `invalidate` 뒤 `get`이 다시 로드; EX-19 로드 중 `invalidate`(로더 가짜가 콜백으로 무효화) → 캐시에 남지 않음 |
| BR-U2-18 | 코드 리뷰 항목(테스트 없음; 스냅샷을 바꾸는 코드가 없음을 grep) |
| BR-U2-19 | EX-20 `knowledge_for_region` 결과의 `title`이 `Knowledge.title`과 같다 |
| BR-U2-20 | EX-21 지식 4개(확신도 다름) 지역의 `region_briefs(top_k=3)` → 상위 3 title, 지식 없는 지역도 포함 |
| BR-U2-21/22 | EX-22 NPC import → `:NPC` 노드·`LIVES_IN` 엣지·`label="NPC"` 검색 문서; `delete_world` 뒤 셋 다 없음 |
| BR-U2-23/24 | EX-23 빌드·import·(가짜)편집 뒤 `WorldMeta.updated_at`·`last_writer`; 메타 없는 월드의 목록 항목 `name=id` |
| BR-U2-25 | EX-24 API: 열린 세션 1개 + `confirm` 없음 → 409 `{open_sessions: 1}`; `confirm=true` → 세션 닫힘 + `closed_session_ids` |
| BR-U2-26 | EX-25 CLI: `--force` 없이 종료 코드 1; `--force`로 진행 |
| BR-U2-27 | `tests/test_boundaries.py`(world → play import 금지) |
| BR-U2-28/29 | EX-26 `DemoWorlds.load("aldermoor", "w")` → 카운팅 LLM 호출 0, 지역 5·연결 1·NPC ≥ 5; embedding=None이어도 성공 |
