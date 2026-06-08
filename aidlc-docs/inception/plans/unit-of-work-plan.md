# Unit of Work Plan — Locus (Units Generation · Part 1 Planning)

시스템을 개발 가능한 **작업 단위(Unit of Work)**로 분해합니다. 모놀리스이므로 Unit = 스토리의 논리적 묶음(병렬/순차 개발 단위, 각 Unit이 Construction에서 개별 설계·코드 생성을 거침). 아래 질문에 답해 주시면 `unit-of-work.md` / `unit-of-work-dependency.md` / `unit-of-work-story-map.md`를 생성합니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## 제안 Unit 분해 (확인용 — UOW-Q1에서 동의/수정)

| Unit | 이름 | 포함 컴포넌트 | 주요 스토리 |
|---|---|---|---|
| **U1** | Foundation | Models, Config, Storage(Neo4j+OpenSearch 어댑터), LLM Provider, **CommonsenseWiki 인터페이스(+seed lookup)** | US-9.1, 9.2, 9.4 |
| **U2** | Ingestion | Ingestion(text/map-image/structured/concept-art) | US-1.1~1.4 |
| **U3** | Topology | TopologyBuilder(+Wiki 가중 hook) | US-2.1~2.3 |
| **U4** | Ontology | OntologyBuilder(+스코핑+고증) | US-3.1~3.3 |
| **U5** | Consensus | ConsensusEngine(precompute) + PropagationResolver(왜곡/소문) | US-4.1~4.3 |
| **U6** | Commonsense Wiki (build) | Wiki 빌드(실세계 자료, 파이프라인 재사용) + 편집 + 근거 | US-1.5, 5.1~5.3 |
| **U7** | Augmentation | AugmentationEngine + AugmentationGraph(LangGraph 루프) | US-6.1~6.3 |
| **U8** | Query & Serving API | QueryEngine + serving router(공개 쿼리) | US-8.1~8.3 |
| **U9** | Orchestration & Authoring | PipelineOrchestrator + authoring router + CLI | US-1.x 실행, 7.x 백엔드, 빌드 |
| **U10** | Web UI | React 시각화·편집·보강 UI | US-7.1~7.3 |

> 순환 회피: **CommonsenseWiki 인터페이스(+seed lookup)**를 U1에 두어 U3/U4가 인터페이스에만 의존. 실제 Wiki **빌드**(파이프라인 재사용)는 U6에서 구현.

---

## Planning Questions

## Question UOW-Q1 — Unit 분해 동의 여부 / 입도
위 10-Unit 분해에 동의하시나요?

A) 동의 — 10개 Unit 그대로 (Recommended — capability·스토리 경계와 일치)
B) 더 굵게 — 일부 통합 (예: U3+U4 그래프 빌드, U8+U9 백엔드, → 7개 내외)
C) 더 세분 — Ingestion을 모달리티별 등으로 더 분리
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question UOW-Q2 — Foundation(U1) 우선 빌드
공유 토대(Models/Storage/LLM/Wiki 인터페이스)를 첫 Unit으로 먼저 완성하는 데 동의하시나요?

A) 동의 — U1 Foundation을 먼저 (Recommended — 이후 Unit이 안정적 토대 위에서 진행)
B) 아니오 — capability와 함께 점진적으로 토대 구축
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question UOW-Q3 — 코드 디렉토리 구조 (Greenfield)
리포지토리 구조는?

A) 단일 Python 패키지 `locus/`(서브모듈) + `api/` + `web/` + `tests/` + `docker-compose.yml` (Recommended — 참고 프로젝트 Enola와 동일)
B) `src/` 레이아웃 (`src/locus/...`)
C) 모노레포 분리 (`backend/`, `frontend/`)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question UOW-Q4 — 개발/빌드 순서
Unit 진행 순서는?

A) 의존도 순 — U1 → U2 → U6(Wiki) → U3 → U4 → U5 → U8 → U7 → U9 → U10 (Recommended — Wiki 빌드를 토폴로지/온톨로지 정교화 전에 확보)
B) 가치 순(빠른 end-to-end) — U1 → U2 → U3 → U4 → U5 → U8(쿼리까지 관통) 후 U6/U7/U9/U10
C) 직접 지정 (X에 기재)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question UOW-Q5 — Wiki(U6) 시드 데이터 처리
U1의 Wiki "seed lookup"을 초기에 어떻게 채울까요?

