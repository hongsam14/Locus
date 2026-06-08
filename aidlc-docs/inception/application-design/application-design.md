# Application Design — Locus (Consolidated)

Inception · Application Design 통합 문서. 상세는 `components.md` / `component-methods.md` / `services.md` / `component-dependency.md` 참조.

## Design Decisions (확정)
| 결정 | 값 |
|---|---|
| 아키텍처 스타일 (AD-Q1) | 계층형 모듈러 모놀리스 (Python 코어 + FastAPI + React) |
| 모듈 경계 (AD-Q2) | capability별 모듈 |
| 파이프라인 오케스트레이션 (AD-Q3) | 동기 순차 오케스트레이터 |
| LLM/VLM (AD-Q4 + AD-CL1) | LangChain 추상화 + OpenAI 기본; **LangGraph는 보강 Q&A 루프 등 국소만** |
| 저장소 접근 (AD-Q5) | Repository/Adapter (Neo4j, OpenSearch) |
| API 표면 (AD-Q6) | authoring / serving 분리 |

## High-level Architecture

```text
┌───────────────────────────────────────────────────────────────┐
│ Application Layer                                               │
│   web/ (React: 시각화·편집·보강 UI)   CLI (locus)              │
│   api/  authoring router        |     serving router            │
└───────────────┬───────────────────────────┬───────────────────┘
                │                             │
┌───────────────▼─────────────────────────────────────────────┐
│ Service Layer (locus/services)                               │
│   PipelineOrchestrator                                       │
│   Ingestion · Topology · Ontology · Consensus ·             │
│   CommonsenseWiki · Augmentation · Query  Services          │
└───────────────┬─────────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────────┐
│ Capability Modules (locus/*)                                │
│   ingestion topology ontology consensus                     │
│   commonsense_wiki augmentation query                       │
└───────────────┬───────────────┬─────────────────────────────┘
   cross-cutting │               │
        ┌────────▼──────┐  ┌─────▼───────────────┐
        │ llm (LangChain│  │ storage (Repo/Adapter)│
        │  +OpenAI,VLM) │  │  Neo4j │ OpenSearch   │
        └───────────────┘  └──────────────────────┘
        models (Pydantic, 전역 공유)   config
```

## Component Inventory (14)
- **Capability**: C1 Ingestion · C2 Topology · C3 Ontology · C4 Consensus · C5 Commonsense Wiki · C6 Augmentation · C7 Query
- **Cross-cutting**: C8 LLM Provider · C9 Storage · C10 Models · C11 Config
- **Application**: C12 API(authoring/serving) · C13 CLI · C14 Web UI

## Key Flows
1. **World Build** (동기 순차): Ingestion → Topology(+Wiki 가중) → Ontology(+스코핑+고증) → Consensus.precompute → 저장.
2. **Augmentation** (LangGraph): detect(빈틈/모순 + Wiki 충돌 + 저신뢰) → 질문 → 답변 → 적용 → 재탐지 → 수렴.
3. **Query** (하이브리드): 정적 직접 스코프 + 쿼리 시점 전파/소문 → 공유/고유 구분 JSON.
4. **Wiki Build** (디지털 트윈): 실세계 자료를 동일 빌드 파이프라인 "wiki 모드"로 → prior KB.

## Requirements Coverage
- FR-A→C1 · FR-B→C2 · FR-C→C3 · FR-D→C4 · FR-E→C5 · FR-F→C6 · FR-G→C14 · FR-H→C7/C12 · FR-I→C9
- NFR-A→아키텍처/C9/Docker · NFR-B→C8 · NFR-E→C4(하이브리드) · NFR-C(PBT Partial)→직렬화/순수함수(models, consensus 계산)

## Consistency / Validation
- 순환 의존 없음(Models leaf, Storage/LLM leaf, Wiki build는 Service가 조율).
- 모든 외부 I/O(그래프·검색·LLM)는 인터페이스 뒤 → 테스트(mock) 및 제공자/저장소 교체 용이.
- authoring/serving 분리로 소비자(NPC 런타임) 계약 안정.

## Deferred to next stages
- 정확한 그래프 스키마(노드/관계/속성), 임베딩 모델, weight/전파 공식 → **Functional Design**.
- 성능·확장·제공자 세부 → **NFR Requirements/Design**.
- Docker Compose·서비스 토폴로지 → **Infrastructure Design**.
- Unit 분해 → **Units Generation**.
