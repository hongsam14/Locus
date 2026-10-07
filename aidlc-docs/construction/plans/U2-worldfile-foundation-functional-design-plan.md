# U2 World File·캐노니컬 기반 — Functional Design Plan

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지는 것을 겪는 솔로 TRPG.
**지금 하는 것**: U2 — 플레이와 에디터가 함께 딛는 캐노니컬 기반(NPC 모델, World File 저장·로드, 스냅샷 캐시, 빌드 결함 A1·A2·A3·A4·A7·A8·A11·A13 수정)의 업무 논리 설계. 이 단계가 정하는 것은 "월드가 파일과 그래프 사이를 어떻게 오가고, 빌드가 무엇을 보장하는가"다.

근거: `inception/application-design/purpose-restructure/{unit-of-work,component-methods,services}.md`(U2 절, S1·S4·K3·K4·K5·W1·W2·W3·W6·W9·W10·A4·A5), 요구사항 FR-B1·B3·B4·B5·B8·B9·B10·F1·D2·NFR-2·NFR-3·NFR-9, 스토리 US-2.7·6.2·6.3(주) + US-1.3·2.1·2.3·2.4·2.6·6.4·5.2(백엔드 부분), RE `code-quality-assessment.md` A1~A13.

## Plan (답을 받은 뒤 만드는 산출물)
- [x] `construction/U2-worldfile-foundation/functional-design/domain-entities.md` — `NPC`, `WorldMeta`, `WorldSnapshot`, `WorldFile` v1, `ImportReport`, `BuildReport` 확장, `RegionBrief`, `BuildWarning.severity`
- [x] `construction/U2-worldfile-foundation/functional-design/business-logic-model.md` — 빌드 파이프라인(교체·병합·해석·리포트), World File export/import, 캐시, 데모 로드, `region_briefs`, 로더 재독(NPC·관계)
- [x] `construction/U2-worldfile-foundation/functional-design/business-rules.md` — BR-U2-*(병합 보존, id 재매핑, 결정적 해석, 버전 검사, 교체·세션 정책, ok 판정, 캐시 무효화) + Testable Properties(PBT-02/03/07)
- [x] Plan Review(architecture-reviewer, adversarial ≤ 2) → 리뷰 기록 `construction/U2-worldfile-foundation/functional-design/reviews/functional-design-review-NN.md`
- [x] 완료 메시지 + 승인 게이트

프론트 컴포넌트 문서는 만들지 않는다(U2는 `web/src/api/world.ts`의 호출 함수만 더한다; 화면은 U3).

---

## Functional Design Questions (FD-U2)

`[Answer]:`에 알파벳. 권장안은 맨 앞. 답을 대화창에서 주셔도 된다.

### FD-U2 Q1 — World File의 id 규칙과 옛 export 파일 수용
**배경**: World File v1은 `format_version`, `world{id,name,description}`, 지역·연결·엔티티·관계·지식·스코프·prior·prior_link·NPC를 담는다(AD W9). 저장→로드→저장이 같아야 한다(PBT-02). 그런데 Neo4j 제약은 `id` 전역 유일이라, 같은 파일을 두 world_id에 불러오면(데모를 world A와 B에 각각) id가 충돌한다. 로더·임포터·데모 로드·PBT 생성기가 이 답에 기댄다.

A. **(권장)** 같은 world_id로 불러올 때는 파일의 id를 그대로 쓰고, 다른 world_id로 불러올 때는 모든 id를 결정적으로 재매핑한다(`uuid5(target_world_id, old_id)`, 참조 전부 재작성). `format_version`이 없는 옛 export JSON은 v0으로 보고 메타를 기본값(name=world_id)으로 채워 받아들인다 — 왕복 동일성은 같은 world_id에서 성립하고, 교차 로드는 한 번 재매핑된 뒤 안정된다. 옛 파일도 열린다. 비용: 재매핑 함수 하나와 테스트.
B. id를 항상 그대로 쓴다 — 단순하지만 같은 파일을 두 월드에 못 넣는다(데모 재사용 불가, 제약 위반 오류). 옛 export는 거절.
C. id를 항상 새로 만든다 — 왕복 동일성이 깨져 PBT-02를 "구조 동일(id 제외)"로 낮춰야 한다.
X. Other (please specify)

[Answer]: A

### FD-U2 Q2 — 월드 메타(이름·설명)의 저장 위치
**배경**: World File의 `world.name/description`과 월드 목록(US-6.4: 이름·지역 수·마지막 수정)을 채우려면 월드 단위 메타가 그래프 어딘가에 있어야 한다. 지금은 월드 노드가 없고(CL-A1=A) U1에서 미사용 `World` DTO를 지웠다. 임포터·에디터(U3)·월드 목록 API가 이 답에 기댄다.

