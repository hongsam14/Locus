# U8 데모·배포·문서 — Infrastructure Design (light)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 배치 설계입니다. 관람자가 `.env` 두 값과 준비 명령·기동 명령으로 다섯 서비스를 띄우고 `:3000`에서 데모를 누르게 하는 배치를 정합니다. 함께 CI의 배치도 정합니다.

근거
- 답: ID-U8 Q1=B(bind mount 유지), Q2=A(Dashboards는 `tools` 프로필), Q3=A(CI에 이미지 작업)
- 가정: 플랜 I8-1~8
- 승인된 U8 FD: BR-U8-28~35(문서·메타·CI), 데모 소스는 패키지 데이터(BLM §1.1), `GET /api/capabilities`, FD R-01 이월(이미지에 데모 소스)
- U3 code-review-01 설계 메모 9(nginx 요청 크기)

배치 대상은 로컬 Docker Compose 하나입니다. 클라우드·쿠버네티스·TLS·인증은 범위 밖입니다(C-4, NFR-6).

## 1. 서비스와 프로필
| 서비스 | 이미지 | 프로필 | 포트(호스트 → 컨테이너) | healthcheck | 바뀜 |
|---|---|---|---|---|---|
| neo4j | `neo4j:5.15-community` | 기본 | `127.0.0.1:${NEO4J_HTTP_PORT:-7474}` → 7474, `127.0.0.1:${NEO4J_BOLT_PORT:-7687}` → 7687 | HTTP 7474 | 주소·포트 변수 |
| opensearch | `opensearchproject/opensearch:2.13.0` | 기본 | `127.0.0.1:${OPENSEARCH_PORT:-9200}` → 9200 | `_cluster/health` | 주소·포트 변수 |
| postgres | `postgres:16-alpine` | 기본 | `127.0.0.1:${SESSION_DB_PORT:-5432}` → 5432 | `pg_isready` | 주소·포트 변수 |
| app | `build: .` | `service` | `${API_PORT:-8000}` → 8000 | `curl /health` | 없음 |
| web | `build: ./web` | `service` | `${WEB_PORT:-3000}` → 80 | **새로** `wget -q --spider http://127.0.0.1/` 〔Step 1.2 정정〕(localhost는 ::1로 풀릴 수 있다, Infra 검토 R-02) | 이미지(§3), healthcheck |
| dashboard | `opensearch-dashboards:2.13.0` | **`tools`**(Q2=A) | `127.0.0.1:${DASHBOARD_PORT:-5601}` → 5601 | 없음 | 프로필, 주소·포트 변수 |

- `docker compose --profile service up -d --build`는 다섯 서비스를 띄웁니다(US-1.1). Dashboards는 `docker compose --profile tools up -d dashboard`로만 뜹니다.
- 인프라 포트는 `127.0.0.1`에만 엽니다(I8-3). 로컬 데모인데 바깥에 열 까닭이 없습니다. 호스트에서 uvicorn을 띄우는 개발 흐름은 localhost로 닿으므로 그대로 됩니다.
- 호스트 포트 번호는 env로 바꿀 수 있습니다. 기본값은 지금과 같아 `.env` 두 값만으로 뜹니다. 이미 7474/7687이 쓰이는 호스트(이 개발 호스트가 그렇다)는 `.env`에 `NEO4J_HTTP_PORT`·`NEO4J_BOLT_PORT` 두 줄을 더해 띄웁니다. 컨테이너끼리는 compose 네트워크(`neo4j:7687` 등)로 닿으므로 app 설정은 바뀌지 않습니다. 호스트 uvicorn 개발 흐름에서는 `.env`의 `NEO4J_URI`도 같은 번호로 맞춥니다(operations.md에 적는다).
- app·web 포트는 지금처럼 모든 주소에 엽니다(같은 망의 다른 기기에서 데모를 보일 수 있게). README에 그렇다고 한 줄 적습니다.
- compose 머리 주석은 다섯 서비스와 세 프로필(기본·`service`·`tools`), 준비 명령을 적습니다(postgres가 빠진 지금 주석을 고친다).

