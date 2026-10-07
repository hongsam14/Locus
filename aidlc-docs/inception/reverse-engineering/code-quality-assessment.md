# Code Quality Assessment

> Reverse Engineering — Follow-up Cycle (2026-10-07). 기준 커밋 `240e82d` (`feat/purpose-restructure`). 이 문서는 2026-09-29 판(기준 `ee61277`)을 대체한다.
> **[재현]** = 실제로 돌려 확인했다. 인메모리 가짜, 운영 SQL 어댑터를 SQLite 위에 올린 것, 가짜 API 위의 실제 프론트 빌드를 썼다. **[코드]** = 코드를 읽고 판단했다.
> 재현 스크립트는 세션 스크래치에서만 돌렸고 저장소에 남기지 않았다. 항목마다 재현 조건을 적어 두어 다시 돌릴 수 있다.
> 결함 번호: 캐노니컬 월드 `RE-W`, 플레이·API `RE-P`, 프론트엔드 `RE-F`, 도구·인프라 `RE-T`, 화면 다듬기 `UX-`(`screen-inventory.md`). 이월 항목은 원래 번호(U8 #9 등)를 쓴다.

## Test Coverage

- **Overall**: Good.
  - 백엔드 라인 커버리지는 **94%**다(`locus` 94.0%, `api` 92.9%, 9,923문 중 605 미실행).
  - 오프라인 **pytest 948**(43 s)과 **vitest 202**(7.8 s)가 모두 GREEN이다.
  - 2026-09-29에는 pytest 281, vitest 24, 87%였다.
- **패키지별**: `play` 97.8%, `knowledge` 95.7%, `world` 93.5%, `localization` 89.6%, `shared` 88.9%, CLI `__main__` 75.3%, `api/routers` 92.5%.
- **70% 미만 모듈 6개**:
  - `localization/wiring.py` 45%: 실제 조립 경로를 지나는 테스트가 없다.
  - `augmentation/graph.py` 46%: 진행 중 모듈이다.
  - `shared/llm/openai_provider.py` 47%, `shared/storage/schema.py` 55%, `opensearch_repo.py` 66%, `llm/factory.py` 69%: 실제 어댑터라 오프라인에서 돌지 않는다.
  - `api/main.py`의 `lifespan`(115-146)은 어떤 테스트도 지나지 않는다. 여기에는 시작 때 끊긴 턴 정리와 종료 처리가 있다.
- **Unit Tests**: 경계별 테스트 수는 play 394, world 224, api 120, shared 114, localization 41, 루트 29, knowledge 26이다.
  - 목적별로 다시 나누면 play 47.7%, world 28.7%, infra 15.2%, localization 4.9%, knowledge 3.6%다. 목적이 솔로 TRPG이므로 play가 가장 두꺼운 것은 목적과 맞다.
  - 다만 "지역마다 다르게 안다"의 핵심인 `knowledge/`의 직접 테스트는 34건뿐이다. 합의 전파의 순서 결함(RE-W01)이 잡히지 않은 까닭이다.
- **속성 테스트(PBT)**: `@given`이 29파일에 55개 있다. 순수 함수와 직렬화 왕복을 덮는다(합의 경로 가중, 동역학, 이동, 전파 계획, NPC 범위, World File 왕복, 지역 삭제 재시도 안전 등).
- **경계 테스트**: `tests/test_boundaries.py`가 다섯 경계의 import 행렬, 상대 import 금지, 최상위 모듈 제한을 강제한다.
- **Integration Tests**:
  - 라이브 통합 테스트는 **없다**.
  - PostgreSQL 어댑터는 SQLite로 검증한다. 그래서 `FOR UPDATE` 행 잠금은 오프라인에서 돌지 않는다. SQLite는 이 구문을 컴파일하지 않고 [재현], 인메모리는 `for_update`를 무시한다.
  - Neo4j·OpenSearch는 드라이버를 흉내 내서 시험한다.
  - 라이브 검증은 운영자가 `scripts/live_scenario.py`(15단계)로 한다. 2026-10-02에 키를 넣고 15/15 PASS였다. CI 밖이다.
- **프론트**:
  - 커버리지 도구가 없다(`@vitest/coverage-*` 미설치).
  - 시각 회귀·반응형·접근성·브라우저 E2E 테스트가 없다. jsdom이라 레이아웃 결함을 잡지 못한다.
  - act() 경고가 6개 테스트에서 난다.

## Code Quality Indicators

- **Linting**:
  - ruff(0.16.2)와 black(26.5.1)은 clean이다.
  - mypy는 **11건(6파일)**으로 기준선과 같다(2026-09-29에는 16건).
    - langchain 타입 4건, 지연 클라이언트의 Optional 표기 4건, Optional 좁히기 2건, 튜플 길이 1건이다.
    - **CI에 mypy가 없어** 기준선이 늘어도 잡히지 않는다.
  - 프론트는 `tsc --noEmit`만 있고 **ESLint가 없다.** 그런데 소스에 `eslint-disable` 주석이 13개 있다. 훅 의존성 누락은 리뷰로만 잡힌다(RE-F15).
- **CI**: `.github/workflows/ci.yml`이 있다(backend·frontend·audit·images). PR #4의 첫 실행은 모두 GREEN이었다.
  - 빠진 것: mypy, `api` 커버리지, 커버리지 하한, `scripts/` lint, 의존성 고정.
  - Python 버전이 다르다. CI는 3.11이고 로컬은 3.14.4다.
- **Code Style**: 일관된다. 생성자 DI, 경계별 조립 함수와 타입 컨테이너, 포트·어댑터, 순수 함수 코어, 기능별 단일 책임 서비스를 쓰고 파사드가 없다. 남은 중복과 우회는 § F에 있다.
- **Documentation**: Fair.
  - README는 대체로 정확하다.
  - **`CLAUDE.md` Status 문단이 자기 안에서 어긋난다.**
    - "948 pytest + 202 vitest"(현재값과 맞음)와 "986 offline tests GREEN (857 + 129)"(U3 시점의 수)가 함께 있다.
    - "in progress"와 "COMPLETE"도 함께 있다.
    - "compose ports on 127.0.0.1"이라고 쓰지만 app·web은 0.0.0.0이다.
  - 낡은 docstring과 주석이 여럿 있다(§ G).

## Technical Debt

### A. `operations/next-cycle.md` 이월 항목의 현재 상태

| 항목 | 지금 | 근거 |
|---|---|---|
| 화면 고도화 | 다듬을 곳 42건을 정리했다(UX-01~42) | `screen-inventory.md` |
| 실제 PostgreSQL 동시성 (U3 #10) | **코드로는 닫혔다**. GM 설정은 ACTIVE 사건을 `FOR UPDATE`로 읽고 기여를 `WHERE status='active'`로만 쓴다(`play/distortion_service.py:68-77`, `storage/postgres_repo.py:341-367`). 남은 것은 둘이다. (i) 오프라인 테스트는 이 잠금을 돌릴 수 없다 [재현]. (ii) 되먹임 몫을 트랜잭션 밖에서 읽어, 같은 지역 설정 둘이 겹치면 둘 다 `feedback_share_cleared: 0.2`를 적는다 [재현] | 운영자 확인은 그대로 필요하다 |
| U8 #9 다른 두 사건의 동시 해소 | **남아 있다 [재현]**. 해소는 자기 사건 행만 잠그고, 지역 왜곡도는 잠그지 않고 읽어 절대값으로 쓴다(`play/event/service.py:143-157`). 두 해소를 겹치면 둘 다 RESOLVED가 되고 타임라인도 둘 다 복원했다고 적는데, 지역은 0.45/0.42/0.36(기준 0.3)에 남는다 | — |
| U8 #10 World File 중복 id, 라벨 없는 삭제 | **남아 있다 [재현, 인메모리]**. `file_ids`가 집합이고 `validate_references`는 참조만 본다(`world/worldfile/remap.py:18-30,138-234`). 씨앗 id를 지역 id로 바꾼 파일이 `ok=True`에 경고 0으로 들어온다. Neo4j에서는 라벨마다 유일이라 두 노드가 공존한다. 그 상태에서 라벨 없는 `get_node`/`delete_node`(`shared/storage/neo4j_repo.py:199-207,282-286`)가 같은 id의 지역을 연결째 지운다 [코드] | 뿌리: RE-W13 |
| U8 #11 매니페스트 `name` ≠ 파일 `world.id` | **남아 있다 [재현]**. `_check`가 `world.id`를 보지 않는다(`world/demo/__init__.py:169-191`). 불러온 월드에 시작 지역이 없다 | `operations.md:400`도 일치 조건을 적지 않는다 |
| U8 #12 씨앗 시작 경합 | **남아 있다 [재현]**. 두 시작이 모두 201이고 ACTIVE 사건이 둘 생겨 한 턴 상승이 두 배가 된다(`play/event/seeds.py:54-68`). 웹의 [시작]도 요청 중에 켜져 있어 두 번 누르면 두 번 나간다 | — |
| U8 #13 `needs`가 대상 종류를 안 봄 | **남아 있다 [재현], 원인은 백엔드**다. `NEEDS`가 이슈 종류만 키로 쓴다(`world/augmentation/questions.py:39-46`). 엔티티 질문에 제목 칸이 생기고, 제목만 보내면 빈 변경이 기록되며 같은 질문이 다시 나온다 | 웹은 그대로 그릴 뿐이다 |
| U8 #14 PlayerStrip 늦은 답 | **남아 있다 [재현]**. 효과에 정리 함수가 없다(`web/src/features/gm/PlayerStrip.tsx:30-53`). 옛 세션의 답이 새 세션 지도에 플레이어 표식을 그린다 | — |
| U8 #15 일괄 생성 503 | **남아 있다 [코드]**. `useBulkRumors.ts:34-38`이 실패를 수로만 세고 503 본문을 버린다 | — |
| U8 #5(a) `turn_running`의 정의 | **바뀌지 않았다 [재현]**. GM 리스만 쥔 동안에도 `turn_running=True`이고 run이 0개다. 플레이어의 `act`는 내부값 "(run gm)"이 붙은 409를 받는다(`play/turn/guard.py:37,44-47`) | 결정 대기 |
| U8 리뷰 §3(상한 밖 정확성) | 영역별로 다시 확인했다. **아직 유효한 것**: 피드백 몫 이중 기록 [재현], 외톨이 서로게이트 → 500 [재현], 깊은 중첩 `RecursionError` 500, 소스 빌드 라우트가 소스 확인 전에 세션 관문을 봄, 주입한 앱의 `/health`가 늘 ok, 제안 상한 복구 경로, `listSeeds` 실패가 "씨앗 없음"으로 보임 [재현], DemoCard가 언마운트 뒤에도 이동함, DemoCard `ok=false` 교체 뒤 목록을 안 읽음, 홈에서 "에디터"가 활성 [재현], 끌기가 옛 지역 전체를 PUT, 추가한 지역이 선택되지 않음 [재현], 409 원문 셋, 제목 칸 라벨, nginx 이름 풀이 | 22건 전부를 하나씩 다시 대조하지는 않았다. 원 기록: `construction/U8-demo-deploy-docs/code/reviews/code-review-01.md` §3 |
| U8 리뷰 §2(정리) | C1(인스펙터가 쓰기 뒤 두 번 읽음), C4(503 규칙 우회 넷, "wiki admin (LLM provider)" 문구), C6(LLM 필요 처리 복사), C9(씨앗 시작이 스냅숏 3번 읽음)이 남아 있다 | — |
| U8 설계 메모 | 11·13은 정해졌다(SPDX, nginx 600 s). **12(GM 짧은 쓰기의 세션 직렬화)는 구현되지 않았다**. `hold`가 카운트만 올린다(`play/turn/guard.py:76-81`). 12를 정하면 #9, #12, 피드백 몫, RE-P01, RE-P06이 함께 닫힌다. RE-P02는 닫기도 같은 잠금을 쥘 때 닫힌다. 메모 6(지도를 누르면 탭이 바뀜)은 그대로다(UX-24) | 나머지 메모는 원 기록을 본다 |
| U3 메모 1 전역 지식의 자리 | **미결**. 전역 지식은 스코프가 없다. 인스펙터·스코프 없음 목록·보강 탐지 대부분이 전역 지식을 보지 않는다. 전역 지식을 나열하는 API도 없다 | `world/ontology/builder.py:49-50` |
| U3 메모 2 "맞음"이 wiki_conflict를 끝내는 방법 | **미결 [재현]**. "맞음"은 신뢰도만 올린다. 판정 캐시 키가 `(id, statement, terrain)`이라 같은 질문이 다시 나온다. 두 번째부터 빈 변경이 쌓여, 앞 변경의 되돌리기(최신부터)를 막는다 | `world/augmentation/apply.py:138-140`, `engine.py:94` |
| U3 메모 5 보강 예산 | **미결**. 다시 탐지할 때마다 판정 최대 20회와 다듬기 5회를 직렬로 돈다. 예산은 60으로 고정이다 | `world/augmentation/service.py:27`, `engine.py:91-110` |
| U3 S16 답의 변경 기록 | **남아 있다 [코드]**. 변경 기록은 엣지 diff라, 그사이 에디터에서 한 저장이 섞인다 | `world/augmentation/apply.py:59-77` |
| 진행 중: 교차 월드 prior 검색 | **늘 0건 [재현, 쿼리 본문 수준]**. 필터는 최상위 `domains`를 보는데 문서는 `meta.domains`에 둔다(`shared/storage/opensearch_repo.py:63-67`, `graph_mapping.py:434-448`). 테스트 스텁과 인메모리 가짜는 이 불일치를 잡지 못한다 | `world/wiki/cross_world.py` |
| 진행 중: 컨셉 아트 수집 | 장마다 VLM 1회와 LLM 1회로 저신뢰 엔티티(상한 0.4)를 만든다. 지식은 만들지 않아 NPC 범위에 들어가지 않는다. 장마다 보강 질문이 하나씩 생긴다 | `world/ingestion/concept_art_ingestor.py` |
| 진행 중: LangGraph 래퍼 | 부르는 곳이 없다. 그런데 `langgraph`가 필수 의존성이다 | `world/augmentation/graph.py`, `pyproject.toml:23` |
| 진행 중: wiki 순환 | 되돌아가는 길이 없다. 에디터·보강·플레이 결과가 prior를 고치지 않는다. 증류 문맥의 지형 목록은 사실상 늘 비어 있다(`EntityType.TERRAIN`을 읽는데 지형은 지역이 됨) | `world/wiki/distiller.py:65` |
| CI 액션 버전 | **그대로**다(Node 20 경고). `ubuntu-latest`가 **2026-10-19**(12일 뒤)에 Ubuntu 26으로 바뀐다 | `.github/workflows/ci.yml` |
| mypy 기준선 | 11건, 같은 집합이다 | — |
| dev npm audit | **4건에서 5건으로 늘었다**(moderate 3, high 2): `@vitest/mocker`, `baseline-browser-mapping`, `browserslist`, `source-map-js`. 모두 `npm audit fix`로 고칠 수 있다 | 런타임(`--omit=dev`)은 0건이다 |
| 라이브 시나리오 10a | 그대로다(`scripts/live_scenario.py:285-293`). 왜곡도가 다른지만 보고, 어느 쪽이 큰지는 보지 않는다. 10b와 12도 내용은 보고만 한다 | — |

### B. 캐노니컬 월드 결함 (새로 찾음)

| # | 심각도 | 내용 | 근거 |
|---|---|---|---|
| **RE-W01** | **medium (목적 직결)** | **합의 전파가 최선 경로가 아니라 먼저 발견한 출처를 고른다.** 지식 하나가 dict 순회에서 처음 나온 출처 지역에 잠긴다. 0.9 경로가 있어도 0.3 경로가 먼저 나오면 hearsay가 된다. Neo4j의 엣지 순서는 정해져 있지 않다. 그래서 같은 월드도 로드할 때마다 "이 지역 NPC가 아는 것"이 달라질 수 있다. `unknown_count`도 과대 계산될 수 있다. 주석("best path weight per knowledge")과도 다르다 | `knowledge/consensus.py:127-152` [재현] |
| RE-W02 | medium | **다른 프로세스가 교체하는 동안 API 캐시가 불완전한 스냅샷을 영구히 잡는다.** `persist_graph`는 노드(WorldMeta 포함)를 먼저 쓰고 엣지를 나중에 쓴다. 그래서 버전 표식이 연결·스코프보다 먼저 최종값이 된다. CLI 교체 중에 API가 읽으면 연결 0·스코프 0인 스냅샷이 새 버전으로 캐시되어 계속 쓰인다. WorldMeta가 없을 때 읽으면 버전 확인 자체를 건너뛴다 | `shared/storage/persistence.py:62-84`, `knowledge/cache.py:57-58` [재현] |
| RE-W03 | low | 캐시 hit 경로의 버전 읽기에 try가 없어 오류가 호출자에게 그대로 간다. hit마다 Neo4j 왕복이 한 번 든다 | `knowledge/cache.py:59` [재현] |
| RE-W04 | medium | **백업이 실패해도 교체가 진행되고 `ok=True`다.** 편집한 월드를 되살릴 길 없이 잃을 수 있다 | `world/build.py:364-381`, `worldfile/import_.py:123-135` [재현] |
| RE-W05 | low–medium | 빌드 전용 힌트(`connection_hints`, `parent_name`, `adjacent_names`)가 Region.attributes째 Neo4j와 World File에 남는다. 그중 일부는 LLM 문맥으로도 들어간다 | `world/topology/builder.py:61-62` [재현] |
| RE-W06 | low–medium | 구조화 지도의 좌표가 숫자가 아니면 빌드 전체가 500이 된다. 모듈 docstring은 "경고로 거르고 계속"이라고 한다. NaN은 1.0이 된다 | `world/ingestion/structured_map_ingestor.py:28-35` [재현] |
| RE-W07 | low | `WikiAdmin.upsert_prior`에 월드 존재 검사와 라벨 검사가 없다. 없는 월드에 넣으면 WorldMeta 없는 유령 월드가 홈 목록에 뜬다 | `world/wiki/admin.py:44-62` [재현] |
| RE-W08 | medium (비용·시간) | 빌드의 LLM·임베딩 호출에 상한이 없고(세기만 함) 모두 직렬이다. 조정기는 고아 엔티티마다 지역 전체를 다시 임베딩한다(엔티티 20 × 지역 30 → 텍스트 620). nginx 600초와 부딪힐 수 있다 | `world/ontology/reconciler.py:143-191` [재현] |
| RE-W09 | low | 세션 DB URL이 늘 조립된다. 그래서 CLI의 "PostgreSQL 없음" 분기가 죽어 있고, PG가 없으면 traceback으로 끝난다 | `shared/config/settings.py:188-199` [재현] |
| RE-W10 | low | 키 없이 `locus world build`를 하면 친절한 메시지 대신 traceback이 난다. 테스트는 이 길을 바꿔 끼워 보지 않는다 | `shared/wiring.py:98-103` [재현] |
| RE-W11 | low | 같은 사실이 속성과 엣지 두 곳에 있다(ABOUT·DERIVED_FROM 등). 지식 PUT은 속성만 고친다. 로더가 어느 쪽을 믿는지가 라벨마다 다르다 | `world/editor/knowledge.py:19-68`, `knowledge/loader.py:60-79` [재현] |
| RE-W12 | low | World File이 한 방향 연결을 경고 없이 받는다. 에디터의 쌍 불변식이 불러오기에서 지켜지지 않는다 | `world/worldfile/remap.py:167-172` [재현] |
| RE-W13 | medium (규모), #10의 뿌리 | 라벨 없는 Cypher가 많다(`MATCH (a {id, world_id})`). 그래서 라벨별 인덱스를 못 쓰고 전체를 훑는다. 노드·엣지 쓰기는 항목마다 auto-commit이라 O(E·N)이고, 중간에 끊기면 반쪽이 남는다 | `shared/storage/neo4j_repo.py:87-297` [코드] |
| RE-W14 | low | 끝점이 없는 엣지는 경고 없이 사라진다 | `neo4j_repo.py:107-121` [코드] |
| RE-W15 | low | OpenSearch 문서 `_id`가 맨 노드 id다. 다른 월드의 같은 id가 서로의 문서를 덮을 수 있다 | `opensearch_repo.py:131` [코드] |
| RE-W16 | low–medium | 월드 전체를 임베딩 호출 한 번에 보낸다. 한도를 넘으면 벡터 없이 색인된다. CLI 불러오기는 임베딩하지 않고 API는 임베딩하므로, 같은 데모도 들어온 길에 따라 kNN 유무가 다르다 | `shared/storage/persistence.py:105-112` [코드] |
| RE-W17 | medium | 빌드 커밋 창이 길다. 온톨로지 LLM 작업이 `delete_world` 뒤에 돌아, 그동안 월드가 없거나 반쪽이다 | `world/build.py:255-272` [코드] |
| RE-W18 | medium (제품) | **빌드는 NPC와 사건 씨앗을 만들지 않고, 교체는 그것들을 지운다.** 소스로 다시 빌드하면 제작자가 더한 NPC·씨앗·보강 답이 백업 파일에만 남는다. README의 "NPC가 만들어집니다"와 다르다 | `world/build.py:296-314` [코드] |
| RE-W19 | low | CLI `--force`는 다른 프로세스의 턴 진행을 모른 채 세션을 닫는다(새 `TurnGuard`) | `locus/__main__.py:95-131` [코드] |
| RE-W20 | low | 재시도가 모든 예외에 걸린다(401·스키마 실패도 3번). VLM은 그림 형식과 무관하게 `image/png`로 보낸다 | `shared/llm/retry.py:79`, `openai_provider.py:84-87` [코드] |
| RE-W21 | low | wiki 조회 기준이 느슨하다(`score_threshold=0.0`). "terrain feature: X" 질의는 낱말 하나만 맞아도 근거가 된다 | `world/wiki/base.py:52,70-98` [코드] |
| RE-W22 | low | 번역 warm에 상한과 묶음이 없다. (항목, 필드)마다 LLM 1회를 직렬로 부르고, 어떤 예산에도 들지 않는다 | `localization/service.py:198-214` [코드] |
| RE-W23 | low | `create_knowledge`의 쓰기 순서가 색인 → 노드 → 스코프다. 중간에 끊기면 스코프 없는 지식이 남고, 같은 id 재시도는 400이다 | `world/editor/knowledge.py:48-60` [코드] |
| RE-W24 | 참고 | kNN 엔진이 nmslib이다(새 OpenSearch에서 deprecated). 기존 인덱스의 차원이 바뀌어도 아무것도 하지 않는다 | `opensearch_repo.py:34-39,119-122` [코드] |

### C. 플레이·API 결함 (새로 찾음)

| # | 심각도 | 내용 | 근거 |
|---|---|---|---|
| RE-P01 | low–medium | **GM 지지도 조정이 취소된 행적의 소문을 되살린다.** 조정은 소문을 UoW 밖에서 읽고 행 전체(`active` 포함)를 다시 쓴다. 그래서 그 사이 커밋된 취소나 재생성의 비활성화가 되돌아간다. 되살아난 소문은 다음 턴에 한 칸 퍼진다. "취소가 그 행적이 낳은 모든 것을 되돌린다"(BR-U6-27)를 깬다 | `play/rumor/service.py:179-198`, `deeds/service.py:315-348` [재현] |
| RE-P02 | low | 세션 닫기는 턴만 보고 GM 쓰기 리스는 보지 않는다. 그래서 LLM GM 쓰기가 닫힌 세션에 소문을 쓴다. 월드 교체의 닫기도 같다 | `play/session_service.py:113-116`, `turn/guard.py:55-65` [재현] |
| RE-P03 | low | 재시작 정리는 run을 `failed/interrupted`로만 바꾸고 보상하지 않는다. 플레이어는 옮겨진 채, 청구된 채 남는다. 도착 행적도 남고 `turn_run_failed` 줄은 없다 | `api/main.py:118-124` vs `play/turn/advancer.py:508-556` [재현] |
| RE-P04 | low | 지역이 월드에서 지워진 뒤에도 그 지역의 ACTIVE 지속 사건이 매 턴 왜곡도 행을 쓴다. GM 목록은 그 행을 숨긴다 | `play/turn/advancer.py:930-957` [재현] |
| RE-P05 | low | 행 쓰기와 그 타임라인 줄이 다른 트랜잭션이다. 사건 생성·제안·승인, 소문 생성, 지지도가 그렇다. U4가 U7로 넘긴 비원자성 가운데 왜곡도 설정만 고쳐졌고, 이 항목은 next-cycle 목록에 없다 | `play/event/service.py:105-112,248-275`, `rumor/service.py:87-89,185-187` [코드] |
| RE-P06 | low | 승인이 상태 조건 없이 읽고 행 전체를 쓴다. 승인이 겹치면 줄이 둘 생기고, 승인과 폐기가 겹치면 어긋난다 | `play/event/service.py:266-286` [코드] |
| RE-P07 | low | 같은 지역의 재생성 둘(또는 생성과 재생성)이 겹치면 새 소문이 두 벌 생긴다 | `play/rumor/service.py:97-177` [코드] |
| RE-P08 | low | GM 수동 턴이 요청 스레드에서 동기로 돈다. 턴당 LLM 8회를 쓰면 nginx 130초를 넘길 수 있다. 그러면 504가 나는데 턴은 서버에서 끝까지 돈다 | `api/routers/gm.py:222-229` [코드] |
| RE-P09 | perf | 턴마다 세션의 모든 활성 소문을 한 행씩 upsert한다(바뀌지 않은 행도). 타임라인 줄도 넣을 때마다 다시 읽는다 | `play/turn/advancer.py:661,713` [코드] |
| RE-P10 | perf | N+1이 있다. 열린 세션마다 `get_player`, 월드마다 `list_sessions`, 제안 초안마다 스냅숏을 읽는다 | `play/session_service.py:144-152` 등 [코드] |
| RE-P11 | debt | 끝없이 자라는 읽기가 있다. GM 타임라인 전체, 플레이어 로그(전체를 읽은 뒤 Python에서 자름), run 목록(결과 JSON 통째)이 그렇다 | `api/routers/gm.py:99-104`, `play/player/service.py:94-100` [코드] |
| RE-P12 | low | 오류 매핑에 빈틈이 있다. 서로게이트는 500 [재현], 깊은 중첩은 `RecursionError` 500이다. `?status=`는 검증 없이 빈 목록을 준다. 플레이어에게 가는 409에 "(run gm)"이 드러난다 | `api/main.py:34-44`, `play/turn/guard.py:37` |
| RE-P13 | low | 범위 밖 GM 입력을 조용히 clamp하고 200을 준다(크기 5 → 1.0, 왜곡도 −1 → 0). 문서에 적힌 설계 선택이 아니다 | `play/event/service.py:98` 등 [코드] |
| RE-P14 | naming | `*_ko` 칸이 실제로는 "기본 대상 언어" 칸이다. `SUPPORTED_LANGS=ja,en`이면 `statement_ko`에 일본어가 들어간다 | `api/schemas.py:71-85` [코드] |
| RE-P15 | low | 플레이어 지역이 지워졌을 때 `/region`은 404인데 `/npcs`는 200 빈 목록이다. 플레이어를 옮길 길도 없다 | `play/npc/dialogue.py:98-107` [코드] |
| RE-P16 | low | 월드 교체 관문의 "mid-turn" 409가 GM 리스 때도 난다. 문구가 틀린다 | `api/routers/world.py:64` [코드] |

### D. 프론트엔드 결함 (새로 찾음)

| # | 내용 | 근거 |
|---|---|---|
| RE-F01 | 첫 세션 읽기가 실패한 뒤 GM [다시 시도]는 세션만 다시 읽는다. 월드는 끝내 읽지 않아 지도가 빈다 | `web/src/routes/GmPage.tsx:60-82,120` [재현] |
| RE-F02 | **[턴 진행]과 GM 쓰기에 진행 중 막기가 없다.** 빨리 두 번 누르면 턴이 둘 넘어간다 | `features/gm/GmHub.tsx:111-140` [재현] |
| RE-F03 | 홈의 시작 폼이 다른 월드에서 고른 지역을 기억했다가 그대로 보낸다 | `features/play/NewSessionForm.tsx:20-23` [재현] |
| RE-F04 | 세션 [닫기]가 확인 없이 영구 종료한다(UX-35) | `SessionBar.tsx:81-91` [코드] |
| RE-F05 | GM 지도 마커가 끌렸다가 놓으면 되돌아간다(UX-36) | `MapOverlay.tsx:40`, `GmPage.tsx:187` [재현] |
| RE-F06 | 빌드 리포트의 "스코프 없음 N"에 처리기가 없다(UX-22) | `BuildReportPanel.tsx:30-33` [재현] |
| RE-F07 | 에디터 `reload()`에 늦은 답 막기가 없다. 실패해도 하위 패널이 다시 읽는다 | `routes/EditorPage.tsx:42-66` [코드] |
| RE-F08 | 턴 run 폴링에 상한과 간격 늘리기가 없다(`for(;;)`, 700ms) | `routes/PlayPage.tsx:131-171` [코드] |
| RE-F09 | 실패하거나 낡은 capabilities를 다시 읽지 않는다 | `capabilities.ts:10-20` [코드] |
| RE-F10 | DeedPanel이 읽기 전에 빈 상태를 보인다(UX-10) | `features/gm/DeedPanel.tsx:24` [코드] |
| RE-F11 | 일괄 실행 중 세션을 바꿔도 진행·알림·옛 세션 다시 읽기가 이어진다 | `features/gm/useBulkRumors.ts:26-52` [코드] |
| RE-F12 | 인스펙터 읽기가 성공해도 오류 줄을 비우지 않는다 | `features/editor/RegionInspector.tsx:58-66` [코드] |
| RE-F13 | 지도 배경 object URL을 해제하지 않는다 | `EditorPage.tsx:157`, `GmPage.tsx:167` [코드] |
| RE-F14 | 세션을 바꿀 때 옛 `session`을 비우지 않아, 새 세션이 올 때까지 옛 세션이 그대로 보인다 | `routes/GmPage.tsx:60-70` [코드] |
| RE-F15 | ESLint가 없다. 훅 의존성 누락(#14, RE-F07 같은 정리 함수 누락)을 도구가 잡지 못한다 | `web/package.json:10` [코드] |

- 늦은 답을 무시하는 방식이 셋 섞여 있다: 시퀀스 ref, 효과 지역 플래그, 라우트 id ref. 시퀀스 ref 방식은 언마운트를 막지 못하고, 이것이 #14의 원인이다.
- 쓰기 래퍼(`run`/`write`/`call`)를 화면마다 따로 둔다.
- 요청 취소(AbortController)는 어디에도 없다. `any`는 0개다.

### E. 도구·인프라·패키징

| # | 내용 | 근거 |
|---|---|---|
| RE-T01 | 고정 대기가 약 11 s로 전체 테스트 시간의 25%다. 계약 테스트 하나는 5 s 시간 초과에 기대어 지나가고, 그 안의 단언 `… or True`는 늘 참이다. retry 테스트 둘은 실제로 3 s씩 잔다 | `tests/play/test_repository_contract.py:268-301`, `tests/shared/llm/test_retry_and_factory.py` |
| RE-T02 | 경고가 52건이다. 51건은 dispose하지 않은 sqlite 엔진의 ResourceWarning으로, Python 3.13 이상에서만 나서 CI(3.11)에서는 안 보인다. 1건은 Starlette의 httpx → httpx2 경고다 | pytest 로그 |
| RE-T03 | CI에 mypy, `api` 커버리지, 커버리지 하한이 없다. Python은 CI 3.11, 로컬 3.14다 | `.github/workflows/ci.yml` |
| RE-T04 | **Python lock 파일이 없다.** 상한 없는 의존성이 런타임 8개, dev 6개다. CI와 Docker는 빌드할 때마다 최신을 받는다(지금이면 SQLAlchemy 2.1, openai 3.x, mypy 2.4) | `pyproject.toml` |
| RE-T05 | 선언과 사용이 어긋난다. `langchain`과 `openai`는 선언했지만 직접 import하지 않는다. `langchain_core`는 쓰지만 선언하지 않았다. `httpx`는 TestClient 테스트 17파일이 필요한데 dev에 없다. `langgraph`는 연결 안 된 모듈 하나만 쓴다 | `pyproject.toml` |
| RE-T06 | app 이미지가 root로 돈다. 베이스 이미지 태그가 움직이고 다이제스트 고정이 없다. neo4j 5.15와 opensearch 2.13.0은 오래된 버전이다 | `Dockerfile`, `docker-compose.yml` |
| RE-T07 | `api`가 휠에 들어가지 않아(`include=["locus*"]`) 이미지의 소스 디렉터리에 기댄다. API 버전은 0.2.0, 패키지는 0.1.0이다. 로컬 `.venv`의 설치 메타데이터는 아직 Proprietary와 옛 Summary다 | `pyproject.toml:49-50`, `api/main.py:148` |
| RE-T08 | `env.example`에 `SESSION_DB_HOST`와 `TRANSLATION_WARM_WORKERS`가 없다 | `shared/config/settings.py:60,138` |
| RE-T09 | app(:8000)과 web(:3000)은 0.0.0.0에 열리고 인증이 없다. README는 의도라고 적었지만 CLAUDE.md는 "127.0.0.1"이라고 적는다 | `docker-compose.yml:145,170` |
| RE-T10 | 프론트에 ESLint와 커버리지 도구가 없다. act() 경고가 6개 테스트에서 난다 | `web/package.json` |
| RE-T11 | `api/main.py` lifespan과 `localization/wiring.py`의 실제 조립을 지나는 테스트가 없다 | 커버리지 |
| RE-T12 | 라이브 시나리오는 `OSError, KeyError, TypeError, ValueError`만 잡는다. 응답 모양이 이상해 `AttributeError`가 나면 FAIL로 기록되지 않고 멈춘다 | `scripts/live_scenario.py:352` |
| RE-T13 | 시각·반응형·접근성·E2E 테스트가 없다(`screen-inventory.md` §6) | — |

### F. 죽은 코드·중복

- **부르는 곳이 없다**:
  - 월드 쪽: `TopologyBuilder.set_wiki`, `OntologyBuilder.set_wiki`, `IngestionService.from_factory`, `KnowledgeContainer.loader`(조립만 하고 안 씀).
  - 플레이 쪽: `TurnGuard.running_run_id`, `ThreadTurnExecutor.pending`, `ConversationStore.list_conversations`(운영), `FeedbackOutcome.raised`, `GmNarrator.narrate`(테스트 전용), `_IN_CHUNK`. play의 `IN`은 실제로 나누지 않는다.
  - `RumorService`의 `min_source_support`/`include_existing` 매개변수는 기본값 말고는 넘겨지지 않는다.
- **테스트만 부른다**: `WikiAdmin.prior_refs`/`broken_refs`.
- **만들고 버린다**: `IngestionResult.low_confidence_item_ids`·`entity_id_map`, `KnowledgeGraph.unconnected_entity_ids`, 구조화 지도의 `name_set`.
- **옛 필드가 남았다**: `ScopeLink.is_rumor`, 저장되지 않는 ScopeType 넷, 빌드용이라면서 저장되는 `Knowledge.region_hint`.
- **중복 로직**:
  - 같은 함수가 두 벌씩 있다: cosine, `_hit_to_prior`, `_backup`(직렬화도 다름).
  - unscoped 규칙이 두 곳에 있다.
  - "규칙 하나"를 두고 우회한다: `names_of`, `movement.npcs_here`.
  - `SessionService`가 `SessionAppService`를 상속하지 않아 `_require`와 기본 왜곡도 시드 루프가 두 번 있다.
- **계층 우회·중복 실행**:
  - GM 라우터가 서비스를 건너뛰고 저장소를 직접 읽는다(`api/routers/gm.py:198`).
  - play DDL이 시작 때 두 번 돈다.
  - localization 조립 함수가 DDL을 돈다.

### G. 문서-코드 어긋남 (주요한 것)

| 문서 | 문장 | 실제 |
|---|---|---|
| `CLAUDE.md` Status | "986 offline tests GREEN (857 + 129)", "in progress", "compose ports on 127.0.0.1" | 948 + 202이고, 주기는 COMPLETE이며, app·web은 0.0.0.0이다 |
| `CLAUDE.md` Gates | mypy가 CI 게이트처럼 읽힌다 | CI에는 mypy가 없다 |
| `CLAUDE.md` Conventions | "Cross-world prior reference … by shared domain tags" | 필터 불일치로 늘 0건이다 |
| `CLAUDE.md` Conventions | "`world_id` partitions every graph" | 속성 분할일 뿐이다. 유일 제약은 라벨마다 전역이다 |
| `CLAUDE.md` Code 목록 | play 하위 모듈 열거 | `event/seeds.py`, `turn/changes.py`, `rumor/{generator,promotion,feedback,dynamics}.py`, `deeds/caps.py`, `storage/clock.py`가 빠졌다. `DeedPanel`은 GmHub가 아니라 GmPage에 있다 |
| `README.md` | "NPC가 만들어집니다" | 빌드는 NPC를 만들지 않는다(RE-W18) |
| `README.md:11` | "행적과 사건이 소문이 되어 한 칸씩 퍼집니다" | 한 칸씩 퍼지는 것은 행적 소문뿐이다. 사건은 같은 턴에 왜곡도를 최대곱 경로로 번지게 한다 |
| `README.md` / `operations.md:402` | "[바로 플레이]는 LLM을 부르지 않는다" | LLM은 맞다. 그러나 API 경로는 키가 있으면 임베딩 API를 부른다 |
| `operations.md:405` | "두 번째 시작은 409" | 차례로 보낼 때만 그렇다. 겹치면 둘 다 201이다(#12) |
| `operations.md:276` | interrupted run은 행적을 남긴다 | 위치와 턴 청구도 남는다(RE-P03) |
| `operations.md` Observability | healthcheck 셋 | app·web의 healthcheck가 빠졌다. 제목도 아직 "(placeholder)"다 |
| `next-cycle.md:40` | dev npm audit 4건 | 5건이다 |
| `web/README.md` | LLM 꺼짐 안내, 세션 띠 설명 | GM은 허브 안에 안내가 있다. 세션 띠는 닫힌 세션도 보이고 [새 세션]도 있다 |
| `web/index.html:6` | `<title>Locus — Spatial Knowledge</title>` | 옛 정체성이다(목적: 솔로 TRPG) |
| X2 BR-X2-4·12·1 | 제목만 손글씨, 가로 스크롤 없음, 하드코드 색 지양 | 버튼·배지도 손글씨이고, 390px에서 가로 스크롤이 생기며, `viz.ts:14`에 색이 하드코드돼 있다 |
| 낡은 docstring | `neo4j_repo.py:1-4` "weighted traversal", `:71-72` "World nodes are not persisted", `cache.py:4` "no TTL"(버전 확인이 더해짐), `loader.py:3-4` 노드 6종, `event/dynamics.py`·`suggester.py` "GameMasterService", `api/routers/play.py:7-8` "NPC dialogue lands here in U5", `postgres_repo.py:7-8` "created_at is set by the DB server", `api/errors.py` 매핑 목록, `Dockerfile:9` "api = …" | 각각 코드와 다르다 |

## Patterns and Anti-patterns

- **Good Patterns**:
  - 다섯 경계와 import 행렬 테스트가 있다(`tests/test_boundaries.py`).
  - 모든 외부 I/O가 포트 뒤에 있고, 드라이버는 지연 import한다.
  - 경계별 `assemble_*()`와 타입 컨테이너가 있다. LLM 의존 서비스는 Optional이라, 없으면 503으로 내려간다.
  - 순수 함수 코어를 두고 PBT를 붙였다: 합의, 전파 계획, 동역학, 이동, NPC 범위, World File 재매핑.
  - 쓰기 순서로 원자성을 대신한다. 지역 삭제 순서와 되돌리기의 `revert_started` 재개가 그 예이고, 재시도해도 안전하다.
  - 턴 엔진은 진입점이 하나다(`TurnAdvancer`). 계산 → 초안 → 저장으로 나누고, LLM은 UoW 밖에서만 부른다. 실패하면 보상한다.
  - 데모가 코드가 아니라 데이터다(매니페스트).
  - 번역은 캐시 우선, 비차단 읽기, 백그라운드 warm이다.
  - 프롬프트 위생으로 `one_line`과 `MATERIAL` 머리말을 쓴다.
  - 플레이에는 `localization`과 `world` import가 없다. 번역은 `api/schemas.py`에서만 붙인다.
- **Anti-patterns**:
  - **읽고 나서 행 전체를 쓰는 GM 쓰기**가 GM 리스 공유와 겹친다. #9, #12, RE-P01, RE-P06, RE-P07, 피드백 몫이 모두 같은 뿌리다. 지역 왜곡도·소문·행적 행은 어디서도 잠그지 않는다.
  - **라벨 없는 그래프 질의**와 항목별 auto-commit이 있다(RE-W13). #10과 성능 문제의 뿌리다.
  - **같은 사실을 두 곳에 둔다**(속성과 엣지, RE-W11).
  - **경고로 삼키는 실패**가 있다. 백업 실패(RE-W04), 끝점 없는 엣지(RE-W14)가 그렇다.
  - **프론트의 화면별 복사 패턴**이 있다. 쓰기 래퍼, 대화상자 넷, select 스타일, `String(e)` 오류, LLM 필요 처리가 화면마다 복사돼 있다.
  - **레이아웃 상수**가 있다: 800×500 지도, `min-w-*`, 브레이크포인트 없음.
