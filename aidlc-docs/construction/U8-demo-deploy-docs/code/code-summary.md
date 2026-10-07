# U8 데모·배포·문서 — Code Summary

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 코드 생성을 마쳤습니다(Step 1~16). 이 문서는 단계마다 바뀐 것, 검증, 이탈, 남은 결정, 운영자 확인을 모읍니다. 다음은 코드 승인 지점(Step 17)입니다.

플랜: `construction/plans/U8-demo-deploy-docs-code-generation-plan.md` (17단계, 승인 2026-10-01).

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1, HEAD `589dc2b`) | 결과 (Step 16.1) |
|---|---|---|
| pytest | 857 | **933** |
| vitest | 129 | **197** |
| mypy (`locus api`) | 11 (6 파일) | 11 (6 파일), 늘지 않음 |
| ruff · black · tsc | clean | clean (`scripts` 포함) |
| `npm ci` (깨끗한 설치) | 된다(202 패키지) | 된다(203 패키지, react-router 7.18.4) |
| `npm audit --omit=dev` | moderate 2 (react-router 6.30.6) | **0** |
| `dangerouslySetInnerHTML` | 0 | 0 |
| 이미지 | — | app·web 빌드 됨, 설치본 `check_packaged()` [], `import api.main` 됨 (Step 12.7) |

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
- **Step 10** (프런트엔드: U8 기능)
  - 10.1 API·타입
    - `api.capabilities()`, `listSeeds`, `startSeed`(사건 타입)를 더했다. `loadDemo(worldId, name, options)`는 이름 기본값이 없다. `buildWorldDemo`는 지웠다.
    - `types.ts`: `Capabilities`·`EventSeed`·`SeedView`, `DemoInfo` 확장, `RegionDeletePlan.seed_ids`·`RegionDeleteReport.seeds_deleted`, `WorldExport.unscoped_knowledge_ids`
    - `http.ts`
      - `openSessionsOf(err)`: 409 본문의 `open_sessions`·`busy_sessions`·`session_ids`를 읽는다.
      - `needsLlm(err)`: 503이고 공급자를 말할 때만 참이다. 실패한 호출은 아니다.
      - `useReplaceConfirm()`(C8): "교체?" → "열린 세션 N개 닫기?" 두 단계 질문. DemoCard가 쓴다. BuildPanel·WorldFileBar는 Step 11.3에서 옮긴다.
    - C5 서버 쪽: `WorldSnapshot.unscoped_knowledge_ids`가 규칙을 직접 계산한다. 편집기 목록과 보강 탐지기가 이것을 읽고, export에도 싣는다.
      - 〔기록〕 9.3에 체크했지만 Step 9 커밋에 빠져 있었다. 이 단계 커밋에 넣는다. 웹이 export 값을 쓰는 것은 C1(11.3)이다.
  - 10.2 `capabilities.ts`, `LlmNotice`, `InProgressBadge`
    - `useCapabilities`: 한 번 읽어 모듈에 두고 구독자에게 알린다. 실패하면(동기 예외 포함) `null`이고, 아무것도 끄지 않는다.
    - `LlmNotice`가 `LlmBanner`를 대신한다(PlayPage는 `play.noLlm` 문구 그대로). `features/play/LlmBanner.tsx`는 지웠다.
  - 10.3 `features/home/DemoCards`·`DemoCard`, `HomePage`, `AppNav`
    - HomePage에서 DEMO 상수를 지웠다. 카드는 월드가 있어도 보인다. LlmNotice를 둔다.
    - AppNav: "Locus"는 `/`로 가는 링크다. 월드가 없으면 에디터 링크도 `/`다(S01).
  - 10.4 SeedPanel과 LLM 끄기
    - `features/gm/SeedPanel.tsx`: 목록, [시작], "진행 중". 닫힌 세션이거나 일괄 작업 중이면 꺼진다.
    - GmHub: LlmNotice, SeedPanel 자리. 오류 줄에 testid `gm-hub-error`가 생겼다(GmPage의 `gm-error`와 겹치지 않게).
    - LLM 없을 때 끄는 버튼: [사건 제안]·[전체 생성]·[전체 재생성](ManualTurnPanel), [생성]·[재생성](RumorPanel), [만들기](BuildPanel), [초안](NpcDraftCards). 모두 `title`과 옆 글 `llm.required`를 붙인다.
    - 컨셉 아트 칸에 InProgressBadge를 둔다. EditorPage에 LlmNotice를 둔다.
    - 공급자가 없다는 503은 `llm.required`로 보인다(GmHub·BuildPanel·NpcDraftCards·DialoguePanel). DialoguePanel에서 실패한 호출은 지금처럼 `dialogue.failed`다.
    - 지역 삭제 계획에 씨앗 수 줄 `delete.region.seeds`를 더했다(EX-7).
  - 10.5 i18n
    - 새 키 25개와 `delete.region.seeds`를 ko·en 같은 집합으로 넣었다.
    - FC §4대로 키 이름은 `timeline.seedStarted`, 문구는 "씨앗 사건 시작: {title}"이다. `timelineText`는 `event_created`에 `seed_title`이 있으면 이 문구를 쓴다.
    - C14의 21개와, 이번에 쓰지 않게 된 `home.loadDemo`를 지웠다(22개). 여러 줄 값이 남긴 이어지는 줄 4개도 지웠다. 머리말의 "~150 keys"를 고쳤다.
  - 10.6 테스트
    - 새로 쓴 테스트
      - `capabilities.test.ts` 11: 읽기 한 번·실패·동기 예외, `openSessionsOf`·`needsLlm`, `useReplaceConfirm` 둘, 실제 URL로 본 `loadDemo` 인자 순서, 씨앗 라우트, 씨앗 타임라인 줄, 키 집합
      - `home.test`: EX-1·2·3·8·12·13·14, 카드 둘, 지금 월드로 플레이, 에디터로 불러오기(+세션 질문), 모름, 목록 실패
      - `gm.test` 6: 씨앗 목록·시작·409·닫힘·빈 목록, LLM 끄기, 모름, 503 문구
      - `editor.test` 6: 만들기 끄기·켜기, 배지, 503 문구, 초안 끄기·503, 삭제 계획 씨앗 수
      - `components.test` 3: AppNav 둘, 에디터 LlmNotice
      - `dialogue.test`: 공급자 없음 503
      - 서버 C5 둘(`tests/world/editor/test_u3_review_carry.py`)
    - 의도된 변경: `home.test`(옛 데모 버튼), `play.test` 둘(`llm-banner`→`llm-notice`), `dialogue.test`(실패한 호출의 503 본문을 서버 실제 문구로), api 목에 `capabilities`·`listSeeds`·`listDemos` 기본값
    - TP-U8-6: 검사 범위에 `web/src`를 넣었다(`web/src/__tests__` 제외). 검사가 비어 있지 않음을 보이는 테스트 하나를 더했다.
    - 변이(18건 중 17건 잡음)
      - 웹 14: busy, ok=false, 재사용 경로, `llmOff` 둘, 씨앗 닫힘, 삭제 계획 씨앗, 씨앗 타임라인, 대화 503, 초안 끄기, 만들기 끄기, 훅 confirmed, 훅 answer, DemoCard edit 경로
      - 서버 3: C5 스냅샷 규칙, C5 export, 웹 소스의 데모 이름(TP-U8-6)
      - 남은 하나는 같은 동작이다: `useCapabilities`에서 캐시 확인을 빼도 `useState(cached)`가 같은 값을 준다.
  - 게이트: pytest 918, vitest 169, tsc·ruff·black clean, mypy 11
