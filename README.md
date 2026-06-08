# Locus

게임 세계의 지형·문화 데이터를 입력받아, NPC가 참조하는 **공간 지식(Spatial Knowledge)** 토폴로지 + 온톨로지(지식 그래프)를 자동 구성하는 시스템.

> 본 리포지토리는 AWS AI-DLC 방법론으로 개발됩니다. 설계·계획 산출물은 `aidlc-docs/`, 애플리케이션 코드는 워크스페이스 루트(`locus/` 등)에 있습니다.

## 현재 상태
CONSTRUCTION 단계 — **U1 Foundation** 구현 중. 공유 토대(도메인 모델·그래프 스키마, 설정, LLM/VLM/임베딩 제공자 추상화, Neo4j/OpenSearch 저장소, 상식 Wiki lookup 인터페이스, Docker Compose).

## 아키텍처 (요약)
- 계층형 모듈러 모놀리스: Python 코어 `locus/` + (후속) FastAPI `api/` + React `web/`.
- 저장소: **Neo4j**(그래프) + **OpenSearch**(하이브리드 BM25+벡터 검색).
- LLM/VLM: LangChain 추상화 + 기본 OpenAI(교체 가능). 임베딩 기본 `text-embedding-3-small`.

## 설치
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp env.example .env   # 값 채우기 (OPENAI_API_KEY 등)
```

## 의존성 기동 (Docker)
```bash
./scripts/setup-volumes.sh           # ./data 바인드마운트 디렉토리 생성 (최초 1회)

docker compose up -d                 # 기본: 인프라만 (neo4j + opensearch)
docker compose --profile tools up -d # + OpenSearch Dashboards (http://localhost:5601)
docker compose --profile service up -d --build  # + app(:8000) + web(:3000)  ※ .env에 OPENAI_API_KEY 필요
```
- 데이터는 `./data/{neo4j,opensearch}`에 영속(바인드마운트). 프로파일: 기본=인프라, `service`=앱+UI, `tools`=대시보드.
- 호스트 개발: 인프라만 띄우고 `uvicorn api.main:app`(백엔드) + `cd web && npm run dev`(프론트).

## 스키마 초기화
```bash
locus init-schema   # Neo4j 제약/인덱스 + OpenSearch 인덱스(locus_search) 생성 (idempotent)
```

## 테스트
```bash
pytest                       # 단위 테스트 + 커버리지 (외부 호출은 mock)
ruff check locus/
black --check locus/
```

## 디렉토리
```
locus/        코어 패키지 (models, config, llm, storage, commonsense_wiki)
tests/        단위 테스트
aidlc-docs/   AI-DLC 설계/계획 문서 (코드 아님)
docker-compose.yml
```
