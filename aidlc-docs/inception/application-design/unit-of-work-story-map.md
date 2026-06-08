# Unit of Work ↔ Story Map — Locus

전 30개 스토리가 Unit에 배정되었는지 검증.

| Unit | 스토리 | 우선순위 | 사이클 |
|---|---|---|---|
| **U1 Foundation** ✅ | US-9.1 [x], US-9.2 [x], US-9.4 [x], US-9.3 [x](토대) | P0(9.1/9.2/9.4), P1(9.3) | MVP — **CODE DONE** |
| **U2 Ingestion** ✅ | US-1.1 [x], US-1.2 [x], US-1.3 [x], US-1.4 [x] | P0(1.1/1.2/1.3), P1(1.4) | MVP — **CODE DONE** |
| **U3 Topology** ✅ | US-2.1 [x], US-2.2 [x], US-2.3 [x] | P0 | MVP — **CODE DONE** |
| **U4 Ontology** ✅ | US-3.1 [x], US-3.2 [x], US-3.3 [x] | P0 | MVP — **CODE DONE** |
| **U6 Wiki build** ✅ | US-1.5 [x], US-5.1 [x], US-5.2 [x], US-5.3 [x] | P0(5.1), P1(1.5/5.2/5.3) | MVP — **CODE DONE** |
| **U5 Consensus** ✅ | US-4.1 [x], US-4.2 [x], US-4.3 [x] | P0 | MVP — **CODE DONE** |
| **U8 Query & Serving** ✅ | US-8.1 [x], US-8.2 [x], US-8.3 [x] | P0(8.1/8.2), P1(8.3) | MVP — **CODE DONE** |
| **U9 Orchestration & Authoring** ✅ | US-9.3 [x](앱 통합), 빌드/오케스트레이션, authoring 편집 | P0 | MVP — **CODE DONE** |
| **U7 Augmentation** ✅ | US-6.1 [x], US-6.2 [x], US-6.3 [x] | P0(6.1/6.2), P1(6.3) | cycle 2 — **CODE DONE** |
| **U10 Web UI** ✅ | US-7.1 [x], US-7.2 [x], US-7.3 [x] | P0(7.1/7.2), P1(7.3) | cycle 2 — **CODE DONE** |

## Coverage Check (30/30)
- EPIC-1: US-1.1→U2, 1.2→U2, 1.3→U2, 1.4→U2, 1.5→U6 ✓
- EPIC-2: US-2.1→U3, 2.2→U3, 2.3→U3 ✓
- EPIC-3: US-3.1→U4, 3.2→U4, 3.3→U4 ✓
- EPIC-4: US-4.1→U5, 4.2→U5, 4.3→U5 ✓
- EPIC-5: US-5.1→U6, 5.2→U6, 5.3→U6 ✓
- EPIC-6: US-6.1→U7, 6.2→U7, 6.3→U7 ✓
- EPIC-7: US-7.1→U10, 7.2→U10, 7.3→U10 ✓
- EPIC-8: US-8.1→U8, 8.2→U8, 8.3→U8 ✓
- EPIC-9: US-9.1→U1, 9.2→U1, 9.3→U1/U9, 9.4→U1 ✓

**모든 30 스토리 배정 완료. 누락 없음.**

## Notes
- US-7.x(검토·편집·UI 내 보강)는 프론트(U10) + 백엔드(authoring API=U9, 보강 로직=U7)로 구현 — UI 스토리는 U10에 귀속하되 U7/U9 의존.
- US-9.3(Docker Compose)는 U1에서 토대(Neo4j/OpenSearch), U9에서 앱 서비스 통합으로 마무리.
