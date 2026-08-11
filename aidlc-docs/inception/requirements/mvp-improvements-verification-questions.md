# MVP 개선 사이클 — 요구사항 확인 질문

각 질문의 `[Answer]:` 태그 뒤에 선택지(A/B/C…)를 적어주세요. 맞는 선택지가 없으면 마지막 "Other"를 고르고 설명을 적어주세요. 다 끝나면 알려주세요.

---

## 영역 1 — `real_world` 개념 삭제 & world 간 상식 위키 공유

현재: 위키(WikiPrior)는 예약 파티션 `__realworld__`(`REALWORLD_WORLD_ID`)에 저장되고, 모든 게임 world가 이 단일 실세계 위키를 참조합니다.
목표: `__realworld__` 특수 개념을 없애고, 여러 world가 서로의 상식을 참조하도록 확장.

### Question 1
`__realworld__` 예약 파티션을 없앤 뒤, 상식 위키(WikiPrior)는 어디에 저장되어야 하나요?

A) 일반 world와 동일하게, 위키도 그냥 하나의 "world"로 취급 (예: `world_id="commonsense"` 같은 평범한 world. 예약어 아님). 다른 world들이 이 world를 참조 대상으로 등록
B) WikiPrior에서 단일 파티션 개념을 제거하고, **각 world가 자기 자신의 WikiPrior를 보유**. world들끼리 서로의 WikiPrior를 교차 참조
C) 전역 공유 풀(파티션 없는 글로벌 WikiPrior 저장소) + 각 world가 자기 WikiPrior도 보유하는 하이브리드
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 2
"world끼리 서로 참고한다"의 참조 방향/범위는 어떻게 동작해야 하나요?

A) 명시적 등록: world A가 "world B를 참조한다"고 등록하면, A의 빌드/쿼리 시 B의 위키·상식을 함께 사용 (단방향, 사용자가 지정)
B) 자동 전체 공유: 모든 world의 상식이 자동으로 서로에게 보임 (등록 불필요)
C) 태그/도메인 기반: world가 관심 도메인 태그를 선언하면, 같은 태그의 다른 world 상식을 참조
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 3
world가 다른 world의 상식을 "참조"할 때, 그 지식이 참조하는 world로 어떻게 들어오나요?

A) 읽기 전용 참조(read-through): 쿼리 시점에 참조 대상 world의 그래프를 함께 조회만 함 (복사 없음, 원본 유지)
B) 복사/물질화(materialize): 빌드 시점에 참조 대상의 상식을 현재 world로 복사해 가져옴 (provenance로 출처 표시)
C) 둘 다 지원 (참조는 기본 read-through, 사용자가 "고정/복사" 선택 가능)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 4
기존 `__realworld__` 파티션에 이미 빌드된 데이터/번들 실세계 샘플(`load_bundled_realworld`, `examples/realworld_sample/`)은 어떻게 처리하나요?

A) 마이그레이션: 기존 `__realworld__` 데이터를 새 구조의 기본 상식 world로 자동 이전 (하위 호환 별칭 제공)
B) 클린 컷: `__realworld__` 완전 제거, 번들 샘플은 일반 world 빌드 예제로 재배치 (기존 데이터 재빌드 필요, 마이그레이션 없음)
C) 호환 별칭만 유지: 코드상 `__realworld__`는 사라지되 기존에 쓰던 사람을 위해 이름만 일반 world로 매핑
X) Other (please describe after [Answer]: tag below)

[Answer]: B. 사실상 더미 데이터였어서 완전히 없애도 무방

---

## 영역 2 — WikiPrior 타입 관리 강화 (커뮤니티 + 교차 연결)

현재: WikiPrior 노드는 엣지가 전혀 없는 orphan. `prior_type`은 `terrain_rule/climate/logistics/fact` 4종.
목표: 분야(도메인)별 커뮤니티 형성 + 분야를 넘나드는 연결성.

### Question 5
WikiPrior의 "분야별 커뮤니티"는 그래프에서 어떻게 표현되어야 하나요?

