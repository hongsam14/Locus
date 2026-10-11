# 다음 주기 목록 — Follow-up 주기 뒤 (2026-10-12)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: Follow-up 주기(V1~V9)를 닫으며 남은 일을 한곳에 모았다. 항목마다 출처(유닛·리뷰 번호)와 지금 위치를 적었다. 위치는 `feat/follow-up`의 `fa0927d` 기준이다. 코드가 바뀌면 줄 번호도 움직이니 출처의 설명으로 찾는다.

출처 약어:
- **RE-…** — `inception/reverse-engineering/code-quality-assessment.md` §§ B~E
- **U8 #n / Cn / 메모 n** — `construction/U8-demo-deploy-docs/code/reviews/code-review-01.md`. § 3의 행 순서가 #n, § 2가 Cn, § 5 끝의 설계 메모가 메모 n이다.
- **Vn § m** — `construction/<Vn 폴더>/code/code-summary.md`
- **요구 § 9** — `inception/requirements/follow-up-requirements.md` § 9

## 0. 이번 주기에 닫혀 이 목록에서 지운 것
- 화면 다듬기(사람의 지시, 2026-10-02) — V2 디자인 시스템, V4 홈·플레이, V6 GM, V8 에디터.
- U8 #5(a)·#9~#15 — V5(GM 쓰기 직렬화)와 V7(월드·지식 정확성).
- CI 액션 버전과 Ubuntu 26 러너 — V1. mypy 11건 → 0건, CI 단계 — V9. dev 의존성 npm audit → 0건 — V9. 라이브 시나리오 10a의 방향 단언 — V9.
- U3 메모 2를 run 안에서 닫음 — V7 `kept_keys`. run 사이에 기억할지는 § 2에 남는다.
- 앞 유닛의 넘김: 에디터·지도 문장 해요체와 옛 사전 키(V9), CLAUDE.md Status·Gates(V9), 빌드 리포트의 이어 붙인 수·단계 이름(V8), 409 문장 셋(V6), SessionBar·MapOverlay 지우기(V6·V8), 데모 번역의 엔티티·사전(V9가 "고칠 것 아님"으로 판정 — V9 code-summary).

