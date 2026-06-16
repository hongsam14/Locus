# Unit-A FD — 후속 확인 (2건)

FD-A Q1을 질문으로 되물으셨고, Q2=A의 단서("NPC 생성 시 단일 world, 교차참조는 기획자 전용")가 설계를 바꿉니다. 산출물 작성 전 확정합니다.

### CL-A1 — World 노드 없이 글로벌 도메인 검색 (FD-A Q1 답)
맞습니다, World를 그래프 노드로 둘 이유가 약합니다. 제안하는 설계:
- 도메인은 **WikiPrior의 태그(enum, FD-A Q4=A)**로만 존재.
- world의 도메인 태그 = 그 world의 WikiPrior 도메인 집합을 **필요할 때 계산**(저장 안 함, CL1=A).
- 교차참조 = "이 도메인들을 가진 WikiPrior를 **world 구분 없이 글로벌 검색**".

이 방향이 맞나요?

A) 맞음 — World 그래프 노드 추가하지 않음. 교차참조는 WikiPrior에 대한 글로벌(전 world) 도메인 태그 검색으로 구현
B) 그래도 가벼운 World 노드(도메인 태그 보관용)는 저장하고 싶음
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### CL-A2 — 교차참조의 사용 범위 (Q2=A 단서 확정)
"NPC 정보 생성용 검색은 다중 world면 안 되고, 교차참조는 기획자 전용"을 다음과 같이 확정하려 합니다:
- **자동 빌드 파이프라인**(corroboration 등 NPC가 알 지식 생성)과 **NPC 런타임 쿼리**: 엄격히 **현재 world의 WikiPrior만** 사용 (교차참조 없음).
- **교차참조(글로벌 도메인 검색)**: 기획자가 다른 world의 상식을 탐색/참조하기 위한 **별도 authoring/조회 기능**(API/CLI). 자동으로 NPC 지식에 섞이지 않음.

이 범위가 맞나요?

A) 맞음 — 교차참조는 기획자 전용 별도 기능. 빌드/런타임 NPC 경로는 단일 world 고정
B) 빌드의 corroboration까지는 교차참조 허용(다른 world 상식으로 보강), 단 NPC 런타임 쿼리는 단일 world
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 확정된 나머지 FD-A 답 (참고)
- Q3=A: WikiPrior 엣지는 **world 내부만**.
- Q4=A: 도메인은 **고정 Enum**(예: geography/geology/climate/economy/logistics/culture/history/politics — 최종 목록은 domain-entities.md에서 확정).
- Q5=A: 엣지는 전용 **WikiPriorLink**(source/target/relation/weight/provenance), 그래프엔 엣지로만, 단순화 무방향.
- Q6=A: title을 검색 텍스트에 포함.
