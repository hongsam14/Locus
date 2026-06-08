# U1 Foundation — Code Generation Plan

**Single source of truth for U1 code generation.** Greenfield 모놀리스, 코드 위치 = `locus/` 패키지(UOW-Q3=A). 문서 요약만 `aidlc-docs/construction/U1-foundation/code/`.

## Unit Context
- **Stories**: US-9.1(Neo4j 그래프 영속화), US-9.2(OpenSearch 의미·하이브리드 검색), US-9.4(LLM/VLM/Embedding 제공자 추상화), US-9.3(Docker Compose 토대).
- **Dependencies**: 없음(U1은 최하위 토대). 이후 모든 Unit이 U1에 의존.
- **Contracts 제공**: 도메인 모델, GraphRepository/SearchRepository 포트, LLM/VLM/Embedding 포트, CommonsenseWiki lookup 인터페이스(+LLM 폴백), SchemaInitializer.
- **설계 근거**: domain-entities/business-rules(:Rumor 별도 라벨), nfr-design(retry 3x/30s, 단일 인덱스+world_id, 캐시 없음), infrastructure-design(compose).

## Steps

- [x] **Step 1 — Project Structure Setup**: pyproject.toml, .gitignore, env.example, README.md, 패키지 디렉토리, tests 구조. (pytest 설정은 pyproject [tool.pytest])
- [x] **Step 2 — Domain Models** (`locus/models/`): enums/graph/io/reports + 검증. [US-9.1/9.2/9.4 계약]
- [x] **Step 3 — Models Unit Tests**(+PBT): round-trip(hypothesis), 범위 검증, Rumor 불변식.
- [x] **Step 4 — Config** (`locus/config/settings.py`): pydantic-settings(.env, populate_by_name).
- [x] **Step 5 — LLM Provider Layer** (`locus/llm/`): base/retry/openai_provider/factory. [US-9.4]
- [x] **Step 6 — LLM Unit Tests**: retry + factory(mock).
- [x] **Step 7 — Storage Ports + Neo4j** (`locus/storage/`): base/neo4j_repo/schema. [US-9.1]
- [x] **Step 8 — Storage OpenSearch** (`opensearch_repo.py`): 단일 인덱스, kNN+BM25, world_id 필터. [US-9.2]
- [x] **Step 9 — Storage Unit Tests**: Cypher/쿼리 구성 + injection guard(mock).
- [x] **Step 10 — CommonsenseWiki Interface** (`commonsense_wiki/base.py`): lookup + LLM 폴백. [FR-E lookup]
- [x] **Step 11 — Wiki Interface Unit Tests**: hit/miss 폴백.
- [x] **Step 12 — Deployment Artifacts**: docker-compose.yml, Dockerfile, requirements(.txt/-dev.txt).
- [x] **Step 13 — Documentation**: code-gen-summary.md, README.

**Verification**: 24 tests PASS, ruff/black clean, compileall clean (외부 호출 mock, 오프라인).

## Story Coverage
- US-9.1 → Step 2,7 · US-9.2 → Step 2,8 · US-9.4 → Step 5 · US-9.3 → Step 1,12.
- FR-E lookup(폴백) → Step 10 (전체 Wiki는 U6).

## Notes
- 테스트는 작성만(실행은 Build & Test 단계). 외부 호출(OpenAI/Neo4j/OpenSearch)은 단위테스트에서 mock.
- 코드 스타일: black(line 100), ruff, 타입 힌트. Pydantic v2.
