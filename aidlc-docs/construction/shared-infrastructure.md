# Shared Infrastructure — Locus (전 Unit 공유)

U1 Foundation에서 정의된 인프라는 모든 Unit이 공유한다. 이후 Unit은 새 인프라를 추가하지 않고 이 스택 위에서 동작(U10 Web UI만 정적 프론트 서빙 추가).

## 공유 스택
| 서비스 | 이미지/런타임 | 포트 | 볼륨 | 용도 |
|---|---|---|---|---|
| neo4j | `neo4j:5` (Community) | 7687, 7474 | `neo4j_data` | 그래프(토폴로지+온톨로지+Wiki) |
| opensearch | `opensearchproject/opensearch:2` (단일노드, 보안 off) | 9200 | `opensearch_data` | 하이브리드 검색(벡터+BM25) |
| app | Python 3.11 + uvicorn | 8000 | — | 코어/서비스/API(authoring+serving) |
| (U10) web | Node/정적 빌드 | 5173/정적 | — | React 검토·편집 UI(차순) |
| 외부 | OpenAI API | — | — | LLM/VLM/Embedding |

## 공유 규약
- 단일 OpenSearch 인덱스 `locus_search` + `world_id` 필터(ND1-Q2=A).
- Neo4j 단일 그래프 + `world_id` 파티션; Wiki는 `__realworld__`.
- 모든 서비스는 `.env`/환경변수로 구성(ID/NFR1-Q6=A).
- SchemaInitializer가 제약/인덱스 부트스트랩(앱 시작 또는 `locus init-schema`).

## Compose 구성 (개선, Enola 패턴 참고)
- **프로파일**: 기본=인프라(neo4j/opensearch); `service`=app(uvicorn)+web(nginx); `tools`=OpenSearch Dashboards.
- **볼륨**: 바인드마운트 `./data/{neo4j/data, neo4j/logs, opensearch}` (호스트 영속·검사). `./scripts/setup-volumes.sh`로 생성.
- **버전 핀**: `neo4j:5.15-community`, `opensearchproject/opensearch:2.13.0`.
- **app**: `init-schema` 후 `uvicorn api.main:app` 실행, `/health` 헬스체크, `OPENAI_API_KEY` 필요.
- **web**: `web/Dockerfile`(node build → nginx) + `/api` 프록시 → app:8000.

## Unit별 인프라 영향
- U2~U9: 새 인프라 없음(공유 스택 사용).
- U6(Wiki): `__realworld__` 파티션 사용(별도 인프라 없음).
- U10(Web UI): 정적 프론트 빌드 서빙(개발 시 Vite dev server, 배포 시 정적 파일).

## N/A (전 Unit 공통, 범위 외)
메시징/큐, 로드밸런서, API 게이트웨이, 오토스케일, 멀티테넌시, 클라우드 매니지드 서비스, 고가용성.
