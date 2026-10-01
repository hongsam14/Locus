# U8 데모·배포·문서 — Code Summary (작성 중)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 코드 생성 중입니다. 이 문서는 단계마다 바뀐 것과 그 검증을 모읍니다(Step 16에서 마무리).

플랜: `construction/plans/U8-demo-deploy-docs-code-generation-plan.md` (17단계, 승인 2026-10-01).

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1, HEAD `589dc2b`) | 결과 (Step 16.1) |
|---|---|---|
| pytest | 857 | |
| vitest | 129 | |
| mypy (`locus api`) | 11 (6 파일) | |
| ruff · black · tsc | clean | |
| `npm ci` (깨끗한 설치) | 된다(202 패키지) | |
| `npm audit --omit=dev` | moderate 2 (react-router 6.30.6) | |

## 2. 단계별 기록
- **Step 1**
  - 1.1 기준선을 다시 쟀다(위 표).
  - 1.2 승인 산출물 정정(〔Step 1.2 정정〕).
    - FD BLM §7: 9a 기다리기(R-05).
    - FD frontend-components §3: `startSeed` 타입(R-12).
    - FD domain-entities §5.2·BR-U8-11: Ironcrag 전해 들음 목록(R-13).
    - FD BR-U8-35: react-router 7.18.x(사람의 결정).
    - Infra §1 web healthcheck 127.0.0.1(R-02), §3.1 package-data(R-04a), §3.2 nginx 49m(R-03), §5 설치본에서 확인(코드 플랜 R-02).
- **Step 2** (shared: 씨앗 모델과 저장)
  - `EventCategory`·`EventLifecycle`·`CATEGORY_DEFAULT_LIFECYCLE`·`default_lifecycle`을 `shared/models/enums.py`로 옮겼다(FR-A2 예외를 주석으로 남김). `play/models.py`는 같은 이름을 다시 내보낸다(호출처 무변경).
  - `EventSeed`(`shared/models/graph.py`), `WorldSnapshot.event_seeds`
  - 저장: `NODE_LABELS`에 `EventSeed`, `graph_mapping.seed_to_node`·`node_to_seed`, `persist_graph(seeds=)`
  - 로더가 씨앗을 싣고, 지역이 없는 씨앗은 dangling 경고와 함께 뺀다(NPC 집과 같은 규칙).
  - 테스트 `tests/shared/test_event_seed.py` 4개: 매핑 왕복, 범위, 로더, 재내보내기
  - pytest 861
- **Step 3** (World File `event_seeds`)
  - `schema.SECTIONS`·`WorldFile.event_seeds`(선택 절, 기본 `[]`, v1 그대로)
  - `remap`: `file_ids`·재매핑(씨앗 id·`region_id`)·`set_world_id`·`validate_references`(지역 없으면 error로 뺌)
  - `export`(정렬·스냅샷 씨앗), `import_`(`persist_graph(seeds=)`)
  - 생성기 `world_files`가 씨앗 0~2개를 뽑는다(U2 왕복 PBT·U3 편집 PBT도 씨앗과 함께 돈다).
  - 테스트 4: TP-U8-1, TP-U8-2, EX-5, EX-6
  - 변이(모두 잡음): 재매핑에서 `region_id` 빼기 → TP-U8-2 실패, 참조 검사 끄기 → EX-6 실패
  - pytest 865
- **Step 4** (지역 삭제의 씨앗)
  - `RegionDeletePlan.seed_ids`, `RegionDeleteReport.seeds_deleted`, `deleted_ids`에 씨앗 포함
  - 삭제 순서 ③ 스코프 뒤, ④ NPC 앞에 ③b 씨앗 노드 삭제(씨앗마다 한 번, 재시도 계획이 남은 것을 다시 찾는다)
  - TP-U3-2 신탁(`Stack.dangling`)이 `region_id` 속성을 본다(TP-U8-3). TP-U3-2a가 씨앗과 함께 돈다(생성기가 씨앗을 뽑음).
  - 구조 단언 "9 + NPC 수"는 씨앗 없는 EX-2 월드라 그대로다. 씨앗이 있으면 씨앗 수만큼 더한다(EX-7이 순서를 본다).
  - 테스트: TP-U3-2 의도된 변경, EX-7 새로
  - 변이: 씨앗 삭제를 빼면 3개 실패(잡음)
  - pytest 866
