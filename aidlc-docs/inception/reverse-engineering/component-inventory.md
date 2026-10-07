# Component Inventory

> Reverse Engineering — Follow-up Cycle (2026-10-07). 기준 커밋 `240e82d`. 2026-09-29 판을 대체한다.
> 줄 수는 `wc -l`(공백·주석 포함)이다. 2026-09-29 판의 수(개편 전)는 비교용으로 괄호에 적었다.

## Application Packages
- `locus/world` (6,455줄) - 월드 만들기와 편집이다. 빌드(수집·토폴로지·온톨로지·wiki), 에디터, 보강 Q&A, World File, 매니페스트 데모, NPC 초안을 맡는다.
- `locus/play` (8,524줄) - 플레이다. 세션, 플레이어 이동, 턴 엔진, NPC 대화·판단, 행적, 소문(생성·전파·동역학), 사건(동역학·제안·씨앗), GM 조작, 세계 상태, PostgreSQL 저장소를 맡는다.
- `locus/knowledge` (717줄) - 스냅샷 로더, `WorldCache`, 지역별 합의, 질의를 맡는다.
- `locus/localization` (684줄) - 번역 캐시(읽기·warm·purge)를 맡는다.
- `api/` (2,544줄) - FastAPI 합성 루트와 라우터 다섯(`world`, `world_editor`, `knowledge`, `play`, `gm`)이다. 라우트는 77개다.
- `locus/__main__.py` (355줄) - CLI 합성 루트다.
- `web/` (src 7,851줄, 77파일) - React SPA 네 화면이다(홈·에디터·플레이·GM). 2026-09-29에는 1,968줄이었다.

## Infrastructure Packages
- `docker-compose.yml` - Compose - 서비스 여섯(neo4j, opensearch, postgres, dashboard[tools], app[service], web[service])이다. 인프라 포트는 `127.0.0.1`에 묶이고, app·web은 `0.0.0.0`이다.
- `Dockerfile` - Docker - app 이미지다(`python:3.11-slim`, root로 실행, `api/`는 소스 디렉터리로 import).
- `web/Dockerfile` + `web/nginx.conf` - Docker/nginx - `node:22-alpine` 빌드 → `nginx:alpine`. 빌드 경로 600초, `/api` 130초, 본문 49m.
- `.github/workflows/ci.yml` - GitHub Actions - 잡 넷(backend, frontend, audit, images)이다. 2026-09-29에는 CI가 없었다.
- `scripts/setup-volumes.sh` - bash - `./data` 바인드 폴더를 만든다.
- `env.example` - 설정 - 필수 비밀값 둘과 조정값 약 50개.
- CDK, Terraform, CloudFormation은 없다.

## Shared Packages
- `locus/shared` (3,046줄) - Models/Utilities/Clients - 도메인 모델, 설정·조정값, LLM 포트와 OpenAI 어댑터, 그래프·검색 포트와 Neo4j·OpenSearch 어댑터, SQL 보조, 프롬프트 위생을 담는다.
- `locus/world/demo/worlds/` - Data - 매니페스트와 Emberleaf World File, 소스(메모·구조화 지도)다. 패키지 데이터로 휠에 들어간다.
- `web/src/ui/` (14파일) - UI primitives - Button, Panel, Card, Badge, Field, Range, CommitRange, Modal, Toast, NotificationCenter, LocalizedText, LlmNotice, InProgressBadge.

## Test Packages
- `tests/play/` - Unit/Contract/PBT - 29파일, 394 테스트.
- `tests/world/` - Unit/PBT - 20파일, 224 테스트.
- `tests/api/` - API(TestClient + 가짜) - 14파일, 120 테스트.
- `tests/shared/` - Unit/Contract - 8파일, 114 테스트.
- `tests/localization/` - Unit/PBT - 4파일, 41 테스트.
- `tests/knowledge/` - Unit/PBT - 4파일, 26 테스트.
- `tests/` 루트 - Meta - 5파일, 29 테스트(경계 행렬, 패키징, 데모는 데이터, CLI, 라이브 시나리오 분기).
- `web/src/__tests__/` - Component(vitest + jsdom) - 9파일, 202 테스트.
- `scripts/live_scenario.py` - Live E2E(운영자가 돌림, CI 밖) - 15단계.
- 라이브 통합 테스트(실제 Neo4j·OpenSearch·PostgreSQL·OpenAI)는 없다.

## Total Count
- **Total Packages**: 18. 백엔드 경계 5 + `api` + CLI + `web` + 인프라 묶음 5(compose, app Dockerfile, web Dockerfile/nginx, CI, scripts) + 테스트 묶음 3(`tests/`, `web/src/__tests__/`, live scenario). 데이터·UI 프리미티브는 위 패키지에 포함해 따로 세지 않았다.
- **Application**: 7 (`world`, `play`, `knowledge`, `localization`, `api`, CLI, `web`)
- **Infrastructure**: 5
- **Shared**: 1 (`locus/shared`)
- **Test**: 3
- **코드 규모**:

  | 영역 | 줄 |
  |---|---|
  | `locus/` 전체 | 19,784 (151파일) |
  | `api/` | 2,544 |
  | `web/src` | 7,851 |
  | 백엔드 테스트 | 20,434 |
  | 프론트 테스트 | 3,742 |
