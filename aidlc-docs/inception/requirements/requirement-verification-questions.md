# Requirements Verification Questions — Locus

아래 질문에 각 `[Answer]:` 태그 뒤에 보기 문자(A/B/C/...)를 적어 답변해 주세요.
보기 중 맞는 것이 없으면 마지막 보기 `X) Other`를 고르고 `[Answer]:` 뒤에 직접 설명을 적어주세요.
각 질문에는 기획서와 참고 프로젝트(KnowledgeBase-Nuclei-Template) 기반의 **권장(Recommended)** 기본값을 표시해 두었습니다. 그대로 동의하면 해당 문자만 적으셔도 됩니다.
모두 작성하신 뒤 "완료" 라고 알려주세요.

---

## A. 도메인 핵심 개념 (기획서 §10 미해결 질문)

## Question 1 — 지역(노드)의 granularity
공간 지식이 귀속되는 "지역" 노드의 기본 단위를 무엇으로 할까요?

A) 단일 평면 단위 — 마을/도시 등 하나의 레벨만 사용 (단순, MVP 적합)
B) 계층 구조 — 대륙 > 지방 > 마을 > 구역 처럼 다단계로 표현 (Recommended — 세계관 확장성·스코프 상속에 유리)
C) 자유 그래프 — 고정 레벨 없이 "포함(contains)" 관계로 임의 중첩 허용
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2 — 지식의 "왜곡(소문/rumor)" 표현 방식
멀거나 단절된 지역에서 지식이 왜곡되어 전달되는 현상을 어떻게 모델링할까요?

A) 확신도(confidence) 속성 — 같은 지식 노드에 지역별 confidence/accuracy 속성을 부여 (단순)
B) 별도 변형(variant) 노드 — 원본 지식과 별개의 "소문 버전" 노드를 만들고 `distorted_from` 관계로 연결 (Recommended — 내용 자체가 바뀐 소문 표현에 적합)
C) 둘 다 — 경미한 차이는 confidence, 내용이 바뀌는 소문은 variant 노드
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 3 — 컨센서스(지식 전파·공유 범위) 계산 시점
지역 간 연결 강도에 따른 지식 공유/전파/왜곡 범위를 언제 계산할까요?

A) 정적 전처리 — 그래프 생성 시 각 지역의 지식 스코프를 미리 계산해 저장 (쿼리 빠름, 재계산 비용 있음)
B) 쿼리 시점 동적 계산 — NPC 쿼리 시 토폴로지를 순회해 그때 계산 (유연, 쿼리 비용 있음)
C) 하이브리드 — 직접 보유 지식은 정적 저장, 전파/소문 범위는 쿼리 시 계산 (Recommended)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4 — 지도 입력 포맷
지형/지도 데이터를 어떤 형태로 입력받을까요?

A) 이미지 중심 — 지도 이미지를 VLM으로 해석해 지역/지형 추출 (기획서의 비정형 자료 가정에 충실)
B) 범용 구조화 포맷 중심 — GeoJSON / 노드-엣지 JSON 등 범용 포맷만 지원 (해석 안정적)
C) 둘 다 지원 — 이미지 입력 + 범용 구조화 포맷 입력 모두 (Recommended — 이미지로 초안 생성, 구조화 포맷으로 정밀 입력)
D) 게임 엔진(Unity/Unreal) 맵 포맷 직접 파싱
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## B. 기술 스택 & 저장소

## Question 5 — 구현 언어/런타임
주 구현 언어는 무엇으로 할까요? (참고 프로젝트는 Python 3.11+)

A) Python 3.11+ (Recommended — 참고 프로젝트와 동일, LLM/VLM·그래프 생태계 풍부)
B) TypeScript / Node.js
C) 기타
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6 — 지식 그래프 / 토폴로지 저장소
생성된 그래프(토폴로지 + 온톨로지)를 어디에 저장할까요?

A) Neo4j (Recommended — 참고 프로젝트와 동일, 그래프 순회·관계 쿼리에 최적, Docker로 구동)
B) 임베디드/파일 기반 (예: SQLite + 그래프 라이브러리, NetworkX 직렬화) — 설치 부담 최소
C) RDF / 트리플스토어 (온톨로지 표준 SPARQL 지향)
X) Other (please describe after [Answer]: tag below)

[Answer]: X. A와 유사하지만, Opensearch를 통한 vectorDB도 필요한지 고려.

## Question 7 — LLM/VLM 제공자
멀티모달 해석(텍스트→엔티티/관계, 이미지→지형/장소)에 사용할 모델 제공자는?

A) Anthropic Claude (Opus/Sonnet, 멀티모달 vision 지원) (Recommended — 현재 환경, 최신 모델)
B) OpenAI GPT 계열
C) 로컬/오픈소스 모델 (예: Llama, Qwen-VL)
D) 추상화 계층을 두어 교체 가능하게 (특정 제공자 비종속)
X) Other (please describe after [Answer]: tag below)

[Answer]: B. OpenAI api를 가지고 있음. 하지만 D가 가능하면 D로.

---

