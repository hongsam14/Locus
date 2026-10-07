# Technology Stack

> Reverse Engineering — Purpose Restructure Cycle (2026-09-29). "선언"은 pyproject/package.json, "설치"는 로컬 `.venv`와 `web/package-lock.json` 기준이다.

## Programming Languages

- Python — `>=3.11` 선언
  - Docker 이미지는 3.11-slim이다.
  - 로컬 `.venv`는 3.14.4다. 시스템 python을 가리키는 심볼릭 링크이고 3.13·3.14 site-packages가 섞여 있어, 동작은 하지만 불안정하다.
  - 백엔드 전체(`locus/`, `api/`, `tests/`)에 쓴다.
- TypeScript — 5.9.3 — 프론트엔드 `web/src` (strict. 단 `noUnusedLocals`·`noUnusedParameters`는 false)
- Cypher — Neo4j 쿼리. `neo4j_repo.py` 안에 문자열로 있다.
- SQL — SQLAlchemy Core로 생성한다. 수작업 `ALTER TABLE`이 하나 있다.

## Frameworks

- FastAPI — 0.141.1 — HTTP API (`on_event("startup")` deprecated)
- Pydantic v2 / pydantic-settings — 2.13.4 / 2.15.0 — 도메인 모델, 설정
- LangChain / langchain-openai — 1.3.14 / 1.4.3 — OpenAI 호출 추상화 (`llm/openai_provider.py`에서만)
- LangGraph — 1.2.10 — 호출되지 않는 `augmentation/graph.py`에서만 import
- SQLAlchemy — 2.0.51 (Core) — 세션 저장소
- React / React DOM — 18.3.1 — UI
- Tailwind CSS — 4.3.3 (`@tailwindcss/vite`) — "Doodly" 종이+잉크 디자인 시스템
- Vite — 8.0.16 — 번들러, 개발 서버 `/api` 프록시

## Infrastructure

| Service | Image / Version | Port | Purpose | 비고 |
|---|---|---|---|---|
| Neo4j | neo4j:5.15-community + APOC | 7474, 7687 | 캐노니컬 그래프 | `NEO4J_PASSWORD` 필수 |
| OpenSearch | opensearch:2.13.0 | 9200 | 하이브리드 검색 (실제로 읽는 것은 WikiPrior뿐) | 보안 꺼짐 |
| OpenSearch Dashboards | 2.13.0 | 5601 | 인덱스 확인 | 기본 프로파일로 뜬다 (`tools` 프로파일 없음) |
| PostgreSQL | postgres:16-alpine | 5432 | 세션, 번역 캐시 | `SESSION_DB_PASSWORD` 필수 |
| app | 루트 Dockerfile (python 3.11-slim) | 8000 | uvicorn `api.main:app` | `service` 프로파일. `api/`가 이미지에 없어 기동하지 못함 |
| web | node:20-alpine → nginx:alpine | 3000→80 | SPA + `/api` 프록시 | `service` 프로파일 |
| OpenAI API | `gpt-4o`, `text-embedding-3-small`(1536) | – | LLM, VLM, 임베딩 | 공급자는 openai만 |

- 볼륨: `./data/{neo4j,opensearch,postgres}` 바인드 마운트.
- 네트워크: `locus-net` 브리지.
- 클라우드 IaC 없음.

## Build Tools

- setuptools (≥61) + wheel — Python 패키지, `locus` 콘솔 스크립트
- pip — `requirements.txt`는 sqlalchemy·psycopg가 빠져 pyproject와 어긋난다
- npm — 로컬 9.2 / Node v22.22.1. Docker 빌드는 node 20에서 `npm install`(ci 아님)
- Docker / Docker Compose — 로컬 배포

## Testing Tools

- pytest — 9.1 — 백엔드 281 테스트, 약 10초, 오프라인
- pytest-cov — 7.1 — 커버리지 87% (`locus`+`api`)
- hypothesis — 6.165 — PBT (Partial: 순수 함수·직렬화 왕복)
- Vitest — 4.1.9 + jsdom 24 + Testing Library (react 16.3.2, dom 10.4.1, jest-dom 6.9.1) — 프론트 24 테스트
- ruff — 0.16 — lint (clean)
- black — 26.5 — format (clean)
- mypy — 2.3 — 설정만 있고 강제하지 않는다. 오류 16개(10 파일)
- tsc — `--noEmit`가 프론트 "lint"를 대신한다. ESLint 없음.
- CI — 없음
