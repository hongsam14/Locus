# Components — Locus Application Design

**아키텍처**: 계층형 모듈러 모놀리스 (AD-Q1=A). Python 코어 패키지 `locus/` + FastAPI 백엔드 `api/` + React 프론트 `web/`.
**모듈 경계**: capability별 (AD-Q2=A). **저장소**: Repository/Adapter (AD-Q5=A). **LLM/VLM**: LangChain 추상화 + OpenAI 기본 (AD-Q4=C). **오케스트레이션**: 동기 순차 + LangGraph 국소(AD-Q3=A/AD-CL1=A). **API**: authoring/serving 분리 (AD-Q6=A).

## Layered View

```text
Application Layer   → api/ (FastAPI: authoring + serving routers), CLI (locus.__main__), web/ (React)
Service Layer       → locus/services/ (오케스트레이션 서비스 + PipelineOrchestrator)
Capability Modules  → locus/{ingestion, topology, ontology, consensus, commonsense_wiki, augmentation, query}
Cross-cutting       → locus/llm (provider 추상화), locus/models (Pydantic), locus/config
Storage Adapters    → locus/storage (GraphRepository→Neo4j, SearchRepository→OpenSearch)
```

---

## Capability Components

### C1. Ingestion (`locus/ingestion`)
- **목적**: 멀티모달 입력을 정규화된 추출 결과로 변환.
- **책임**: 텍스트 메모→엔티티/관계 추출(LLM); 지도 이미지→지역/지형 추출(VLM); 구조화 맵(GeoJSON/노드-엣지)→직접 파싱; 컨셉아트→보조 단서; 각 항목에 confidence 부여; 저신뢰 항목 플래그.
- **인터페이스**: `Ingestor`(공통), 하위 `TextIngestor`, `MapImageIngestor`, `StructuredMapIngestor`, `ConceptArtIngestor`. 출력 `IngestionResult`.
- **의존**: `llm`(LLM/VLM), `models`.
- **추적성**: FR-A1~A6, US-1.1~1.5.

### C2. Topology (`locus/topology`)
- **목적**: 지역 노드(계층) + 지형 제약 반영 연결 그래프 생성.
- **책임**: 지역 식별; 계층(대륙>지방>마을>구역) 구성; 인접/접근/단절 엣지 생성; 상식 Wiki 참조 연결 강도(weight) 산정.
- **인터페이스**: `TopologyBuilder`. 출력 `RegionTopology`(노드+엣지+weight+근거).
- **의존**: `commonsense_wiki`(가중치 prior), `models`, `storage`.
- **추적성**: FR-B1~B3, US-2.1~2.3.

### C3. Ontology (`locus/ontology`)
- **목적**: 지식 그래프(엔티티/관계) 구성 + 지역 스코핑 + 고증 생성.
- **책임**: 엔티티/관계 그래프화; 중복 병합; 지식의 지역 귀속 + 계층 상속; 상식 Wiki 참조 고증 지식 추론·추가(출처 표시).
- **인터페이스**: `OntologyBuilder`. 출력 `KnowledgeGraph`.
- **의존**: `commonsense_wiki`, `storage`(의미 매칭은 SearchRepository), `models`.
- **추적성**: FR-C1~C3, US-3.1~3.3.

### C4. Consensus (`locus/consensus`)
- **목적**: 컨센서스·왜곡 모델링.
- **책임**: 연결 강도 기반 공유/전파/미지 분류; 직접 보유 지식 스코프 **정적 전처리**; 전파·소문은 **쿼리 시점 계산** 지원; 왜곡을 confidence 속성 + variant 노드(`distorted_from`)로 표현.
- **인터페이스**: `ConsensusEngine`(precompute), `PropagationResolver`(query-time).
- **의존**: `storage`, `models`.
- **추적성**: FR-D1~D3, US-4.1~4.3.

