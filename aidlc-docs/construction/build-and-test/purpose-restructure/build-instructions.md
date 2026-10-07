# Build Instructions — Purpose Restructure (U1~U8)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: 이 주기의 Build & Test입니다. 이 문서는 무엇을 어떻게 빌드하는지 적습니다.

## 준비
- Docker + Docker Compose(v2, `--wait` 지원)
- 처음 한 번: `./scripts/setup-volumes.sh`(`./data` bind mount 폴더)
- `cp env.example .env` 후 `NEO4J_PASSWORD`, `SESSION_DB_PASSWORD` 두 값을 채운다. `OPENAI_API_KEY`는 없어도 뜬다. 넣으면 LLM 기능이 켜진다.
- 호스트 개발: Python 3.11+, Node 22

## 이미지 빌드와 기동 (배포 경로)
```bash
docker compose --profile service up -d --build --wait   # neo4j·opensearch·postgres + app(:8000) + web(:3000)
docker compose ps                                       # 다섯 서비스 healthy
curl -s localhost:8000/health                           # {"status":"ok",...}
curl -s localhost:8000/api/capabilities                 # {"llm":…,"vlm":…,"embedding":…}
```
- 포트가 이미 쓰이면 `.env`나 명령줄에 포트 변수를 준다. 이 개발 호스트에서는 3000을 다른 스택이 써서 `WEB_PORT=13000 docker compose …`로 띄웠다. 인프라 포트는 127.0.0.1에만 열린다. 변수: `NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, `OPENSEARCH_PORT`, `SESSION_DB_PORT`, `DASHBOARD_PORT`, `API_PORT`, `WEB_PORT`.
- app 이미지
  - `python:3.11-slim`에 `pip install .`을 한다(비편집 설치, 빌드 요구 `setuptools>=77`).
  - 기동마다 `init-schema`를 돌린 뒤 uvicorn 워커 하나로 뜬다.
- web 이미지
  - `node:22-alpine`에서 `npm ci` 후 `vite build`를 하고, nginx로 서빙한다.
  - nginx: `/api` 130초, 빌드 경로 600초, `client_max_body_size 49m`
- 멈추기: `docker compose --profile service --profile tools down`(데이터는 `./data`에 남는다)

## 이미지 안 확인 (CI images 작업과 같음)
```bash
docker run --rm -w /tmp <app-image> python -I -c "import locus; assert 'site-packages' in locus.__file__; from locus.world.demo import check_packaged; p=check_packaged(); print(p); raise SystemExit(bool(p))"
docker run --rm -w /app <app-image> python -c "import api.main"
```

## 호스트 개발 빌드
```bash
pip install -e ".[dev]"
cd web && npm ci && npm run build      # tsc + vite build -> web/dist
```

## 문제 해결
- `NEO4J_PASSWORD is required`: `.env`의 필수 두 값이 비어 있다.
- 포트 충돌(`address already in use`): 위 포트 변수로 번호를 바꾼다.
- Neo4j가 처음 뜰 때 APOC 플러그인을 내려받는다(인터넷 필요). healthy까지 1~2분 걸린다.
- 빌드 요구 setuptools를 받지 못하면(오프라인) 이미지 빌드가 멈춘다. pip 프록시나 캐시를 쓴다.
