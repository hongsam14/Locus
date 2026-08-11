# MVP 개선 사이클 — 요구사항 (Requirements)

> 본 문서는 완료된 Locus MVP(117 tests GREEN) 위에서 진행하는 **brownfield 개선 사이클**의 요구사항이다.
> 원 프로젝트 요구사항은 `requirements.md`, 본 문서는 그 위의 증분 요구사항이다.

## 1. Intent Analysis Summary
- **User Request**: 초기 MVP에서 발견된 4개 개선점 반영 — (1) `real_world` 개념 삭제 + world 간 상식 위키 교차 참조, (2) WikiPrior 커뮤니티/교차연결, (3) Knowledge `title` 추가, (4) VLM 추출 entity orphan 해소.
- **Request Type**: Enhancement + Refactoring (레거시 `__realworld__` 제거 포함).
- **Scope**: Multiple Components — models, commonsense_wiki, ontology, ingestion, topology, query, storage, api.
- **Complexity**: Complex (데이터 모델·위키 구조·인제스션 파이프라인 동시 변경).
- **Depth**: Comprehensive.
- **호환 정책 (Q15=B)**: 클린 리팩터링 우선. 레거시 과감히 제거, 테스트는 새 구조에 맞게 갱신. 기존 데이터는 마이그레이션 없이 폐기·재빌드 (Q4=B/Q11=B).

## 2. Unit 분할 (Q16=C)
- **Unit-A — Model & Wiki Structure**: 영역 1 + 2 + 3 (데이터 모델/위키 구조 변경).
- **Unit-B — Ingestion Connection**: 영역 4 (VLM entity 연결 / orphan 해소).
- 웹 UI는 이번 사이클 **제외** (Q17=B) — 다음 사이클.

---

## 3. Functional Requirements

### 영역 1 — `real_world` 개념 삭제 & world 간 상식 위키 교차 참조 (Unit-A)

- **FR-IM1.1 (`__realworld__` 완전 제거)**: `REALWORLD_WORLD_ID`, `load_bundled_realworld`, `examples/realworld_sample/`, `World.kind`의 `"realworld"` 특수 취급, 그리고 단일 실세계 위키 파티션 가정을 코드/문서/테스트에서 모두 제거한다. (Q4=B, 가정 2)
- **FR-IM1.2 (world별 WikiPrior 보유)**: WikiPrior는 더 이상 예약 파티션이 아니라 **각 world의 `world_id`에 소속**된다. 위키 lookup/저장/검색은 대상 world 파티션 기준으로 동작한다. (Q1=B)
- **FR-IM1.3 (world별 WikiPrior 생성 — 자동+수동)**: 각 world의 WikiPrior는 (a) `PriorDistiller`를 범용화하여 **그 world의 ingestion(memo/map)에서 자동 증류**하고, (b) authoring API로 **사용자가 직접 추가/편집**할 수 있다. (CL3=C)
- **FR-IM1.4 (도메인 태그 기반 교차 참조)**: world는 **도메인 태그 집합**을 가진다. world A의 빌드/쿼리 시, A의 도메인 태그와 **겹치는 도메인 태그를 가진 다른 world들의 WikiPrior**를 함께 참조한다. (Q2=C)
- **FR-IM1.5 (read-through 참조)**: 교차 참조는 **쿼리/빌드 시점의 읽기 전용 조회**다. 참조 대상 WikiPrior를 현재 world로 복사하지 않으며 원본 world 파티션에 그대로 둔다. (Q3=A)
- **FR-IM1.6 (교차 참조 범위 = WikiPrior 한정)**: world 간 공유/참조 대상은 **WikiPrior(상식)뿐**이다. 게임 고유의 Knowledge/Entity/Region/Rumor/Topology는 world 경계 안에 머문다. (가정 1)
- **FR-IM1.7 (world 도메인 태그 자동 집계)**: world의 도메인 태그는 **그 world가 보유한 WikiPrior들의 도메인 집합으로 자동 집계**된다. 별도 수동 선언을 1차 출처로 두지 않는다. (CL1=A)

### 영역 2 — WikiPrior 커뮤니티 & 교차 도메인 연결 (Unit-A)