### C5. Commonsense Wiki (`locus/commonsense_wiki`)
- **목적**: 실세계 prior KB(디지털 트윈) — 토폴로지 가중·고증의 근거.
- **책임**: 동일 수집 파이프라인을 "wiki 모드"로 실행해 prior 그래프 구성; 영속 저장·조회·편집; prior 조회 API(지형→기후/물류 규칙, 유사 사례 검색); 근거 기록.
- **인터페이스**: `CommonsenseWiki`(lookup/build/edit).
- **의존**: `storage`, `llm`, `models`, (build 시 `ingestion`/`topology`/`ontology` 재사용).
- **추적성**: FR-E1~E3, FR-A6, US-5.1~5.3.

### C6. Augmentation (`locus/augmentation`)
- **목적**: 인터랙티브 지식 보강 Q&A.
- **책임**: 보강 질문 생성(그래프 빈틈·모순 A / Wiki 충돌 B / 저신뢰 입력 C); 답변 적용→그래프 갱신; 루프(수렴까지); 변경 이력·되돌리기. **LangGraph로 구현(국소)**.
- **인터페이스**: `AugmentationEngine`(detect/generate/apply), `AugmentationGraph`(LangGraph 루프).
- **의존**: `commonsense_wiki`, `consensus`, `storage`, `llm`, `models`.
- **추적성**: FR-F1~F3, US-6.1~6.3.

### C7. Query (`locus/query`)
- **목적**: "지역 X NPC가 아는 지식" 조회.
- **책임**: 직접+상속+전파 지식 집계; 공유 vs 지역 고유 구분; confidence·variant·출처 메타데이터 포함; 결정적 JSON 계약.
- **인터페이스**: `QueryEngine`.
- **의존**: `consensus`(PropagationResolver), `storage`, `models`.
- **추적성**: FR-H1~H3, US-8.1~8.3.

---

## Cross-cutting Components

### C8. LLM Provider (`locus/llm`)
- **목적**: LLM/VLM 제공자 추상화(NFR-B).
- **책임**: `LLMProvider`/`VLMProvider` 추상 인터페이스(LangChain 백엔드); OpenAI 기본 구현; 설정 기반 교체; 프롬프트 체인 헬퍼.
- **인터페이스**: `LLMProvider`, `VLMProvider`, `ProviderFactory`.
- **의존**: LangChain, `config`.
- **추적성**: NFR-B1~B3, US-9.4.

### C9. Storage (`locus/storage`)
- **목적**: 저장소 추상화(AD-Q5=A).
- **책임**: `GraphRepository`(노드/엣지 CRUD·순회) → Neo4j 어댑터; `SearchRepository`(벡터+BM25 색인·검색) → OpenSearch 어댑터; 임베딩 생성 연계.
- **인터페이스**: `GraphRepository`, `SearchRepository`, 어댑터 구현.
- **의존**: Neo4j 드라이버, OpenSearch 클라이언트, `llm`(임베딩) 또는 별도 임베딩 유틸, `models`.
- **추적성**: FR-I1~I2, US-9.1~9.2.

### C10. Models (`locus/models`)
- **목적**: 공유 도메인 모델(Pydantic v2).
- **핵심 타입**: `Region`(계층), `ConnectionEdge`(weight·근거), `Entity`, `Relation`, `KnowledgeItem`(scope·confidence·source), `KnowledgeVariant`(distorted_from), `WikiPrior`, `AugmentationQuestion`, `AugmentationAnswer`, `IngestionResult`, `RegionTopology`, `KnowledgeGraph`, `QueryResult`.
- **추적성**: 전 FR (데이터 계약).

### C11. Config (`locus/config`)
- **목적**: 설정 중앙화(제공자 키, 저장소 접속, 임베딩 모델 등).

---

## Application-layer Components

### C12. API (`api/`)
- **authoring router** (`/api/authoring/*`): 수집 실행, 그래프 조회/편집, 보강 Q&A, Wiki 관리. (P1/P2)
- **serving router** (`/api/query/*`): 공개 쿼리 API. (P3) (AD-Q6=A)
- **의존**: `services`.

### C13. CLI (`locus/__main__.py`)
- **목적**: 파이프라인 실행, Wiki 빌드, export. (Q8 CLI)

### C14. Web UI (`web/`, React)
- **목적**: 토폴로지·지식 그래프 시각화 + 편집 + 보강 Q&A UI. (FR-G, US-7.x)
- **의존**: authoring router (REST).
