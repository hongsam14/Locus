# Application Design Plan — Locus

**Application Design**은 고수준 컴포넌트 식별 + 서비스 계층 설계입니다(상세 비즈니스 로직은 이후 Functional Design). 아래 설계 결정 질문에 답해 주시면 그에 맞춰 산출물(`components.md` / `component-methods.md` / `services.md` / `component-dependency.md` / `application-design.md`)을 생성합니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 각 질문에 권장(Recommended) 기본값을 표시했습니다.

---

## Design Decision Questions

## Question AD-Q1 — 전체 아키텍처 스타일
시스템 전반의 아키텍처를?

A) **계층형 모듈러 모놀리스** — Python 패키지(코어) + FastAPI(백엔드) + React(프론트). 참고 프로젝트(Enola)와 동일 패턴 (Recommended — MVP에 단순·일관)
B) 마이크로서비스 — 수집/그래프/쿼리 등을 별도 서비스로 분리 (확장성↑, 복잡도↑)
C) 파이프라인 중심 — 수집→토폴로지→온톨로지를 단계별 파이프라인 프레임워크로 (배치 지향)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question AD-Q2 — 컴포넌트 조직(모듈 경계)
코어 모듈을 capability별로 나누는 안에 동의하시나요? (ingestion / topology / ontology / consensus / commonsense-wiki / augmentation / query / storage / llm-provider)

A) 동의 — capability별 모듈, 각 모듈은 명확한 인터페이스로 통신 (Recommended)
B) 더 굵게 — pipeline(수집+토폴로지+온톨로지) / knowledge(컨센서스+wiki+보강) / serving(query+UI API) / infra 로 4분할
C) 더 세분 — 위 capability를 더 잘게 (예: ingestion을 text/image/structured 별도 모듈)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question AD-Q3 — 파이프라인 오케스트레이션 방식
수집→토폴로지→온톨로지→컨센서스 처리 흐름의 실행 방식은?

A) 동기 순차 오케스트레이터 — 단일 프로세스에서 단계별 실행 (Recommended — MVP, 디버깅 쉬움)
B) 비동기 작업 큐 — 잡(job) 단위로 백그라운드 처리(대용량/장시간 대비)
C) 에이전트 그래프 — LangGraph 류로 단계를 에이전트 노드로 구성 (참고 프로젝트 패턴, 유연하나 복잡)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question AD-Q4 — LLM/VLM 추상화 & 에이전트 프레임워크
NFR-B(제공자 추상화, 기본 OpenAI) 구현을 어떤 형태로?

A) 경량 자체 Provider 인터페이스 — `LLMProvider`/`VLMProvider` 추상화 + OpenAI 구현 (외부 프레임워크 최소) (Recommended — 교체 용이·의존성 가벼움)
B) LangChain 기반 추상화 — 참고 프로젝트처럼 LangChain의 모델 추상화 활용
C) LangChain + LangGraph — 추상화 + 오케스트레이션 통합 (AD-Q3=C와 짝)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question AD-Q5 — 저장소 접근 패턴
Neo4j / OpenSearch 접근을?

A) Repository/Adapter 패턴 — 코어는 추상 인터페이스에만 의존, Neo4j/OpenSearch 구현을 어댑터로 (Recommended — 참고 프로젝트의 db adapters와 동일, 테스트 용이)
B) 직접 클라이언트 호출 — 모듈이 드라이버를 직접 사용 (단순하나 결합↑)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question AD-Q6 — API 표면 분리
백엔드 API를 어떻게 나눌까요? (1차 사용자 UI vs 2차 소비자 NPC 런타임)

A) 분리 — 내부 작성/편집·보강 API(authoring)와 공개 쿼리 API(serving)를 별도 라우터/네임스페이스로 (Recommended — 소비자 계약 안정화, 권한 분리 용이)
B) 단일 통합 API — 하나의 API로 모든 기능 제공 (단순)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Design Artifacts (답변 후 생성)
- [ ] `components.md` — 컴포넌트 정의·책임·인터페이스
- [ ] `component-methods.md` — 메서드 시그니처·입출력(상세 규칙은 Functional Design)
- [ ] `services.md` — 서비스 정의·오케스트레이션
- [ ] `component-dependency.md` — 의존 관계·통신 패턴·데이터 흐름
- [ ] `application-design.md` — 위 통합 문서

## Execution Checklist (생성 단계)
- [x] 1. AD-Q1~6 (+AD-CL1) 결정 반영해 컴포넌트/서비스 구조 확정
- [x] 2. components.md / component-methods.md 작성
- [x] 3. services.md / component-dependency.md 작성
- [x] 4. application-design.md 통합 + 일관성 검증

---

## Follow-up (상충 해소 — 답변 필요)

답변에서 **AD-Q3=A**(전체 파이프라인 = 동기 순차 오케스트레이터)와 **AD-Q4=C**(LangChain **+ LangGraph**)가 상충합니다. LangGraph는 그 자체가 오케스트레이션 프레임워크라, "동기 순차로 오케스트레이션"과 "LangGraph로 오케스트레이션"이 양립하지 않습니다. LangGraph의 역할 범위를 정해 주세요.

## Question AD-CL1 — Q3(동기 순차) vs Q4(LangGraph) 관계
A) **하이브리드** — 전체 파이프라인 골격은 동기 순차 오케스트레이터(Q3=A) 유지. LangChain은 LLM/VLM 제공자 추상화·프롬프트 체인에, **LangGraph는 특정 다단계 부분에만 국한** 사용(예: 지식 보강 Q&A 루프, 복잡한 멀티스텝 추출). (Recommended — Q3=A 유지하면서 LangGraph 이점 국소 활용)
B) **LangGraph 오케스트레이션** — 파이프라인 자체(수집→토폴로지→온톨로지→컨센서스)를 LangGraph 그래프의 노드로 구성. (= AD-Q3을 사실상 **C로 변경**; 가장 참고 프로젝트에 근접)
C) **LangChain만** — LangGraph는 제외. LangChain은 제공자 추상화/체인에만 쓰고, 오케스트레이션은 동기 순차(Q3=A) 유지. (= AD-Q4를 B로 조정)
X) Other (please describe after [Answer]: tag below)

[Answer]: 
