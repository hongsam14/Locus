# Unit-B — Business Rules (Functional Design)

| ID | 규칙 | 출처 |
|---|---|---|
| **BR-B1** | VLM terrain은 kind로 분류한다: barrier kind(mountain/range/sea/ocean/river/road/route/bridge)는 A–B 연결 힌트로만 사용(승격 안 함); 그 외 면적형은 `Region(level=TERRAIN)`으로 승격한다. | Q1=B |
| **BR-B2** | 승격된 terrain-Region은 VLM 추정 `position`(x,y)과 `attributes{terrain_kind, origin:"vlm"}`를 가진다. | Q2=A, Q6=A |
| **BR-B3** | 승격된 terrain-Region은 `between`/인접으로 이웃 Region과 `CONNECTED_TO`를 가진다(VLM 연결성 추론). 연결 못 하면 미연결 잔여로 처리(BR-B8). | Q1=B, CL4=A |
| **BR-B4** | `RegionLevel.TERRAIN`은 거주 계층과 구분된다. 승격 terrain은 더 이상 `Entity(TERRAIN)` orphan으로 남지 않는다. | Q2=A |
| **BR-B5** | 모든 entity의 `located_in`이 채워지면 `LOCATED_IN` 그래프 엣지를 생성·영속화한다(VLM·text·structured 일관). | FR-IM4.4 |
| **BR-B6** | case1 병합: VLM-origin 노드를 비-VLM(text/structured) 노드와 fuzzy→임베딩→LLM 3단계로 매칭하고, 동일 판정 시 **비-VLM을 canonical**로 두고 VLM 노드를 흡수·삭제(참조 remap). | Q3=A |
| **BR-B7** | LLM 매칭은 fuzzy/임베딩으로 후보를 제한한 뒤에만 호출한다(전수 LLM 금지). 임베딩 provider 없으면 fuzzy만으로 후보. | NFR-IM4 |
| **BR-B8** | orphan 연결 순서: (1) 기존 entity 의미매칭→RELATED_TO/병합, (2) 실패 시 가장 그럴듯한 region에 `LOCATED_IN`, (3) 그래도 실패 시 **augmentation 후보**(`unconnected_entity_ids`)로 보존·플래그. **드롭하지 않는다.** | Q4=A, Q5=A, FR-IM4.3 |
| **BR-B9** | 미연결 잔여는 augmentation Q&A로 표면화한다("이 항목을 어디에 연결?"). 사용자 답변이 LOCATED_IN/RELATED_TO를 생성한다. | Q4=A, Q5=A |
| **BR-B10** | 모든 VLM/LLM/임베딩 단계는 graceful: 실패 시 해당 항목은 미연결 잔여로 떨어지고 빌드는 계속된다. | 기존 graceful 컨벤션 |
| **BR-B11** | 병합·승격·연결 결과물은 Provenance를 보존한다(VLM origin 추적 가능). | 기존 BR-7 |
| **BR-B12** | 모든 신규 외부 I/O는 기존 포트 뒤에 둔다. 오프라인 테스트는 mock으로 동작(인제스터/리컨실러는 순수 로직과 포트 호출 분리). | NFR-IM1/3 |

## 엣지 케이스
- 면적형 terrain에 좌표 없음 → position=None으로 승격, 연결은 `between`/리컨실러; 둘 다 실패 시 augmentation(BR-B8).
- barrier terrain의 `between`이 2개 아님 → 기존처럼 unresolved 경고(topology) — 동작 변화 없음.
- VLM 노드가 비-VLM과 다수 매칭 후보 → LLM 최상위 1건만 병합(중복 병합 방지).
- 임베딩/LLM 모두 없음(테스트) → fuzzy만; 매칭 안 되면 위치 기반 LOCATED_IN 또는 augmentation 잔여.
- concept art clue(좌표 없음) → 의미매칭 우선, 실패 시 region 귀속(임베딩/LLM), 실패 시 잔여.