## C. 인터페이스 & 산출물

## Question 8 — MVP 1차 인터페이스
초기 버전에서 우선 제공할 인터페이스는? (기획서 §7: 실시간 엔진 통합은 범위 제외, export/API 수준)

A) CLI + 쿼리 API (FastAPI) — 그래프 생성 파이프라인 CLI + "지역 X 지식" 쿼리 REST API (Recommended — 참고 프로젝트 패턴, 가장 빠른 MVP)
B) 위 A + 웹 검토·편집 UI (React) — 기획자가 그래프를 시각적으로 확인/수정 (참고 프로젝트의 graph-universe-proto 유사)
C) 웹 UI 중심 (검토·편집이 핵심이므로 처음부터 포함)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 9 — 검토·편집 인터페이스(기획서 §6)의 MVP 포함 여부
기획자가 생성 그래프를 보고 수정하는 도구를 1차 MVP에 포함할까요?

A) 1차 제외 — MVP는 자동 생성 + 쿼리까지. 검토/수정은 산출물(JSON/그래프) 직접 편집 또는 차기 버전 (Recommended — 성공 기준 §8에 집중)
B) 읽기 전용 시각화만 포함 — 수정은 불가, 확인만 가능
C) 시각화 + 편집 모두 1차 포함
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 10 — NPC 런타임용 쿼리/Export 산출물 형식
2차 소비자(NPC 런타임)가 가져갈 "지역 X NPC가 아는 지식"의 출력 형식은?

A) JSON REST API 응답 (지역별 지식 항목 + 메타데이터) (Recommended)
B) 정적 Export 파일 (지역별 JSON 번들을 빌드 타임에 내보내기)
C) 둘 다 — 실시간 API + 정적 export 모두
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## D. 실행 환경 & 범위

## Question 11 — 실행/배포 환경
초기 실행 환경은?

A) 로컬 개발 + Docker Compose (앱 + Neo4j 등 의존성) (Recommended — 참고 프로젝트와 동일)
B) 순수 로컬 (Docker 없이, 임베디드 저장소)
C) 클라우드 배포 고려 (AWS 등)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 12 — MVP 성공 검증용 샘플 데이터
성공 기준(§8) 검증에 쓸 샘플 세계관 자료를 어떻게 마련할까요?

A) 내(사용자)가 샘플 메모 + 지도 1장을 제공
B) Locus가 데모용 가상 세계관 샘플(메모 + 간단 지도)을 생성해 포함 (Recommended — 즉시 end-to-end 검증 가능)
C) 둘 다 — 데모 샘플 기본 포함 + 실제 자료로 교체 가능
X) Other (please describe after [Answer]: tag below)

[Answer]: C. 내가 생각하는 엔진에서의 핵심 기능 중 하나는 엔진 내부의 "상식 wiki"가 존재하고 "상식 wiki"에서는 지리와 관련된 지질학적 불변성을 이미 내장하고 있어서, 세계관 자료를 해석하고 추가 고증을 생성할 수 있는 기능임. (ex. A지역과 B 지역 사이에 산맥이 있다면, 정보 물류 교류가 느리다. ex2. C지역이 분지라면 지구의 실제 지형 (데스벨리)를 참고하여 높은 기온일 것이라는 추가 고증을 추가 생성)

## Question 13 — 범위 제외 항목 확인 (기획서 §7)
다음을 초기 버전 범위에서 **제외**하는 데 동의하시나요? (① NPC 대사 생성 자체, ② 실시간 게임 엔진 통합, ③ 시간 축 지식 동적 변화 시뮬레이션)

A) 세 가지 모두 제외에 동의 (Recommended — 기획서대로)
B) 일부는 포함하고 싶음 (X에 어떤 항목을 포함할지 기재)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 내가 생각하는 핵심 기능은 이전 답변에서 말한 "상식 wiki"를 기반으로 ai-dlc처럼 기획자의 질의응답을 통해 "지식 보강"을 하는 기능임.

---

## E. AI-DLC 확장(Extensions) Opt-In

## Question: Security Extensions
이 프로젝트에 보안 확장 규칙(SECURITY rules)을 강제 적용할까요?

A) Yes — 모든 SECURITY 규칙을 blocking 제약으로 적용 (프로덕션급 권장)
B) No — SECURITY 규칙 생략 (PoC/프로토타입/실험 프로젝트에 적합) (Recommended for MVP)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question: Property-Based Testing Extension
속성 기반 테스트(PBT) 규칙을 강제 적용할까요?

A) Yes — 모든 PBT 규칙을 blocking 제약으로 적용 (비즈니스 로직/데이터 변환/직렬화/상태 컴포넌트가 많은 프로젝트 권장)
B) Partial — 순수 함수와 직렬화 round-trip 에만 PBT 적용 (Recommended — 그래프 직렬화·컨센서스 계산 로직 검증에 유용하되 과하지 않게)
C) No — PBT 규칙 생략 (단순 CRUD/UI 전용/얇은 통합 계층에 적합)
X) Other (please describe after [Answer]: tag below)

[Answer]: B
성