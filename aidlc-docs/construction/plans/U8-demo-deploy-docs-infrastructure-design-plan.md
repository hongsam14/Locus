# U8 데모·배포·문서 — Infrastructure Design 플랜 (light)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8의 배치 설계입니다. 관람자가 `.env` 두 값과 명령 하나로 다섯 서비스(neo4j, opensearch, postgres, app, web)를 띄우고 `:3000`에서 데모를 누르게 하는 Docker·compose·CI 배치를 정합니다. 새 인프라는 없습니다(C-4, 로컬 Docker Compose).

근거
- 승인된 U8 FD(`construction/U8-demo-deploy-docs/functional-design/`): BR-U8-28~35, 데모 소스는 패키지 데이터, `GET /api/capabilities`, CI 세 작업(backend·frontend·audit), Infra-light로 넘긴 것(이미지에 데모 소스가 들어갔는지 확인, 깨끗한 `npm ci`)
- 스토리: US-1.1(한 번에 기동), US-7.5(peer), US-7.6(CI)
- U3 code-review-01 설계 메모 9: compose web(nginx)의 요청 크기 기본 1 MiB
- 이 호스트의 사정: 다른 프로젝트의 Neo4j가 7474/7687을 쥐고 있어 Locus compose가 뜨지 못한다(지금까지 compose 확인은 운영자 몫)

## 현재 상태 (HEAD 0ddbca7)
| 항목 | 지금 | 걸리는 것 |
|---|---|---|
| 데이터 볼륨 | neo4j·opensearch·postgres는 `./data/…` bind mount(`driver_opts device`). 폴더가 없으면 compose가 실패하므로 `./scripts/setup-volumes.sh`를 먼저 돌려야 한다 | US-1.1 "명령 하나" — Q1 |
| dashboard | OpenSearch Dashboards가 프로필 없이 기본으로 뜬다(:5601, healthcheck 없음). 문서 세 곳은 없는 `tools` 프로필로 띄운다고 적는다 | US-1.1 "없는 프로필을 부르지 않는다" — Q2 |
| 호스트 포트 | 인프라 포트 7474·7687·9200·5432·5601이 모든 주소(0.0.0.0)에 고정으로 열린다 | 보안(로컬 데모인데 바깥에 열림), 포트 충돌(이 호스트) — 가정 I8-3 |
| app 이미지 | `python:3.11-slim`, `COPY locus api`, `pip install .`(비편집). 데모 소스는 패키지 데이터라 FD의 `package-data` 글롭으로 들어가야 한다 | FD R-01 이월 — 가정 I8-4 |
| app 명령 | `init-schema`(플래그 없음 = world·play·localization 모두) → `uvicorn --workers 1`. 기동마다 돌아 새 `EventSeed` 제약도 만든다 | 그대로 |
| web 이미지 | `node:20-alpine` + `npm install`(lock을 따르지 않을 수 있음) → nginx. `client_max_body_size` 없음(1 MiB) | US-7.5 `npm ci`, 설계 메모 9 — 가정 I8-5 |
| CI | 없음 | Q3, 가정 I8-6 |

## 플랜
- [x] 승인된 FD·현재 배치 분석(위 표)
- [x] 질문(아래 ID-U8 Q1~Q3) 답 수집·분석 — Q1=B, Q2=A, Q3=A
- [x] `construction/U8-demo-deploy-docs/infrastructure-design/infrastructure-design.md`(서비스·이미지·볼륨·포트·프로필·CI 매핑)
- [x] `.../deployment-architecture.md`(기동 흐름, 프로필별 구성, CI 작업 그림)
- [x] Plan Review(architecture-reviewer, adversarial ≤ 2) — iter 1 READY, open 6(Major 2: R-01·R-02, Minor 4) → `construction/U8-demo-deploy-docs/infrastructure-design/reviews/infrastructure-design-review-01.md`
- [x] 완료 메시지 + 승인 게이트 → 승인(Continue to Next Stage), R-01~R-06 Accepted risk → 코드 플랜 Step 1 정정·해당 단계 → 다음: U8 Code Generation

## 질문 (대화창에서 2개씩 묻는다)

### ID-U8 Q1 데이터는 어디에 두는가 (US-1.1 "명령 하나")
배경
- 지금은 `./data/…` 폴더를 미리 만들어야 compose가 뜹니다(`scripts/setup-volumes.sh`). 그래서 "`.env` 두 값 + 명령 하나"가 실제로는 명령 둘입니다.
- 폴더를 compose가 저절로 만들게 하면(짧은 bind 문법) 폴더가 root 소유가 되어 opensearch·neo4j가 쓰지 못합니다.
- 이 답에 compose 볼륨 절, README 시작 명령, `setup-volumes.sh`의 운명이 기댑니다.

선택지
- A. Docker가 관리하는 이름 붙은 볼륨으로 바꾼다 — 폴더를 만들 일이 없어 명령 하나로 뜹니다. 데이터는 `docker volume`에 남고, 지우려면 `docker compose down -v`입니다. 지금 `./data`에 있는 데이터는 새 볼륨으로 옮겨지지 않습니다(운영 문서에 옮기는 법 한 줄). `setup-volumes.sh`는 지웁니다.
- B. bind mount를 두고 README에 준비 명령을 한 줄 더 적는다 — 데이터가 프로젝트 폴더에 보여 들여다보기 쉽습니다. 대신 시작이 명령 둘이고, US-1.1의 "명령 하나"는 맞지 않습니다.
- C. 둘 다 — 기본은 이름 붙은 볼륨, `./data`가 필요한 사람은 덮어쓰기 파일(`docker-compose.bind.yml`)로 고른다 — 두 길이 다 되지만 compose 파일이 둘이 되어 관리할 것이 늘어납니다.
- X. Other (please specify)