- **FR-IM2.1 (도메인 taxonomy 확장)**: `prior_type`(4종)과 별개로, WikiPrior에 더 세분화된 **도메인 분류(taxonomy)**를 부여한다 (예: geography/economy/culture/history/climate/logistics…). 도메인은 **LLM이 분류 제안 + 사용자가 편집 가능**. (Q7=B, CL2=C)
- **FR-IM2.2 (도메인 = 공유 어휘)**: WikiPrior 도메인과 world 도메인 태그는 **단일 공유 taxonomy**를 사용한다. world 태그는 보유 WikiPrior 도메인의 집계다. (CL1=A)
- **FR-IM2.3 (WikiPrior 간 직접 엣지)**: 별도 Community/Domain 노드 없이, **WikiPrior끼리 직접 엣지(예: `RELATED_TO`)로 연결**하여 군집이 자연 형성되게 한다. (Q5=B)
- **FR-IM2.4 (엣지 생성 = 임베딩 후보 + LLM 판정)**: 엣지는 **임베딩 유사도로 top-k 후보를 추리고, LLM이 관계 유무/유형/방향을 판정**해 생성한다. (Q6=C) 같은 도메인 내 연결(커뮤니티 응집)과 **다른 도메인 간 연결(cross-domain)**을 모두 만든다.
- **FR-IM2.5 (cross-domain 연결의 용도)**: 생성된 연결성은 (a) **검색 확장** — 한 prior 조회 시 연결된 다른 도메인 prior도 함께 가져와 corroboration/topology 가중치 추론 품질을 높이고, (b) **시각화**를 위한 그래프 구조로도 노출한다. (Q8=C) (단, 시각화 UI 구현은 본 사이클 제외 — 데이터/구조만 제공.)

### 영역 3 — Knowledge `title` 추가 (Unit-A)

- **FR-IM3.1 (`title` 필드 추가)**: `Knowledge`에 `title`을 추가한다. `statement`(전체 내용)·`topic`(분류)와 구분되는 **짧은 한 줄 제목 / UI 표시 대표 라벨**. (Q9=A + UI 라벨)
- **FR-IM3.2 (LLM 생성)**: `title`은 ingestion 시 **LLM이 statement로부터 추출/생성**한다 (추출 스키마에 포함). (Q10=A)
- **FR-IM3.3 (필수 필드)**: `title`은 **필수**다. 마이그레이션은 불필요 — 데이터는 폐기·재빌드한다. (Q11=B) 모든 Knowledge 생성 경로(ingestion, corroboration, augmentation)는 title을 채워야 한다.

### 영역 4 — VLM 추출 entity orphan 해소 (Unit-B)

- **FR-IM4.1 (VLM 신규 지형 → Region 승격)**: VLM이 map.json/memo에 없던 신규 지형을 발견하면(case 2), 해당 요소를 **Region 노드로 승격**한다 — `position` 좌표 포함, 토폴로지(`CONNECTED_TO`)에 편입. 연결성은 VLM이 좌표/그림 기반으로 추론한다. 이 처리는 **인제스터 내부**에서 수행. (Q12/13/14=X case2, CL4=A, Q14=X-A)
- **FR-IM4.2 (이름 오추출 VLM entity → 기존 노드 병합)**: VLM이 추출한 entity의 이름이 다른 소스(text/structured map)의 Region/Entity와 사실상 동일 대상인데 철자/표기가 달라 고립된 경우(case 1), **OntologyBuilder 단계에서** 다른 소스 노드들과 **유사어 검색(임베딩+문자열) → LLM 최종 판정**으로 병합/연결한다. (Q13=X case1, Q14=X-B)
- **FR-IM4.3 (orphan 제로 목표)**: 위 두 경로 처리 후에도 어떤 Region/Entity에도 연결되지 않는 VLM entity가 남지 않도록 한다. (영역 4 본래 목표 — orphan node 제거)
- **FR-IM4.4 (일관 처리)**: VLM·텍스트 양쪽 entity가 그래프 연결(LOCATED_IN/RELATED_TO/Region 편입) 관점에서 일관되게 다뤄지도록 한다.

---

