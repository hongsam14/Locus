# Unit of Work — Locus

**Deployment model**: 단일 배포(모놀리스) — Python 코어 + FastAPI + React, Docker Compose로 함께 기동.
**Unit 정의**: Unit = 스토리의 논리적 묶음(개발/설계/코드생성 단위). 각 Unit은 Construction에서 per-unit 설계+코드 생성 사이클을 거침.
**결정**: UOW-Q1=A(10 Unit) · Q2=A(Foundation 우선) · Q3=A(`locus/`+`api/`+`web/`) · Q4=A+CL1=A(의존 순서 조정) · Q5=X(Wiki=실세계 ingest+LLM 폴백) · Q6=A(MVP=U1~U6,U8,U9).

---

## Code Organization Strategy (Greenfield)

```text
Locus/
├── locus/                      # 코어 Python 패키지
│   ├── models/                 # U1  Pydantic 도메인 모델
│   ├── config/                 # U1  설정
│   ├── llm/                    # U1  LLM/VLM provider 추상화(LangChain+OpenAI)
│   ├── storage/                # U1  GraphRepository(Neo4j)·SearchRepository(OpenSearch) 어댑터
│   ├── commonsense_wiki/       # U1(인터페이스+폴백) / U6(빌드)
│   ├── ingestion/              # U2  멀티모달 수집
│   ├── topology/               # U3  토폴로지 빌더
│   ├── ontology/               # U4  온톨로지 빌더
│   ├── consensus/              # U5  컨센서스·왜곡
│   ├── query/                  # U8  쿼리 엔진
│   ├── augmentation/           # U7  보강 Q&A(LangGraph)
│   ├── services/               # U9  서비스 + PipelineOrchestrator
│   └── __main__.py             # U9  CLI
├── api/                        # U8(serving) / U9(authoring) FastAPI 앱
│   ├── main.py
│   └── routers/ {authoring.py, query.py}
├── web/                        # U10 React 검토·편집·보강 UI
├── tests/                      # 각 Unit 테스트(PBT Partial 포함)
├── examples/                   # 데모 샘플 세계관(메모+지도) — SC 검증
├── docker-compose.yml          # U1~ 앱+Neo4j+OpenSearch
├── pyproject.toml
└── CLAUDE.md
```

---

## Unit Definitions

### U1 — Foundation  *(MVP, build #1)*
- **책임**: 공유 도메인 모델, 설정, LLM/VLM provider 추상화(+OpenAI), Storage 어댑터(Neo4j GraphRepository + OpenSearch SearchRepository + 임베딩), **CommonsenseWiki lookup 인터페이스 + LLM 폴백**(빈 wiki 시), Docker Compose 토대(Neo4j/OpenSearch 컨테이너).
- **컴포넌트**: C10 Models, C11 Config, C8 LLM, C9 Storage, C5(인터페이스부).
- **스토리**: US-9.1, US-9.2, US-9.4, US-9.3(토대).
- **PBT**: 모델 직렬화 round-trip, 순수 유틸.

### U2 — Ingestion  *(MVP, build #2)*
- **책임**: text/map-image(VLM)/structured(GeoJSON)/concept-art 수집, confidence 부여, 저신뢰 플래그, 결과 병합.
- **컴포넌트**: C1.
- **스토리**: US-1.1, US-1.2, US-1.3, US-1.4.

### U3 — Topology  *(MVP, build #3)*
- **책임**: 지역 식별·계층화, 지형 제약 연결 그래프, Wiki lookup 통한 연결 강도 가중(빈 wiki 시 폴백).
- **컴포넌트**: C2.
- **스토리**: US-2.1, US-2.2, US-2.3.

### U4 — Ontology  *(MVP, build #4)*
- **책임**: 엔티티/관계 그래프, 지역 스코핑(계층 상속), Wiki 기반 고증 생성(출처 표시), 중복 병합.
- **컴포넌트**: C3.
- **스토리**: US-3.1, US-3.2, US-3.3.

### U6 — Commonsense Wiki (build)  *(MVP, build #5)*
- **책임**: 실세계 자료(사용자 제공 지도·텍스트) ingest → 동일 파이프라인(U2/U3/U4) 재사용해 prior KB(디지털 트윈) 빌드; 영속 저장·조회·편집; 근거 기록. U1의 lookup을 실제 데이터로 채움.
- **컴포넌트**: C5(빌드부).
- **스토리**: US-1.5, US-5.1, US-5.2, US-5.3.
- **의존 주의**: U2/U3/U4 재사용 → 이들 뒤에 빌드(CL1=A).

### U5 — Consensus  *(MVP, build #6)*
- **책임**: 직접 보유 지식 정적 precompute, 쿼리 시점 전파/소문 resolve, 왜곡(confidence + variant `distorted_from`).
- **컴포넌트**: C4.
- **스토리**: US-4.1, US-4.2, US-4.3.
- **PBT**: 전파/감쇠 계산 순수 함수.

### U8 — Query & Serving API  *(MVP, build #7)*
- **책임**: 지역 지식 집계(직접+상속+전파), 공유 vs 고유 구분, 메타데이터, serving router(공개 쿼리, 안정 계약).
- **컴포넌트**: C7, C12(serving).
- **스토리**: US-8.1, US-8.2, US-8.3.

### U9 — Orchestration & Authoring  *(MVP, build #8)*
- **책임**: PipelineOrchestrator(동기 순차 build_world), authoring router(수집 실행·편집·Wiki 관리·보강 연계), CLI(build_world/build_wiki/export), 데모 샘플.
- **컴포넌트**: C12(authoring), C13 CLI, Services(C-services).
- **스토리**: US-1.x/US-7.x 백엔드 실행 경로, 빌드 오케스트레이션, US-9.3(앱 서비스 통합).

### U7 — Augmentation  *(차순, build #9)*
- **책임**: 이슈 탐지(빈틈/모순 + Wiki 충돌 + 저신뢰), 질문 생성, 답변 적용, LangGraph 루프, 변경 이력·되돌리기.
- **컴포넌트**: C6.
- **스토리**: US-6.1, US-6.2, US-6.3.

### U10 — Web UI  *(차순, build #10)*
- **책임**: 토폴로지·지식 그래프 시각화, 노드/관계/지식 편집, UI 내 보강 Q&A.
- **컴포넌트**: C14.
- **스토리**: US-7.1, US-7.2, US-7.3.

---

## MVP vs Next
- **MVP 1차 사이클 (Q6=A)**: U1 → U2 → U3 → U4 → U6 → U5 → U8 → U9 (end-to-end 자동 생성 + 쿼리; SC-1/SC-2/SC-4 충족).
- **차순 사이클**: U7(보강 Q&A) → U10(Web UI).
