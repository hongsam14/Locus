# Build Instructions — Follow-up 주기 (V1~V9)

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것.
**지금 하는 것**: 이 주기의 Build and Test다. 이 문서는 무엇을 어떻게 빌드하는지 적는다. 지난 주기(`../purpose-restructure/build-instructions.md`)와 같은 것은 다시 적지 않고, 이 주기에 바뀐 것만 적는다.

## 준비
- Docker + Docker Compose v2. 이 호스트는 Docker 29.1.1, Compose v2.40.3.
- 처음 한 번 `./scripts/setup-volumes.sh`를 돌린다.
- `cp env.example .env` 후 필수 두 값(`NEO4J_PASSWORD`, `SESSION_DB_PASSWORD`)을 채운다. V9부터 `env.example`이 모든 설정을 적는다(`SESSION_DB_HOST`, `TRANSLATION_WARM_WORKERS` 포함).
- 호스트 개발: Python 3.11+, Node 22. 잠금 파일을 고칠 때는 npm 11을 쓴다(npm 9·10의 `audit fix`는 arborist에서 죽는다. V9 code-summary § 5).

## 이미지 빌드와 기동
```bash
WEB_PORT=13000 docker compose --profile service up -d --build   # 이 호스트: 3000은 다른 서비스가 쓴 적이 있다
docker compose ps                                               # 다섯 서비스 healthy
curl -s localhost:8000/health                                   # {"status":"ok", 네 경계 true}
curl -s localhost:8000/api/capabilities                         # {"llm":true,"vlm":true,"embedding":true}
```
- 인프라 포트(Neo4j·OpenSearch·PostgreSQL·Dashboards)는 127.0.0.1에만 열린다. app(`API_PORT`)과 web(`WEB_PORT`)은 모든 주소에 열린다.
- app 이미지
  - `python:3.11-slim`에 `pip install .`을 한다. 휠에는 `locus*`만 들어가고, `api`는 `/app`의 소스로 읽힌다(V9 Dockerfile 주석).
  - 기동마다 `init-schema` 뒤 uvicorn 워커 하나로 뜬다.
  - healthcheck: `curl -sf http://localhost:8000/health`.
- web 이미지
  - `node:22-alpine`에서 `npm ci`와 `vite build`를 한다. nginx가 서빙한다.
  - `/` 는 `no-cache`, `/assets/`는 1년 `immutable`이다. `favicon.svg`(V9)도 함께 나간다.
  - healthcheck: `wget -q --spider http://127.0.0.1/`.
- 멈추기: `docker compose --profile service --profile tools down`. 데이터는 `./data`와 이름 볼륨 `locus_data`(백업)에 남는다.

## 호스트 개발 빌드
```bash
pip install -e ".[dev]"
cd web && npm ci && npm run build      # tsc -b + vite build -> web/dist (에디터·GM은 지연 묶음)
```

## 이 주기에 바뀐 빌드 사실
- CI(V1): 러너 `ubuntu-26.04`, 액션 새 주 버전.
- CI(V9)
  - backend 잡에 `mypy locus api`(오류 0)를 더했다. ruff·black 대상에 `scripts`를 넣었다.
  - pytest 설정이 ResourceWarning을 오류로 본다.
- 의존성(V9): `langchain-openai>=0.2`. 공급자가 pydantic v2 `SecretStr`로 키를 넘기기 때문이다.
- 웹(V2~V8): 글꼴 셋을 `@fontsource`로 자체 호스팅한다. 첫 화면 JS gzip은 119.39 kB이고, 에디터 14.68 kB와 GM 11.98 kB는 지연 묶음이다.