## 4. Non-Functional Requirements
- **NFR-IM1 (포트 추상화 유지)**: 모든 신규 외부 I/O는 기존 `GraphRepository/SearchRepository/LLMProvider/EmbeddingProvider/VLMProvider` 포트 뒤에 둔다. 오프라인 테스트는 mock으로 동작. (기존 컨벤션)
- **NFR-IM2 (world_id 파티셔닝 불변식)**: 모든 그래프 노드/엣지는 `world_id`로 파티션된다. 교차 참조는 **읽기 쿼리에서 여러 world_id를 함께 조회**하는 방식으로만 경계를 넘으며, 쓰기는 항상 단일 world에 한정. (가정 1·FR-IM1.5)
- **NFR-IM3 (결정론/테스트 가능성)**: LLM/임베딩 의존 로직(도메인 분류, 엣지 판정, VLM 병합 판정)은 순수 함수 경계와 mock 가능한 포트로 분리해 오프라인 테스트를 유지한다. PBT(Partial)는 순수 함수·직렬화 라운드트립에 한해 적용. (기존 확장 설정 유지)
- **NFR-IM4 (성능/비용 가드)**: WikiPrior 엣지 생성은 임베딩 top-k로 후보를 제한한 뒤에만 LLM을 호출(전수 O(n²) LLM 호출 금지). 교차 참조 조회는 도메인 태그 일치 world로 범위를 제한.
- **NFR-IM5 (테스트 GREEN)**: 변경 후 오프라인 테스트 스위트는 GREEN을 유지(레거시 제거로 삭제/갱신되는 테스트 제외). ruff/black/tsc 클린.

## 5. Data Model 변경 요약 (확정 설계는 Functional Design에서)
- `Knowledge`: `+ title: str` (필수). (FR-IM3.1)
- `WikiPrior`: `+ domains: list[str]`(공유 taxonomy), `world_id` 소속(예약 파티션 제거). (FR-IM1.2/2.1)
- world 도메인 태그: 별도 필드 저장 또는 보유 WikiPrior에서 파생(설계 시 결정). world 간 참조용. (FR-IM1.7)
- WikiPrior 간 엣지: 신규 관계(예: `WikiPriorLink`/`RELATED_TO`). (FR-IM2.3)
- VLM 신규 지형: `Region`으로 표현(신규 노드 타입 추가 아님). (FR-IM4.1)
- 제거: `REALWORLD_WORLD_ID`, `load_bundled_realworld`, `examples/realworld_sample/`, `World.kind="realworld"` 특수 경로.

## 6. Out of Scope
- 웹 UI(`web/`) 변경 (title 표시, 위키 커뮤니티 그래프 시각화, world 참조 UI) — 다음 사이클 (Q17=B).
- 데이터 마이그레이션 도구 (폐기·재빌드 전제 — Q4/Q11/Q15).
- 새로운 외부 인프라/배포 변경.

## 7. Traceability
| 개선 영역 | FR | Unit | 영향 컴포넌트 |
|---|---|---|---|
| 1. real_world 삭제 + 교차참조 | FR-IM1.1~1.7 | A | `__init__`, models(graph/World), commonsense_wiki(base/builder/admin/distiller/bundled), storage(graph_mapping), query, api(authoring), CLI |
| 2. WikiPrior 커뮤니티/교차연결 | FR-IM2.1~2.5 | A | models(WikiPrior/enums), commonsense_wiki, ontology(similarity), storage |
| 3. knowledge title | FR-IM3.1~3.3 | A | models(Knowledge), ingestion(schemas/text_ingestor), ontology(corroboration), augmentation, storage(graph_mapping) |
| 4. VLM orphan | FR-IM4.1~4.4 | B | ingestion(map_image/concept_art/schemas), topology(builder), ontology(builder) |

## 8. 확정된 가정
1. 교차 참조 범위 = WikiPrior 한정. (가정 1)
2. 데이터 폐기·재빌드, 마이그레이션 없음. (가정 2)
3. VLM case1 = OntologyBuilder 병합, case2 = 인제스터 내 Region 승격. (가정 3 + CL4)
4. world 도메인 태그는 보유 WikiPrior 도메인의 자동 집계 (CL1=A); 도메인 자체는 LLM 분류 + 사용자 편집 (CL2=C, Q7=B).

## 9. Key Requirements 요약
- `__realworld__` 예약 개념을 완전히 제거하고, 위키를 **world별 보유 + 도메인 태그 기반 read-through 교차 참조** 구조로 전환.
- WikiPrior를 **도메인 taxonomy + 임베딩/LLM 기반 직접 엣지**로 연결해 커뮤니티·교차도메인 연결성 확보(검색 확장 + 시각화 데이터).
- `Knowledge.title`(필수, LLM 생성) 추가.
- VLM 추출 지형을 **Region 승격(case2, 인제스터)** + **이름 오추출 병합(case1, OntologyBuilder)**으로 연결해 orphan 제거.
- 2 Unit(A: 모델·위키 구조 / B: 인제스션 연결), 웹 UI 제외.
