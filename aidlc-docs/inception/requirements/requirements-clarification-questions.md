# Requirements Clarification Questions — Locus (Round 1)

1차 답변 감사합니다. 모순은 없었습니다. 다만 Q12·Q13에서 기획서에 없던 **두 핵심 기능**이 새로 드러났고(상식 Wiki, 지식 보강 Q&A), Q6(저장소)이 열린 결정으로 남아 있습니다. 이 셋은 요구사항의 중심축이라 아래만 확정하면 `requirements.md`를 정확히 작성할 수 있습니다.

각 `[Answer]:` 뒤에 보기 문자를 적어주시고, 끝나면 "완료"라고 알려주세요.

---

## 상식 Wiki (Common-sense Wiki)

## Question CL1 — 상식 Wiki의 본질 / 저장 형태
"엔진 내부에 상식 wiki가 **존재하고**" 라고 하셨는데, 이를 어떤 형태로 둘까요?

A) LLM 내장 세계지식만 활용 — 별도 저장소 없이, 해석·고증 시점에 프롬프트로 추론 (가장 단순)
B) 영속적 상식 KB — 지질/기후/물류 등 실세계 prior를 구조화해 **저장**하고, 그래프 생성·고증에 참조 (조회·편집 가능) (Recommended — "존재한다"는 표현에 부합)
C) B + 게임 세계 확립 사실(캐논)도 함께 축적 — 실세계 prior와 세계관 지식을 하나의 KB로 통합
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question CL2 — 상식 Wiki prior의 출처
실세계 불변성/규칙(예: 산맥→교류 지연, 분지→고온)은 어디서 가져올까요?

A) LLM이 실세계 지식으로 추론 생성 — 별도 큐레이션 없음 (유연하나 재현성 낮음)
B) 큐레이션된 규칙/데이터셋(지형→기후·물류 영향 규칙표) + LLM 보완 (Recommended — 재현성 + 확장성 균형)
C) 외부 지리/기후 데이터셋 임포트 중심
X) Other (please describe after [Answer]: tag below)

[Answer]: B. 하지만 B 데이터셋을 구성하기 위해선 실제 지도와 관런 텍스트를 입력받아서 B를 구성하는 기능이 필요한데, 이 기능은 이미 구현하고자 하는 기능임. 결론은 동일한 포멧으로 구성된 실제 상식 데이터(디지털 트윈의 일종인가?)를 저장하고 기획자의 가상 세계데이터를 만드는데 활용하는거지.

## Question CL3 — 상식 Wiki의 적용 범위 (어디에 영향?)
주신 예시는 ① 토폴로지 가중치(산맥→연결 약화)와 ② 고증 지식 생성(분지→고온) 두 가지를 모두 포함합니다. MVP 적용 범위는?

A) 토폴로지 가중치(연결 강도·접근성)만
B) 고증 지식 생성(추가 지식 추론)만
C) 둘 다 (Recommended — 예시가 둘 다 포함)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## 지식 보강 (Knowledge Augmentation Q&A)

## Question CL4 — "지식 보강" 상호작용 방식 (MVP 포함 여부)
"AI-DLC처럼 기획자 질의응답으로 지식 보강"을 어떤 방식으로, 어느 범위까지 1차에 넣을까요?

A) 인터랙티브 Q&A 루프 — 시스템이 갭/모순을 찾아 기획자에게 질문 → 답변 → 그래프 보강(반복). MVP 포함 (Recommended — 핵심 기능이라 명시하심)
B) 비대화형 제안 — 시스템이 갭·고증 후보를 목록으로 제시, 기획자가 검토·편집 UI에서 수용/반영 (대화 루프는 없음)
C) 차기 버전으로 (MVP에서는 제외)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question CL5 — 지식 보강 질문의 생성 근거
시스템이 기획자에게 던질 "보강 질문"은 주로 무엇을 근거로 만들까요? (복수 선택 가능 — 예: A,C)

A) 그래프의 빈틈/모순 (예: 인접 지역인데 공유 지식이 없음, 끊긴 관계)
B) 상식 Wiki와의 충돌 (예: 분지인데 한랭 기후로 적힘 → 확인 질문)
C) 미해석/저신뢰 입력 (이미지·메모에서 자신 없게 추출된 항목 확인)
X) Other (please describe after [Answer]: tag below)

[Answer]: A, B, 미해결 질문(C)

---

## 저장소 (Q6 해소)

## Question CL6 — 저장소 구성 (벡터 검색 필요성)
Q6에서 "OpenSearch 벡터DB가 필요한지 고려"라 하셨습니다. 의미 검색이 필요한 지점은 (1) 추출 엔티티를 상식 Wiki prior/기존 지식과 매칭, (2) 유사 지식·고증 검색입니다. 구성안은?

A) Neo4j 단독 — 그래프 저장 + Neo4j 내장 벡터 인덱스로 의미 검색까지 (설치 단순, 규모 작을 때 충분) (Recommended — MVP)
B) Neo4j + OpenSearch — 그래프는 Neo4j, 의미·BM25 검색은 OpenSearch (참고 프로젝트와 동일; 지식·wiki 항목이 많고 하이브리드 검색이 중요할 때)
C) Neo4j + 임베디드 벡터(FAISS/sqlite-vec 등) — OpenSearch 운영 부담 없이 벡터 검색만 추가
X) Other (please describe after [Answer]: tag below)

[Answer]: B