- **Step 6 → 5** (〔실행 메모 R-01〕 콘텐츠·매니페스트를 먼저, 그다음 Aldermoor 이동)
  - 6.1~6.3 Emberleaf Isle
    - World File: 지역 12, 연결 10쌍(20 엣지), 지식 23(전역 2·지방 3·마을 18), 엔티티 8, 관계 2, prior 2, NPC 15, 씨앗 3
    - 소스 `emberleaf/memo.md`·`map.json`(그림 없음)
    - 매니페스트는 `emberleaf` 하나(제목·설명·credits·`start_region_id`·sources)
    - 만든 방법: 스크래치 생성 스크립트가 실제 모델로 만들어 `sort_sections`·`to_json`으로 썼다. 저장소에는 결과 파일만 있다(데모는 데이터).
  - 5.1 `locus/world/demo/__init__.py`를 다시 썼다.
    - `DemoSources`·`DemoInfo`(+ `start_region_id`·`credits`·`sources`·`has_sources`)
    - 조립 때 한 번 검사하고 `problems`를 공개한다(〔실행 메모 R-02〕).
    - `importer`는 선택 인자다(없으면 `load`만 RuntimeError).
    - `sources()`, `build_from_sources`
    - 경로 탈출 거절. 상수·`load_demo_world`·이름 검사 삭제.
  - 5.2 `GET /demos` → `DemoInfoOut`(카드 필드만)
  - 5.3 CLI
    - `world build --demo <name>`, 별칭 `build-world --demo`(소스가 있는 첫 항목)
    - 도움말 정리
    - `npc_drafts.py`·`topology/naming.py` docstring 예시, `locus/world/__init__.py` 내보내기(`DemoSources`·`check_packaged`)
  - 5.4 `check_packaged()`(설치본 확인용, `DemoWorlds.problems` + 빈 목록)
  - 5.5 package-data `world/demo/worlds/*.json`, `world/demo/worlds/*/*`
  - 5.6 옛 Aldermoor World File과 `examples/demo_world/*`를 `tests/fixtures/aldermoor/`로 옮겼다(`examples/` 삭제).
    - ruff·black은 `tests/fixtures`를 제외한다(픽스처 데이터, `generate_map.py`의 옛 린트).
    - `_demo_file`(World File 테스트)은 픽스처를 읽는다.
    - CLI 테스트는 패키지 데모(`emberleaf`)로 바꿨다(`# U8 intended change`).
    - API 테스트의 가짜 `DemoInfo`에 `start_region_id`를 더했다. `/demos` 응답 단언은 카드 필드다.
  - 테스트
    - `tests/world/test_demo.py` 다시 씀(11)
      - 매니페스트, 불러오기(LLM 0, 교체), 소스, EX-11(잘못된 항목 여섯)
      - 소스 없음 → LookupError, 지도 그림 base64
      - TP-U8-4(모양), 도달·우회, 무게표(domain-entities §5.2, 셋째 자리까지 일치)
      - EX-9: Ironcrag 전해 들음 = 표의 0.15~0.5 마을 전부(FD R-13)
      - EX-10: 1턴 Saltwake·Sylvarch, 3턴 Ironcrag
      - 금지어
    - `tests/test_demo_as_data.py`(TP-U8-6, `locus/`·`api/`; `web/src`는 Step 10에서 더한다)
    - CLI `--demo` 1
  - 변이(모두 잡음): 경로 탈출 검사 빼기, 지나갈 수 있는 시작 지역 검사 빼기 → EX-11 실패
  - pytest 875