A. **(권장)** `:WorldMeta` 노드 1개(`id = world_id`, name, description, `updated_at`, `format_version`)를 두고 빌드·import·편집이 갱신한다 — 목록과 파일 메타가 채워지고 "마지막 수정"이 가능하다. 비용: 노드 라벨 하나, `delete_world`가 함께 지움.
B. 메타를 저장하지 않고 name=world_id, description 없음 — 파일 메타는 내보낼 때 비고, 목록에 "마지막 수정"이 없다. 되돌리기 쉽다(나중에 A로).
X. Other (please specify)

[Answer]: A

### FD-U2 Q3 — 이름이 같고 레벨이 다른 지역의 해석 규칙 (RE A11)
**배경**: "Riverton" town과 "Riverton" province가 함께 있을 때 부모 이름, 연결 힌트, 지식의 `region_hint`가 어느 쪽에 붙는지가 비결정적이다(`hierarchy.py`·`topology/builder.py`·`ontology/builder.py`의 이름 사전이 마지막 항목으로 덮인다). 규칙이 문서에 있어야 한다(US-2.7). 토폴로지·스코핑·보강 탐지가 이 답에 기댄다.

A. **(권장)** 힌트에 레벨이 있으면 (이름, 레벨) 정확 일치. 없으면 **부모 해석은 자식보다 상위 레벨인 후보 중 가장 가까운 레벨**, **연결·지식 힌트는 가장 구체적인(하위) 레벨** 후보. 동률은 이름·id 순으로 고정하고 경고를 남긴다 — 결정적이고 규칙이 짧다. 비용: 후보 색인을 `name → [regions]`로 바꾸고 규칙 함수 하나.
B. 모호하면 붙이지 않고 경고 + 미해석(지식은 unscoped, 부모는 top-level) — 가장 안전하지만 데모 자료에서 흔한 "같은 이름의 마을/주"가 전부 미해석이 되어 에디터 작업이 는다.
X. Other (please specify)

[Answer]: A

### FD-U2 Q4 — 빌드 `ok` 판정과 경고 등급 (RE A13)
**배경**: 지금 `BuildReport.ok`는 항상 True다. 요구는 "ok가 실제 상태를 반영"(US-2.1)이고 AD는 "ok = errors 없음"까지만 정했다. 무엇이 error이고 무엇이 warning인지가 UI 표시(U3)·CLI 종료 코드·데모 판정에 기댄다.

A. **(권장)** `BuildWarning.severity: warning | error`. **error** = 저장 실패(persist-graph/persist-search), 입력 하나가 통째로 읽히지 않음(깨진 JSON·이미지), 지역 0개. **warning** = 항목 단위 거절, 미해석 힌트, 미해석 지식, 임베딩 실패, 계층 경고. `ok = error 없음`. CLI는 ok가 아니면 종료 코드 1 — 부분 성공은 살리고 UI가 등급별로 보인다.
B. 경고가 하나라도 있으면 ok=False — 단순하지만 데모 자료도 거의 항상 ok=False가 되어 신호가 죽는다.
X. Other (please specify)

[Answer]: A

### FD-U2 Q5 — 데모 World File을 만드는 방법 (FR-B3, US-1.3 메커니즘)
**배경**: 데모 로드는 LLM 0회여야 하므로 패키지 안에 완성된 World File이 있어야 한다. 지금 데모는 메모+지도 원자료라 빌드에 LLM이 필요하다. U2는 메커니즘(`DemoWorlds.list/load`)과 Aldermoor 파일 1개를 만들고, TRPG 규모 콘텐츠(지역 10~15개, NPC, 사건 씨앗)는 U8이 채운다. 데모 테스트·문서·U8 콘텐츠 작업이 이 답에 기댄다.

A. **(권장)** 현재 Aldermoor 자료(지역 5개, 연결 1개, 메모의 사실 몇 개)를 손으로 World File v1로 옮겨 적는다(지식 8~10개, NPC 지역당 1~2명, 결정적·재현 가능). `--demo` 원자료 빌드 경로는 `build_from_sources`로 남긴다 — 커밋된 파일이 곧 테스트 픽스처가 된다. 비용: 작성 시간 약간, LLM 불필요.
B. 운영자가 실제 LLM으로 빌드한 뒤 export한 JSON을 커밋한다 — 내용이 풍부하지만 비결정적이고 API 키가 필요하며, 리뷰하기 어렵다.
X. Other (please specify)

