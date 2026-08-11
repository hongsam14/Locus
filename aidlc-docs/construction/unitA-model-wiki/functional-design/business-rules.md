# Unit-A — Business Rules (Functional Design)

| ID | 규칙 | 출처 |
|---|---|---|
| **BR-A1** | `Knowledge.title`은 필수이며 비어 있지 않다. 모든 생성 경로(ingestion/corroboration/augmentation)가 채운다. | FR-IM3.1/3.3, Q11=B |
| **BR-A2** | title은 LLM이 생성한다. LLM이 비우면 `statement` 앞부분(≈60자, 단어 경계)으로 fallback하여 BR-A1을 항상 만족시킨다. | FR-IM3.2, Q10=A |
| **BR-A3** | title은 Knowledge 하이브리드 검색 텍스트에 포함된다(`text = title + statement + topic`). | FD-A Q6=A |
| **BR-A4** | `WikiPrior`는 `world_id`로 소속 world 파티션에 저장된다. 예약 파티션(`__realworld__`)은 존재하지 않는다. | FR-IM1.2, Q4=B |
| **BR-A5** | `WikiPrior.domains`는 `WikiDomain` enum에서 1개 이상. distill 시 LLM 분류, authoring에서 사용자 편집. 분류 실패 시 `[OTHER]`. | FR-IM2.1/2.2, CL2=C, FD-A Q4=A |
| **BR-A6** | `WikiPriorLink`(엣지)는 **같은 world의** prior 사이에서만 생성한다. world 경계를 넘지 않는다. | FD-A Q3=A |
| **BR-A7** | 링크 생성은 임베딩 top-k 후보로 한정한 뒤에만 LLM을 호출한다(전수 O(n²) LLM 호출 금지). | NFR-IM4, req Q6=C |
| **BR-A8** | 링크 `weight`는 [0,1]; threshold 미만은 폐기. 무방향 중복 제거. | FD-A Q5=A |
| **BR-A9** | **NPC 경로 단일 world 불변식**: 빌드 corroboration과 런타임 QueryEngine은 **현재 world의 WikiPrior만** 사용한다. 교차참조를 절대 끌어오지 않는다. | CL-A2=A, FD-A Q2=A |
| **BR-A10** | 교차참조(글로벌 도메인 검색)는 **read-through 전용**: 다른 world prior를 복사/물질화하지 않으며 현재 world에 쓰지 않는다. 기획자 조회 결과로만 반환(출처 world_id 포함). | Q3=A, CL-A2=A |
| **BR-A11** | world의 도메인 태그는 그 world의 WikiPrior `domains` 합집합으로 **필요 시 계산**한다. World 그래프 노드는 영속화하지 않는다. | CL1=A, CL-A1=A |
| **BR-A12** | 각 world의 WikiPrior는 build-world 시 그 world의 ingestion에서 자동 증류되며, authoring으로 추가/편집 가능하다. | FR-IM1.3, CL3=C |
| **BR-A13** | **제거 불변식**: 코드/문서/테스트/예제에 `__realworld__`·`REALWORLD_WORLD_ID`·`load_bundled_realworld`·`realworld_sample`·`World.kind=="realworld"` 참조가 남지 않는다. | Q4=B, Q15=B |
| **BR-A14** | prior 증류·링크·title 생성 등 모든 LLM/임베딩 단계는 graceful: 실패 시 해당 항목 생략(또는 fallback)하고 빌드를 중단하지 않는다. | 기존 graceful 컨벤션 |
| **BR-A15** | 모든 신규 생성물(WikiPrior/WikiPriorLink/Knowledge)은 `Provenance`를 보존한다. | 기존 BR-7 |
| **BR-A16** | 모든 외부 I/O(글로벌 검색 포함)는 기존 포트(Graph/Search/LLM/Embedding) 뒤에 둔다. 오프라인 테스트는 mock으로 동작. | NFR-IM1/3 |

## 검증/엣지 케이스
- title 누락 LLM 응답 → BR-A2 fallback.
- domains 빈 응답 → `[OTHER]`(BR-A5).
- 임베딩 provider 없음 → 링크 생성 생략(BR-A14), 빌드 성공.
- prior 1개뿐 → 링크 후보 없음 → 링크 0개(정상).
- 교차참조 호출 시 다른 world에 prior 없음 → 빈 결과(정상).
- world에 prior 없음 → world_domains = 공집합 → 교차참조 빈 결과.
