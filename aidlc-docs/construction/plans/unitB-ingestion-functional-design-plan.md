# Unit-B (Ingestion Connection) — Functional Design Plan

영역 4: VLM 추출 entity orphan 해소. 요구사항 FR-IM4.1~4.4.
확정: case2(신규 지형)=인제스터 Region 승격(CL4=A) / case1(이름 오추출)=OntologyBuilder 유사어+LLM 병합 / orphan 제로 목표.

## Functional Design 작업 체크리스트
- [x] domain-entities.md: RegionLevel.TERRAIN, ExtractedTerrain.x/y, terrain-Region 승격, LOCATED_IN 엣지 신설, unconnected_entity_ids, EntityMatchVerdict
- [x] business-logic-model.md: 인제스터 terrain 분류·승격(case2) + EntityReconciler(case1, fuzzy→임베딩→LLM, 비-VLM 승자) + orphan 연결(매칭/LOCATED_IN/augmentation) + topology 편입 + augmentation 표면화
- [x] business-rules.md: BR-B1~B12 (분류/승격/LOCATED_IN/병합 승자/후보가드/orphan순서/augmentation/graceful)

---

## 설계 확인 질문 (남은 결정)

### FD-B Q1 — terrain → Region 승격의 범위
현재 VLM terrain은 `Entity(TERRAIN)`가 되고, `between=[A,B]`는 A–B 사이 연결 힌트(예: mountain→blocked)로만 쓰입니다. CL4=A(신규 지형 Region 승격)를 어떻게 적용할까요?

A) **모든 VLM terrain을 Region으로 승격** + `between`은 그 terrain-Region과 인접 region들 간 연결로 변환 (예: mountain region이 A·B와 CONNECTED_TO). 별도 barrier 엣지는 terrain-Region 경유로 표현
B) **지형 유형별 분기**: 면적형 지형(plain/forest/valley/desert 등)은 Region 승격 / 순수 장벽·연결선(mountain range/river/road "between A,B")은 기존처럼 A–B 직접 연결 힌트로 유지(승격 안 함)
C) **승격 + barrier 엣지 둘 다 유지**: terrain을 Region으로 승격하되, 기존 A–B blocked/route 직접 엣지도 그대로 생성(중복 표현 허용)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### FD-B Q2 — 승격된 terrain-Region의 level/타입
`RegionLevel`은 현재 continent/province/town/district 뿐입니다. 지형은 거주 구역이 아닙니다. 어떻게 표현할까요?

A) **`RegionLevel`에 `FEATURE`(또는 `TERRAIN`) 추가** — 지형 region을 명시적 레벨로 구분 (계층/consensus에서 별도 취급 가능)
B) 기존 레벨 재사용(예: province/district) + `attributes`에 `is_terrain=True`, `terrain_kind` 마킹 (enum 변경 없음)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. TERRAIN 추가

### FD-B Q3 — case1 교차소스 병합(OntologyBuilder)의 매칭 신호 & 승자
VLM이 만든 Region/Entity가 text/structured 소스의 노드와 같은 대상인데 표기가 다른 경우, 어떻게 매칭·병합하나요?

A) **문자열 유사도(fuzzy) 후보 → 임베딩 유사도 → LLM 최종 판정** 3단계. 승자(canonical)는 **비-VLM 소스 우선**(text/structured가 더 신뢰), VLM 노드는 흡수·삭제
B) 임베딩 유사도만으로 후보 → LLM 판정 (fuzzy 생략)
C) LLM에게 전체 노드 목록을 주고 한 번에 중복 판정 (후보 추림 없음 — 소규모 가정)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-B Q4 — 좌표 없는 concept-art entity의 연결 경로
concept art clue(place/object/custom, 좌표 없음, 저신뢰)는 어떻게 연결하나요?

A) **기존 entity/region과 의미 매칭(임베딩+LLM)** → 매칭되면 RELATED_TO(또는 동일시 병합), 안 되면 가장 그럴듯한 region에 LOCATED_IN
B) 무조건 가장 그럴듯한 단일 region에 LOCATED_IN(임베딩으로 region 선택)
C) 기존 entity와 매칭만 시도(RELATED_TO); region 연결은 하지 않음
X) Other (please describe after [Answer]: tag below)

[Answer]: A + Q&A 루프에서 질문.

### FD-B Q5 — 끝내 연결 못 한 노드의 최종 처리 (orphan 제로 목표 FR-IM4.3)
매칭·승격·LOCATED_IN 모두 실패한 VLM 노드는?

A) **augmentation 후보로 표시** — 기존 Q&A 루프가 "이 항목을 어디에 연결?" 질문 (사용자 개입). 그래프엔 저신뢰로 보존하되 미연결 플래그
B) 가장 가까운/루트 region에 강제 LOCATED_IN (휴리스틱, 절대 orphan 안 남김)
C) 드롭(폐기) — 저신뢰 미연결 VLM 클루 제거
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-B Q6 — 승격 위해 terrain에 좌표 추출 추가
Region 승격엔 position이 필요합니다. 현재 `ExtractedTerrain`엔 x,y가 없습니다.

A) **`ExtractedTerrain`에 x,y 추가** — VLM이 지형 위치도 추정(이미 region엔 추정 중)
B) 좌표 없이 승격하되 position은 인접 region들의 중점으로 계산
X) Other (please describe after [Answer]: tag below)

[Answer]: A
