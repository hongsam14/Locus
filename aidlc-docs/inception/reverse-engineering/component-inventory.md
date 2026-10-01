# Component Inventory

> Reverse Engineering — Purpose Restructure Cycle (2026-09-29). 목적 태그는 `business-overview.md` § 목적 지도를 따른다.

## Application Packages

| Package | 줄 수 | Purpose | 목적 태그 | 핵심 산출물 기준 필수도 |
|---|---|---|---|---|
| `locus/ingestion` | 758 | 입력 자료 → 후보 구조 | TOPOLOGY, KNOWLEDGE | 메모·구조화 지도는 **필수**, 지도 이미지는 보조, 컨셉아트는 부가 |
| `locus/topology` | 248 | 지역 계층 + 가중치 연결망 | TOPOLOGY | **필수** (산출물 1) |
| `locus/ontology` | 657 | 스코핑, 고증, 중복 제거, 정합 | KNOWLEDGE, WIKI | `scope_knowledge`는 **필수**, 나머지는 보조·부가 |
| `locus/consensus` | 204 | 지역별 "아는 것" 계산 | KNOWLEDGE, NPC-SERVE | **필수** (산출물 2) |
| `locus/query` | 116 | 월드 로드, 지역 질의, 비교 | NPC-SERVE | **필수** |
| `locus/services` | 200 | 조립, 편집, 내보내기 | INFRA, DESIGNER | orchestrator는 **필수**, editor·exporter는 보조 |
| `locus/commonsense_wiki` | 452 | 월드별 상식 prior | WIKI | 부가 (근거 문구와 고증에만 쓰임) |
| `locus/augmentation` | 571 | 기획자 보강 Q&A | DESIGNER | 부가 (현재 UI에서 동작하지 않음) |
| `locus/session` | 2,180 | 게임 세션 시뮬레이터 | SIMULATION (+ NPC-SERVE 1) | 별도 제품에 가까운 부가 기능 |
| `locus/translation` | 209 | 표시용 번역 캐시 | L10N | 부가 (NPC 산출물과 무관) |
| `api/` | 545 | HTTP 서빙, 조립 | INFRA + 전부 | 필수 (라우터별로 다름) |
| `web/` | 1,968 (+388 테스트) | 단일 페이지 UI | SIMULATION 51%, INFRA 15%, TOPOLOGY 12%, DESIGNER 9%, KNOWLEDGE 6%, L10N 6% | 보조 |
| `locus/__main__.py`, `locus/demo.py` | 168 | CLI, 데모 입력 | INFRA | 필수 (현실적인 유일한 진입점) |

## Infrastructure Packages

| Package | Type | Purpose |
|---|---|---|
| `docker-compose.yml` | Docker Compose | neo4j, opensearch, postgres, dashboard (기본) / app, web (`service` 프로파일) |
| `Dockerfile` | Docker | 백엔드 이미지. `api/`를 복사하지 않아 기동하지 못한다 |
| `web/Dockerfile`, `web/nginx.conf` | Docker + nginx | 프론트 빌드와 `/api` 프록시 |
| `scripts/setup-volumes.sh` | Shell | `./data` 바인드 마운트 준비 |
| CDK / Terraform / CloudFormation | – | 없음 |

## Shared Packages

| Package | Type | Purpose |
|---|---|---|
| `locus/models` (554) | Models | 도메인 어휘 (세션·번역 필드가 섞여 있음) |
| `locus/config` (121) | Utilities | 설정 (세션·루머·번역 설정이 섞여 있음) |
| `locus/llm` (274) | Clients | LLM·VLM·임베딩 포트와 OpenAI 어댑터 |
| `locus/storage` (1,650) | Clients | Neo4j·OpenSearch 어댑터, 매핑, 저장, 스키마 + PostgreSQL 세션 어댑터 (706) |

## Test Packages

| Package | Type | Files | Tests | 비고 |
|---|---|---|---|---|
| `tests/session` | Unit + PBT + API + Contract | 14 | 121 | 전체의 44%. 계약 테스트는 인메모리 어댑터만 |
| `tests/storage` | Unit (mocked) + SQLite | 3 | 26 | PostgreSQL 어댑터는 SQLite로 검증 |
| `tests/ingestion` | Unit + PBT | 2 | 19 | |
| `tests/commonsense_wiki` | Unit | 2 | 17 | 교차 월드 테스트가 필터 dict만 확인해서 실환경 결함을 놓친다 |
| `tests/query` | Unit + API | 3 | 17 | |
| `tests/ontology` | Unit + PBT | 2 | 15 | |
| `tests/augmentation` | Unit + API | 2 | 12 | detectors·engine 커버리지 48% |
| `tests/topology` | Unit + PBT | 1 | 10 | |
| `tests/translation` | Unit + PBT | 2 | 10 | |
| `tests/models` | Unit + PBT | 1 | 8 | |
| `tests/services` | Unit | 1 | 7 | |
| `tests/consensus` | Unit + PBT | 1 | 6 | |
| `tests/llm` | Unit | 1 | 4 | |
| `web/src/__tests__` | Unit + Component | 2 | 24 | 62%가 세션 관련. App, Toolbar, 드래그, 보강 답변은 테스트 없음 |

라이브 통합 테스트(Neo4j, OpenSearch, PostgreSQL, OpenAI)는 없다. 운영자가 직접 돌리는 시나리오 문서만 있다(`construction/build-and-test/**`).

## Total Count

- **Total Packages**: 35 (아래 넷의 합)
- **Application**: 13 (ingestion, topology, ontology, consensus, query, services, commonsense_wiki, augmentation, session, translation, api, web, CLI·demo)
- **Infrastructure**: 4 (compose, 백엔드 Dockerfile, web Dockerfile·nginx, scripts)
- **Shared**: 4 (models, config, llm, storage)
- **Test**: 14 (backend 13 + frontend 1)