- **Step 11a** (U3 이월: 에디터 화면)
  - C1
    - 지도 끌기는 PUT 한 번이고, 성공하면 `rev`만 올린다(인스펙터가 지역을 다시 읽음, U3 #1 유지). 실패하면 월드를 다시 읽어 표식을 되돌리고 오류를 보인다.
    - `listWorlds`는 마운트, World File 불러오기, 빌드 뒤에만 읽는다(`reloadAll`).
    - 스코프 없음 탭 수는 export의 `unscoped_knowledge_ids`다(C5).
  - #14: EditorPage도 패널을 열 때마다 `BuildPanel`의 `key`를 바꾼다(HomePage는 Step 10에서).
  - #15
    - `sameConnection`(같은 쌍·종류, 방향 무관)이 있으면 연결 폼이 "연결 고치기"로 열리고, 저장된 가중치와 안내 줄(`connection-exists`)을 보인다.
    - 저장 본문은 기존 연결(근거·prior·출처)에 폼의 가중치만 얹는다. 다른 종류를 고르면 새 연결이다.
  - S01 나머지
    - 〔기록〕 플랜은 Step 10에 두었지만 10.3에서 AppNav만 했다. 여기서 마저 했다.
    - WorldFileBar는 열린 세션이 0이면 [세션 시작] 띠(`start-session-band`)로 세션 picker를 연다.
    - `gm.noSessionHint`·`play.noSession` 문구가 홈(/)과 에디터 띠를 가리킨다.
  - S05: 지역 삭제 409(`session_ids`)는 계획의 `blocked_by_sessions`로 넣는다. 그래서 막힘 문구와 세션이 보이고 확인은 꺼진다(원문 409를 보이지 않음).
  - S21(화면): 월드가 없으면(export 404) 지도 도구 셋이 꺼진다(`MapCanvas disabled`).
  - S23
    - 끌기 시작 때 표식(`<g>`)이 포인터를 잡는다. `pointercancel`·`lostpointercapture`는 저장 없이 끌기를 끝낸다.
    - 〔설계 메모〕 플랜은 "pointerdown에서 setPointerCapture"다. 잡는 곳을 svg가 아닌 표식으로 했다. click을 잡은 요소로 보내는 브라우저에서도 표식 클릭(지역 고르기)이 살아 있게 하려는 것이다.
  - S24: 고른 뒤 파일 칸을 비운다.
  - S25: 지역 삭제 계획 여섯 항목 모두 수와 이름을 보인다. 연결은 다른 끝 지역 이름과 종류로 보인다.
  - S31: RegionInspector·UnscopedPanel은 읽기 순번을 두고 마지막 읽기만 그린다.
  - C8
    - BuildPanel·WorldFileBar가 `useReplaceConfirm`을 쓴다(정규식 파싱 삭제).
    - 지도의 새 지역 폼 이름을 `NewRegionForm`으로 바꿨다.
    - `openSessionsOf`가 평범한 `Error`의 "NNN Status: 본문" 메시지도 읽는다.
  - C12: UnscopedPanel의 쓰기 뒤 `load()`를 뺐다. 페이지의 `reloadKey`가 한 번 읽는다.
  - C17(웹): 제목 칸이 비면 빈 제목을 보낸다(서버가 `fallback_title`로 채움, 9a).
  - 테스트
    - `editor.test` 16(위 항목마다, EditorPage는 라우터로 그림)과 `capabilities.test` 1
    - 의도된 변경: UnscopedPanel 테스트(C12, 페이지처럼 `reloadKey`를 올리는 하네스. 읽기 2번 단언)
  - 변이 20건 모두 잡음: C1 셋, #14, #15 둘, S21, S01, S05, S25, S31 둘, C12, C17, S23 셋, S24, C8 WorldFileBar
  - 게이트: vitest 185, tsc clean
- **Step 11b** (U3 이월: 보강 화면)
  - #12(패널)
    - 답·되돌리기·다시 묻기가 404이면 `GET runs/{id}`로 run이 남아 있는지 본다.
    - 남아 있으면 run을 다시 그리고 서버 문장을 오류로 보인다(`detailOf`: JSON `detail` 글). run도 404일 때만 "잃음"이다.
  - C2(웹)
    - 카드 입력은 질문의 `needs`(행동별 입력)로 그린다. 답은 그 행동이 받는 입력만 보낸다.
    - 참조 선택지는 `ref_kind`(region·entity·prior)로 고른다. `issue_key` 쪼개기와 필드→라벨 표를 지웠다.
    - 타입: `AugQuestion.type`·`needs`·`ref_kind`, `QuestionTarget.connection`, `AugInput`
  - S06: 고치기·추가 카드에 제목과 신뢰도(0~1, 범위 밖이나 빈칸이면 보내지 않음) 입력이 생겼다(서버 `needs`가 부를 때).
  - S28: 카드 입력을 `issue_key`로 잡는다. 다시 탐지가 질문 id를 바꿔도 다른 카드의 입력이 남는다.
  - 테스트
    - `editor.test` 5: #12, C2/S06 둘, C2 참조 종류, S28
    - `capabilities.test` 1: `detailOf`
    - 의도된 변경: "잃은 run" 테스트가 `getRun` 404를 직접 둔다. 앞 테스트의 mock에 기대던 순서 의존도 함께 없앴다.
  - 변이 8건
    - 7건은 처음부터 잡았다: 404→잃음, `needs` 대신 합집합, 신뢰도 범위, entity 선택지, 입력 키 둘, 제목
    - `detailOf` 변이는 처음에 살아남았다(부분 문자열 단언). 단언을 정확한 문장으로 바꾼 뒤 잡았다.
  - 게이트: vitest 191, tsc clean
- **Step 11c** (U3 이월: 플레이·GM 화면)
  - S02
    - PlayPage는 `turn_running`인데 실행 중인 run이 없으면(GM 쓰기나 에디터 리스가 세션을 쥠) `heldRetryMs`(1초)마다 다시 읽는다. 최대 5번이다.
    - 마운트 때뿐 아니라 어느 읽기 뒤에도 같다. 플래그가 풀리거나 run이 생기면 횟수를 되돌린다.
    - U7 C7의 즉시 한 번 더 읽기는 그대로다.
  - S04: DialoguePanel은 세션·NPC가 바뀔 때만 오류 줄을 비운다. `readOnly`로 다시 읽어도 "세션이 종료되었습니다"가 남는다.
  - S08: `timelineText`는 템플릿의 자리표시자와 params를 대조한다. 이름에 `{…}`가 있어도 지역 이름이 남는다.
  - S13: [전체 생성]의 `/state` 읽기가 제안 상한을 고친다(마운트 읽기가 실패했을 때).
  - S14
    - GmPage가 `PlayerStrip`에 `key={session.id}`를 준다.
    - 세션이 바뀌면 지도 표식의 플레이어를 비운다. s2 읽기가 실패해도 s1의 플레이어·표식이 남지 않는다.
  - 테스트
    - `play.test` 2(S02 풀림, 5번 상한)
    - `dialogue.test` 2(S04, S08)
    - `gm.test` 2(S13, S14: GmPage를 라우터로 s1→s2)
  - 변이 7건 모두 잡음: S02 둘, S04, S08, S13, S14 둘
  - 게이트: vitest 197, tsc clean
- **Step 12** (배치, Infra-light)
  - 12.1 기준선: ruff·black·tsc clean. `npm ci`가 lock 그대로 된다(202 패키지).
  - 12.2 `docker-compose.yml`
    - 인프라 포트를 `127.0.0.1:${VAR:-기본값}`으로 연다(`NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, `OPENSEARCH_PORT`, `SESSION_DB_PORT`, `DASHBOARD_PORT`).
    - dashboard는 `tools` 프로필로 옮겼다.
    - web healthcheck: `wget -q --spider http://127.0.0.1/`
    - 머리 주석: 다섯 서비스·세 프로필·준비 명령·멈춤 명령·포트 변수. 키 없이도 뜬다는 문구도 넣었다.
    - `docker compose config`로 확인했다: 기본 프로필 3, `service`+`tools` 6, 포트 변수 적용.
  - 12.3 이미지
    - `.dockerignore`에 `web`·`scripts`
    - `web/Dockerfile`: `node:22-alpine`, `npm ci`(lock 필수)
    - `web/.dockerignore`에 `tsconfig*.tsbuildinfo`
    - `web/nginx.conf`: `client_max_body_size 49m`
  - 12.4 `env.example`
    - 머리말 중복을 지우고 필수 두 값을 앞에 적었다. 키는 없어도 된다는 안내를 넣었다.
    - 포트 변수 주석을 넣었다(호스트 uvicorn이면 URL도 같은 번호로).
    - `scripts/setup-volumes.sh`의 다음 단계 문구를 실제 프로필과 멈춤 명령으로 고쳤다.
  - 12.5 react-router
    - `react-router-dom` 6.30.6 → 7.18.4(사람의 결정 A). 고친 곳은 `package.json`·lock뿐이고, 라우터 밖으로 번진 수정은 없다.
    - tsc clean, vitest 197. `npm audit --omit=dev`는 0건이다.
    - 〔관찰〕 전체 `npm audit`에는 dev 의존성 4건(browserslist 등, moderate 3·high 1)이 있다. 게이트(`--omit=dev`, FD Q5=A) 밖이라 이 단계에서는 손대지 않았다.
  - 12.6 `.github/workflows/ci.yml`
    - 네 작업: backend, frontend, audit, images
    - backend는 seed를 찍고 `--hypothesis-seed`로 넘긴다.
    - npm 캐시는 `cache-dependency-path: web/package-lock.json`이다.
    - `concurrency`로 같은 ref의 앞선 실행을 취소한다. 권한은 `contents: read`이다.
    - images 작업은 데모를 설치본에서 확인한다(`-w /tmp`, `python -I`, `site-packages` 단언, `check_packaged()`). `import api.main`은 `/app`에서 따로 본다.
    - push와 첫 실행 확인은 사람이 한다.
  - 12.7 로컬 확인
    - `docker build`(app·web)가 된다.
    - app 이미지 안: `check_packaged()` 문제 0, `import api.main` 됨
    - web 이미지: `app` 호스트를 주면 `nginx -t`가 통과한다. 컨테이너 안에서 healthcheck 명령이 성공한다.
    - 확인용 이미지는 지웠다. 실제 compose 기동은 라이브 시나리오 1단계(운영자, Infra R-01)다.
- **Step 13** (메타, BR-U8-29~31)
  - `pyproject.toml`
    - `license = { text = "MIT" }`(`LICENSE`와 같음)
    - 설명은 목적 문장(요구사항 §0)의 영어판이다.
    - `[project.urls] Repository`를 더했다.
  - `requirements.txt`에 빠져 있던 셋(`sqlalchemy`, `psycopg[binary]`, `python-multipart`)을 넣어 `dependencies`와 같게 했다.
  - `STATUS: in-progress — …` docstring을 진행 중 넷에 맞췄다.
    - 교차 월드 prior 검색, LangGraph 래퍼: 문구를 맞췄다.
    - 컨셉 아트: 낡은 "U2에서" 문구를 고쳤다.
    - wiki 순환 구조(`distiller.py`): 새로 넣었다.
    - 넷 모두 README 표를 가리킨다.
  - TP-U8-7 `tests/test_packaging.py` 4: requirements 일치, MIT 둘, 설명과 URL, STATUS 넷
  - 변이 4건 모두 잡음: 줄 빠짐, 버전 조건 바뀜, 라이선스, STATUS
  - app 이미지 빌드로 메타데이터를 확인했다(`License: MIT`, `Project-URL`, `check_packaged()` []). 로컬 venv에는 setuptools가 없어 그쪽으로는 보지 못했다.
  - 게이트: pytest 922, ruff·black clean, mypy 11
- **Step 14** (문서, BLM §5, BR-U8-28·31·32)
  - 14.1 `README.md`를 새로 썼다(한국어).
    - 첫 줄이 목적 문장이다. CI 배지를 단다.
    - 이어서 6단계 흐름, 스크린샷 자리, 시작하기가 온다.
      - 시작하기 명령 셋: 준비 명령, `.env` 두 값, `--profile service up -d --build`. 그 뒤 :3000에서 [바로 플레이]를 누른다.
      - 포트 덮어쓰기, 127.0.0.1 바인딩, Dashboards, 멈춤, 상태 보기도 여기에 적었다.
    - 다음 절: 키 없이 둘러보기(되는 것·꺼지는 것·켜는 법), 데모 월드, 진행 중 기능 표(넷), 개발(호스트 흐름·검사), 디렉터리, MIT와 데모 크레딧(참고한 인벤 글 링크)
  - 14.2 `CLAUDE.md`
    - Project Overview를 목적 문장으로 바꾸고, 영어 한 단락을 덧붙였다.
    - Status에 U8 진행을 넣었다.
    - 레이아웃에 홈·데모 카드·SeedPanel·LlmNotice·`useReplaceConfirm`을 넣었다.
    - CLI 줄을 emberleaf와 `world build --demo`로 바꿨다.
    - Build/Run을 `npm ci`, 준비 명령, 프로필, `--workers 1`로 바꿨다. 게이트·CI·포트 줄을 더했다.
  - 14.3 `operations.md`
    - Run 절: 키 선택, `service` 기동 먼저, `tools`는 dashboard만, 멈춤 명령
    - 낡은 줄을 고쳤다.
      - aldermoor 명령 둘, 데모 버튼
      - 키 없음 문장 〔U8 정정〕: `/health`는 `ok`. 503 경로를 정확히 적었다.
      - 홈 화면 줄
      - 지식 삭제·번역: 보강 지우기·되돌리기 포함(S10)
      - "Web UI (U10)" → "Web UI": `npm ci`, nginx
      - `--legacy-peer-deps`
      - Future Operations
    - 보강 절에 #12 동작과 S16 알려진 한계 한 줄을 더했다.
    - U8 절을 새로 썼다: 데모는 데이터(매니페스트·`check_packaged`·데모 더하기·옛 명령 대응·[바로 플레이]), 씨앗(파일·API·409·`init-schema --world`), 키 없음, 포트·프로필, CI(seed 재현), CLI 교체의 번역 공백(A8-10), 라이선스.
    - 라이브 시나리오 줄은 스크립트가 생기는 Step 15에서 더한다.
  - 14.4 `web/README.md`
    - 홈 데모 카드, 키 없음, GM 씨앗 패널, 세션 띠, 연결 도구 고치기, 컨셉 아트 배지, `npm ci`
    - 〔U8 정정〕 둘
      - U3 BLM §1.4: 종류 바꾸기는 `previous_kind` PUT 하나다.
      - U3 nfr-light §3: compose web(nginx)은 리버스 프록시이고 49m이다.
  - 〔기록〕 키 없음 안내 문구(`llm.offNotice`)에 ".env에 OPENAI_API_KEY를 넣고 다시 띄우면 켜집니다"를 더했다. BLM §4.2는 무엇이 꺼졌는지와 켜는 법을 적으라고 한다. Step 10 문구에 켜는 법이 빠져 있었다. 테스트는 `t()`로 비교하므로 그대로다.
  - 테스트 2(`tests/test_packaging.py`)
    - README 첫 줄과 CLAUDE.md에 목적 문장이 있다.
    - README의 `--profile` 값이 compose에 있는 프로필이다.
    - 변이 2건 모두 잡음
  - 게이트: pytest 924, vitest 197, ruff·black clean
- **Step 15** (라이브 시나리오, BLM §7, BR-U8-36)
  - 15.1 `scripts/live_scenario.py`(표준 라이브러리 `urllib`)
    - 단계: 1·2·3·4·5·6·7·8·9·9a·10a·10b·11·12
    - 10은 둘로 나눴다. 왜곡도(LLM 없음)와 대화(LLM)라서, 키가 없을 때 앞쪽은 여전히 판정한다.
    - 지역은 이름으로 찾는다. 다른 world id로 불러와 id가 다시 매겨져도 돈다. NPC는 플레이어 지역의 첫 NPC, 씨앗은 Ambermeadow 지역의 것이다.
    - PASS·FAIL·SKIP
      - 키가 없으면 5·6·10b가 SKIP이다. 선언이 없으면 9·11이 SKIP이다.
      - 증인 판단이 씨앗을 만들지 않았으면 9·11이 까닭과 함께 SKIP이다. LLM에 달린 일이라 FAIL로 보지 않는다.
      - 1~3 중 하나가 FAIL이면 나머지는 SKIP이다.
      - 연결 실패와 응답 모양 오류는 FAIL이고 멈추지 않는다.
      - FAIL이 있으면 종료 코드 1이다.
    - 옵션: `--base`, `--world`(교체된다고 알린다), `--poll`, `--timeout`
    - 〔설계 메모〕 FD 2단계의 `llm_calls=0`은 `ImportReport`에 없는 필드다. 불러오기 `ok`와 지역 12로 본다. LLM 0회는 BR-U2-28 테스트가 지킨다.
  - 15.2 테스트 `tests/test_live_scenario.py` 9
    - 실제 API를 프로세스 안에서 키 없이 조립해(TP-U8-8 조립) TestClient 어댑터로 끝까지 돌린다(9 PASS, 5 SKIP). world id 둘(`emberleaf`, `emberleaf-live` 다시 매김)로 돌린다.
    - 흉내 서버로 본 판정: LLM 있음 전부 PASS, 씨앗 안 됨 SKIP, 너무 빠른 전파 FAIL, 스택 꺼짐(1 FAIL + 13 SKIP, 종료 1), 연결 거부, 실패한 run과 끝나지 않는 run, `main` 옵션
    - 변이 5건 모두 잡음: 먼 지역 단언, 게이트, 종료 코드, 씨앗 SKIP, id를 이름으로 찾기
  - 〔발견·수정〕 키 없는 조립 테스트(`tests/api/test_keyless_api.py`)의 fixture에 문제가 있었다.
    - `KnowledgeContainer(params=None)`로 조립해서 `GET /region`이 500이었다(제품 코드는 `assemble_knowledge`라 문제없음).
    - 실제 API로 시나리오를 돌리다 드러났다. fixture를 `assemble_knowledge(shared)`로 바꿨다. TP-U8-8 docstring의 "production way"에 맞는 조립이다.
  - 문서: operations.md U8 절과 README 개발 절에 시나리오 명령 한 줄
  - 15.3 실제 실행은 Build & Test(운영자, 또는 사람이 허락한 이 호스트의 포트 덮어쓰기 기동)에서 한다. 아직 하지 않았다.
  - 게이트: pytest 933, ruff·black clean(`scripts` 포함), mypy 11
- **Step 16** (검증·요약)
  - 16.1 게이트: pytest 933, vitest 197, ruff·black(`locus api tests scripts`) clean, tsc clean, mypy 11, `npm audit --omit=dev` 0, `dangerouslySetInnerHTML` 0
  - 250줄 게이트(NFR-7의 god component 기준으로 읽었다)
    - U8이 250줄을 넘긴 컴포넌트 둘을 나눴다.
      - `GmHub.tsx`: 275 → 228(일괄 생성·재생성을 `features/gm/useBulkRumors.ts` 훅으로)
      - `AugmentPanel.tsx`: 258 → 182(질문 카드를 `features/editor/AugmentQuestion.tsx`로)
      - vitest 197 그대로이고, S13·S28·#5 변이를 다시 잡았다.
    - 남긴 것은 §6에 적었다.
  - 16.2 이 요약의 §3~§9

## 3. 바뀐 파일 (영역별)
- **shared**: `models/{enums,graph,io,__init__}.py`(EventSeed, 사건 열거형 이동, 스냅샷 unscoped 규칙), `storage/{base,neo4j_repo,graph_mapping,persistence}.py`(EventSeed 라벨, `replace_edges`, `edges_touching`)
- **knowledge**: `loader.py`(씨앗 읽기, 지역 없는 씨앗 빼기)
- **world**
  - `worldfile/{schema,remap,export,import_}.py`(`event_seeds`)
  - `editor/*`(씨앗을 지우는 지역 삭제, U3 이월 9a)
  - `demo/__init__.py` + `demo/worlds/`(매니페스트, Emberleaf World File·메모·지도)
  - `augmentation/*`·`wiki/admin.py`(9b)
  - `ingestion/service.py`(9c)
  - `npc_drafts.py`(9e)
  - STATUS docstring 넷
- **play**
  - `event/{service,seeds}.py`(SeedService)
  - `storage/{memory_repo,postgres_repo}.py`(`update_event_contributions`, `for_update`)
  - `distortion_service.py`, `gm/narrator.py`, `turn/advancer.py`, `rumor/{spread,generator,service}.py`(9d)
- **api**
  - `main.py`(`/api/capabilities`, 422 bytes)
  - `deps.py`(`need_service`), `errors.py`(SeedAlreadyRunning 409), `schemas.py`(DemoInfoOut, SeedView, WorldInfo)
  - `uploads.py`(root_path, 여유)
  - `routers/{world,world_editor,gm}.py`
- **CLI**: `__main__.py`(`world build --demo`, `world demo --name`, WorldCatalog)
- **web**
  - 새 파일: `capabilities.ts`, `features/home/DemoCard(s).tsx`, `features/gm/{SeedPanel.tsx,useBulkRumors.ts}`, `features/editor/AugmentQuestion.tsx`, `ui/{LlmNotice,InProgressBadge}.tsx`
  - 고친 파일: `api/{http,world,gm,meta}.ts`, `types.ts`, `i18n.ts`, 홈·에디터·GM·플레이 화면과 패널(Step 10·11)
  - 지운 파일: `features/play/LlmBanner.tsx`
- **배치**: `docker-compose.yml`, `.dockerignore`, `web/{Dockerfile,.dockerignore,nginx.conf}`, `env.example`, `scripts/setup-volumes.sh`, `web/package.json`·lock(react-router 7.18.4), `.github/workflows/ci.yml`
- **메타·문서**: `pyproject.toml`, `requirements.txt`, `README.md`, `CLAUDE.md`, `web/README.md`, `aidlc-docs/operations/operations.md`, 〔U8 정정〕(U3 BLM §1.4, U3 nfr-light §3)
- **스크립트**: `scripts/live_scenario.py`
- **테스트**
  - 새 파일: `tests/{test_demo_as_data,test_packaging,test_live_scenario}.py`, `tests/api/{test_seeds_api,test_keyless_api}.py`, `tests/shared/test_event_seed.py`, `tests/{world/editor,world/augmentation,play}/test_u3_review_carry.py`, `tests/fixtures/aldermoor/`(옛 데모 이동), `web/src/__tests__/capabilities.test.ts`
  - 고친 파일: 각 경계의 기존 테스트(의도된 변경은 주석으로 표시)

## 4. 검증 번호 → 테스트
| 번호 | 테스트 |
|---|---|
| TP-U8-1·2, EX-5·6 | `tests/world/worldfile/test_worldfile.py`(씨앗 왕복, 재매핑, 씨앗 없는 옛 파일, 없는 지역의 씨앗) |
| TP-U8-3, EX-7 | `tests/world/editor/test_region_delete.py`(씨앗 삭제, 끊고 재시도), `web` `editor.test`(계획의 씨앗 수) |
| TP-U8-4, EX-9·10·11 | `tests/world/test_demo.py`(데모 모양, 경로 무게 표, 합의·전해 들음, 행적 3턴, 매니페스트 항목 검사) |
| TP-U8-5, EX-4 | `tests/api/test_seeds_api.py`(시작 201·두 번째 409·해소 뒤 다시 201, 닫힘·바쁨·없음) |
| TP-U8-6 | `tests/test_demo_as_data.py`(`locus`·`api`·`web/src`) |
| TP-U8-7 | `tests/test_packaging.py`(requirements·MIT·설명·STATUS·README 첫 줄·프로필) |
| TP-U8-8, EX-8 | `tests/api/test_keyless_api.py`, `web` `home.test`(안내·[바로 플레이] 켜짐), `editor.test`(초안·만들기 끔), `gm.test`(LLM 버튼 끔) |
| EX-1·2·3·12·13·14 | `web/src/__tests__/home.test.tsx` |
| BR-U8-36 | `tests/test_live_scenario.py`(실제 API 프로세스 안 실행 + 흉내 서버) |

## 5. U3 리뷰 이월의 위치
| 항목 | 단계(커밋) |
|---|---|
| #10 | 9d `4d29984` |
| #12 | 서버 9b `3135873`, 패널 11b `acb47e7` |
| #13 | 9a `87d4603` |
| #14·#15 | 11a `c85609b` |
| S01 | AppNav 10 `dbcf861`, 나머지(세션 띠·문구) 11a |
| S02·S04·S08·S13·S14 | 11c `d4d147f` |
| S03·S09·S10·S15 | 9b |
| S05·S21(화면)·S23·S24·S25·S31 | 11a |
| S06·S28 | 11b |
| S07·S19·S20·S27 | 9c `2c85b3c` |
| S11 | C17과 같이(9a 서버, 11a 웹) |
| S12·S21(서버)·S26·S29·S30·S32 | 9a |
| S16 | 알려진 한계(§6, operations.md) |
| S17·S18 | 9d |
| S22 | 9e |
| C1 | 11a |
| C2 | 서버 9b, 웹 11b |
| C3·C4·C6·C11 | 9a |
| C5 | 서버 10 `dbcf861`(9.3 체크했으나 Step 9 커밋에 빠져 있었다), 웹 11a |
| C7·C9·C13·C15 | 9c |
| C8 | 훅 10, BuildPanel·WorldFileBar 11a |
| C10 | 9b |
| C12 | 11a |
| C14 | 10 |
| C16 | 9d |
| C17 | 서버 9a, 웹 11a |
| 설계 메모 9(nginx) | 12 `4eeb1a9` |
| 설계 메모 10(409 모양) | 10(`openSessionsOf`) |
| 문서(503 문장, 지식 삭제·번역, BLM §1.4, nfr-light §3) | 14 `552b003` |

## 6. 이탈·알려진 한계
- **US-1.1 "명령 하나"**: 사람의 결정(Infra Q1=B)으로 시작이 준비 명령(`setup-volumes.sh`)과 기동 명령 둘이다. README 시작 절이 두 줄로 적는다.
- **S16**: 보강 답의 변경 기록은 주시 노드 주변 엣지 차이다. 그래서 그 답의 임베딩 호출(약 1초) 사이에 한 지도 저장이 섞일 수 있다. 제작자 한 명 전제(A-4) 안의 한계로 operations.md에 적었다.
- **PostgreSQL 행 잠금(#10)**: 오프라인 테스트는 `FOR UPDATE`의 실제 동시성을 돌리지 못한다(SQLite가 무시함). 운영자 확인 몫이다.
- **250줄 게이트에서 남긴 것**
  - `neo4j_repo.py`(249 → 306): 포트 메서드 둘을 더한 저장소 어댑터라 컴포넌트가 아니다.
  - `scripts/live_scenario.py`(350): 혼자 도는 스크립트라 한 파일이 의도다.
  - 테스트 파일 둘(`home.test` 277, 에디터 `test_u3_review_carry` 278)
  - 데모 World File(데이터 1691줄)
  - U8 이전부터 250줄을 넘던 파일(`postgres_repo.py`, `advancer.py`, `i18n.ts` 등)은 고친 곳만 손댔다.
- **dev 의존성 audit**: 전체 `npm audit`에는 dev 의존성 4건(browserslist 등)이 남아 있다. 게이트는 `--omit=dev`(FD Q5=A)라 손대지 않았다.
- **설계 메모(코드)**
  - S23: 포인터는 svg가 아니라 지역 표식이 잡는다(클릭을 잡은 요소로 보내는 브라우저에서도 지역 고르기가 살게).
  - 라이브 시나리오 2단계: `ImportReport`에 `llm_calls`가 없어서 `ok`와 지역 12로 판정한다.
  - 10단계: 10a(왜곡도)와 10b(대화)로 나눴다.
- **기록(늦게 바로잡은 것)**
  - C5 서버 커밋: 9.3에 체크했지만 커밋에 빠져 있었다. Step 10에서 넣었다.
  - S01: 세션 띠와 문구를 Step 10에서 빠뜨렸다. Step 11a에서 넣었다.
  - 키 없음 안내: 켜는 법이 빠져 있었다. Step 14에서 더했다.
  - 키 없는 테스트 fixture: `KnowledgeContainer(params=None)` 조립이었다. Step 15에서 고쳤다.

## 7. 변이 결과
| 단계 | 결과 |
|---|---|
| 10 | 18건 중 17 잡음. 남은 1은 같은 동작(`useCapabilities` 캐시 확인) |
| 11a | 20/20 |
| 11b | 8/8. `detailOf`는 단언을 정확한 문장으로 바꾼 뒤 잡았다 |
| 11c | 7/7 |
| 13 | 4/4 |
| 14 | 2/2 |
| 15 | 5/5. 같은 동작인 변이 1건은 의미 있는 변이로 바꿨다 |
| 16 | 추출 뒤 다시 3/3(S13, S28, #5) |
| 2~9 | 단계별 기록(§2)에 적은 대로 모두 잡음 |

## 8. 남은 결정 (U8 범위 밖, U3 리뷰 설계 메모)
1. **전역 지식의 자리**
   - 지금: 전역 지식은 스코프가 없다. 그래서 에디터 어디에도 나오지 않고, 보강도 묻지 않는다.
   - 정할 것: 전역 탭을 둘지, 스코프 없음 목록에 전역 절을 둘지.
2. **"맞음"이 wiki_conflict를 끝내는 방법**
   - 지금: "맞음"은 신뢰도만 올린다. 같은 질문이 다시 나오고, 빈 변경이 쌓여 되돌리기를 막는다.
   - 정할 것: (지식, 지형) 판정을 "확인함"으로 기억할지, 그 선택지를 뺄지.
5. **보강 예산 모델(U3 #8)**
   - 정할 것: 다시 탐지의 따라잡기를 시작 때만 할지, 바뀐 것에 예산을 남길지, NFR-5 확인을 고칠지.
   - 이 답이 BR-U3-41·NFR-5 문구를 정한다.

## 9. 운영자 확인 (사람이 할 일)
- **compose 기동** (Infra R-01): `./scripts/setup-volumes.sh` → `.env` 두 값 → `docker compose --profile service up -d --build` → 다섯 서비스 healthy, :3000에서 [바로 플레이]
  - 이 호스트는 7474·7687을 다른 컨테이너(`sigraph-neo4j-1`)가 쓴다. `.env`에 `NEO4J_HTTP_PORT`·`NEO4J_BOLT_PORT`를 더해 띄운다. 그 컨테이너는 멈추지 않는다.
- **라이브 시나리오(15.3)**: 띄운 스택에 `python scripts/live_scenario.py`를 돌린다. 키가 없으면 9 PASS·6 SKIP, 키가 있으면 15단계 모두 PASS가 기대값이다(프로세스 안 실행과 같음, §10).
- **CI 첫 실행**: 브랜치를 원격에 push하면 네 작업이 돈다. 배지와 이미지 작업의 데모 확인을 본다.
- **PostgreSQL 동시성(#10)**: 실제 PG에서 GM 설정 ∥ 사건 해소를 겹쳐 돌려, 해소된 사건이 되살아나지 않는지 본다.

## 10. U8 리뷰 후속 (code-review-01, 사람의 선택 A, 2026-10-01)
리뷰 기록은 `code/reviews/code-review-01.md`다. 정확성 지적 15건이 모두 재현으로 확인됐다. 사람의 선택 A에 따라 #1~#8(#5는 (b)만)을 Build & Test 전에 고쳤다. 나머지는 다음 주기 목록(아래)에 올렸다.

| # | 고친 것 | 커밋 |
|---|---|---|
| 1 | 데모 카드의 첫 불러오기를 `replace=false`로 보낸다. 서버의 409 "world already exists"는 [지금 월드로/새로 불러와] 질문(에디터는 그대로 열기)으로 바뀐다. 그래서 목록이 아직 없거나 실패했거나 낡아도 묻지 않고 교체하지 않는다. FC §2.3을 정정했다 | `377e80c` |
| 2 | 화면: 쉬는 패널을 닫으면 입력·파일·리포트를 잊고(U3 #14), 빌드 중에 닫으면 그대로 둔다(다시 열면 진행 중 표시와 꺼진 [만들기], 끝나면 리포트). 숨은 파일은 빌드가 끝날 때 비운다. 부모의 열 때마다 key 바꾸기는 지웠다. 서버: `WorldBuilder`가 월드마다 한 번에 빌드 하나만 받는다. 둘째는 `BuildInProgressError` 409이고, 세 빌드 라우트가 이를 받는다 | `377e80c` |
| 5(b) | 쥠 다시 읽기 횟수를 state로 둔다. 실패한 읽기도 다음 읽기를 예약한다 | `377e80c` |
| 4 | S29: 저장된 DIRECT 스코프 엣지 값과 비교한다. 이미 어긋난 엣지도 다음 저장에서 고쳐진다(U3 설계 메모 4). C11: 지식·NPC·엔티티 모두 검색 문서를 비교 기준인 노드보다 먼저 쓴다. 그래서 끊긴 편집을 다시 보내면 끝난다 | `6111fd2` |
| 6 | 검사를 통과한(`revert_started`) 되돌리기가 끊겼으면, 재시도는 각 노드·엣지가 "변경이 남긴 대로"이거나 "변경 전"이면 받아들이고 멱등 쓰기를 모두 다시 한다. 둘 다 아닌 것만 바깥 편집(409)이다. `is_undone`·`finish_revert`는 지웠다 | `2db1856` |
| 7 | wiki 검색이 한 번 실패하면 그 탐지의 남은 조회를 멈춘다(탐지마다 실패 한 번). 다음 탐지는 다시 해 본다(S09) | `c2fcf4b` |
| 8 | `Issue.connection`에 탐지기의 `ConnectionKey`를 싣는다. 질문 이름, 주시 범위, prior 답이 그것을 읽는다("a\|b\|kind"를 다시 쪼개지 않는다). 지역 id에 `\|`가 있어도 run이 시작되고 답·되돌리기가 된다 | `e6b4951` |
| 3 | 라이브 시나리오에 6a(대화 마침)를 더했다. 그 지역 NPC에게 한 줄 하고 `end_talk`를 보내면 판단이 일어난다(BR-U6-7). 전할 만한 판단이 있는데 소문이 없으면 FAIL, 없으면 9·11이 까닭과 함께 SKIP이다. 9·11은 그 세션의 모든 행적 소문을 센다(도착 행적이 목초지의 한 칸을 먼저 쓸 수 있다). 11은 T+2인지 먼저 본다. FD BLM §7을 정정했다(턴 번호가 하나씩 밀림) | `54e306c` |

- **새 테스트**
  - web: `home.test` 2(#1), `editor.test` 3(#2), `play.test` 1(#5(b))
  - pytest
    - `test_build` 2, `test_uploads` 1(#2)
    - 에디터 `test_u3_review_carry` 3(#4)
    - 보강 `test_u3_review_carry` 5(#6 셋을 매개변수로 + 바깥 편집, #7, #8)
    - `test_live_scenario`: 가짜 LLM을 붙인 실제 API에서 15단계 모두 PASS(판단 T3, 한 칸 T4, Ironcrag 없음 T5). 판단 없음 SKIP, 전할 만한데 소문 없음 FAIL, T+2 확인
- **의도된 변경**
  - `home.test`: 첫 불러오기 `replace:false` 둘. "월드 없음 + 열린 세션" 경우를 "목록이 모르는 월드" 둘로 바꿨다.
  - `test_services`: 색인 실패 뒤 노드가 없다.
  - `test_live_scenario`: 키 없는 실행 9 PASS·6 SKIP, 흉내 서버는 `end_talk`에서 씨앗
- **변이**: 30건 모두 잡았다.
  - 처음에 셋이 살았다: #2의 빌드 중 닫기 갈래, #8의 `_watched`, #3의 T+2. 테스트를 강화해 잡았다(진행 중 메모 단언, 되돌리기 단언, 두 턴짜리 기다리기 서버).
- **앞선 기록의 정정**
  - Step 9b의 "409가 나지 않는다"(S03)는 그래프 쓰기 뒤에서 끊긴 경우만 맞았다. 이제 모든 자리에서 맞다(#6).
  - Step 11c의 "s2 읽기가 실패해도 s1의 플레이어·표식이 남지 않는다"(S14)는 늦게 온 s1 답에서는 틀린다(리뷰 #14, 다음 주기).
  - Step 15의 "키 없이 9 PASS·5 SKIP"은 이제 9 PASS·6 SKIP이다.
- **다음 주기 목록**(리뷰 기록에 상세)
  - 정확성 #9~#15
    - #9 다른 두 사건의 동시 해소
    - #10 World File 절 사이 중복 id와 라벨 없는 삭제
    - #11 매니페스트 `name` ≠ 파일 `world.id`
    - #12 씨앗 시작 경쟁
    - #13 `needs`가 대상 종류를 보지 않음
    - #14 PlayerStrip의 늦은 답
    - #15 일괄 생성의 503 문구
  - 그밖에 §3 상한 밖 22건, §2 정리 11건, 설계 메모 13건, #5 (a)(`turn_running`이 GM 보유를 포함할지)
  - **화면 고도화**(사람의 지시, 2026-10-02): 첫 동작 화면은 확인했고, 고도화는 후속 태스크다
- **배포 결정 둘**(Build & Test 전, 사람의 선택 A·A)
  - 설계 메모 13: nginx에 빌드 경로 전용 location을 두고 600초로 했다(나머지 `/api`는 130초).
  - 설계 메모 11: `license = "MIT"`, `license-files = ["LICENSE"]`, 빌드 요구 `setuptools>=77`로 바꿨다. app 이미지가 `LICENSE`를 복사한다.
  - 정정: Infra §3.2, BR-U8-29, operations.md
  - 확인
    - app 이미지: `License-Expression: MIT`, `License-File: LICENSE`(Metadata 2.4), `check_packaged()` [], `import api.main`
    - nginx: `-t`가 통과한다. 버리는 네트워크에 둔 흉내 `app`으로 두 location이 모두 프록시함을 봤다. 확인용 컨테이너·네트워크·이미지는 지웠다.
  - 테스트: `test_packaging`(SPDX·`setuptools>=77`, Dockerfile이 LICENSE를 복사함), 변이 잡음
- **게이트**: pytest 948, vitest 202, ruff·black clean, tsc clean, mypy 11, `npm audit --omit=dev` 0
