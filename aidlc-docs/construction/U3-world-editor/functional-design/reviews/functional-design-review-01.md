## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — U3 월드 에디터
**Reviewed artifact:** `aidlc-docs/construction/U3-world-editor/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-01T07:05:44Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/U3-world-editor/functional-design/business-logic-model.md > §5.1 빌드가 근거를 저장한다 (BR-U3-29, EX-10) | §5.1은 "토폴로지·온톨로지 단계가 쓴 wiki의 created_priors를 증류 prior 목록에 더해" 한 번에 저장한다고 적는다. 그런데 `locus/world/build.py`는 토폴로지 단계를 prepare 구간(delete_world 이전)에서 돌리고, prior를 먼저 persist한 뒤에야 `ontology_builder.build`(코로보레이션, `corroboration.py`가 지역마다 wiki를 조회하고 `derived_from_prior_ids`를 채움)를 commit 구간에서 돌린다. 온톨로지 단계가 만든 폴백 prior는 첫 persist 시점에 존재하지 않으므로 §5.1 순서로는 저장할 수 없다. 저장하지 못하면 `derived_from_edges`의 MATCH가 조용히 실패하고 속성 `derived_from_prior_ids`만 끊긴 채 남는다(A9 그대로). 또 `CommonsenseWiki._lookup`은 검색 miss마다 새 id의 폴백 prior를 LLM으로 만든다(`base.py` _fallback). 토폴로지는 연결 후보마다 조회하므로 중복·유사 prior가 후보 수만큼 쌓일 수 있는데 병합·상한 규칙이 없다. `new_prior_ids` 필터(build.py 212행)가 prepare 구간에서 계산되는 점도 `created_priors`와 어떻게 합쳐지는지 적혀 있지 않다. | 두 단계의 저장 시점을 명시한다(예: 온톨로지 뒤 prior를 한 번 더 persist하고 그 뒤 knowledge를 쓰거나, 폴백 prior를 단계마다 저장). `created_priors`의 중복 병합 키(condition+effect)와 상한을 정한다. 참조를 버리는 조건("옛 월드 prior")을 `new_prior_ids ∪ created` 기준으로 코드 용어로 다시 적는다. EX-10에 지식 쪽(`derived_from_prior_ids`) 경로를 더한다. | New |
| R-02 | Major | aidlc-docs/construction/plans/U3-world-editor-functional-design-plan.md > A3-9 대 business-rules.md > BR-U3-37, BR-U3-3, BR-U3-19 / frontend-components.md > §2.3 NPC 목록 / domain-entities.md > §2.3 | 플랜 A3-9와 unit-of-work U3("에디터의 캐노니컬 지식 번역 표시")는 지식 번역만 말한다. 그런데 BR-U3-37·frontend §2.3·domain-entities §2.3은 NPC 설명의 번역(+원문 토글, `*_ko`)을 요구하고, BR-U3-3·BR-U3-19·BLM §1.6은 NPC 삭제 때 NPC 번역 캐시를 지운다고 한다. 현재 번역 종류는 knowledge, rumor, event, deed, deed_appraisal뿐이고 `kind="npc"`는 어디에도 없다(`api/schemas.py` 203·214·252·274·348, `localization/models.py` 22행). NPC 대화는 번역하지 않는다(A-1, `schemas.py` 주석). 즉 "U5 enrich 재사용"이 아니라 새 번역 종류와 그 워밍(LLM 호출)을 추가하는 일이며, 승인된 unit 범위 밖이고 비용 영향이 있다. 지금 문장대로면 지울 번역 행이 없는 purge가 규칙으로 남는다. | 둘 중 하나를 정한다. (a) NPC 번역을 범위에서 빼고 BR-U3-37·3·19, frontend §2.3, domain-entities §2.3을 지식 번역으로 맞춘다. (b) 새 번역 종류(`npc`: 필드, 키, 워밍, purge 호출 지점)를 설계에 정식으로 넣고 §8 이탈 목록에 올려 사람이 고르게 한다. | New |
| R-03 | Major | aidlc-docs/construction/U3-world-editor/functional-design/domain-entities.md > §4.2 AugmentationAnswer 그대로 / business-logic-model.md > §4.2 dangling edit, §4.1 이슈마다 하나, §4.3 ignore | (1) dangling/edit는 prior id(`wiki_prior_ref`, `derived_from_prior_ids`)나 entity id(`about_entity_ids`)를 새 대상으로 받아야 하는데, `AugmentationAnswer`(`types.py`, extra="forbid")에는 `region_id`뿐이고 domain-entities는 "그대로"라고 한다. `target_id`는 서버가 질문에서 채우고 UI가 보낸 값을 믿지 않는다(BR-U3-25)고 했으므로 새 id를 실을 칸이 없다(frontend §2.5는 "대상 id 선택(dangling-prior)"을 요구). 6개 끊김 속성 중 3개가 표현 불가다. 리스트 속성에서 어느 원소가 끊겼는지도 `QuestionTarget.field`만으로는 모른다. (2) "무시한 이슈는 그 run에서 다시 묻지 않는다"(BR-U3-28)는 이슈 동일성이 필요하다. 그런데 `Issue.id`는 탐지마다 새로 `new_id`이고, `AugmentationRun`에는 이슈·무시 집합 칸이 없다("이슈는 run 안에 둔다"고만 적고 domain-entities §4에 필드가 없음). 안정 키가 없으면 무시가 다음 라운드에 풀린다. (3) `detect_all`은 (type, 정렬된 target_ids)로 중복을 제거하므로, 한 노드에 끊긴 속성이 둘이면 "이슈마다 하나"(BLM §4.1)가 깨진다. | `AugmentationAnswer`에 새 참조 칸(예: `ref_id`)을 정의하고 BR-U3-25와 맞춘다. 이슈 안정 키(type+target+field)를 정하고 `AugmentationRun`에 무시 집합·이슈 보관 필드를 domain-entities §4.3에 더한다. dedup 키에 field를 넣는다고 명시한다. | New |
| R-04 | Major | aidlc-docs/construction/U3-world-editor/functional-design/business-rules.md > BR-U3-28 / business-logic-model.md > §4.3 run | BR-U3-28은 "한 run 최대 5라운드, 라운드마다 질문 최대 20개"를 "그대로"라고 적는다. 그러나 `service.py`의 `round`는 답 한 번마다 +1이고 `round >= max_rounds`이면 STOPPED로 바꾸며 `open_questions`를 비운다. B2를 고쳐 run을 유지하면 제작자는 run 하나에서 질문 20개를 보고도 5개만 답할 수 있고, 이는 US-2.6("빈틈을 채운다")과 AugmentPanel의 "다음 질문" 흐름에 맞지 않는다. 이전에는 답마다 새 run을 열어 이 한계가 가려져 있었다. 또 STOPPED·CONVERGED run에서 되돌리기를 하면 "다시 탐지해 질문을 고친다"는 문장만 있고 status가 OPEN으로 돌아오는지 규칙이 없다(BLM §4.3). 개발자가 라운드의 뜻을 추측해야 한다. | "라운드"를 정의한다(답 한 번인지, 질문 묶음 한 번인지). 상한이 의도라면 5답 상한을 화면 문구와 US-2.6 검증 기준에 쓰고, 아니면 상한을 라운드 단위로 바꾼다. 되돌리기 뒤 run status 전이(STOPPED, CONVERGED에서 OPEN으로)를 상태 표로 적는다. | New |
| R-05 | Minor | aidlc-docs/construction/U3-world-editor/functional-design/business-logic-model.md > §4.1·§4.3 (질문 다듬기, 다시 탐지) | `generate_questions`는 이슈마다 LLM을 한 번씩 부르고(`questions.py`), `detect_wiki_conflicts`는 직접 스코프마다 LLM을 부른다(`detectors.py`). 이 둘이 시작·답마다·되돌리기마다 전부 다시 돈다. 질문 20개 상한은 있으나 호출 수 상한이 없어 답 하나에 수십 번의 순차 LLM 호출이 동기 HTTP 안에서 일어날 수 있다(NFR-5 LLM 비용, NFR-3 응답성). | 라운드당 LLM 호출 상한 또는 질문 문장 캐시(이슈 안정 키별)를 정하거나, NFR-light로 넘긴다고 명시하고 이월 목록에 올린다. | New |
| R-06 | Minor | aidlc-docs/construction/U3-world-editor/functional-design/business-rules.md > BR-U3-23 / business-logic-model.md > §4.2 dangling/remove | `NPC.home_region_id`를 dangling 대상으로 든다. 그러나 `locus/knowledge/loader.py`는 `home_region_id`가 지역에 없는 NPC를 스냅샷에서 버리고(`"NPC home region"` 경고만) LIVES_IN으로 값을 덮어쓴다. 탐지기가 읽는 `kg`·`topo`에는 NPC가 없다(`detect_all(kg, topo)`). 이 경우는 스냅샷 위 순수 탐지로 볼 수 없고 "home_region_id는 비울 수 없어 NPC를 지운다" 분기는 도달하지 않는다. | NPC를 dangling 대상에서 빼거나(로더 경고로만 처리), 탐지기 입력에 NPC 원본 노드 읽기를 추가하는 변경을 명시한다. `detect_gaps`의 옛 relation-dangling 분기를 없애는지도 적는다. | New |
| R-07 | Minor | aidlc-docs/construction/U3-world-editor/functional-design/domain-entities.md > §8 설계 이탈 (완결 목록) | §8은 "완결 목록"이라 하지만 `component-methods.md`와 다른 계약이 더 있다. `upsert_connection`은 ConnectionEdge 단건이 아니라 list를 돌려주고, `delete_connection(world_id,a,b)`가 ConnectionKey로, `delete_region(..., cascade: CascadePolicy) -> DeleteReport`가 `protected`·`RegionDeleteReport`로, `upsert_knowledge(k, scope_region_ids)`가 `create_knowledge`로 나뉘고, `NpcDraftService.suggest -> list`가 `draft -> NpcDraftResult`로, `WikiAdmin.prior_refs`가 `prior_usage`·`broken_refs`로, `WorldInfo`가 `WorldSummary`로, `AugmentationRun.questions`/`options`가 `open_questions`/`actions`로 바뀐다. unit-of-work의 `UploadPanel`도 `BuildPanel`이 된다. | §8에 이 변경들을 올려 "완결"을 사실로 만들거나, 해당 상위 산출물이 이름만 다르다고 한 줄로 정리한다. | New |
| R-08 | Minor | aidlc-docs/construction/U3-world-editor/functional-design/business-logic-model.md > §4.3 revert, business-rules.md > TP-U3-4 | 되돌리기는 run의 임의 변경을 고를 수 있다(`change_id`). 같은 노드를 두 변경이 바꾼 뒤 앞의 변경을 되돌리면 뒤 변경의 결과까지 `nodes_before`로 덮인다. LIFO 강제 여부, 뒤 변경과 충돌할 때의 동작이 없고 TP-U3-4는 "적용 한 번 뒤 되돌리기"만 다룬다. run 저장소는 `InMemoryRunStore`뿐이라 재시작이나 다중 워커에서 `GET runs/{id}`·답·되돌리기가 404가 되는데 이 한계가 적혀 있지 않다. | 되돌리기를 최신 변경부터만 허용하거나 충돌 규칙을 적고, TP-U3-4를 변경 둘 이상으로 넓힌다. in-memory run의 수명 한계를 BR 또는 NFR 이월에 기록한다. | New |
| R-09 | Minor | aidlc-docs/construction/U3-world-editor/functional-design/business-logic-model.md > §2 열린 세션 확인, §1.4 종류 변경 | (1) 삭제 보호 확인과 `delete_region` 사이에 플레이어가 그 지역으로 이동하거나 턴이 도는 경쟁이 있다. 같은 라우터 파일의 `_open_sessions`는 교체 때 `play.guard.is_running`을 미리 보지만 §2는 이 확인이 없다. (2) 연결 종류 변경을 "옛 키 삭제 + 새 키 추가" 두 호출로 보내므로 두 번째가 실패하면 연결이 사라진다. 이때 `rationale`·`wiki_prior_ref`·`provenance`를 새 키로 옮기는지도 적혀 있지 않다. | (1) 진행 중 턴이 있는 세션을 어떻게 다루는지(보호 집합에 포함 또는 409) 한 줄 규칙으로 정한다. (2) 종류 변경용 단일 연산(`ConnectionKey` 옛 키 + 새 `ConnectionEdge`)과 보존 필드를 정한다. | New |
| R-10 | Minor | aidlc-docs/construction/U3-world-editor/functional-design/frontend-components.md > §2.1 HomePage | [세션 시작]이 `NewSessionForm`을 "그 월드로" 연다고 하지만, 이 폼은 `regions` 목록을 props로 받는다(`features/play/NewSessionForm.tsx`). 홈에는 월드별 지역 목록이 없고, 어떤 API로 읽는지(`export`는 월드 전체)와 시작 호출(`SessionBar.startPlay` 경로)이 적혀 있지 않다. | 지역 목록 출처(경량 API 또는 export)와 세션 시작 호출을 한 줄로 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| BR-U3-1..40, TP-U3-1..6, EX-1..12 ID 해소 | 모두 존재, 번호 순서만 BR-U3-31이 30보다 앞 | 참조는 끊기지 않음 |
| US-2.1..2.8, US-6.2..6.4, FR-B1..B10, FR-F1..F3 해소 | stories.md·requirements.md에 모두 존재, 추적표가 모든 US를 규칙에 연결 | 추적 완전 |
| `editor.py` 현 상태(메서드 셋, 74줄) | 일치(upsert_region, upsert_knowledge, delete_node) | 플랜 표 정확 |
| `neo4j_repo.upsert_nodes`가 `SET n += props`이고 `_flatten`이 None을 뺀다 | 확인 | A3-1 교체 쓰기 필요성이 근거 있음 |
| `topology/builder.py`가 연결을 양방향 한 쌍으로 만든다 | 확인 | A3-3·BR-U3-10이 기존 데이터와 맞음 |
| `loader.py`의 NPC·연결·스코프 끊김 처리 | NPC는 스냅샷에서 버려짐 | R-06 |
| `build.py` 단계 순서(토폴로지 prepare, prior persist, 온톨로지 commit) | §5.1 순서와 충돌 | R-01 |
| `localization` 번역 종류 grep | npc 종류 없음 | R-02 |
| `augmentation/service.py`·`types.py`·`detectors.py`·`questions.py` | round=답 1회, Issue.id 매번 신규, 답 모델에 참조 칸 없음 | R-03, R-04, R-05 |
| `distortion_service.set_region_distortion`·U7 BR-U7-5·code-review-01 §5·§8 | 설계 메모 1과 BR-U3-38이 일치, EX-12 산술 일치 | Q6 이월은 정합. UoW 사용은 `PlayRepository.uow`가 있어 가능 |
| `TOPOLOGY_DEFAULT_BASE` 사용처 | settings 환경 변수는 기본값과 병합되고 모르는 kind는 거부됨 | A3-15 제거는 안전. 호출 지점(weights.py, tuning.py, settings.py, env.example, 테스트 2개)은 코드 계획에서 열거 필요 |
| component-methods.md W4~W8 시그니처 대조 | 다수 이름·반환형 변경 | R-07 |
| MapOverlay·RegionPanel·App.tsx 현 상태 | 설계 설명과 일치(드래그 즉시 저장, 루트 리다이렉트, GM의 RegionPanel ✕) | 프런트 현황 표 정확 |

### Summary

NOT-READY: Critical 0건, Major 4건(R-01~R-04)으로 기준(Major 2건 초과)에 걸린다. 규칙 ID·스토리·요구 추적과 지역 삭제 cascade 순서, 양방향 연결, Q6 이월은 코드와 상위 산출물에 대조해 정합하다. 막히는 곳은 세 군데다. 첫째, 빌드의 prior 저장은 build.py의 실제 단계 순서(온톨로지가 prior persist 뒤에 돈다)와 맞지 않고 중복 규칙이 없다. 둘째, NPC 번역은 승인된 unit 범위와 플랜 A3-9를 벗어나 새 번역 종류를 암묵적으로 들인다. 셋째, 보강 Q&A는 dangling 수정 답을 실을 칸, 무시 이슈의 안정 키, 5라운드 상한의 뜻이 정해지지 않아 구현자가 추측해야 한다.

제안(차단 아님): WorldEditor가 지역·연결·지식·스코프·NPC·엔티티·월드 목록·삭제 계획까지 약 20개 메서드를 맡는다. 프로젝트의 "기능별 단일 책임 클래스" 선호에 비추어 코드 계획에서 RegionOps·ConnectionOps·KnowledgeOps 등 협력 클래스로 나누는 것을 고려한다. 지식 PUT은 전체 모델 교체라 낡은 폼이 보강 답의 신뢰도를 덮어쓸 수 있으나 MVP 단일 사용자 가정(인증 없음)이라 이월로 충분하다.
