# Unit Dependency — Rumor Distortion / Game Session (Phase 1)

## 의존 매트릭스
| 단위 | 의존(빌드 선행) | 사유 |
|---|---|---|
| S1 Foundation & Infra | (없음) | 세션 모델/포트/인프라 토대. 첫 단위. |
| S2 Rumor Engine | **S1** | 모델·SessionRepository·SessionService 사용; 기존 QueryEngine/WorldLoader/LLM 재사용. |
| S3 Web UI | **S2** | S2의 세션/소문/턴/쿼리 API 호출. |

빌드 순서: **S1 → S2 → S3** (단순 선형).

## 캐노니컬(기존 시스템) 의존
- S1·S2는 기존을 **읽기**로만: S2 GameMaster/SessionQueryEngine → `WorldLoader`/`QueryEngine`(Neo4j). 세션 쓰기는 캐노니컬 변경 없음(NFR-R2).
- S1 정리(미사용 Neo4j Rumor 제거)는 캐노니컬 모델 표면을 줄이되 동작 변화 없음(rumors는 현재 전부 빈 값).

## 신규 외부 인프라
- **PostgreSQL** + **SQLAlchemy**(S1, Infrastructure Design). 기존 Neo4j/OpenSearch 스택 유지.

## 통신
- 모든 단위 간/레이어 간 결합은 포트(SessionRepository, 기존 Graph/Search/LLM) + HTTP(API↔웹). 직접 DB 결합 없음.