## 1. 사람이 확인할 것 (운영자)
- **실제 PostgreSQL 동시성(U3 #10)** — 확인할 내용이 V5로 바뀌었다. 같은 세션의 GM 쓰기는 이제 프로세스 안의 짧은 쓰기 잠금으로 줄을 선다(`locus/play/write_section.py:37-57`, `locus/play/turn/guard.py:99-110`). 그래서 워커가 하나면(`docker-compose.yml:148`, `--workers 1`) PostgreSQL에서 두 쓰기가 겹칠 수 없고, `FOR UPDATE`는 둘째 겹이다. 볼 것은 셋이다. V5 `nfr/nfr-light.md` § 3의 P1~P6 스모크(겹친 해소 둘, 설정 ∥ 해소, 씨앗 둘 …), psql로 사건 행을 `SELECT … FOR UPDATE`로 쥔 채 해소가 기다리는지(V5 § 7 R-01), 그리고 워커 수.
- **이번 주기 Build and Test가 볼 것** — nginx 머리, PG 잠금 P1~P6, Neo4j 라벨 삭제, 백업 실패, GM·에디터 한 바퀴(V2 § 6, V5 § 7, V6 § 7, V7 § 8, V8 § 8). 거기서 남는 것은 이 절로 옮긴다.

## 2. 정할 것 (설계 결정)
| 항목 | 한 줄 | 지금 위치 |
|---|---|---|
| U3 메모 1 — 전역 지식의 자리 | 전역 지식이 에디터 어디에도 나오지 않는다(지역 보기는 스코프된 것만, 스코프 없음 목록은 전역을 뺀다) | `locus/world/editor/regions.py:145-152`, `locus/world/editor/knowledge.py:149-154`, `web/src/features/editor/UnscopedPanel.tsx:58` |
| U3 메모 2 — run 사이의 "맞음" | "맞음"은 같은 run에서만 wiki_conflict를 끝낸다. 새 run은 다시 묻는다 | `locus/world/augmentation/service.py:71-77`, `:109-110` |
| U3 메모 5 — 보강 예산 | 보강 LLM 예산이 run마다 고정 수이고, 다시 탐지의 따라잡기가 정해지지 않았다 | `locus/world/augmentation/service.py:28`, `:147-152`; `locus/world/augmentation/engine.py:32` |
| U3 S16 — 답의 변경 기록 | 답의 엣지 차이에 그사이의 지도 저장이 섞일 수 있다(제작자 한 명 전제, 알려진 한계) | `locus/world/augmentation/apply.py:69-90` |
| U8 메모 2 — wiki 검색 실패 비용 | 탐지마다 실패 한 번(`with_retry`)이 run 잠금 안에서 남는다. backoff·NFR 문구가 없다 | `locus/world/augmentation/engine.py:92-102`, `:125-139` |
| U8 메모 3 — 다시 탐지 실패 | 다시 탐지가 실패하면 질문을 비워 빈 run이 된다 | `locus/world/augmentation/service.py:51-53`, `:133-141` |
| U8 메모 5 — [맞음]의 신뢰도 칸 | [맞음]이 쓰지 않는 신뢰도 칸을 함께 보인다 | `web/src/features/editor/AugmentQuestion.tsx:76-80`, `locus/world/augmentation/apply.py:154-156` |
| U8 메모 7 — World File 두 길의 한도 | JSON 본문과 업로드 길이 한 정규식에 20 MiB + 1 MiB로 묶여 있다 | `api/uploads.py:40-41` |
| U8 메모 8 — 편집마다 월드 다시 읽기 | 편집 쓰기마다 스냅숏 전체를 읽고 캐시를 비운다 | `locus/world/editor/writes.py:46-49`, `:73-78` |
| U8 메모 9 — `edges_touching`의 라벨 | 라벨 없이 월드 전체 엣지를 훑는다(RE-W13과 같은 뿌리) | `locus/shared/storage/neo4j_repo.py:283-284` |
| U8 메모 10 — 해석 못 한 본문 | 422 응답이 받은 본문을 길이 제한 없이 되돌려 보낸다 | `api/main.py:45-46`, `:175-178` |
| RE-P14 — `*_ko` 칸 이름 | `*_ko` 칸에 실제로는 아무 표시 언어나 들어간다(요구 A-2가 이름을 그대로 두기로 함) | `api/schemas.py:89-103`, `api/deps.py:101` |

## 3. 정확성 결함

### 3.1 RE medium에서 남은 것
| 항목 | 한 줄 | 지금 위치 | 상태 |
|---|---|---|---|
| RE-W08 | 빌드의 LLM·임베딩 호출에 상한이 없고, 고아 엔티티마다 지역 전체를 다시 임베딩한다 | `locus/world/ontology/reconciler.py:70-77`, `:145-169`, `:180-193`; 세기만 하는 `locus/world/build.py:200-203` | 열림 |
| RE-W13 | 엣지·월드 질의가 라벨 없이 전체를 훑고, 쓰기가 항목마다 auto-commit이다(get/delete/update_node 라벨은 V7에서 닫힘) | `locus/shared/storage/neo4j_repo.py:118-119`, `:142-143`, `:210-212`, `:251`, `:283`, `:310`, `:314`; 커밋 `:97-155` | 일부 열림 |
| RE-W17 | 옛 월드를 지운 뒤에 온톨로지 LLM 작업이 돌아 그동안 월드가 비어 있다 | `locus/world/build.py:279-301` | 열림 |

### 3.2 U8 리뷰 § 3 (상한으로 뺀 정확성 지적)
| 항목 | 한 줄 | 지금 위치 | 상태 |
|---|---|---|---|
| U8 #1 | 제안 상한이 `/state` 실패 때 5로 남고, 400 뒤에도 다시 읽지 않는다(지도 겹쳐 보기 쪽은 V6에서 닫힘) | `web/src/features/gm/GmSessionView.tsx:117`, `:125-133`; `web/src/features/gm/useGmData.ts:134` | 일부 열림 |
| U8 #6 | 쓰기 뒤 다시 탐지가 실패하면 번역 지우기에 닿지 않는다 | `locus/world/augmentation/service.py:133-141`; `api/routers/world.py:551-561`, `:575-581` | 열림 |
| U8 #7 (= RE-W07) | prior 저장이 월드가 있는지 보지 않아 오타 world_id가 월드 목록에 뜬다(라벨 검사는 V7에서 닫힘) | `locus/world/wiki/admin.py:44-64`; `api/routers/world.py:500-506` | 일부 열림 |
| U8 #8 | 새 NPC는 노드보다 LIVES_IN을 먼저 써서 Neo4j에서 엣지가 생기지 않는다 | `locus/world/editor/npcs.py:42-44` | 열림 |
| U8 #12 (≈ RE-P12) | 외톨이 서로게이트·깊은 리스트가 422가 아니라 500이 된다 | `api/main.py:37-47`, `:170-184` | 열림 |
| U8 #13 | 소스 빌드가 소스 유무보다 세션 관문을 먼저 본다 | `api/routers/world.py:484-492`; `locus/world/demo/__init__.py:190-192` | 열림 |
| U8 #14 | 입력 상한을 넘으면 CLI는 traceback, 데모 빌드는 500이다 | `locus/__main__.py:47-49`; `locus/world/demo/__init__.py:53`, `:203-209`, `:260-284`; `api/routers/world.py:493` | 열림 |
| U8 #18 | 고치기에서 제목을 비우면 옛 제목이 남는다(라벨 "비우면 진술에서"는 더하기에만 맞음) | `locus/world/augmentation/apply.py:161-165`; `web/src/features/editor/AugmentQuestion.tsx:72-74` | 열림 |
| U8 #19 | nginx가 app 이름을 기동 때 한 번만 푼다(app이 다시 뜨면 502) | `web/nginx.conf:21`, `:30`; `docker-compose.yml:166-168` | 열림 |

### 3.3 앞 유닛의 알려진 한계 (서버)
| 항목 | 한 줄 | 출처 | 지금 위치 |
|---|---|---|---|
| SQL 엔진 시한 | 엔진에 `connect_timeout`·`pool_pre_ping`이 없어 DB가 멈추면 요청도 멈춘다 | V3 § 6, V3 코드 리뷰 #11 | `locus/shared/storage/sql.py:17-19` |
| 진행 중 warm과 손번역 | 시딩 직전에 시작한 warm이 손으로 다듬은 번역을 덮을 수 있다 | V3 § 6 (R-04) | `locus/localization/service.py:285-310` |
| 번역 키의 월드 | 번역 키에 월드가 없어 같은 id를 쓰는 두 월드가 서로 덮는다 | V3 § 6 (R-05) | `locus/localization/storage/schema.py:25-27` |
| 이름표 warm 비용 | 키가 있으면 큰 월드의 첫 이름표 읽기가 텍스트 수만큼 번역을 예약한다 | V3 § 6 (R-03) | `api/routers/world.py:314-328`, `api/schemas.py:301-309` |
| LLM 이름표 함께 주기 | LLM 대사·서술·소문의 고유명사가 화면의 이름표 음역과 어긋날 수 있다 | V3 § 6 | `locus/play/npc/prompts.py:53`, `:69`; `locus/play/gm/narrator.py:38`, `:51`; `locus/play/rumor/generator.py:89` |
| 교체 점검과 닫기 사이 | 점검 뒤 시작된 턴 때문에 교체 뒤에도 그 세션이 열린 채 남을 수 있다 | V5 § 6 | `api/routers/world.py:85`, `:161`, `:174` |
| 지운 지역 소문 되먹임 | 턴 되먹임이 지운 지역의 소문으로 그 지역 행을 쓸 수 있다 | V5 § 6 | `locus/play/rumor/feedback.py:67-68`(호출 `locus/play/turn/advancer.py:745`) |
| 한 프로세스 보장 | 짧은 쓰기 구간과 guard가 프로세스 안 잠금이라 워커가 하나일 때만 보장된다 | V5 § 6 | `locus/play/turn/guard.py:37-43`, `:107`; `docker-compose.yml:148` |
| 닫기 상한 틈 | "닫혔다"를 받은 턴이 있어도 닫기가 gm_busy로 실패하면 세션은 열린 채다(받아들인 한계) | V5 § 6, V5 코드 리뷰 § 4 | `locus/play/session_service.py:122-123` |
| V5 시험의 약점 | 일부 인메모리 겹침 시험은 구간 없이도 통과하고, 끼워 넣기 문은 0.5초에 기댄다 | V5 § 6 | `tests/play/concurrency.py:123`, `:155`; `tests/play/test_v5_overlap.py` |
| 닿지 않는 방어 코드 | 지운 지역의 초안을 건너뛰는 코드에 이제 닿는 길이 없다 | V5 § 6 | `locus/play/turn/advancer.py:686-690` |
| 메타 없는 옛 월드 | WorldMeta가 없는 옛 월드는 캐시되지 않아 읽을 때마다 불러온다 | V7 § 6 | `locus/knowledge/cache.py:30`, `:65` |
| 이미 저장된 중복 id | 이미 저장된 중복 id가 남아 있고, 그 경우 라벨 없는 읽기가 모호하다 | V7 § 6 | `locus/world/editor/writes.py:60`, `:118` |
| 이름 바뀐 지역의 NPC·씨앗 | 이름이 바뀐 지역의 NPC·씨앗은 이어 붙지 않고 경고와 백업에만 남는다 | V7 § 6 | `locus/world/carry_over.py:38-48` |
| 읽기와 백업 사이의 편집 | 옛 월드를 읽은 뒤 백업 전에 에디터로 한 편집은 이어 붙지 않는다 | V7 § 6 | `locus/world/build.py:267-280`, `:403` |
| 확인한 답(kept_keys) | 확인한 답은 되살릴 수 없고, 그 run에서는 다시 묻지 않는다 | V7 § 6 | `locus/world/augmentation/service.py:72-75` |
| 로더가 버린 것 | 로더가 버린 NPC·씨앗은 경고만 남고 백업에는 없다 | V7 § 9 | `locus/knowledge/loader.py:36-37` |

## 4. 화면 (앞 유닛의 넘김과 알려진 한계)
| 항목 | 한 줄 | 출처 | 지금 위치 |
|---|---|---|---|
| 화면별 사전 나누기 | ko·en 사전이 한 모듈이라 첫 화면 JS에 다 실린다(V8에서 +2.55 kB, V9 뒤 119.41 kB) | V8 code-summary § 5·§ 8 | `web/src/i18n/index.ts:9-10`, `:18` |
| 1024px 경계 다시 그림 | 넓음과 좁음이 다른 트리라 경계를 넘으면 부품이 새로 그려진다(GM도 같음) | V8 § 6·§ 8 | `web/src/layout/MapPanelLayout.tsx:30-56` |
| 교체 전 끌기 저장 기다리기 | 불러오기·빌드가 이미 나간 끌기 저장을 기다리지 않는다 | V8 § 9, 코드 리뷰 01 #2 | `web/src/features/editor/FileActions.tsx:80`, `BuildPanel.tsx:66`, `useEditorWorld.ts:249-258`, `dragSaves.ts:60-65` |
| 저장 안 한 폼 글 | 섹션을 접거나 탭을 바꾸면 저장하지 않은 폼 글이 사라진다 | V8 § 6 | `web/src/features/editor/RegionForm.tsx:39-42` |
| 390 지도 라벨·sticky 패널 | 390에서 지도 라벨이 작고, 페이지를 내리면 패널도 같이 올라간다 | V8 § 6 | `web/src/map/WorldMap.tsx:50`, `web/src/layout/MapPanelLayout.tsx:36-37` |
| BuildPanel 입력 | Esc나 바깥 누름으로 빌드 대화상자를 닫으면 입력이 지워진다 | V2 코드 리뷰 § 6(V8 FD § 4.6이 "지금과 같다"로 둠) | `web/src/features/editor/BuildPanel.tsx:86-97`, `:102` |
| 교체 경고 문장 | 닫지 못한 세션 경고가 빌드 리포트에서만 사람 말로 나오고, 데모 카드·파일 불러오기는 아니다 | V6 § 7 | `web/src/features/home/DemoCard.tsx:94`, `web/src/features/editor/FileActions.tsx:156-157` |
| GM 타임라인 서버 쪽 페이지 | 쓰기마다 기록 전부를 읽고, 서버는 쪽을 나누지 않는다 | V6 § 6·§ 7 | `api/routers/gm.py:101-104`, `locus/play/session_service.py:164`, `web/src/features/gm/useGmData.ts:133` |
| GM 타임라인 줄 말투 | GM 기록 줄에 이름씨 꼴, 해라체, 해요체가 섞여 있다 | V6 § 7, V6 코드 리뷰 #39 | `web/src/i18n/ko.ts:107-136`, `:286` |
| V6 읽기·일괄 제약 | "새로"에 플레이어 줄이 섞이고, 플레이어 띠는 폴링하지 않으며, 일괄은 이미 보낸 요청을 끊지 못한다 | V6 § 6 | `web/src/features/gm/newLines.ts:10`, `PlayerStrip.tsx:12`, `web/src/api/gm.ts:23-26` |
| V6 캡처에서 본 것 | 세션 라벨이 잘리고, 390에서 탭 줄이 바뀌고, "보는 눈"이 원문으로 나온다 | V6 § 6 | `web/src/features/gm/sessionLabel.ts:16-18`, `DeedPanel.tsx:70` |
| 대화상자 초점 | 대화상자 초점 보호 두 가지를 jsdom 시험이 잡지 못한다 | V6 § 3·§ 6 | `web/src/ui/Dialog.tsx:72-84` |
| 플레이·대화·데모 문장 말투 | 플레이·대화·데모 카드의 ko 16줄이 아직 합니다체다(V9는 에디터·지도만 고침) | V4 § 6·§ 7, V9 Step 7 | `web/src/i18n/ko.ts:66-94`, `:273-281` |
| 작은 지도 초점·글자 | 이웃이 넓게 퍼진 곳에서는 플레이 지도가 거의 전체가 되고 글자가 작다 | V4 § 6·§ 7 | `web/src/map/focus.ts:5-33`, `web/src/features/play/PlayMap.tsx:35` |
| V4 기타 제약 | 잡힌 세션 다시 읽기가 최대 1초 늦고, 영어에서는 데모 카드 시작 줄이 빠진다 | V4 § 6 | `web/src/hooks/useTurnRun.ts:205`, `web/src/features/home/DemoCard.tsx:62` |
| JS 전체 합 | JS 전체 합이 V4 예산 125.6 kB를 넘고 첫 화면만 예산 안이다 | V4 § 6 | `web/src/App.tsx:11-12` |
| CSS 84.7 kB gzip | 한글 글꼴 조각마다 @font-face가 붙어 첫 화면 CSS가 크다 | V2 § 6 | `web/src/index.css:7-10` |

## 5. RE low·정리 항목
| 항목 | 한 줄 | 지금 위치 | 상태 |
|---|---|---|---|
| RE-W05 | 빌드 전용 힌트가 attributes째 저장·내보내지고 일부는 LLM 문맥에 든다 | `locus/world/topology/builder.py:61-62`, `locus/shared/storage/graph_mapping.py:57-58`, `locus/world/ontology/corroboration.py:81-83` | 열림 |
| RE-W06 | 지도 좌표가 숫자가 아니면 빌드가 500이 되고 NaN은 1.0이 된다(docstring은 "경고로 거름") | `locus/world/ingestion/structured_map_ingestor.py:28-35`(호출 `:153`), `api/routers/world.py:197` | 열림 |
| RE-W07 | prior 넣기가 월드가 있는지 보지 않아 유령 월드가 목록에 뜬다(라벨 검사는 V7 #17에서 닫힘) | `locus/world/wiki/admin.py:44-64`, `api/routers/world.py:500-506`, `locus/shared/storage/neo4j_repo.py:312-318` | 일부 열림 |
| RE-W09 | 세션 DB URL이 늘 조립되어 CLI의 "PG 없음" 분기가 죽어 있다 | `locus/shared/config/settings.py:191-202`; `locus/__main__.py:99-100`, `:153-154`, `:276-277` | 열림 |
| RE-W10 | 키 없이 CLI `world build`를 하면 안내 대신 traceback이 난다(API는 V2에서 고침) | `locus/__main__.py:169`, `:83-84`; `locus/shared/wiring.py:98-103`; `locus/shared/llm/factory.py:19-25` | 열림 |
| RE-W11 | 같은 사실이 속성과 엣지 두 곳에 있고, 지식 PUT은 속성만 고친다 | `locus/world/editor/knowledge.py:19-42`, `:63-68`; `locus/knowledge/loader.py:60-90` | 열림 |
| RE-W12 | World File이 한 방향 연결을 경고 없이 받는다 | `locus/world/worldfile/remap.py:196-201` | 열림 |
| RE-W14 | 끝점 노드가 없는 엣지는 MATCH가 비어 경고 없이 사라진다 | `locus/shared/storage/neo4j_repo.py:112-131`, `:133-155` | 열림 |
| RE-W15 | OpenSearch `_id`가 맨 노드 id여서 다른 월드의 같은 id 문서를 덮을 수 있다 | `locus/shared/storage/opensearch_repo.py:136` | 열림 |
| RE-W16 | 월드 전체를 임베딩 한 번에 보내고, CLI `world import`·`build`의 길은 임베딩 여부가 API와 다르다 | `locus/shared/storage/persistence.py:104-111`; `locus/__main__.py:204`, `:234` | 열림 |
| RE-W19 | CLI `--force`가 새 TurnGuard로 다른 프로세스의 턴을 모른 채 세션을 닫는다 | `locus/__main__.py:97-105`, `:123-133`; `locus/play/session_service.py:55` | 열림 |
| RE-W20 | 재시도가 모든 예외에 걸리고, VLM은 그림을 늘 image/png로 보낸다 | `locus/shared/llm/retry.py:84`, `locus/shared/llm/openai_provider.py:87` | 열림 |
| RE-W21 | wiki 조회 기준이 0.0이어서 낱말 하나만 맞아도 근거가 된다 | `locus/world/wiki/base.py:52`, `:68-74`, `:96` | 열림 |
| RE-W22 | 번역 warm이 (항목, 필드)마다 LLM을 직렬로 부르고 상한이 없다 | `locus/localization/service.py:285-317` | 열림 |
| RE-W23 | 지식 만들기가 색인→노드→스코프 순이어서 끊기면 스코프 없는 지식이 남고 재시도는 400이다 | `locus/world/editor/knowledge.py:44-61`, `:63-68` | 열림 |
| RE-W24 | kNN 엔진이 deprecated nmslib이고, 차원이 바뀌어도 아무 일도 하지 않는다 | `locus/shared/storage/opensearch_repo.py:42`, `:124-127` | 열림 |
| RE-P08 | GM 수동 턴이 요청 스레드에서 동기로 돌아 nginx 130초를 넘기면 504가 날 수 있다 | `api/routers/gm.py:223-232` → `locus/play/turn/advancer.py:177-195`; `web/nginx.conf:36` | 열림 |
| RE-P09 | 턴마다 활성 소문을 전부 upsert하고, 타임라인 줄은 넣을 때마다 다시 읽는다 | `locus/play/turn/advancer.py:744`, `:796`; `locus/play/storage/postgres_repo.py:305-310` | 열림 |
| RE-P10 | 열린 세션마다 get_player, 월드마다 list_sessions를 부른다(제안 초안마다 스냅숏은 V5에서 닫힘) | `locus/play/session_service.py:154-162`; `api/routers/world.py:298-301` | 일부 열림 |
| RE-P11 | GM 타임라인·플레이어 로그·run 목록을 상한 없이 다 읽는다 | `locus/play/session_service.py:164-166`; `locus/play/player/service.py:96-102`; `locus/play/storage/postgres_repo.py:486-492` | 열림 |
| RE-P12 | 서로게이트·깊은 중첩 JSON은 500이고, `?status=`는 검증 없이 빈 목록이다("(run gm)" 노출은 V5에서 닫힘) | `api/main.py:180-184`; `api/routers/gm.py:238`; `api/routers/play.py:135` | 일부 열림 |
| RE-P13 | 범위 밖 GM 입력을 조용히 clamp하고 200을 준다 | `api/schemas.py:41-53`; `locus/play/event/service.py:142`; `locus/play/distortion_service.py:70`; `locus/play/rumor/dynamics.py:30` | 열림 |
| RE-P14 | `*_ko` 칸에 실제로는 아무 표시 언어나 들어간다(요구 A-2가 이름을 그대로 둠) | `api/schemas.py:89-103` 등; `api/deps.py:101` | 열림 |
| RE-P15 | 지역이 지워지면 `/region`은 404인데 `/npcs`는 200 빈 목록이다 | `locus/play/npc/dialogue.py:98-107` vs `locus/play/player/service.py:59-60` | 열림 |
| RE-F13 | 지도 배경 object URL을 만들고 해제하지 않는다(V6·V8로 옮겨 옴) | `web/src/routes/EditorPage.tsx:170`(`:62`); `web/src/routes/GmPage.tsx:63` | 열림 |
| RE-F15 | ESLint가 없어 훅 의존성 누락을 도구가 못 잡는다(`eslint-disable` 주석도 검사 안 됨) | `web/package.json:11`; 예 `web/src/features/editor/useEditorWorld.ts:114` | 열림 |
| RE-T04 | Python 잠금 파일이 없고 의존성 상한도 없다 | `pyproject.toml:16-31`, `:37-44`; `requirements.txt:3-16` | 열림 |
| RE-T05 | 선언한 의존성과 실제 import가 어긋난다(langchain·openai 직접 import 없음, langchain_core·httpx 선언 없음) | `pyproject.toml:21-24`, `:37-44`; `locus/shared/llm/openai_provider.py:82`; `locus/world/augmentation/graph.py:30` | 열림 |
| RE-T06 | app 이미지가 root로 돌고 이미지 태그·다이제스트가 고정 안 됐다 | `Dockerfile:1`; `docker-compose.yml:21`, `:52`, `:104`; `web/Dockerfile:3`, `:11` | 열림 |
| RE-T07 | `api`가 휠에 없고 API 버전 0.2.0과 패키지 0.1.0이 어긋난다 | `pyproject.toml:7`, `:49-50`; `api/main.py:151`; `Dockerfile:9-13` | 열림 |
| RE-T09 | app·web이 0.0.0.0에 인증 없이 열린다(문서는 V9에서 사실대로 고침, 바인드는 의도) | `docker-compose.yml:145`, `:148`, `:170` | 일부 열림 |
| RE-T10 | 프론트에 ESLint와 커버리지 도구가 없다 | `web/package.json:11`, `:23-37` | 열림 |
| RE-T11 | `assemble_all`, 소유 컨테이너 닫기, store 없는 Postgres 분기, 번역 LLM 분기를 지나는 시험이 없다(lifespan·keyless 조립은 V5·V3에서 닫힘) | `api/main.py:50-91`, `:134-149`; `locus/localization/wiring.py:39-44`, `:49-56` | 일부 열림 |
| RE-T13 | 시각·반응형·접근성(axe)·E2E 시험이 없다(jsdom만) | `web/vite.config.ts:15`; `web/package.json:6-12` | 열림 |

## 6. U8 리뷰 § 2 정리 지적
| 항목 | 한 줄 | 지금 위치 | 상태 |
|---|---|---|---|
| C2 | export가 스냅숏을 두 번 읽고, 로더는 아무도 읽지 않는 목록을 계산한다 | `locus/world/worldfile/export.py:44`, `:67-70`; `locus/knowledge/loader.py:138-139`, `:148` | 열림 |
| C3 | WikiAdmin이 쓰기·색인·스냅숏을 따로 구현한다(`delete_held`·`own_label`은 닫힘; `refs()`의 이중 계산, 매번 임베딩, 손으로 하는 touch·invalidate가 남음) | `locus/world/wiki/admin.py:48-63`, `:71-84`, `:129`, `:138` | 일부 열림 |
| C4 | 503 규칙이 넷으로 갈리고, npc 잔재와 REF_KIND 표 둘이 남았다 | `api/deps.py:38-44`, `:52-55`; `api/routers/world_editor.py:46-49`; `locus/world/augmentation/apply.py:31-37`; `locus/world/augmentation/questions.py:54-60` | 열림 |
| C5 | 손으로 쓴 지역 확인 둘이 `require_region`을 다시 쓴다 | `locus/world/npc_drafts.py:74-75`; `locus/world/augmentation/apply.py:237-239` | 열림 |
| C6 | "AI 키 필요" 처리가 공용 컴포넌트 없이 다섯 곳에 복사돼 있다 | `web/src/features/gm/RumorPanel.tsx:36`, `TurnTools.tsx:45`; `web/src/features/editor/NpcDraftCards.tsx:37`, `BuildPanel.tsx:73`; `web/src/features/play/DialoguePanel.tsx:137` | 열림 |
| C7 | 매니페스트의 지나갈 수 있는 연결 검사가 이동 규칙을 베꼈다 | `locus/world/demo/__init__.py:276-281`; `locus/play/player/movement.py:25-27` | 열림 |
| C8 | Neo4j 엣지 쿼리가 두 벌씩 있다(SET 연산자와 WHERE만 다름) | `locus/shared/storage/neo4j_repo.py:112-155`, `:244-301` | 열림 |
| C9 | 씨앗 시작이 스냅숏을 두 번 읽고, 해소된 사건까지 읽는다(3번 → 2번은 V5에서 닫힘) | `locus/play/event/seeds.py:34`, `:51`, `:54`, `:58` | 일부 열림 |
| C10 | `STATUS:` 첫 줄이 100자를 넘는다(E501 무시로 게이트 통과) | `locus/world/wiki/distiller.py:1`, `locus/world/ingestion/concept_art_ingestor.py:1`, `locus/world/wiki/cross_world.py:1`, `locus/world/augmentation/graph.py:1` | 열림 |

## 7. 진행 중 기능 넷 (README 표, 모듈 `STATUS: in-progress`)
| 기능 | 한 줄 | 지금 위치 |
|---|---|---|
| 교차 월드 prior 검색 | 필터가 맨 위 `domains`를 찾는데 색인은 `meta.domains`에 둔다. 그래서 늘 0건이다 | `locus/world/wiki/cross_world.py:1`, `:57`; `locus/shared/storage/opensearch_repo.py:65-71` |
| 컨셉 아트 수집 | 단서가 낮은 확신 엔티티로만 남고 지식이 되지 않는다 | `locus/world/ingestion/concept_art_ingestor.py:1` |
| LangGraph 래퍼 | 보강 루프의 그림일 뿐 서비스에 연결되지 않았다 | `locus/world/augmentation/graph.py:1` |
| wiki 순환 | prior를 빌드마다 한 번 증류하고, 쓰인 결과로 다듬지 않는다 | `locus/world/wiki/distiller.py:1` |

## 8. 이번 주기에 범위 밖으로 둔 것 (요구 § 9)
| 항목 | 한 줄 | 지금 위치 |
|---|---|---|
| Python 잠금 파일·의존성 상한 | 상한 없는 의존이 많은데 잠금 파일이 없다(RE-T04) | `pyproject.toml:16-31`; `requirements.txt:3-16`; `Dockerfile:14` |
| Docker non-root·digest 고정 | app 이미지가 root로 돌고, 베이스 이미지가 움직이는 태그다(RE-T06) | `Dockerfile:1`; `web/Dockerfile:3`, `:11`; `docker-compose.yml:21`, `:52`, `:82`, `:104` |
| `api` 패키징 | `api`가 휠 밖이라 이미지가 소스 복사에 기대고, 버전도 어긋난다(RE-T07) | `pyproject.toml:7`, `:49-50`; `Dockerfile:9-13`; `api/main.py:151` |
| 의존성 선언 | langchain·openai는 직접 import가 없고, langchain_core·httpx는 선언이 없다(RE-T05) | `pyproject.toml:21-24`, `:37-44` |
| 0.0.0.0 바인드 | app·web 호스트 포트가 인증 없이 모든 인터페이스에 열린다(RE-T09, 의도) | `docker-compose.yml:145`, `:148`, `:170` |
| Playwright·axe·지도 키보드 | 자동 접근성·화면 시험이 없고, 지도는 `role="img"`로 키 처리가 없다(지역 목록으로 대신함) | `.github/workflows/ci.yml:45-62`; `web/src/map/WorldMap.tsx:211` |
| UX-26 지도 바탕 그림 | 바탕 그림은 이 브라우저의 object URL로만 남고 저장되지 않는다 | `web/src/routes/EditorPage.tsx:170`, `web/src/routes/GmPage.tsx:63`, `web/src/features/gm/MapPane.tsx:27` |
| 어두운 테마 밖 | 테마는 어두운 것 하나다. 두 번째 테마나 전환은 없다 | `web/src/index.css:12-15`, `:94` |
| 에디터·GM의 폰 배치, 지도 터치 그리기 | 좁은 폭은 한 열로 쌓기만 하고, 지도는 포인터 끌기뿐이다 | `web/src/layout/MapPanelLayout.tsx:50-56`; `web/src/map/WorldMap.tsx:187`, `:324` |
| 보안 기준선 확장 | AI-DLC 보안 확장 규칙은 꺼진 채다 | `aidlc-docs/aidlc-state.md:29` |