## 2. 데이터 (Q1=B)
| 볼륨 | 위치 | 비고 |
|---|---|---|
| neo4j data·logs·import·plugins | `./data/neo4j/*` bind mount | 그대로 |
| opensearch | `./data/opensearch` bind mount | 그대로 |
| postgres | `./data/postgres` bind mount | 그대로 |
| app 백업(`LOCUS_DATA_DIR`) | 이름 붙은 볼륨 `locus_data` | 그대로 |

- bind mount 폴더는 미리 있어야 하므로 `./scripts/setup-volumes.sh`를 둡니다. 스크립트의 안내 문구는 실제 명령으로 고칩니다(`--profile tools`는 이제 있다).
- **US-1.1과의 차이(사람의 결정, Q1=B)**: 시작은 "준비 명령(`./scripts/setup-volumes.sh`) + 기동 명령"입니다. README 시작 절은 두 줄로 적습니다. 준비 명령은 처음 한 번만 필요하고, 두 번 돌려도 해가 없습니다(`mkdir -p`).

## 3. 이미지
### 3.1 app (`Dockerfile`)
- 지금 그대로입니다. `python:3.11-slim`, curl, `COPY pyproject.toml README.md locus api`, `pip install .`(비편집), `CMD init-schema`. 〔Step 1.2 정정〕 단, `pyproject.toml`의 package-data 글롭은 코드 생성에서 바뀐다(Infra 검토 R-04a).
- 데모 소스는 FD의 package-data 글롭(`world/demo/worlds/*.json`, `world/demo/worlds/*/*`)으로 설치본에 들어갑니다. 이 사실은 CI 이미지 작업(§5)이 확인합니다.
- `.dockerignore`에 `web`과 `scripts`를 더합니다. root 이미지가 쓰지 않는 것을 빌드 문맥에서 빼서 문맥을 줄입니다. `examples/`는 FD에서 사라집니다.
- compose의 app 명령(`init-schema && uvicorn --workers 1`)은 그대로입니다. 기동마다 `init-schema`(world·play·localization)가 돌아 새 `EventSeed` 제약도 만듭니다. 그래서 compose 사용자는 따로 할 일이 없습니다. 호스트에서 돌리는 사람은 `locus init-schema --world`를 한 번 다시 돌립니다(FD R-07, operations.md).

### 3.2 web (`web/Dockerfile`, `web/nginx.conf`)
| 항목 | 지금 | 바뀜 |
|---|---|---|
| 빌드 이미지 | `node:20-alpine` | `node:22-alpine`(Vite 8은 Node ≥ 20.19 또는 22.12) |
| 설치 | `npm install` | `npm ci`(lock 그대로, US-7.5) |
| nginx 요청 크기 | 없음(기본 1 MiB) | `client_max_body_size 49m;` 〔Step 1.2 정정〕(앱 요청 상한 48 MiB보다 조금 크게: 상한 판정과 JSON 413은 앱이 한다, Infra 검토 R-03) |
| 프록시 시간 | `proxy_read/send_timeout 130s` | 그대로(LLM 한 줄 대기) |
| healthcheck | 없음 | compose에 `wget -q --spider http://localhost/`(nginx:alpine의 busybox wget) |

## 4. 기동 순서와 의존
```
setup-volumes.sh (처음 한 번) → cp env.example .env (두 값)
docker compose --profile service up -d --build
  neo4j ─┐
  opensearch ─┼─ healthy → app (init-schema → uvicorn) ─ healthy → web
  postgres ─┘
```
- app은 세 인프라가 healthy일 때 뜨고, web은 app이 healthy일 때 뜹니다(지금 그대로).
- 키가 없어도 app은 뜨고 `/health`는 `ok`입니다(FD BLM §4). 화면은 `GET /api/capabilities`로 LLM이 없음을 알립니다.

