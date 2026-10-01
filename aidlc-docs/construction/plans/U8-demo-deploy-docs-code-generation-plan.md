# U8 데모·배포·문서 — Code Generation 플랜 (Part 1)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 코드 생성 계획입니다. 처음 온 사람이 준비 명령과 기동 명령으로 띄우고, 클릭 한 번으로 데모 월드에서 플레이하게 합니다. 앞 유닛이 넘긴 결함도 닫습니다.

이 플랜이 Code Generation Part 2의 유일한 기준입니다. 단계마다 체크박스를 고치고 단계마다 커밋합니다.

## 유닛 컨텍스트
- 단위: `inception/application-design/purpose-restructure/unit-of-work.md` U8(실행 8/8, 마지막 유닛)
- 스토리: US-1.1, US-1.2, US-1.3, US-1.4, US-7.3, US-7.5, US-7.6(P2)
- 승인된 설계
  - FD: `construction/U8-demo-deploy-docs/functional-design/{domain-entities,business-logic-model,business-rules,frontend-components}.md` (BR-U8-1~36, TP-U8-1~8, EX-1~14)
  - Infra: `construction/U8-demo-deploy-docs/infrastructure-design/{infrastructure-design,deployment-architecture}.md`
  - 플랜 질문·답: `plans/U8-demo-deploy-docs-functional-design-plan.md`(넘겨받은 것 포함), `plans/U8-demo-deploy-docs-infrastructure-design-plan.md`
