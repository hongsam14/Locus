# Unit of Work Dependencies — Locus

## Dependency Matrix (행 Unit이 열 Unit에 의존)

| ↓ \ → | U1 | U2 | U3 | U4 | U5 | U6 | U7 | U8 | U9 | U10 |
|---|---|---|---|---|---|---|---|---|---|---|
| **U1 Foundation** | – | | | | | | | | | |
| **U2 Ingestion** | ✓ | – | | | | | | | | |
| **U3 Topology** | ✓ | ✓ | – | | | (lookup via U1) | | | | |
| **U4 Ontology** | ✓ | ✓ | ✓ | – | | (lookup via U1) | | | | |
| **U5 Consensus** | ✓ | | ✓ | ✓ | – | | | | | |
| **U6 Wiki build** | ✓ | ✓ | ✓ | ✓ | | – | | | | |
| **U7 Augmentation** | ✓ | | | ✓ | ✓ | ✓ | – | | | |
| **U8 Query & Serving** | ✓ | | | ✓ | ✓ | | | – | | |
| **U9 Orchestration & Authoring** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | (opt) | ✓ | – | |
| **U10 Web UI** | | | | | | | (api) | ✓(api) | ✓(api) | – |

- **U1**은 무의존(leaf 토대). 모든 Unit이 U1에 의존.
- U3/U4는 **Wiki 빌드(U6)에 직접 의존하지 않음** — U1의 lookup 인터페이스(+LLM 폴백)에만 의존 → **순환 없음** (CL1=A).
- U6는 U2/U3/U4 재사용 → 이들 뒤 빌드.
- U10(UI)은 백엔드 API(U8/U9)에만 의존(REST), 코어 모듈 직접 의존 없음.

## Build Order (CL1=A)

```mermaid
flowchart LR
    U1["U1 Foundation"] --> U2["U2 Ingestion"]
    U2 --> U3["U3 Topology"]
    U3 --> U4["U4 Ontology"]
    U4 --> U6["U6 Wiki build"]
    U6 --> U5["U5 Consensus"]
    U5 --> U8["U8 Query & Serving"]
    U8 --> U9["U9 Orchestration & Authoring"]
    U9 -. 차순 .-> U7["U7 Augmentation"]
    U7 -. 차순 .-> U10["U10 Web UI"]

    style U1 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U2 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U3 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U4 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U6 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U5 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U8 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U9 fill:#4CAF50,stroke:#1B5E20,color:#fff
    style U7 fill:#FFA726,stroke:#E65100,stroke-dasharray: 5 5,color:#000
    style U10 fill:#FFA726,stroke:#E65100,stroke-dasharray: 5 5,color:#000
    linkStyle default stroke:#333,stroke-width:2px
```

- 🟢 녹색 = MVP 1차 사이클(U1~U6,U8,U9) · 🟠 주황(점선) = 차순(U7, U10).
- **런타임 주의**: 운영 시 사용자가 실세계 자료로 **Wiki를 먼저 빌드**(U6 실행) → 이후 가상 세계 build_world(U3/U4가 Wiki 활용). 코드 빌드 순서와 런타임 실행 순서는 별개.

## Parallelization
- 모놀리스·단일 개발 흐름 가정 → 순차 권장. 단, U2 완료 후 U3/U4는 일부 병렬 가능(공유 U1 안정 시).

## Integration / Rollback
- 통합 지점: U8(쿼리 관통, SC-2 검증), U9(end-to-end build_world, SC-1/SC-4 검증).
- Rollback: greenfield — Unit별 독립 추가, 실패 시 해당 Unit 격리.
