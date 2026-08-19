# UX Improvement — Build Instructions

## Prerequisites
- Python 3.11+ (this env: 3.13 `.venv`), Node 18+ / npm.
- `.env` from `env.example` (NEO4J_PASSWORD, SESSION_DB_PASSWORD required; TRANSLATION_* optional).

## Build Steps
### Backend
```bash
pip install -e ".[dev]"
python -m compileall -q locus api      # sanity
```
### Frontend
```bash
cd web && npm install --legacy-peer-deps   # pre-existing @vitejs/plugin-react↔vite8 peer
npm run build                              # tsc -b && vite build
```
> `--legacy-peer-deps`는 기존 vite8/plugin-react peer 불일치 때문(런타임 영향 없음).

## Verify
- Backend: `python -m compileall` OK, `ruff check` / `black --check` clean.
- Frontend: `vite build` 성공(dist/), Gaegu 폰트 woff2 번들 확인, 외부 CDN 호출 없음.
- API: `python -c "from api.main import create_app; print(len(create_app(session_query=object()).openapi()['paths']))"` → 31.

## Artifacts
- `web/dist/`(정적 번들, git-ignored), 백엔드는 소스 실행(uvicorn).
