# U1 Foundation — Tech Stack Decisions

| 영역 | 선택 | 버전/세부 | 근거 |
|---|---|---|---|
| 언어/런타임 | Python | 3.11+ | Q5(요구)=A, 참고 프로젝트 동일 |
| 데이터 모델 | Pydantic | v2 | 검증·직렬화·PBT round-trip |
| 그래프 DB | Neo4j Community | **5.x** | NFR1-Q4=A, 그래프 순회/관계 쿼리 |
| Neo4j 드라이버 | `neo4j` (공식) | 5.x | 공식 지원 |
| 검색/벡터 | OpenSearch | **2.x** | NFR1-Q4=A, 하이브리드 BM25+vector (CL6=B) |
| OpenSearch 클라이언트 | `opensearch-py` | 2.x | 공식 |
| LLM/VLM 추상화 | LangChain | 최신 안정 | AD-Q4=C (LangChain 추상화) |
| 오케스트레이션(국소) | LangGraph | 최신 안정 | AD-CL1=A (보강 Q&A 루프 등) — U7에서 본격 사용 |
| LLM/VLM 기본 제공자 | OpenAI | `openai` SDK (LangChain 경유) | Q7=D 기본 OpenAI |
| 임베딩 | OpenAI `text-embedding-3-small` | 추상화 뒤, 교체 가능 | NFR1-Q1=A |
| API (후속 Unit) | FastAPI | 최신 안정 | AD-Q1=A |
| 설정 | pydantic-settings + `.env` | — | NFR1-Q6=A |
| 재시도 | tenacity (또는 자체 백오프) | — | NFR1-Q5=A |
| 패키징 | `pyproject.toml` (pip/`-e .`) | — | 참고 프로젝트 동일 |
| 컨테이너 | Docker + docker-compose | — | Q11=A |
| 품질 | black(line 100) · ruff · (선택) mypy · pytest | — | 유지보수 |
| 테스트 | pytest + hypothesis(PBT Partial) | — | NFR-C2 |

## 라이브러리 의존(요지)
- 런타임: `pydantic`, `pydantic-settings`, `neo4j`, `opensearch-py`, `langchain`, `langgraph`, `openai`, `tenacity`, `fastapi`/`uvicorn`(후속).
- 개발: `pytest`, `pytest-cov`, `hypothesis`, `black`, `ruff`, (선택) `mypy`.

## 비고
- 버전 고정은 5.x/2.x 계열로 핀(정확한 패치 버전은 코드 생성/Infra에서 `docker-compose.yml`·`requirements`로 확정).
- 임베딩 차원·인덱스 매핑(OpenSearch)은 NFR Design/Infra에서 구체화.