## 5. CI (`.github/workflows/ci.yml`, Q3=A)
| 작업 | 러너·버전 | 단계 | 실패 기준 |
|---|---|---|---|
| backend | ubuntu-latest, Python 3.11, pip 캐시 | `pip install -e ".[dev]"` → `ruff check locus api tests` → `black --check locus api tests` → seed를 정해 찍고 `pytest -q -p no:cacheprovider --hypothesis-seed=$SEED` | 하나라도 실패 |
| frontend | ubuntu-latest, Node 22, npm 캐시 | `web/`에서 `npm ci` → `npx tsc --noEmit` → `npx vitest run` | 하나라도 실패 |
| audit | ubuntu-latest, Node 22 | `web/`에서 `npm audit --omit=dev --audit-level=moderate`(lock만 읽는다) | moderate 이상이 있으면 실패(Q5=A) |
| images | ubuntu-latest, Docker | `docker build -t locus-app .` → `docker build -t locus-web web` → `docker run --rm locus-app python -c "<데모 확인>"` | 빌드 실패 또는 확인 실패 |

- 트리거: 모든 브랜치 push와 main 대상 PR. 같은 ref의 앞선 실행은 취소합니다(`concurrency`).
- 비밀값을 쓰지 않습니다. 테스트는 오프라인이고, 외부 서비스(Neo4j 등)를 띄우지 않습니다.
- **seed 기록**(BR-U8-34): `SEED=$(python -c "import secrets; print(secrets.randbelow(2**32))")`, `echo "hypothesis seed: $SEED"`, `pytest … --hypothesis-seed=$SEED`. 실패를 재현하려면 로그의 seed를 같은 옵션으로 넘깁니다. 실패한 예제의 blob은 지금 프로필(`print_blob=True`)이 찍습니다.
- **이미지의 데모 확인**: 설치된 `locus.world.demo`에서 매니페스트를 읽어(`DemoWorlds`, 서비스 없이) 항목이 하나 이상인지, 모든 항목이 검사를 통과했는지, `sources`가 있는 항목의 소스 파일이 설치본 안에 있는지 봅니다. app 이미지에 `api/`가 있는지는 `python -c "import api.main"`으로 봅니다(US-1.1). 〔Step 1.2 정정〕 데모 확인은 소스 트리가 가리지 않도록 설치본에서 돕니다(`docker run --rm -w /tmp locus-app python -I -c …`, `locus.__file__`이 site-packages 아래인지 단언). `api`는 설치되지 않으므로 `import api.main`은 `/app`에서 따로 봅니다(코드 플랜 검토 01 R-02).
- `npm ci`가 lock 그대로 성공하는 것이 frontend·images 작업의 전제입니다(US-7.5). peer 충돌이 생기면 이 두 작업이 먼저 깨집니다.
- README 배지: `https://github.com/hongsam14/Locus/actions/workflows/ci.yml/badge.svg`.
- mypy는 넣지 않습니다(기준선 11건, FD BR-U8-33).
- 워크플로는 원격에 push해야 돕니다. push와 첫 실행 확인은 사람이 합니다.

## 6. 관측
- `/health`(경계 상태)와 `GET /api/capabilities`(LLM·VLM·임베딩 유무), `docker compose ps`(healthy), `docker compose logs`가 전부입니다. 새 관측 도구는 없습니다(I8-7).

## 7. 공유 인프라
- 없습니다. 이 사이클에서 배치를 가진 유닛은 U8뿐이라 `shared-infrastructure.md`는 만들지 않습니다(I8-8).

## 8. 이탈과 위험
- **US-1.1 "명령 하나"**: Q1=B로 준비 명령이 하나 더 있습니다(사람의 결정).
- **npm audit 막기**: 외부 자문이 새로 나오면 audit 작업만 빨갛게 됩니다(FD Q5=A의 감수한 위험).
- **이미지 작업 시간**: PR마다 3~5분이 더 듭니다(Q3=A).
- **호스트 포트 충돌**: 기본값이 쓰이는 호스트는 `.env`에 포트 변수를 더해야 합니다. operations.md에 예를 둡니다.