- **Step 7** (씨앗 시작)
  - `EventService.create_event(…, provenance=, timeline_extra=)`. 기존 호출처는 바뀌지 않는다. 씨앗이면 타임라인 요약이 "started seed '…' in …"이고 payload에 `seed_id`·`seed_title`이 있다.
  - `locus/play/event/seeds.py` `SeedService`
    - `list_seeds`(제목 순, 지역 이름, `running_event_id`)
    - `start`(열림 → 씨앗 → 지역 → 진행 중 → 생성)
    - 진행 중 판정: 해소되지 않은 사건 중 `provenance.generated_by == "seed"`이고 `refs`에 씨앗 id가 있는 것
  - `SeedView`(`play/models.py`), `SeedAlreadyRunningError`(`play/errors.py`) → `api/errors.py` 409(`PLAY_ERRORS`에 포함)
  - `PlayContainer.seeds`. GM 라우트 `GET /sessions/{sid}/seeds`, `POST /sessions/{sid}/seeds/{seed_id}/start`(201 `EventOut`, GM 리스 `_idle`)
  - 테스트 `tests/api/test_seeds_api.py` 2
    - EX-4·TP-U8-5: 시작 → ACTIVE·타임라인 → 409 → 해소 → 201, LLM 0
    - 404·턴 중 409·닫힘 409, 읽기는 닫혀도 됨
  - 변이: 진행 중 검사 빼기 → EX-4 실패(잡음)
  - pytest 877
- **Step 8** (LLM 유무와 503)
  - `GET /api/capabilities` → `{llm, vlm, embedding}`(조립된 shared 공급자). `/health`는 그대로다.
  - TP-U8-8(`tests/api/test_keyless_api.py`): 공급자 없이 운영과 같은 방식(`assemble_world`·`assemble_play`)으로 조립한 앱
    - BLM §4.1 표의 여덟 경로가 모두 503이다: build, build/upload, demo build, npc-drafts, 소문 생성·재생성, 사건 제안, 대화.
    - 키 없이 쓰는 경로는 된다: 데모 불러오기 → 시작 지역 세션 → 강 이동 → 씨앗 시작, 보강 시작, `POST priors`.
    - 표 밖에서 500이 나온 경로는 없었다(고칠 것 없음).
  - pytest 878
