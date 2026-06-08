# U1 Foundation — Infrastructure Design

결정: ID-Q1=A(앱 Compose 서비스 + 호스트 실행 지원) · ID-Q2=A(OpenSearch 보안 비활성, 로컬) · ID-Q3=A(명명 볼륨). 환경: 로컬 + Docker Compose(Q11=A). 클라우드 범위 외.

## 논리 → 인프라 매핑

| 논리 컴포넌트 | 인프라 매핑 | 세부 |
|---|---|---|
| GraphRepository → Neo4jGraphRepository | **neo4j** 컨테이너 | 이미지 `neo4j:5` (Community), 포트 7687(bolt)/7474(http), 볼륨 `neo4j_data`, 인증 `NEO4J_AUTH` |
| SearchRepository → OpenSearchRepository | **opensearch** 컨테이너 | 이미지 `opensearchproject/opensearch:2`, 포트 9200, 단일 노드, **보안 플러그인 off**(`DISABLE_SECURITY_PLUGIN=true`), 볼륨 `opensearch_data` |
| API/코어(app) | **app** 컨테이너(+호스트 실행 지원) | Python 3.11, uvicorn, 포트 8000, `depends_on` neo4j·opensearch(healthcheck) |
| Settings/secrets | `.env` + 환경변수 | `OPENAI_API_KEY`, `NEO4J_URI/USER/PASSWORD`, `OPENSEARCH_URL` |
| LLM/VLM/Embedding | 외부 API(OpenAI) | 컨테이너 아님; 앱에서 호출 |

## 네트워킹/포트
- compose 네트워크 내 서비스명으로 접속(`neo4j`, `opensearch`). 호스트 실행 시 `localhost` 매핑 포트 사용.
- 노출 포트: 8000(app), 7474/7687(neo4j), 9200(opensearch).

## 환경변수 (env.example 제공)
```
OPENAI_API_KEY=
LLM_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
NEO4J_URI=bolt://neo4j:7687        # 호스트 실행 시 bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=locus-dev-password
OPENSEARCH_URL=http://opensearch:9200   # 호스트 실행 시 http://localhost:9200
OPENSEARCH_INDEX=locus_search
```

## N/A (범위 외)
- 메시징/큐, 로드밸런서/API 게이트웨이, 오토스케일, 멀티테넌시, 클라우드 매니지드 서비스.
