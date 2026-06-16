# MVP 개선 사이클 — 후속(명확화) 질문

답변 잘 받았습니다. 아래 4가지는 답변들이 서로 맞물리면서 설계가 갈리는 지점이라 확정이 필요합니다.
각 `[Answer]:` 뒤에 선택지를 적어주세요.

---

## 맥락
- Q2=C: world가 **도메인 태그**를 선언하면 같은 태그의 다른 world 상식을 참조
- Q7=B: WikiPrior에 더 세분화된 **도메인 taxonomy** 추가 (LLM 분류)
- 이 둘이 자연스럽게 동작하려면 "도메인" 어휘가 어떻게 정의/공유되는지 확정해야 합니다.

### Clarification 1 — 도메인 분류 체계의 통합
world의 도메인 태그(Q2)와 WikiPrior의 도메인(Q7)은 같은 분류 체계를 공유하나요?

A) 예, 단일 공유 taxonomy. **world의 도메인 태그 = 그 world가 보유한 WikiPrior들의 도메인 집합**(자동 집계 — 별도 선언 불필요)
B) 예, 단일 taxonomy지만 world 태그는 WikiPrior 도메인과 **별개로 명시 선언**(어휘만 공유)
C) 아니오 — world 태그와 WikiPrior 도메인은 서로 다른 분리된 체계
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Clarification 2 — world 도메인 태그는 누가 정하나
(CL1에서 A를 고르면 자동 집계이므로 이 질문은 생략 가능합니다. B/C라면 답해주세요.)

A) LLM이 world 콘텐츠(memo/map/WikiPrior)에서 자동 추론
B) 사용자가 world 생성/설정 시 직접 선언
C) 둘 다 (LLM 제안 + 사용자 편집)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## 맥락
- Q1=B: `__realworld__`를 없애고 **각 world가 자기 자신의 WikiPrior를 보유**.
- 그렇다면 게임 world의 WikiPrior(상식)는 어디서 생기는지 확정이 필요합니다.
  (현재는 `PriorDistiller`가 실세계 ingestion에서만 증류)

### Clarification 3 — 각 world의 WikiPrior 출처
각 world가 보유하는 WikiPrior는 어떻게 생성되나요?

A) `PriorDistiller`를 일반화 — **모든 world의 ingestion(memo/map)에서** 상식 prior를 증류 (real-world 전용 → 범용)
B) 사용자가 authoring API/UI로 직접 작성
C) 둘 다 (자동 증류 + 사용자 추가/편집)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## 맥락
- Q12=X: "VLM 추출 entity는 사실상 Region과 같은 노드로 봐도 무방"
- Q13=X case(2): map.json/memo에 없던 신규 지형 — VLM이 좌표를 추출했고, 연결된 지형인지 VLM이 추론
- 이 경우 그 지형 요소가 그래프에서 **무엇이 되는지**(노드 타입)를 확정해야 토폴로지/온톨로지 연결 방식이 정해집니다.

### Clarification 4 — VLM 추출 지형 요소의 노드 모델링
VLM이 새로 발견한 지형 요소(case 2)는 그래프에서 무엇이 되나요?

A) **Region 노드로 승격** — position 좌표를 갖고 토폴로지(CONNECTED_TO)에 편입 (VLM이 연결성도 추론)
B) **Entity(terrain/place)로 유지**하되 반드시 LOCATED_IN으로 가장 가까운/관련 Region에 연결
C) 상황별 — 충분히 큰 지형은 Region 승격, 작은 랜드마크/오브젝트는 Entity + LOCATED_IN
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 참고 — 별도 확인 없이 둔 가정 (틀리면 알려주세요)
1. **교차 참조 범위**: world 간에 공유/참조되는 것은 **WikiPrior(상식)만**입니다. 게임 고유의 Knowledge/Entity/Region은 world 경계 안에 그대로 머뭅니다. (Q1=B의 명시적 표현에 근거)
2. **데이터 초기화**: Q4=B/Q11=B/Q15=B에 따라 기존 데이터는 마이그레이션 없이 폐기·재빌드하며, `__realworld__`/`REALWORLD_WORLD_ID`·`load_bundled_realworld`·`examples/realworld_sample/`는 완전히 제거합니다.
3. **VLM case(1) 처리**: 이름이 잘못 추출된 VLM entity는 OntologyBuilder에서 다른 소스의 Region/Entity와 유사어 검색(임베딩/문자열) 후 LLM 최종 판정으로 병합합니다.
