# Component Dependencies — Locus

## Dependency Matrix (행이 열에 의존)

| ↓의존 \ 대상→ | Ingestion | Topology | Ontology | Consensus | Wiki | Augment | Query | LLM | Storage | Models |
|---|---|---|---|---|---|---|---|---|---|---|
| **Ingestion** | – | | | | | | | ✓ | | ✓ |
| **Topology** | (입력) | – | | | ✓ | | | | ✓ | ✓ |
| **Ontology** | (입력) | (입력) | – | | ✓ | | | | ✓ | ✓ |
| **Consensus** | | (topo) | (kg) | – | | | | | ✓ | ✓ |
| **Wiki** | ✓(build) | ✓(build) | ✓(build) | | – | | | ✓ | ✓ | ✓ |
| **Augmentation** | | | (kg) | ✓ | ✓ | – | | ✓ | ✓ | ✓ |
| **Query** | | | | ✓ | | | – | | ✓ | ✓ |
| **LLM** | | | | | | | | – | | ✓ |
| **Storage** | | | | | | | | (임베딩) | – | ✓ |

- `Models`는 모든 모듈이 의존(공유 계약), 자신은 무의존 → **순환 없음**.
- `Storage`/`LLM`은 leaf(코어 capability가 의존, 역방향 없음).
- `Wiki`는 build 시 Ingestion/Topology/Ontology를 **재사용**하지만, 그 모듈들은 평소 Wiki를 **읽기만**(가중·고증) → build 경로는 Service 계층(S6)이 조율해 모듈 간 직접 순환을 피함.

## Communication Patterns
- **In-process 함수 호출**: 모든 코어 모듈 간 통신은 동일 프로세스 메서드 호출(모놀리스).
- **Repository 경유 영속화**: 모듈은 `GraphRepository`/`SearchRepository` 인터페이스에만 의존(어댑터가 Neo4j/OpenSearch 구현). (AD-Q5=A)
- **Provider 경유 LLM/VLM**: 모듈은 `LLMProvider`/`VLMProvider`에만 의존(LangChain+OpenAI 구현). (AD-Q4=C)
- **API 경계**: web/CLI ↔ 백엔드는 REST(JSON). authoring/serving 라우터 분리. (AD-Q6=A)

## Data Flow — World Build (동기 순차)

```mermaid
flowchart LR
    IN["WorldInputs<br/>(memo, map img, geojson, art)"] --> ING["IngestionService"]
    ING --> RES["IngestionResult"]
    RES --> TOPO["TopologyService"]
    WIKI["CommonsenseWiki"] -.prior.-> TOPO
    TOPO --> RT["RegionTopology"]
    RES --> ONTO["OntologyService"]
    RT --> ONTO
    WIKI -.고증.-> ONTO
    ONTO --> KG["KnowledgeGraph"]
    RT --> CON["ConsensusService.precompute"]
    KG --> CON
    CON --> STORE["GraphRepository + SearchRepository"]
    STORE --> REP["BuildReport"]

    style IN fill:#CE93D8,stroke:#6A1B9A,color:#000
    style REP fill:#CE93D8,stroke:#6A1B9A,color:#000
    style WIKI fill:#FFF59D,stroke:#F57F17,color:#000
    linkStyle default stroke:#333,stroke-width:2px
```

## Data Flow — Augmentation (LangGraph 루프)

```mermaid
flowchart TD
    START(["start_session"]) --> DET["detect_issues<br/>(빈틈/모순 + Wiki 충돌 + 저신뢰)"]
    DET --> GEN["generate_questions"]
    GEN --> ASK["기획자 답변 대기 (UI)"]
    ASK --> APP["apply_answer → ChangeSet"]
    APP --> RED{"미해결 남음?"}
    RED -- 예 --> DET
    RED -- 아니오 --> DONE(["수렴/종료"])

    style START fill:#CE93D8,stroke:#6A1B9A,color:#000
    style DONE fill:#CE93D8,stroke:#6A1B9A,color:#000
    linkStyle default stroke:#333,stroke-width:2px
```

## Data Flow — Query (하이브리드)

```mermaid
flowchart LR
    Q(["GET /api/query/regions/{id}/knowledge"]) --> QS["QueryService"]
    QS --> DIRECT["정적 직접 스코프<br/>(precomputed)"]
    QS --> PROP["PropagationResolver<br/>(쿼리 시점 순회)"]
    DIRECT --> AGG["집계 + 공유/고유 구분 + 메타"]
    PROP --> AGG
    AGG --> RESP(["QueryResult (JSON)"])

    style Q fill:#CE93D8,stroke:#6A1B9A,color:#000
    style RESP fill:#CE93D8,stroke:#6A1B9A,color:#000
    linkStyle default stroke:#333,stroke-width:2px
```