A) 명시적 Domain/Community 노드 추가 + 각 WikiPrior가 `BELONGS_TO`로 커뮤니티에 연결
B) WikiPrior끼리 직접 엣지(`RELATED_TO`/`SIMILAR_TO`)로 연결해 군집(community)이 자연 형성되게 함 (별도 커뮤니티 노드 없음)
C) 둘 다: Domain 노드(상위 분류) + WikiPrior 간 직접 엣지(세부 관계) 모두
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 6
WikiPrior 간 연결(엣지)은 무엇을 기준으로 만들어야 하나요?

A) 의미 임베딩 유사도 기반 (이미 있는 EmbeddingProvider로 top-k 유사 prior끼리 연결)
B) LLM이 prior들을 보고 관계를 추론 (예: "이 기후 규칙은 저 물류 규칙에 영향" 같은 인과/연관)
C) 둘 다: 임베딩으로 후보 추리고 LLM이 관계 유형/방향 판정
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 7
현재 `prior_type`(4종: terrain_rule/climate/logistics/fact)이 "분야"의 단위로 충분한가요?

A) 충분함 — 기존 4종 prior_type을 그대로 커뮤니티/도메인 단위로 사용
B) 확장 필요 — 더 세분화된 도메인 분류 체계(taxonomy) 추가 (예: geography/economy/culture/history… LLM이 분류)
C) 자유 태그 — 고정 분류 대신 prior마다 도메인 태그(여러 개)를 LLM/사용자가 부여
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 8
"분야를 넘나드는 연결성(cross-domain connectivity)"은 어떤 목적/용도로 쓰이나요? (이게 빌드/쿼리에 어떤 영향을 주는지)

A) 검색 확장: 한 prior를 찾으면 연결된 다른 분야 prior도 함께 가져와 추론 품질↑ (예: corroboration·topology 가중치 계산 시 활용)
B) 시각화 위주: 웹 UI에서 위키 그래프를 보여주고 탐색하는 용도 (런타임 추론에는 큰 영향 없음)
C) 둘 다 (검색 확장 + 시각화)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## 영역 3 — Knowledge에 `title` 추가

현재: `Knowledge`에 `topic`(선택)·`statement`는 있으나 `title` 없음.

### Question 9
`title`의 역할은 무엇인가요? (`statement`/`topic`과의 구분)

A) 짧은 사람이 읽는 제목/요약 (statement는 전체 내용, topic은 분류, title은 한 줄 제목)
B) 사실상 topic을 대체 — topic을 title로 이름만 변경(rename)
C) UI 표시용 라벨 (그래프 노드/패널에서 보여줄 대표 이름; 검색에는 미사용)
X) Other (please describe after [Answer]: tag below)

[Answer]: A + UI 표시용 라벨

### Question 10
`title`은 어떻게 채워지나요?

A) LLM이 추출/생성 (ingestion 시 statement로부터 자동 생성; 비면 fallback)
B) 추출 스키마에 추가하고, 없으면 statement 앞부분으로 자동 채움 (LLM 호출 추가 없이)
C) 사용자가 authoring/augmentation UI에서 직접 입력/편집
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 11
`title`은 필수인가요 선택인가요? (하위 호환)

A) 선택(`title: str | None = None`) — 기존 데이터/테스트 깨지지 않게 nullable
B) 필수 — 모든 Knowledge가 title을 반드시 가지도록 강제 (마이그레이션/백필 필요)
X) Other (please describe after [Answer]: tag below)

[Answer]: B. 마이그레이션 필요 없음. 데이터 다 날리고 새로 만들거임.

---

## 영역 4 — VLM 추출 entity의 orphan 문제

현재: `concept_art_ingestor`·`map_image_ingestor`의 VLM 추출 entity는 relation/LOCATED_IN이 없어 그래프에서 고립(orphan). (text_ingestor는 relation·ABOUT·LOCATED_IN 생성)

### Question 12
VLM 추출 entity를 그래프에 어떻게 연결해야 하나요?

