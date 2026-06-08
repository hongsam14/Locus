# Services — Locus

서비스 계층은 capability 컴포넌트를 오케스트레이션하고 API/CLI에 단일 진입점을 제공한다. 전체 흐름은 **동기 순차**(AD-Q3=A), 보강 Q&A 루프만 **LangGraph**(AD-CL1=A).

---

## S1. PipelineOrchestrator (핵심 오케스트레이터)
- **책임**: 한 세계(world)의 그래프를 빌드 — `ingestion → topology → ontology → consensus.precompute` 를 동기 순차로 실행하고 진행/오류를 집계.
- **메서드**: `build_world(world_id, inputs) -> BuildReport`
- **흐름**:
  1. IngestionService.ingest_all(inputs) → IngestionResult (병합)
  2. TopologyService.build(result, wiki) → RegionTopology (+ Wiki 가중)
  3. OntologyService.build(result, topo, wiki) → KnowledgeGraph (+ 스코핑 + 고증)
  4. ConsensusService.precompute(world_id) → 정적 직접 스코프 저장
  5. 저장(GraphRepository/SearchRepository), BuildReport 반환
- **오케스트레이션 패턴**: 단계별 산출물을 다음 단계 입력으로 전달; 각 단계 후 저장·로깅; 실패 시 부분 결과 + 오류 보고.

## S2. IngestionService
- **책임**: 입력 종류 라우팅(text/map-image/structured/concept-art) + Ingestor 호출 + 결과 병합·정규화 + 저신뢰 항목 수집.
- **메서드**: `ingest_all(inputs: WorldInputs) -> IngestionResult`
- **의존**: C1 Ingestion, C8 LLM.

## S3. TopologyService
- **책임**: 지역 식별·계층화·연결 그래프·Wiki 가중을 조율.
- **메서드**: `build(ingestion, wiki) -> RegionTopology`
- **의존**: C2 Topology, C5 Wiki, C9 Storage.

## S4. OntologyService
- **책임**: 지식 그래프 구성·스코핑·고증 생성·중복 병합 조율.
- **메서드**: `build(ingestion, topo, wiki) -> KnowledgeGraph`
- **의존**: C3 Ontology, C5 Wiki, C9 Storage.

## S5. ConsensusService
- **책임**: 정적 전처리(precompute)와 쿼리 시점 해석(resolve) 두 진입점 제공.
- **메서드**: `precompute(world_id)`, `resolve(region_id) -> ConsensusView`
- **의존**: C4 Consensus, C9 Storage.

## S6. CommonsenseWikiService
- **책임**: Wiki 빌드(실세계 자료, 동일 파이프라인 재사용)·조회·편집.
- **메서드**: `build_wiki(sources) `, `lookup(...)`, `upsert(prior)`
- **의존**: C5 Wiki; (build 시 S2/S3/S4 재사용 — wiki 모드).

## S7. AugmentationService
- **책임**: 보강 세션 운영(이슈 탐지→질문→답변 적용→재탐지) + 변경 이력/되돌리기. LangGraph 루프 위임.
- **메서드**: `start_session(world_id) -> AugmentationSession`, `submit_answer(session_id, answer) -> ChangeSet`, `revert(change_id)`
- **의존**: C6 Augmentation(AugmentationGraph), C4, C5, C9.

## S8. QueryService
- **책임**: 공개 쿼리(서빙). 지역 지식 집계 + 공유/고유 구분 + 메타데이터.
- **메서드**: `knowledge_for_region(region_id, ...) -> QueryResult`, `diff_regions(a, b) -> RegionDiff`
- **의존**: C7 Query, C5 Consensus(resolve), C9 Storage.

---

## Orchestration Patterns
- **동기 순차(빌드)**: S1 PipelineOrchestrator가 S2→S3→S4→S5 순서로 단일 프로세스에서 실행. (대용량 시 차기 비동기 잡 전환 여지 — Out of scope.)
- **LangGraph 루프(보강)**: S7가 `AugmentationGraph`(detect→generate→await-answer→apply→re-detect)를 수렴까지 반복.
- **쿼리(읽기)**: S8이 정적 스코프 + 쿼리 시점 PropagationResolver를 합성해 응답(하이브리드, FR-D2).

## Service → API/CLI 매핑
- authoring router → S1(빌드), S4/S3(편집), S7(보강), S6(Wiki).
- serving router → S8(쿼리).
- CLI → S1(build_world), S6(build_wiki), export.