- **Step 9a** (U3 이월: 에디터 쓰기)
  - 포트: `GraphRepository.replace_edges`(Neo4j `MERGE … SET r = $props`)·`edges_touching`(한 쿼리). 구현: Neo4j 어댑터, `InMemoryGraphRepository`, `MeteredGraph`(쓰기 하나로 셈). 손으로 쓴 가짜 둘(`test_services._GraphRepo`, `test_query._FakeGraphRepo`)은 그 경로를 타지 않아 그대로다.
  - #13
    - (a) NPC 집 옮기기: 새 LIVES_IN → 노드 → 옛 LIVES_IN. 옛 집은 엣지에서 읽는다.
    - (b) `set_prior_ref`는 `replace_edges`로 제자리 교체한다.
  - C3·S12: `EditorWrites.delete_held`(다른 라벨이면 손대지 않고, 없으면 검색 정리만 하고 메타는 쓰지 않음)
    - 지식·NPC·엔티티 삭제와 `WikiAdmin.delete_prior`가 함께 쓴다.
    - 〔이탈〕 WikiAdmin은 EditorWrites를 받지 않고 자기 안에서 만든다. 에디터 패키지가 wiki 모듈을 import하므로 지역 import로 순환을 피했다.
  - C4: `Editors.prior_ids`·`get_node` 삭제(호출처 `apply.py` 2곳은 `writes.graph.get_node`), `delete_any`는 지식·엔티티만
  - C6: `npc_drafts._path` = `level_path[:-1]`, `regions._connection_edges` → `connections.edge_keys`
  - C11: `EditorWrites.index(…, previous=)`. 글과 meta가 모두 같은 문서는 다시 색인하지 않는다.
    - 〔이탈〕 리뷰는 "글이 같으면 임베딩만 건너뜀"이었다. 색인은 문서를 통째로 덮으므로 벡터 없이 쓰면 벡터를 잃는다. 그래서 문서 전체가 같을 때만 건너뛴다.
  - C17: 빈 제목은 서버의 `fallback_title`(create·upsert)
  - S21: 편집 쓰기 앞의 `require_world`(스냅샷 읽기 — WorldMeta 없는 U2 이전 월드도 편집된다)
  - S26: `own_label` — 같은 id가 다른 라벨이면 400
    - 〔이탈〕 플랜은 가짜를 (world, label, id)로 다시 잡는 것까지였다. 편집 쓰기의 검사가 결함(Neo4j에 같은 id 노드 둘)을 막으므로 가짜의 키는 그대로 두었다. 키를 바꾸면 `get_node(world, id)`의 뜻이 바뀌어 테스트 전반이 흔들린다.
  - S29: 신뢰도가 바뀌면 그 지식의 DIRECT 스코프 엣지 값도 고친다.
  - S30: 지운 지역의 부모가 월드에 없으면 `new_parent_id = None`
  - S32: 있는 id로 지식 추가 → 400
  - #12(서버): 엔티티 확인·고침은 위치가 바뀔 때만 위치를 검사한다.
  - 의도된 변경: `test_world_api._editors`·`test_services.test_graph_editor_upsert_and_delete`가 월드와 캐시를 갖는다(S21).
  - 테스트
    - `tests/world/editor/test_u3_review_carry.py` 13(#13 두 경로는 모든 쓰기에서 끊고 다시)
    - 포트 계약 3
  - 변이(모두 잡음): #13a 옛 집을 속성에서 읽기, #13b 지운 뒤 쓰기, S12 다른 라벨 문서 지우기, C11 이전 문서 무시, S29 스코프 갱신 빼기, S30 부모 그대로
  - 호출처: `upsert_npc`·`update_entity`·`upsert_knowledge`의 서명은 그대로다(새 인자 없음). `EditorWrites.index`의 새 키워드는 선택이다.
  - pytest 894
- **Step 9b** (U3 이월: 보강 Q&A)
  - C2: 질문에 `type`, 동작별 입력 `needs`(gap/add: 진술·제목, 확인 계열 edit: 진술·제목·신뢰도(S06), orphan·unscoped edit: 지역, dangling edit: ref), dangling의 `ref_kind`(region·entity·prior)
    - 연결 대상은 `QuestionTarget.connection: ConnectionKey`를 갖는다.
    - 더한 지식의 이름은 저장된 제목(서버 fallback 포함)이다.
    - `TargetKind`에서 쓰이지 않던 `"npc"`를 뺐다(C4).
  - C10: 변경 기록과 되돌리기 검사의 엣지 읽기가 `edges_touching`(대상 주위만)이다. 인메모리 가짜의 `edges_touching`도 월드 전체 `get_edges`를 거치지 않는다.
  - S03: 검사를 통과한 되돌리기는 `ChangeSet.revert_started`를 세운다. 다시 보낼 때 그래프가 이미 되돌아가 있으면(`is_undone`) 검색 쪽만 마친다(`finish_revert`). 그래서 409 "edited after"가 나지 않는다.
  - S09: wiki 검색 예외는 캐시하지 않는다(다음 탐지에서 다시).
  - S10: 답 라우트(REMOVE로 지운 지식)와 되돌리기 라우트(gap/add로 더했던 지식)가 `purge_translations`를 부른다.
  - S15: 쓰기 뒤 다시 탐지가 실패하면 질문과 이슈를 비운다(같은 답을 두 번 적용하지 못함 → 404, 화면은 run을 다시 읽음).
  - 테스트 `tests/world/augmentation/test_u3_review_carry.py` 7(C2 둘, C10, S03, S09, S15, S10 API)
  - 변이(모두 잡음): S03 재개 빼기, S09 실패 캐시, S15 비우기 빼기, C10 월드 전체 읽기
  - pytest 901
- **Step 9c** (U3 이월: 업로드·한도·API)
  - C7: 열린 세션은 `SessionService.open_sessions()` 하나(`SessionStatus` 비교)
    - 호출처는 셋이다: `world._open_sessions`, `world.list_worlds`, CLI `_guard_open_sessions`. 세션 가짜 둘(`test_world_api`, `test_cli`)에도 같은 메서드를 더했다(의도된 변경).
    - CLI `world list`는 `WorldCatalog`를 쓴다.
    - `_need`는 `api/deps.need_service`로 옮겼다. `world.py`는 이 함수를 `_need` 이름으로 가져온다(라우트 안의 호출 18곳은 그대로).
  - C9: `WikiAdmin.refs`(스냅샷 한 번, 스냅샷의 prior). `GET prior-refs`가 이것을 쓴다.
  - C13: `WorldInfo(WorldSummary)`. `EditorRegionViewOut`은 mypy 필드 재정의 검사 때문에 독립 모델로 두었고, 까닭을 docstring에 적었다.
  - C15: `build/upload`가 개수 검사 바로 뒤, 파일을 읽기 전에 열린 세션을 확인한다.
  - S07: 지도 JSON이 객체가 아니거나 너무 깊으면(`RecursionError`) 고정 문구 422다. World File 업로드도 `RecursionError`면 422다.
  - S19: `WorldInputs`가 개수·길이 상한을 갖는다(메모 20개·60,000자, 지도 5개, 지도 그림 4개, 컨셉 아트 8개, 그림 base64 8 MiB 상당). `api/uploads.py`도 같은 상수를 읽는다.
  - S20: 미들웨어가 `root_path`를 떼고 길을 비교한다. World File 길의 요청 한도는 20 MiB + 1 MiB(multipart 여유)라서, 꽉 찬 파일은 칸의 정확한 413을 받는다.
  - S27: 422 처리기가 bytes 입력을 `errors="replace"`로 푼다(500이 아님).
  - 의도된 변경: `test_uploads`의 World File 한도 둘(21 MiB)
  - 테스트 7: S20 둘, S07, S19, S27, C15, C9
  - 변이(모두 잡음): S20 root_path, S07 객체 검사, S27 bytes, C15 순서, C9 prior 재조회
  - pytest 908
- **Step 9d** (U3 이월: 플레이)
  - #10: 포트 `EventStore.update_event_contributions(…, status=)`(contributions만, 그 상태일 때만)와 `get_event`·`list_events(…, for_update=)`(PostgreSQL `FOR UPDATE`, 인메모리는 이미 잠금)
    - 구현: PG 저장소(`_PgStores`·저장소 래퍼), 인메모리
    - GM 설정은 UoW 안에서 ACTIVE 사건을 잠가 읽고, 조건부로 contributions만 쓴다. 지운 몫은 실제로 지운 것만 기록한다.
    - 해소는 UoW 안에서 사건을 잠가 다시 읽고 그 contributions로 복원한다.
  - C16: 사건 생성은 `require_region`이 돌려준 이름을 쓴다. 해소는 트랜잭션 전에 이름을 한 번 구한다.
  - S17: `GmNarrator.prompts`·`call`·`finish`로 나눴다. 턴 엔진은 프롬프트를 try 밖에서 만들고 공급자 호출만 감싼다.
  - S18: 전파 한 칸·행적 씨앗·LLM 생성 소문의 지지도를 `settle`해서 저장한다.
  - 테스트 `tests/play/test_u3_review_carry.py` 6
    - #10 둘: 해소 전에 읽은 낡은 ACTIVE 사본으로도 되살리지 못함, 저장소 둘(인메모리·SQLite)의 조건부 쓰기
    - C16, S17, S18
  - 변이(모두 잡음): #10 통째 쓰기로 되돌림, S17 프롬프트를 try 안으로, S18 `clamp01`, C16 이름 두 번
  - 〔알려진 한계〕 오프라인 테스트는 PostgreSQL의 행 잠금을 돌리지 못한다(SQLite는 `FOR UPDATE`를 무시). 실제 동시 실행 확인은 운영자 몫이다.
- **Step 9e** (U3 이월: NPC 초안)
  - S22: 프롬프트의 REGION·KNOWN HERE·EXISTING NPCS가 하나의 `MATERIAL` 머리말 아래에 있고, 시스템 문장이 셋을 다 가리킨다.
  - 테스트 1, 변이 잡음
  - pytest 915