A) 지역 귀속(LOCATED_IN): VLM entity를 가장 그럴듯한 Region에 연결 (concept art는 어느 지역 그림인지, map image는 좌표/지역 기반으로 매핑)
B) 의미 연결(RELATED_TO/ABOUT): 기존 텍스트 추출 entity·knowledge와 임베딩/LLM으로 매칭해 연결
C) 둘 다 (가능하면 지역에도 붙이고, 유사 기존 entity와도 연결)
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 통합되어야 함. 사실상 Region과 같은 노드라고 봐도 무방. 하지만 vlm 특성상 text가 잘 못 추출되었을 가능성이 존재. 다음 질문과도 연결되기 때문에 다음 질문에서 서술.

### Question 13
연결할 대상(지역/entity)을 찾지 못한 VLM entity는 어떻게 처리하나요?

A) 그래도 보존하되 augmentation 후보로 표시 (사용자에게 "이 entity를 어디에 연결?"이라고 질문 — 기존 augmentation Q&A 루프 활용)
B) 저신뢰도 orphan으로 남겨두되 명시적으로 플래그 (`is_orphan`/낮은 confidence)만 표시
C) 드롭(폐기) — 연결 못 하는 저신뢰 VLM 클루는 그래프에 넣지 않음
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 두가지 상황을 예상할 수 있음. 1: 이름이 잘 못 추출됨. 2. 사용자가 map.json or memo에서 언급하지 않은 지형 요소들. 결론은 두 경우 모두 llm을 사용해서 해결해야 함. (1)의 경우에는 다른 데이터에서 추출한 region에서 유사한 단어가 있는지 검색하고 최종으로 llm이 판단해야함. 두번째는 llm(vlm)을 통한 좌표가 추출되었기 때문에, llm(vlm)이 연결된 지형인지 추론(결론)지을 수 있을 것.

### Question 14
이 연결 로직은 어디서 수행되어야 하나요? (책임 위치)

A) 인제스터 내부 (각 VLM 인제스터가 추출 즉시 region/relation까지 채움)
B) OntologyBuilder (현재 entity/relation을 그대로 통과시키는 단계에서, entity-region/entity-entity 연결을 일괄 수행) — VLM·텍스트 entity 모두 일관 처리
X) Other (please describe after [Answer]: tag below)

[Answer]: X. A B 섞여야 함. 위에서 말한 (1)의 경우에는 OntologyBuilder 단계에서 수행하는게 맞고, (2)의 경우에는 인제스터 내부에서 추출되는게 맞음.

---

## 횡단 관심사 (Cross-cutting)

### Question 15
이번 개선 사이클의 하위 호환 정책은? (기존 117 테스트 GREEN 유지 관련)

A) 가능한 한 additive — 기존 API/모델 필드/테스트를 깨지 않고 추가 위주. 불가피한 변경만 마이그레이션
B) 깔끔한 리팩터링 우선 — `__realworld__` 같은 레거시는 과감히 제거하고 테스트도 그에 맞게 갱신 (MVP라 사용자 적음)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 16
이 4개 개선을 어떤 단위로 묶어 진행할까요?

A) 4개를 하나의 큰 단위(Unit)로 묶어 한 번에
B) 영역별 4개 Unit으로 분리 (real_world / WikiPrior / title / VLM-orphan) — 독립적으로 설계·테스트·승인
C) 2개 Unit: ① 데이터 모델·위키 구조 변경(영역1+2+3) ② 인제스션 연결(영역4)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 17
웹 UI(`web/`)도 이번에 함께 업데이트해야 하나요? (title 표시, 위키 커뮤니티 그래프, world 간 참조 등)

A) 예 — 백엔드 변경에 맞춰 UI도 이번 사이클에 반영
B) 아니오 — 이번엔 백엔드/데이터 모델만, UI는 다음 사이클
C) 일부만 — title 표시 정도의 최소 변경만, 위키 시각화 등은 다음에
X) Other (please describe after [Answer]: tag below)

[Answer]: B