- 기대는 것(바꾸지 않는 계약): World File v1(U2), 에디터 쓰기 원칙·지역 삭제 순서(U3, 〔U8 추가〕 씨앗 단계), GM 리스(U7 #2), 사건 서비스(Phase 2), 번역 정리(U5)
- 경계: shared ← knowledge ← {world, play}. `EventCategory`·`EventLifecycle`은 shared로 옮긴다(FR-A2의 의도된 예외, FD R-07). `tests/test_boundaries.py`가 지킨다
- 새 외부 의존 없음. 웹은 react-router만 고친 판으로 올린다(BR-U8-35)

## 기준선 (Step 1.1에서 다시 잰다)
| 항목 | 값 |
|---|---|
| pytest | 857 |
| vitest | 129 |
| mypy (`locus api`) | 11 (6 파일) |
| ruff · black · tsc | clean |
| `npm audit --omit=dev` | moderate 2 (react-router) |

## 이월 결정
### 승인 게이트의 감수한 위험 (FD·Infra)
| 출처 | 결정 | 단계 |
|---|---|---|
| FD R-05 | 라이브 시나리오 T3→T4: 단계 10 앞에 `WaitAction` 1턴을 넣는다(Saltwake, T4). 단계 10·11의 단언 시점은 T4 그대로 | 1.2, 15 |
| FD R-12 | `api.startSeed` 반환 타입은 웹의 기존 사건 타입(`EventOut`과 같은 모양) | 1.2, 10 |
| FD R-13 | Ironcrag의 전해 들음 목록은 "표에서 0.15 이상 0.5 미만인 마을 모두"이고, 테스트는 표 값에서 계산한다 | 1.2, 6 |
| Infra R-01 | compose의 상대 `device`는 이 호스트에서 절대 경로로 풀린다(`docker compose config`). 라이브 시나리오 1단계가 실제 기동을 확인하고, 실패하면 `${PWD}/data/…`로 바꾼다 | 12, 15 |
| Infra R-02 | web healthcheck는 `wget -q --spider http://127.0.0.1/` | 12 |
| Infra R-03 | nginx `client_max_body_size 49m`(앱 상한 48 MiB보다 조금 크게): 상한 판정과 JSON 413은 앱이 한다 | 12 |
| Infra R-04 | (a) `pyproject.toml` package-data를 `world/demo/worlds/*.json`, `world/demo/worlds/*/*`로 바꾼다. (b) 이미지 확인은 패키지 함수 `locus.world.demo.check_packaged()`(아래 5.4)를 `python -c`로 부른다 | 5, 12 |
| Infra R-05 | 12.1에서 ruff·black·tsc·`npm ci`의 로컬 기준선을 먼저 확인한다. CI npm 캐시는 `cache-dependency-path: web/package-lock.json`. `web/.dockerignore`에 `tsconfig*.tsbuildinfo` | 12 |
| Infra R-06 | 포트 변수를 `env.example`(주석)과 compose 머리 주석에 적는다. 문서의 `down`은 `--profile service --profile tools` | 12, 14 |

### U3 code-review-01 이월 (사람의 선택 A) — 정확성
| # | 결정 | 단계 |
|---|---|---|
| #10 | `DistortionService.set_region_distortion`이 ACTIVE 사건을 UoW 안에서 읽는다. PG 저장소에 `update_event_contributions(session_id, event_id, contributions, *, only_if_status="active")`(조건부 UPDATE, contributions만)를 두고 Q6=A 지우기가 이것을 쓴다. 사건 해소도 UoW 안에서 읽고 `WHERE status='active'`로 쓴다. 인메모리 저장소도 같은 의미 | 9 |
| #12 | 패널: 404면 `GET runs/{id}`로 run이 정말 없는지 본다. 있으면 서버 문장을 오류로 보인다. 서버: 엔티티 확인·고침은 위치를 바꾸지 않으면 위치 재검사를 건너뛴다(`update_entity(..., recheck_location=False)`) | 9, 11 |
| #13 | (a) NPC 집 옮기기: 새 LIVES_IN → 노드 교체 → 옛 LIVES_IN 삭제. 옛 집은 LIVES_IN 엣지에서 읽는다(재시도가 남은 옛 엣지를 찾는다). (b) `set_prior_ref`: 지운 뒤 다시 쓰지 않고 같은 키의 쌍을 **엣지 교체**로 쓴다. 지금 Neo4j `upsert_edges`는 `SET r += props`(병합)라 비운 prior를 지우지 못하고 가짜(통째 교체)와 다르다. 그래서 포트에 `replace_edges(edges)`(Neo4j `MERGE … SET r = $props`, identity 속성 포함; 가짜는 통째 교체)를 더하고 계약 테스트로 묶는다. 끊기 테스트를 두 경로로 넓힌다(TP-U3-2a 방식) | 9 |
| #14 | `BuildPanel` 부모가 열 때마다 `key`를 바꾼다(EditorPage·HomePage). 닫으면 파일·리포트 상태가 사라진다 | 11 |
| #15 | 지도 연결 도구: 같은 쌍·종류가 있으면 폼을 그 값으로 채운 "고치기"로 열고, 저장 본문에 기존 근거·prior·출처를 싣는다 | 11 |

### U3 code-review-01 이월 — 상한 밖 정확성(§3, S01~S32)
| # | 결정 | 단계 |
|---|---|---|
| S01 | AppNav에 `/` 링크(Locus 글자를 링크로). WorldFileBar·i18n 문구 둘 고침 | 10 |
| S02 | PlayPage: `turn_running`인데 실행 중인 run이 없으면 1초 뒤 한 번 더, 최대 5번 다시 읽는다(GM 쓰기 보유) | 11 |
| S03 | 되돌리기: 검사를 통과하면 쓰기 전에 `reverting` 표시를 둔다. 다시 보낼 때 지금 노드가 `nodes_before`와 같으면 이미 되돌린 것으로 보고 `reverted`를 세운다 | 9 |
| S04 | DialoguePanel: `readOnly` 변화만으로는 오류를 지우지 않는다 | 11 |
| S05 | 지역 삭제 409: `HttpError.body`를 파싱해 `delete.region.blocked`와 세션 목록을 보이고 확인을 끈다 | 11 |
| S06 | 보강 고치기·추가 카드에 제목·신뢰도 입력 | 11 |
| S07 | 지도 JSON이 객체가 아니면 422, `RecursionError`도 422(지도·World File 업로드) | 9 |
| S08 | `timelineText`: 템플릿의 자리표시자를 params와 대조한다(채운 문장을 검사하지 않음) | 11 |
| S09 | 보강 wiki 조회 예외는 캐시하지 않는다 | 9 |
| S10 | 보강 답·되돌리기 라우트가 지운 지식 id로 `purge_translations`를 부른다 | 9 |
| S11 | C17과 같이 | 9, 11 |
| S12 | 종류별 삭제: 노드가 다른 라벨로 있으면 검색 삭제를 건너뛰고 404 | 9 |
| S13 | GmHub: 상한 읽기가 실패하면 다음 `/state` 읽기에서 고친다 | 11 |
| S14 | PlayerStrip에 `key={session.id}` | 11 |
| S15 | 보강 답 뒤 다시 탐지가 실패하면 질문 목록을 비우고 run 상태를 다시 읽게 한다(같은 답 두 번 적용 막기) | 9 |
| S16 | 알려진 한계로 적는다(제작자 한 명 전제 A-4): 답의 변경 기록은 주시 노드에 닿은 엣지 차이라 그사이 지도 저장이 섞일 수 있다. code-summary·operations에 한 줄 | 16 |
| S17 | `_narrate`: 프롬프트를 try 앞에서 만들고 LLM 호출만 감싼다(서술기가 `prompt()`·`call()`을 나눠 준다) | 9 |
| S18 | 전파·씨앗·생성이 지지도를 쓸 때 `settle` | 9 |
| S19 | `WorldInputs`에 개수·길이 상한(multipart 상한과 같은 값). JSON `POST /build`도 같은 규칙 | 9 |
| S20 | `BodyLimitMiddleware`가 `root_path`를 떼고 길을 비교한다. World File 길의 요청 한도를 칸 상한 + multipart 여유(20 MiB + 1 MiB)로 둔다 | 9 |
| S21 | 편집 쓰기 앞에서 WorldMeta로 월드를 확인한다(없으면 404). 에디터의 "월드 없음" 화면에서 지역 추가 도구를 끈다 | 9, 11 |
| S22 | NPC 초안 프롬프트: 세 절을 하나의 MATERIAL 머리말 아래에 둔다 | 9 |
| S23 | MapOverlay: pointerdown에서 `setPointerCapture`, `onPointerCancel`·`onLostPointerCapture`로 끌기를 끝낸다 | 11 |
| S24 | WorldFileBar: 고른 뒤 `e.target.value = ""` | 11 |
| S25 | ConfirmDelete: 여섯 항목 모두 수와 이름 | 11 |
| S26 | 가짜 그래프를 (world, label, id)로 잡는다. 편집 쓰기는 id가 다른 라벨로 있으면 400 | 9 |
| S27 | `_finite`가 bytes를 `errors="replace"`로 푼다 | 9 |
| S28 | 보강 패널 입력을 `issue_key`로 잡는다 | 11 |
| S29 | 신뢰도를 바꾸는 쓰기(보강 확인·고침, `PUT knowledge`)가 그 지식의 DIRECT 스코프 엣지 값도 고친다 | 9 |
| S30 | 지운 지역의 부모가 월드에 없으면 `new_parent_id = None` | 9 |
| S31 | RegionInspector·UnscopedPanel: 읽기 순번을 두고 마지막 것만 그린다 | 11 |
| S32 | `POST …/regions/{r}/knowledge`에 있는 id면 400 | 9 |

### U3 code-review-01 이월 — 정리(§2, C1~C17)
| # | 결정 | 단계 |
|---|---|---|
| C1 | 끌기는 PUT과 지역 상태만 고치고 `rev`를 올린다(인스펙터 다시 읽기, U3 #1 유지). `listWorlds`는 마운트·불러오기·빌드 뒤에만. 스코프 없음 수는 export의 `unscoped_knowledge_ids`(C5) | 11 |
| C2 | 질문에 `type`과 `needs`(입력 종류)를 싣고, 연결 대상은 `ConnectionKey`를 싣는다. 웹은 그것을 읽는다. 바뀐 것의 이름은 저장된 제목 | 9, 11 |
| C3 | `EditorWrites.delete_held(world_id, id, label)` 하나를 지식·NPC·엔티티·prior 삭제가 쓴다(S12 포함). WikiAdmin은 EditorWrites를 받는다 | 9 |
| C4 | `Editors.prior_ids`·`get_node` 지움(쓰는 곳 정리), `delete_any`는 `{knowledge, entity}` 표 | 9 |
| C5 | 스코프 없음은 스냅샷의 `unscoped_knowledge_ids` 하나. export에 싣고 웹도 쓴다 | 9, 11 |
| C6 | `_path`는 `level_path`, `regions._connection_edges`는 `connections.edge_keys`, `require_region` 중복 정리 | 9 |
| C7 | 열린 세션 필터는 `SessionService.open_sessions()`(`SessionStatus` 비교) 하나. CLI는 `WorldCatalog`. `_need`는 `api/deps.py`로 | 9 |
| C8 | `http.ts`에 `openSessionsOf(err)`, `useReplaceConfirm` 훅. BuildPanel·WorldFileBar·DemoCard가 함께 쓴다 | 10, 11 |
| C9 | `WikiAdmin.refs(world_id)` 하나(스냅샷 한 번)로 usages·broken | 9 |
| C10 | 그래프 포트 `edges_touching(world_id, node_ids)`(Neo4j `WHERE a.id IN $ids OR b.id IN $ids`, 가짜·OpenSearch 무관). 보강 기록이 쓴다 | 9 |
| C11 | 편집 쓰기가 문서 글이 같으면 임베딩을 건너뛴다 | 9 |
| C12 | UnscopedPanel `run`에서 `load()` 제거 | 11 |
| C13 | `WorldInfo(WorldSummary)` 상속. `EditorRegionViewOut`은 mypy 때문에 U3에서 독립 모델로 둔 것이라 그대로 두고 까닭을 docstring에 적는다 | 9 |
| C14 | 쓰지 않는 i18n 키 21개 삭제(U8 FD의 둘 포함) | 10 |
| C15 | `build_world_upload`: 개수 검사 바로 뒤 열린 세션 확인 | 9 |
| C16 | 사건 create는 `require_region`이 돌려준 지역 이름, resolve는 트랜잭션 전에 이름을 한 번. advancer는 `names`를 넘겨 쓴다 | 9 |
| C17 | 클라이언트는 `title.trim()`만, 서버 create·upsert가 빈 제목을 `fallback_title`로 | 9, 11 |

### U3 code-review-01 이월 — 문서·설계 메모
| 항목 | 결정 | 단계 |
|---|---|---|
| operations.md:96(503 문장), World editor 절의 지식 삭제·번역 문장 | 고친다 | 14 |
| BLM §1.4:77 남은 문장, nfr-light §3 리버스 프록시 문장 | 〔U8 정정〕 | 14 |
| 설계 메모 9(nginx) | Infra R-03 | 12 |
| 설계 메모 10(409 본문 모양) | C8의 `openSessionsOf`가 셋을 다 읽는다(`open_sessions`, `busy_sessions`, `session_ids`) | 10 |
| 설계 메모 1·2·5(전역 지식의 자리, "맞음"과 wiki_conflict, 보강 예산 #8) | U8 범위 밖. code-summary의 "남은 결정"에 적는다 | 16 |

## 실행 원칙
- 기존 파일은 그 자리에서 고친다. 사본이나 `_v2`는 없다.
- 각 단계는 그 단계의 테스트가 GREEN인 상태로 끝내고, 단계마다 커밋한다.
- 시그니처를 바꾸는 하위 단계는 호출처 전부를 같은 하위 단계에서 고친다.
- 의도된 동작 변경으로 바꾸는 테스트에는 `# U8 intended change: <BR 또는 이월 번호>`를 단다. 지우는 테스트는 없다(옮기는 테스트는 import·경로만 바꾼다).
- 규칙 번호(BR-U8-n)와 검증 번호(TP-U8-n, EX-n), 이월 번호(#n, Sn, Cn)를 테스트 이름이나 docstring에 적는다.
- 고친 결함마다 변이 한 번(고친 줄을 되돌림)으로 테스트가 잡는지 보고 code-summary에 적는다.
- 데모 이름과 지역 id는 코드에 쓰지 않는다(BR-U8-1). 테스트는 패키지 파일과 `tests/fixtures/aldermoor/`를 입력으로 쓴다.
- 이 호스트의 다른 Neo4j 컨테이너(`sigraph-neo4j-1`)는 멈추지 않는다.

## 승인 때의 실행 메모 (코드 플랜 검토 01, Accepted risk, 2026-10-01)
- 〔실행 메모 R-01〕 순서: Step 6(Emberleaf 콘텐츠·매니페스트 교체)을 5.6(Aldermoor 이동)보다 먼저 한다. 5.6은 Step 6 뒤에 하고, 옛 파일을 읽는 테스트(`test_worldfile.py:40`, `test_demo.py`, `test_cli.py`, `test_world_api.py`)는 `tests/fixtures/aldermoor/`의 매니페스트를 `DemoWorlds(worlds_dir=…)`로 주입하거나(CLI는 `LOCUS_DEMO_DIR` 대신 테스트에서 `WORLDS_DIR` monkeypatch) 단언을 emberleaf로 바꾼다(데모 자체를 보는 테스트). `test_region_delete`는 인라인 빌더라 옮기지 않는다.
- 〔실행 메모 R-02〕 이미지 확인은 설치본에서 돈다: `docker run --rm -w /tmp locus-app python -I -c "…"`, 그리고 `locus.__file__`이 site-packages 아래임을 단언한다. `api`는 설치되지 않으므로(`packages.find`는 `locus*`) `import api.main` 확인은 `-w /app`에서 따로 한다(이미지에 `api/`가 있다는 US-1.1 확인). `DemoWorlds.problems -> list[str]`(조립 때 검사 결과)를 공개하고, `importer=None`이면 `list`·`info`·`problems`는 되고 `load`만 RuntimeError다.
- 〔실행 메모 R-03〕 포트: `GraphRepository.replace_edges`·`edges_touching`, `EventStore.update_event_contributions`. 구현: Neo4j 어댑터, `tests/shared/storage/fakes.py` InMemoryGraphRepository, 손으로 쓴 가짜 둘(`tests/world/services/test_services.py:33`, `tests/knowledge/test_query.py:64`, 프로토콜 충족만), PG 저장소(`postgres_repo.py` 저장소 + UoW 스토어), 인메모리(`memory_repo.py` 저장소 + UoW 스토어). C10의 "가짜 무관"은 틀렸다.
- 〔실행 메모 R-04〕 5.1·5.3에 `locus/world/topology/naming.py:3` docstring, `locus/world/__init__.py`의 `load_demo_world` 내보내기 정리를 더한다. TP-U8-6 검색 범위는 `locus/`, `api/`, `web/src/`이고 `web/src/__tests__/`, `locus/world/demo/worlds/`, `tests/`는 뺀다.
- 〔실행 메모 R-05〕 Step 9·11은 영역별로 커밋한다: 9a 에디터 쓰기(C3·C4·C6·C11·S12·S21·S26·S29·S30·S32·#13), 9b 보강(C2·C10·S03·S09·S10·S15·#12), 9c 업로드·한도·API(C7·C9·C13·C15·S07·S19·S20·S27), 9d 플레이(#10·C16·S17·S18), 9e 초안(S22), 11a 에디터 화면, 11b 보강 화면, 11c 플레이·GM 화면. 시그니처 변경의 호출처 수는 그 커밋의 code-summary 기록에 적는다(`_need` 18곳, `open_sessions` 필터 18곳 등).
- 〔실행 메모 R-06·사람의 결정 A〕 react-router-dom을 7.18.x로 올린다(6.x에는 고친 판이 없다). 선언형 API만 쓰므로 바뀌는 곳은 import·타입 정도로 본다. 연쇄 수정이 라우터 밖으로 번지면 멈추고 묻는다.

## Steps

### Step 1 — 기준선·정정
- [x] 1.1 기준선을 다시 잰다(위 표). `npm ci`(깨끗한 설치)가 lock 그대로 되는지 본다(Infra R-05).
- [x] 1.2 승인 산출물 정정(〔Step 1.2 정정〕): FD BLM §7(R-05 WaitAction 단계), FD frontend-components §3(R-12), FD domain-entities §5.2·BR-U8-11·EX-9(R-13 문장), Infra §3.1(R-04 package-data는 바뀜), Infra §1 web healthcheck 주소(R-02), §3.2 nginx 49m(R-03).
- [x] 1.3 code-summary 초안(`construction/U8-demo-deploy-docs/code/code-summary.md`)에 기준선을 적는다.

### Step 2 — shared: 씨앗 모델과 저장 (domain-entities §2·§3)
- [x] 2.1 `locus/shared/models/enums.py`에 `EventCategory`·`EventLifecycle`·`CATEGORY_DEFAULT_LIFECYCLE`(+ `default_lifecycle`)를 옮긴다. docstring에 FR-A2 예외 한 줄. `locus/play/models.py`는 같은 이름을 다시 내보낸다(호출처 무변경).
- [x] 2.2 `EventSeed`(`shared/models/graph.py`, 필드·제약은 domain-entities §2), `WorldSnapshot.event_seeds: list[EventSeed]`.
- [x] 2.3 저장: `neo4j_repo.NODE_LABELS`에 `EventSeed`, `graph_mapping.seed_to_node`·`node_to_seed`, `persist_graph(…, seeds=)`, 로더가 라벨을 읽는다(`knowledge/loader.py`). 가짜는 라벨 목록이 없어 그대로.
- [x] 2.4 테스트: 매핑 왕복, 로더가 씨앗을 싣는다, 경계 테스트 GREEN.

### Step 3 — World File의 `event_seeds` (BR-U8-12·13, TP-U8-1·2, EX-5·6)
- [x] 3.1 `worldfile/schema.py`: `SECTIONS`·`WorldFile.event_seeds`. `remap.py`: `file_ids`·`set_world_id`·재매핑(씨앗 id·`region_id`)·`validate_references`(지역 없으면 빼고 error). `export.py`: 스냅샷의 씨앗, `sort_sections`. `import_.py`: 쓰기.
- [x] 3.2 `tests/world/strategies.py`의 World File 생성기에 씨앗을 더한다(지역 id에서 뽑음).
- [x] 3.3 테스트: TP-U8-1(왕복), TP-U8-2(재매핑), EX-5(옛 파일 → `[]`), EX-6(끊긴 씨앗 → error·`ok=false`). 기존 U2 왕복 PBT가 씨앗과 함께 GREEN.

### Step 4 — 에디터 지역 삭제의 씨앗 (BR-U8-14, TP-U8-3, EX-7)
- [x] 4.1 `editor/regions.py`: 계획에 `seed_ids`, ③ 뒤 ④ 앞에 그 지역 씨앗 삭제(그래프 일괄 하나), 보고 `seeds_deleted`. `editor/models.py`의 `RegionDeletePlan`·`RegionDeleteReport` 필드.
- [x] 4.2 U3 생성기(`editable_worlds`)에 씨앗을 더하고 TP-U3-2·2a 신탁이 `EventSeed.region_id`를 센다. 구조 단언(9 + NPC 수)은 +1로 고친다(`# U8 intended change: BR-U8-14`).
- [x] 4.3 테스트: TP-U8-3, EX-7, API 삭제 계획·보고 필드.

### Step 5 — 데모는 데이터다 (BLM §1, BR-U8-1~5, TP-U8-6, EX-11)
- [x] 5.1 `locus/world/demo/__init__.py`: `DemoSources`, `DemoInfo`(+ `start_region_id`, `credits`, `sources`), 조립 때 한 번 검사·보관(경고 한 번), `list`·`info`·`load`, `build_from_sources`가 항목 소스를 읽는다. 상수(`_DEMO_MEMO`, `_DEMO_MAP`, `_MAP_IMAGE`), `load_demo_world()`, 이름 검사를 지운다. 경로는 매니페스트 폴더 밖 거절. `importer`는 선택 인자(None이면 `load`가 RuntimeError).
- [x] 5.2 API `GET /demos` 응답: `name`, `title`, `description`, `credits`, `start_region_id`, `has_sources`(`api/schemas.py` `DemoInfoOut`). 소스 없는 데모의 소스 빌드는 404.
- [x] 5.3 CLI: `world build --demo <name>`(옛 `--demo-sources` 대신), 별칭 `build-world --demo`는 소스가 있는 첫 항목. 도움말의 Aldermoor 문구 정리. `npc_drafts.py:112` 예시 정리(FD R-10).
- [x] 5.4 `check_packaged() -> list[str]`(같은 모듈): 설치된 매니페스트를 `DemoWorlds(None)`으로 읽어 항목 0개, 검사 실패 항목, 없는 소스 파일을 문제 목록으로 돌려준다. CI 이미지 작업이 `python -c "from locus.world.demo import check_packaged as c; p=c(); print(p); raise SystemExit(bool(p))"`로 쓴다(Infra R-04).
- [x] 5.5 `pyproject.toml` package-data를 `world/demo/worlds/*.json`, `world/demo/worlds/*/*`로.
- [x] 5.6 옛 Aldermoor: World File과 `examples/demo_world/*`(memo.txt, map.json, map.png, generate_map.py, README)를 `tests/fixtures/aldermoor/`로 옮긴다. 일반 입력으로 쓰던 테스트(`test_worldfile`, `test_region_delete`, `test_world_api`, `test_cli`, `test_demo`의 소스 빌드)는 픽스처 경로를 쓴다. `examples/`를 지운다.
- [x] 5.7 테스트: TP-U8-6(코드 검색, 검색어는 새·옛 데모 이름과 지역 id·이름), EX-11(잘못된 항목은 빠지고 나머지는 보임), 경로 탈출 거절, `check_packaged`, CLI `--demo`.

### Step 6 — Emberleaf Isle 콘텐츠 (domain-entities §5, BR-U8-6~11, TP-U8-4, EX-9·10)
- [x] 6.1 `locus/world/demo/worlds/emberleaf.world.json`(v1): 지역 12, 연결 10쌍(두 방향, 무게·종류·근거, 1·2·9번은 `wiki_prior_ref`), 마을 지식(DIRECT 2개 이상, 소문거리 셋 이상), 지방 지식 1~2, 전역 1~2, 엔티티 약 8, prior 2, NPC 15, 씨앗 3. 글은 영어, 이름은 창작(원작 고유명사 없음).
- [x] 6.2 `locus/world/demo/worlds/emberleaf/memo.md`(설정 글), `emberleaf/map.json`(구조 지도: 지역·연결).
- [x] 6.3 매니페스트: `emberleaf` 항목 하나(제목·설명·credits·`start_region_id=region-saltwake`·sources). Aldermoor 항목은 지운다.
- [x] 6.4 테스트(`tests/world/test_demo.py`): TP-U8-4(개수·계층·마을당 NPC 1~3·지방/섬 0·연결 쌍·종류 섞임·시작 지역에서 도달·막힌 쌍의 우회·씨앗 2~3), 최대 곱 무게표(domain-entities §5.2, 셋째 자리), 합의 결과(EX-9: 강 마을 셋 상호 DIRECT 그대로, Ironcrag의 전해 들음 = 표에서 0.15 이상 0.5 미만 마을 모두, FD R-13), 전파 계획(EX-10: Ambermeadow 행적 → 1턴 Saltwake·Sylvarch, Ironcrag는 3턴 전 없음), 금지어(BR-U8-10), 불러오기 LLM 0회.

### Step 7 — 씨앗 시작 (BLM §3, BR-U8-15~18, TP-U8-5, EX-4)
- [x] 7.1 `EventService.create_event`에 키워드 `provenance: Provenance | None = None`, `timeline_extra: Mapping[str, str] | None = None`.
- [x] 7.2 `locus/play/event/seeds.py` `SeedService`: `list_seeds(session_id) -> list[SeedView]`, `start(session_id, seed_id) -> SessionEvent`. `SeedAlreadyRunningError`(`play/errors.py`) → `api/errors.py` 409. `SeedView` 모델.
- [x] 7.3 `play/wiring.py` `PlayContainer.seeds`. GM 라우트 `GET /sessions/{sid}/seeds`, `POST /sessions/{sid}/seeds/{seed_id}/start`(GM 리스 `_idle` 의존, 201 `EventOut`). 스키마 `SeedViewOut`.
- [x] 7.4 타임라인 `event_created` payload에 `seed_id`·`seed_title`.
- [x] 7.5 테스트: TP-U8-5, EX-4(시작 → ACTIVE·타임라인 → 409 → 해소 → 201), 닫힌 세션 409, 턴 중 409, 없는 씨앗 404, LLM 0회.

### Step 8 — LLM 유무와 503 (BLM §4.1, BR-U8-23·24, TP-U8-8)
- [x] 8.1 `GET /api/capabilities` → `{llm, vlm, embedding}`(`api/main.py`, 조립된 shared 공급자).
- [x] 8.2 TP-U8-8: 공급자 없이 조립한 앱에서 BLM §4.1 표 경로가 503, 키 없이 쓰는 대표 경로(데모 불러오기, 세션 시작, 이동 턴, 씨앗 시작, 보강 시작, `POST priors`)가 2xx. 표 밖에서 500이 나오면 같은 규칙으로 막고 표에 더한다.

### Step 9 — U3 이월: 백엔드
- [x] 9.1 정확성: #10, #12(서버), #13
- [x] 9.2 상한 밖: S03, S07, S09, S10, S12, S15, S17~S22, S26, S27, S29, S30, S32
- [x] 9.3 정리: C2(서버), C3, C4, C5, C6, C7, C9, C10, C11, C13, C15, C16, C17(서버)
- [x] 9.4 테스트: 항목마다 하나 이상(재현 조건 그대로). #10은 SQLite 위 `PostgresPlayRepository`로 해소 ∥ 설정 순서를 강제한 결정적 테스트. #13은 끊기 테스트. S26은 가짜 라벨 키 테스트. 의도된 변경 주석.

### Step 10 — 프런트엔드: U8 기능 (frontend-components)
- [x] 10.1 `api/*`·`types.ts`: `capabilities()`, `DemoInfo` 확장, `loadDemo(worldId, name, options)`(기본값 없음), `buildWorldDemo` 삭제, `listSeeds`, `startSeed`(사건 타입, R-12), `RegionDeletePlan.seed_ids`·`RegionDeleteReport.seeds_deleted`, `unscoped_knowledge_ids`(C5). `http.ts` `openSessionsOf(err)`(세 모양, 설계 메모 10)와 `useReplaceConfirm`(C8).
- [x] 10.2 `src/capabilities.ts`(`useCapabilities`, `llmOff`), `ui/LlmNotice.tsx`(LlmBanner 대체, PlayPage도), `ui/InProgressBadge.tsx`.
- [x] 10.3 `features/home/DemoCards.tsx`·`DemoCard.tsx`, `HomePage`(DEMO 상수 삭제, 카드 늘 보임, LlmNotice), `AppNav`(`/` 링크, 월드 없으면 에디터 링크 `/`, S01).
- [x] 10.4 `features/gm/SeedPanel.tsx`, `GmHub`(자리·LlmNotice·LLM 버튼 끄기), `ManualTurnPanel`·`RumorPanel` 끄기, `EditorPage`·`BuildPanel`(만들기 끄기, 컨셉 아트 InProgressBadge)·`NpcDraftCards` 끄기, 503 문구 `llm.required`(DialoguePanel 포함).
- [x] 10.5 i18n: 새 키(FC §4), C14의 21개 삭제, `timelineText`의 `seed_title`.
- [x] 10.6 테스트: `home.test`(EX-1·2·3·12·13·14, 카드 둘, 인자 순서), `gm.test`(SeedPanel, 끄기), `editor.test`(끄기, 배지, 삭제 계획 씨앗 수), `components.test`(AppNav, 의도된 변경), `capabilities.test`.

### Step 11 — U3 이월: 프런트엔드
- [ ] 11.1 정확성: #12(패널), #14, #15
- [ ] 11.2 상한 밖: S02, S04, S05, S06, S08, S13, S14, S21(화면), S23, S24, S25, S28, S31
- [ ] 11.3 정리: C1, C2(웹), C8(BuildPanel·WorldFileBar), C12, C17(웹)
- [ ] 11.4 테스트: 항목마다 하나 이상(jsdom이 재현하지 못하는 S23·S24는 핸들러 단위로).

### Step 12 — 배치 (Infra-light)
- [ ] 12.1 로컬 기준선: ruff, black --check, tsc, `npm ci`(Infra R-05).
- [ ] 12.2 `docker-compose.yml`: 인프라 포트 `127.0.0.1:${VAR:-n}`(NEO4J_HTTP_PORT, NEO4J_BOLT_PORT, OPENSEARCH_PORT, SESSION_DB_PORT, DASHBOARD_PORT), dashboard는 `tools` 프로필, web healthcheck `wget -q --spider http://127.0.0.1/`(R-02), 머리 주석(다섯 서비스·세 프로필·준비 명령·포트 변수, R-06). bind mount는 그대로(Q1=B).
- [ ] 12.3 `.dockerignore`에 `web`, `scripts`. `web/Dockerfile` `node:22-alpine` + `npm ci`. `web/.dockerignore`에 `tsconfig*.tsbuildinfo`(R-05). `web/nginx.conf` `client_max_body_size 49m`(R-03).
- [ ] 12.4 `env.example`: 머리말 중복 삭제, 포트 변수 주석(R-06). `scripts/setup-volumes.sh` 안내 문구(실제 프로필).
- [ ] 12.5 react-router를 고친 판으로 올린다. `npm audit --omit=dev` 0건.
- [ ] 12.6 `.github/workflows/ci.yml`: backend·frontend·audit·images(Infra §5). seed 기록, `cache-dependency-path`, `concurrency`.
- [ ] 12.7 로컬 확인: `docker build`(app·web)와 이미지 안 `check_packaged()`·`import api.main`(이 호스트에서 빌드는 된다).

### Step 13 — 메타 (BR-U8-29·30·31)
- [ ] 13.1 `pyproject.toml`: `license = { text = "MIT" }`, 설명(§0 영어판), `[project.urls] Repository`.
- [ ] 13.2 `requirements.txt` = `dependencies`. TP-U8-7(`tests/test_packaging.py`).
- [ ] 13.3 진행 중 기능 넷의 docstring `STATUS:`: `wiki/cross_world.py`, `ingestion/concept_art_ingestor.py`, `augmentation/graph.py`(이미 있음, 문구 맞춤), `wiki/distiller.py`(wiki 순환 구조 개선 — 다음 사이클).

### Step 14 — 문서 (BLM §5, BR-U8-28·31·32)
- [ ] 14.1 `README.md` 전면 다시 쓰기(A8-1, Infra 시작 절: 준비 명령 + 기동 명령, 포트 덮어쓰기, `down`, 키 없이 둘러보기, 진행 중 기능 표, 개발·게이트, 디렉터리, MIT·데모 크레딧, CI 배지).
- [ ] 14.2 `CLAUDE.md`: Project Overview(§0), Status(U8), Build/Run 명령(`emberleaf`, 프로필), 레이아웃(데모 폴더, `features/home/`, `SeedPanel`, CI).
- [ ] 14.3 `operations.md`: U8 절(데모 데이터, 씨앗, capabilities, 프로필·포트, init-schema 다시 돌리기, CI, 라이브 시나리오), 낡은 줄(Web UI (U10), 데모 버튼, `/health`, `--legacy-peer-deps`, 503 문장, 지식 삭제·번역 문장), `aldermoor` → `emberleaf` 대응 한 줄, CLI 교체의 번역 공백(A8-10).
- [ ] 14.4 `web/README.md`(데모 카드, 씨앗 패널, 키 없음 안내). 〔U8 정정〕: U3 BLM §1.4:77, U3 nfr-light §3 리버스 프록시 문장.

### Step 15 — 라이브 시나리오 (BLM §7, BR-U8-36)
- [ ] 15.1 `scripts/live_scenario.py`(표준 라이브러리 `urllib`): 단계 1~12와 R-05의 기다리기, PASS·FAIL·SKIP, 키 없으면 LLM 단계 SKIP, FAIL이면 종료 코드 1. `--base http://localhost:8000`, `--world emberleaf`.
- [ ] 15.2 단위 테스트: 가짜 HTTP 응답으로 판정·SKIP·종료 코드(서버 없이).
- [ ] 15.3 실제 실행은 Build & Test(운영자 또는 사람이 허락한 이 호스트의 포트 덮어쓰기 기동)에서 한다. 첫 확인 항목은 compose 기동(Infra R-01).

### Step 16 — 검증·요약
- [ ] 16.1 전체 게이트: pytest, vitest, ruff, black --check, tsc, mypy(≤ 11), `npm audit --omit=dev` 0건, `dangerouslySetInnerHTML` 0곳, 새·고친 파일 250줄 이하.
- [ ] 16.2 code-summary: 기준선과 결과, 바뀐 파일, 검증 번호 → 테스트, 이월 결정의 위치, 이탈·알려진 한계(S16, US-1.1 두 명령), 변이 결과, 남은 결정(설계 메모 1·2·5), 운영자 확인(라이브 시나리오, compose 기동, CI 첫 실행).

### Step 17 — 게이트
- [ ] 17.1 코드 게이트를 제시한다. 승인 뒤 `/code-review`를 돌린다. 그다음 Build and Test.

## 스토리 추적
| 스토리 | 단계 |
|---|---|
| US-1.1 한 번에 기동 | 12(compose·이미지·CI images), 14(README 시작), 15(1단계) |
| US-1.2 README | 14 |
| US-1.3 원클릭 데모 | 2~7(씨앗·데모 데이터·콘텐츠), 10(카드), 15 |
| US-1.4 키 없이 둘러보기 | 8, 10 |
| US-7.3 진행 중 표시 | 10(배지), 13.3, 14 |
| US-7.5 메타 | 12.3·12.5(npm ci·audit), 13 |
| US-7.6 CI | 12.6, 14(배지) |
