# U8 데모·배포·문서 — Deployment Architecture

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 배치 설계 중 그림입니다. 관람자·개발자·CI가 각자 무엇을 띄우고 어디로 닿는지 보입니다. 결정과 근거는 `infrastructure-design.md`에 있습니다.

## 1. 관람자 배치 (`--profile service`)
```
브라우저 ──:3000──▶ web (nginx) ──/api/*──▶ app (FastAPI, :8000, --workers 1)
                     │  정적 SPA                   │
                     │  client_max_body_size 48m   ├── bolt ──▶ neo4j (:7687)      ┐
                     │  proxy timeout 130s         ├── http ──▶ opensearch (:9200) ├ compose 네트워크 locus-net
                     └ healthcheck wget /          └── sql  ──▶ postgres (:5432)   ┘
                                                    └── (선택) OpenAI ── OPENAI_API_KEY가 있을 때
호스트 공개: web :3000, app :8000 (모든 주소) · neo4j/opensearch/postgres (127.0.0.1만, 번호는 env)
```
- 데이터: `./data/neo4j/*`, `./data/opensearch`, `./data/postgres`(bind mount, 준비 명령이 만든다), app 백업은 볼륨 `locus_data`.
- 키가 없으면 OpenAI 쪽이 없고, 화면은 `capabilities.llm=false`로 미리 알립니다.

## 2. 시작 흐름 (README 시작 절)
| # | 명령 | 결과 |
|---|---|---|
| 1 | `./scripts/setup-volumes.sh` | `./data/…` 폴더(처음 한 번, Q1=B) |
| 2 | `cp env.example .env` 후 `NEO4J_PASSWORD`·`SESSION_DB_PASSWORD` | 두 값 |
| 3 | `docker compose --profile service up -d --build` | 다섯 서비스 healthy |
| 4 | `http://localhost:3000` → 데모 카드 [바로 플레이] | `/play/:id` |

- 7474/7687이 이미 쓰이는 호스트: `.env`에 `NEO4J_HTTP_PORT=17474`, `NEO4J_BOLT_PORT=17687`을 더한다.
- 다 쓰고 나면 `docker compose --profile service down`. 데이터를 지우려면 `./data`를 지운다.

## 3. 개발자 배치 (기본 프로필 + 호스트 실행)
```
docker compose up -d                 → neo4j, opensearch, postgres (127.0.0.1)
docker compose --profile tools up -d dashboard   → OpenSearch Dashboards (127.0.0.1:5601, 필요할 때만)
locus init-schema                    → 제약·색인·표 (EventSeed 제약 포함)
uvicorn api.main:app --port 8000     → 호스트의 app
cd web && npm run dev                → :5173, /api → :8000 프록시
```

## 4. CI (`.github/workflows/ci.yml`)
```
push(모든 브랜치) / PR(main) ─┬─ backend  : pip install -e .[dev] → ruff → black --check → pytest --hypothesis-seed=$SEED (seed를 로그에)
                              ├─ frontend : npm ci → tsc --noEmit → vitest run
                              ├─ audit    : npm audit --omit=dev --audit-level=moderate
                              └─ images   : docker build app → docker build web → docker run app (import api.main, 매니페스트 데모·소스 확인)
같은 ref의 앞선 실행은 취소 · 비밀값 없음 · 외부 서비스 없음
```

## 5. 무엇이 어디서 확인되는가
| 수용 기준 | 확인 |
|---|---|
| US-1.1 이미지에 `api/` | CI images(`import api.main`) |
| US-1.1 다섯 서비스 healthy, `:3000`, `/health` ok | 운영자(Build&Test 라이브 시나리오 1단계, `docker compose ps`) |
| US-1.1 README가 없는 프로필을 부르지 않는다 | `tools` 프로필이 생기고, 문서 검사(Code Generation의 문서 단계) |
| US-1.3 데모 소스가 이미지에 | CI images(매니페스트·소스 확인) |
| US-7.5 `npm ci` peer 충돌 없음 | CI frontend·images |
| US-7.6 pytest(seed)·vitest·ruff·black·tsc, 배지 | CI backend·frontend, README |
| npm audit 0건 | CI audit |
