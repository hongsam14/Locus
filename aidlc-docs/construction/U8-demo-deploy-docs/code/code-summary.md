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