A) 최소 규칙 시드(LLM 추론 폴백) — 소수 지형→영향 규칙을 코드/데이터로 시드, 나머지는 LLM 추론 (Recommended — U3/U4가 일찍 동작)
B) 빈 인터페이스 — U6 완성 전까지 Wiki 영향은 비활성(기본 가중치)
C) 외부 데이터셋 임포트 우선
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 내가 외부 자료, 지도를 넘기면, ingest하여 사용. 이것을 참고로 LLM 추론 풀백

## Question UOW-Q6 — MVP 우선 범위(첫 사이클 Unit)
첫 Construction 사이클에서 어디까지를 MVP 코어로 잡을까요? (이후 사이클로 나머지)

A) U1~U6, U8, U9 (수집~그래프~컨센서스~Wiki~쿼리~오케스트레이션) 우선, **U7(보강)·U10(UI) 차순** (Recommended — end-to-end 자동 생성+쿼리 SC-1/2/4 먼저 충족)
B) 전체 U1~U10을 한 사이클에 (UI·보강 포함, 범위 큼)
C) 핵심 최소(U1~U5,U8)만 우선, Wiki/보강/UI 모두 차순
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Unit Artifacts (답변 후 생성)
- [ ] `unit-of-work.md` — Unit 정의·책임 + 코드 조직 전략(greenfield)
- [ ] `unit-of-work-dependency.md` — Unit 의존 매트릭스·빌드 순서
- [ ] `unit-of-work-story-map.md` — 스토리 ↔ Unit 매핑(전 스토리 배정 확인)

## Execution Checklist (생성 단계)
- [x] 1. UOW-Q1~6 (+UOW-CL1) 반영해 Unit 경계·순서 확정
- [x] 2. unit-of-work.md 작성(+코드 구조)
- [x] 3. unit-of-work-dependency.md 작성
- [x] 4. unit-of-work-story-map.md 작성(전 스토리 배정 검증 — 30/30)

---

## Follow-up (의존성 충돌 해소 — 답변 필요)

**Q5=X**(Wiki = 외부 실세계 자료 ingest로 구성 + LLM 폴백)와 **Q4=A**(U6를 U3/U4 앞) 사이에 충돌이 있습니다. Wiki 빌드(U6)는 동일 파이프라인을 재사용하므로 **U2·U3·U4에 의존** → U6가 U3/U4보다 먼저 완성될 수 없습니다. 해소 방식을 정해 주세요.

핵심 정리:
- **개발(코드) 순서**: U6(Wiki 빌드)는 U2/U3/U4 재사용 → 이들 **뒤**에 와야 함.
- **런타임(실행) 순서**: 그래도 사용자가 먼저 실세계 자료로 Wiki를 빌드해 두면, 가상 세계 빌드 시 Wiki 내용이 이미 존재 → 가중·고증에 활용됨.
- **U1의 Wiki lookup 인터페이스**는 Wiki가 비어있을 때 **LLM 추론(가용 컨텍스트 기반)으로 폴백**, 안전하게 동작.

## Question UOW-CL1 — Wiki(U6) 순서 해소
A) **개발 순서 조정 + 런타임 우선** (Recommended) — 코드 빌드 순서는 U1→U2→**U3→U4→U6**→U5→U8→U7→U9→U10 으로 조정. 운영상으론 사용자가 실세계 자료로 Wiki를 먼저 빌드해 두고 가상 세계를 빌드(=Wiki 내용 우선 확보). U1 lookup은 비었을 때 LLM 폴백.
B) **U3/U4 1차는 Wiki 없이(degraded)** — U3/U4를 Wiki 비활성(기본 가중치/고증 생략)으로 먼저 만들고, U6 후 2차 패스에서 Wiki 반영 보강.
C) 직접 지정 (X에 기재)
X) Other (please describe after [Answer]: tag below)

[Answer]: 