[Answer]: B. bind mount 유지 — README에 준비 명령(`./scripts/setup-volumes.sh`) 한 줄을 둔다. US-1.1의 "명령 하나"는 "준비 명령 + 기동 명령"이 된다(사람의 결정, 이탈로 기록).

### ID-U8 Q2 OpenSearch Dashboards는 기본으로 띄우는가 (US-1.1)
배경
- 관람자에게 Dashboards(:5601, 색인 들여다보기)는 필요 없습니다. 지금은 기본으로 떠서 메모리를 쓰고, healthcheck가 없어 "모두 healthy"를 흐립니다.
- README·operations.md·`setup-volumes.sh`는 이것을 `--profile tools`로 띄운다고 적지만 그 프로필은 없습니다.

선택지
- A. `tools` 프로필로 옮긴다 — 기본 기동은 다섯 서비스뿐이고, 문서의 `--profile tools`가 실제로 맞게 됩니다. 개발자가 쓸 때만 `docker compose --profile tools up -d`로 띄웁니다.
- B. 기본에 두고 문서의 `tools`를 지운다 — 지금 동작 그대로입니다. 기동이 무겁고, "다섯 서비스"가 여섯이 됩니다.
- C. compose에서 뺀다 — 가장 가볍습니다. 색인을 들여다볼 도구가 사라집니다(필요하면 따로 띄움).
- X. Other (please specify)

[Answer]: A. tools 프로필로 옮긴다

### ID-U8 Q3 CI가 Docker 이미지도 만들어 보는가 (US-1.1, FD R-01 이월)
배경
- FD는 CI에 backend·frontend·audit 세 작업을 정했습니다. 셋 다 이미지를 만들지 않습니다.
- 데모 소스가 비편집 설치(이미지)에 들어가는지, Dockerfile이 지금 코드로 빌드되는지는 지금 손으로만 확인합니다.
- 이 답에 워크플로의 작업 수와 PR마다 걸리는 시간이 기댑니다.

선택지
- A. 이미지 작업을 하나 더 둔다 — app·web 이미지를 만들고, app 이미지 안에서 매니페스트 데모가 모두 읽히는지(소스 포함) 확인합니다. 서비스 없이 도는 확인이라 외부 의존이 없습니다. PR마다 3~5분이 더 듭니다.
- B. 이미지는 운영자가 만든다 — CI는 FD의 세 작업뿐입니다. 이미지가 깨져도 push 뒤에는 모릅니다. Build&Test의 운영자 확인에 이미지 확인을 넣습니다.
- C. main에 들어갈 때만 이미지를 만든다 — PR 시간은 그대로이고, 깨진 이미지는 합친 뒤에 압니다.
- X. Other (please specify)

[Answer]: A. 이미지 작업을 더한다

## 가정 (질문하지 않는 것 — 게이트에서 바꿀 수 있다)
- **I8-1 배치 대상**: 로컬 Docker Compose 하나입니다. 클라우드·쿠버네티스·TLS·인증은 범위 밖입니다(C-4, NFR-6 로컬 데모).
- **I8-2 서비스와 프로필**: 기본 = neo4j·opensearch·postgres. `service` = + app·web. healthcheck는 다섯 모두에 있습니다(web은 nginx `/` 응답을 새로 봅니다).
- **I8-3 호스트 포트**: 인프라 포트는 `127.0.0.1`에만 엽니다. 호스트 쪽 번호는 env로 바꿀 수 있습니다(`NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, `OPENSEARCH_PORT`, `SESSION_DB_PORT`, 기본값은 지금 그대로). app·web은 지금처럼 `API_PORT`·`WEB_PORT`입니다. 컨테이너끼리는 compose 네트워크로 닿으므로 바뀌지 않습니다. 이 호스트처럼 7474/7687이 이미 쓰이면 `.env`에서 두 값만 바꿔 띄울 수 있습니다. 기본값이 그대로라 "`.env` 두 값"은 유지됩니다.
- **I8-4 app 이미지**: `COPY locus api` + `pip install .` 그대로입니다. 데모 소스는 FD의 package-data 글롭(`world/demo/worlds/*.json`, `world/demo/worlds/*/*`)으로 들어갑니다. 이미지 확인(Q3)이나 운영자 확인이 `DemoWorlds.list()`에 `has_sources`가 참인 항목이 있는지 봅니다.
- **I8-5 web 이미지**: `node:22-alpine`(Vite 8의 Node ≥ 20.19 / 22.12 조건)과 `npm ci`(lock 그대로)를 씁니다. nginx에 `client_max_body_size 48m`(앱 요청 상한과 같음, 설계 메모 9)을 둡니다. 큰 빌드 업로드를 위해 `proxy_request_buffering`은 기본 그대로 둡니다.
- **I8-6 CI 배치**: `.github/workflows/ci.yml` 하나에 작업 셋(또는 Q3=A면 넷)을 둡니다. ubuntu-latest, Python 3.11(`pip install -e ".[dev]"`, pip 캐시), Node 22(`npm ci`, npm 캐시). push(모든 브랜치)와 main 대상 PR에서 돕니다. 외부 서비스(Neo4j 등)는 쓰지 않습니다(오프라인 테스트). hypothesis seed는 셸에서 정해 로그에 찍고 `--hypothesis-seed`로 넘깁니다. README 배지는 `hongsam14/Locus`의 워크플로 배지입니다.
- **I8-7 모니터링**: 지금처럼 `/health`와 컨테이너 로그(`docker compose logs`)입니다. 새 관측 도구는 없습니다.
- **I8-8 공유 인프라**: 없습니다. `shared-infrastructure.md`는 만들지 않습니다(이 사이클의 유닛 가운데 배치를 가진 것은 U8뿐이다).
