# Technology Stack

> Reverse Engineering — Follow-up Cycle (2026-10-07). 기준 커밋 `240e82d`. 2026-09-29 판을 대체한다.
> 버전은 **설치된 값**이다. Python은 `.venv`의 importlib.metadata에서, 프론트는 `web/node_modules/*/package.json`에서 읽었다. 선언 범위는 `dependencies.md`에 있다.

## Programming Languages
- Python - 선언 `>=3.11` / CI 3.11 / Docker `python:3.11-slim` / 로컬 3.14.4 - 백엔드 전체(`locus/`, `api/`, `tests/`, `scripts/`). 로컬 `.venv`에 3.13과 3.14 site-packages가 섞여 있다.
- TypeScript - 5.9.3(선언 `^5.5.0`), strict - 프론트엔드 `web/src`.
- Cypher - Neo4j 5 - `shared/storage/neo4j_repo.py`.
- SQL - SQLAlchemy Core(PostgreSQL 16 / 테스트 SQLite) - `play/storage`, `localization/storage`.
- 그 밖: nginx conf, bash, GitHub Actions YAML.

## Frameworks
- FastAPI - 0.141.1 - HTTP API, 의존성 주입, lifespan.
- Starlette - 1.6.0 - FastAPI 아래 ASGI. `BodyLimitMiddleware`가 순수 ASGI로 붙는다.
- uvicorn - 0.52.1 - ASGI 서버(`--workers 1`).
- Pydantic - 2.13.4 / pydantic-settings 2.15.0 - 모델, DTO, 설정.
- SQLAlchemy - 2.0.51 (+ psycopg 3.3.4) - 세션·번역 저장소.
- LangChain - langchain 1.3.14, langchain-core 1.5.3, langchain-openai 1.4.3 - LLM·VLM·임베딩 어댑터.
- LangGraph - 1.2.10 - 진행 중인 래퍼 하나만 쓴다(연결 안 됨).
- openai - 2.53.0 - langchain-openai를 거쳐 쓴다.
- tenacity - 9.1.4 - LLM 재시도.
- React - 18.3.1 / react-dom 18.3.1 - SPA.
- react-router-dom - 7.18.4 - 라우팅(화면 넷).
- Tailwind CSS - 4.3.3(`@tailwindcss/vite`) - 디자인 토큰(`@theme`), 설정 파일 없음.
- @fontsource/gaegu - 5.3.0 - 손글씨 한글 글꼴(자체 호스팅).

## Infrastructure
- Neo4j - 5.15-community + APOC - 캐노니컬 그래프(라벨 7종, 관계 9종). 클라이언트는 neo4j 5.28.4다.
- OpenSearch - 2.13.0(보안 플러그인 꺼짐) - 지식·엔티티·NPC·prior 문서, BM25 + kNN(HNSW, nmslib). 클라이언트는 opensearch-py 2.8.0이다.
- OpenSearch Dashboards - 2.13.0 - `tools` 프로필의 선택 도구다.
- PostgreSQL - 16-alpine - 세션 테이블 11개와 `translations`.
- OpenAI - `gpt-4o`(채팅·VLM), `text-embedding-3-small`(1536차원) - 선택이다. 키가 없으면 LLM 기능만 꺼진다.
- nginx - alpine - SPA 정적 파일과 `/api` 프록시.
- Docker Compose - v2(로컬 2.40.3) - 프로필 셋(기본, `service`, `tools`).
- GitHub Actions - `ubuntu-latest`(2026-10-19부터 Ubuntu 26), `actions/checkout@v4`, `setup-python@v5`, `setup-node@v4`. 이 액션들은 Node 20 대상이라 경고가 난다.

## Build Tools
- setuptools - `>=77.0` + wheel - Python 패키지(SPDX 라이선스, 패키지 데이터).
- pip - `pip install -e ".[dev]"`(CI), `pip install .`(Docker). lock 파일은 없다.
- npm - 9.2.0(로컬), `npm ci` + `package-lock.json` v3 - 프론트 의존성.
- Node - v22.22.1(로컬), CI "22", Docker `node:22-alpine`. engines 선언은 없다. Vite 8은 `^20.19.0 || >=22.12.0`을 요구한다.
- Vite - 8.0.16(rolldown 1.0.3) + @vitejs/plugin-react 5.2.0 - 번들(JS 324.7 kB, gzip 96.6 kB, 코드 분할 없음).
- Docker - 이미지 둘(app, web).

## Testing Tools
- pytest - 9.1.1 - 백엔드 948 테스트.
- pytest-cov - 7.1.0(coverage 7.15.4) - 커버리지 94%. CI는 `locus`만 재고 하한이 없다.
- hypothesis - 6.165.3 - `@given` 55개(PBT Partial).
- ruff - 0.16.2 - lint(E,W,F,I,B,C4).
- black - 26.5.1 - 포맷(줄 100).
- mypy - 2.3.0 - 11건(기준선). CI에는 없다.
- vitest - 4.1.9 + jsdom 24.1.3 - 프론트 202 테스트. 커버리지 도구는 없다.
- @testing-library/react 16.3.2 · dom 10.4.1 · jest-dom 6.9.1 - 컴포넌트 테스트.
- tsc - `--noEmit` - 프론트 타입 검사(`npm run lint`). ESLint는 없다.
- npm audit - 런타임 0건, dev 5건(moderate 3, high 2).
- `scripts/live_scenario.py` - 실제 스택 15단계 시나리오(운영자가 돌림).
- 없는 것: 시각 회귀, 반응형, 접근성(axe), 브라우저 E2E(Playwright 등), 부하 테스트.
