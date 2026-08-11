# U-H2 Fixes — Business Rules

> BR-H2-*. 소규모 독립 3건. 최소 침습·가산; 정상 경로 회귀 0.

| ID | 규칙 |
|---|---|
| **BR-H2-1** | `SessionPanel.refresh`는 독립 read(timeline/events/distortions/rumors)를 `Promise.all`로 병렬 로드(왕복 깊이 1). `rumors`는 `regionId`가 있을 때만, 없으면 `[]`. 에러/표시 동작 불변(FR-H6). |
| **BR-H2-2** | `orchestrator.build_world`는 wiki 생성 + `set_wiki`(topology/ontology)를 **topology.build 전**에 수행 → 토폴로지 rationale이 이 월드의 영속 common-sense prior를 반영. LLM=None이면 미주입(기존 가드). 첫 빌드(빈 wiki)는 기존과 동일(FR-H7). |
| **BR-H2-3** | `map_image_ingestor`에서 barrier terrain의 `between != 2`는 조용히 버리지 않고 `IngestionResult.errors`에 skip 경고를 기록(graceful, 하드 실패 아님). `== 2`는 기존대로 연결 힌트, area terrain은 기존대로 Region 승격(FR-H8). |
| **BR-H2-4** | 세 수정 모두 캐노니컬 데이터 모델·세션 레이어 불변. 정상 입력의 산출물 동일(회귀 0); 달라지는 것은 (H7) 재빌드 시 topology의 wiki 반영, (H8) 비정상 barrier의 가시화, (H6) 프론트 지연뿐. |

## 테스트 포인트
- **FR-H6(vitest)**: refresh가 4 API를 병렬 호출(모두 호출됨), regionId 없으면 rumors 미호출·빈 배열,
  에러 시 setError. 기존 SessionPanel 테스트 회귀 0.
- **FR-H7(pytest)**: mock topology/ontology/wiki로 `build_world` 호출 시 `topology.set_wiki`가
  `topology.build` **전에** 호출됨(호출 순서 검증). LLM=None이면 set_wiki 미호출. 기존 orchestrator 테스트 회귀 0.
- **FR-H8(pytest)**: barrier terrain `between`=1/3 입력 → `errors`에 경고 1건, 힌트 미생성; `between`=2 →
  힌트 생성·errors 없음; area terrain → Region 승격 불변.