[Answer]: A

### FD-U2 Q6 — `WorldCache` 정책 (NFR-3)
**배경**: 플레이 중 행동마다 Neo4j 전체 로드를 막으려고 `WorldCache.get(world_id)`를 둔다. 무효화는 빌드·import·편집(U3)이 부른다. uvicorn을 여러 워커로 띄우면 워커마다 캐시가 따로 있어 편집 뒤 다른 워커가 낡은 스냅샷을 줄 수 있다. 플레이 서비스(U4~U7)와 배포(U8)가 이 답에 기댄다.

A. **(권장)** 프로세스 메모리 + 명시적 무효화만. 단일 워커 배포를 전제로 문서화(데모 규모) — 가장 단순하고 결정적이다. 비용: 다중 워커는 지원하지 않는다고 적는다.
B. A + TTL(예: 60초) 안전망 — 다중 워커에서도 최대 60초 뒤 맞춰지지만 플레이 중 "방금 편집한 것이 안 보이는" 창이 생긴다.
X. Other (please specify)

[Answer]: A

### FD-U2 Q7 — NPC의 검색 색인과 `traits` 형식 (FR-F1)
**배경**: NPC는 `id, world_id, name, role, home_region_id, description(persona), traits, provenance`로 `:NPC` 노드 + `LIVES_IN` 엣지에 저장한다. OpenSearch 색인은 지식·엔티티·prior만 한다. NPC 대화(U5)는 스냅샷에서 NPC를 읽어 프롬프트에 넣고 검색을 쓰지 않는다. 저장 매핑·World File 스키마·U5 프롬프트가 이 답에 기댄다.

A. **(권장)** NPC는 검색 색인하지 않고 그래프에만 둔다. `traits: list[str]`(짧은 성격 태그, 영어) — 대화 프롬프트에 그대로 들어간다. 비용: 없음. 나중에 색인이 필요하면 추가하기 쉽다.
B. NPC description도 색인한다 — 보강 탐지나 검색에 NPC가 잡히지만 이번 사이클에 쓰는 곳이 없다.
X. Other (please specify)

[Answer]: B

---

## 질문 없이 정하는 것 (가정, 승인 시 함께 확인)
- **A1**: `merge_regions`는 같은 (정규화 이름, 레벨)의 힌트를 합칠 때 `attributes`를 합친다 — 리스트(`adjacent_names`, `connections`)는 합집합, 스칼라(`parent_name`, `terrain_kind`)는 먼저 온 값 유지 + 다르면 경고. 구조화 지도의 연결 후보는 병합 뒤에도 남는다.
- **A2**: `merge_entities`는 `(remapped_entities, id_map)`을 돌려주고, 관계·`about_entity_ids`는 `id_map`으로 다시 잇는다.
- **A3**: `WorldBuilder.build(world_id, inputs, *, replace)`: 월드가 있고 `replace=True`면 `graph.delete_world` + `search.delete_world` 뒤 저장. API는 열린 세션이 있으면 `confirm=true` 없이 409(NFR-9), CLI는 `--force`.
- **A4**: 스코프 못 한 지식은 저장하되 `BuildReport.unscoped_knowledge_ids`에 싣고, 로더가 `scope 없음` 지식을 스냅샷에 남긴다(에디터가 지정, U3).
- **A5/FR-B10**: 로더가 `RELATED_TO`·`LIVES_IN`·`:NPC`를 읽어 `WorldSnapshot(kg(관계 포함), topo, npcs, regions_by_id, npcs_by_region)`을 만든다.
- **A7**: `WorldInputs.map_images`는 base64 문자열 목록(디코드는 수집 서비스), API는 JSON(base64)과 multipart(`/build/upload`) 둘 다 받는다.
- **A8**: `KnowledgeView.title`을 채운다.
- **NFR-5**: `llm_calls`는 LLMProvider를 감싸는 카운터로 빌드 단위로 센다.
- **버전**: `format_version=1`만 지원. 다른 값은 422와 지원 버전 목록. 알 수 없는 필드는 무시(상위 호환).
- **PBT-07**: `tests/world/strategies.py`에 월드 생성기(지역 계층·연결·엔티티·관계·지식·스코프·prior·NPC)를 두고 PBT-02(왕복)·PBT-03(병합 시 힌트·참조 보존)이 쓴다.
- **`region_briefs(world_id, top_k=3)`**: 지역 이름·설명·레벨 경로·확신도 상위 DIRECT 지식 k개. 사건 제안(U7)이 쓴다.
