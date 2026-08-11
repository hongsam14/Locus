# Unit-A (Model & Wiki Structure) — Functional Design Plan

영역 1(real_world 삭제+교차참조) + 영역 2(WikiPrior 커뮤니티) + 영역 3(Knowledge.title).
요구사항: `mvp-improvements-requirements.md` FR-IM1.*, FR-IM2.*, FR-IM3.*.

## Functional Design 작업 체크리스트
- [x] 도메인 엔티티 변경 설계 (`domain-entities.md`): Knowledge.title, WikiPrior(world_id+domains), WikiDomain enum, WikiPriorLink, World 미영속(CL-A1=A)
- [x] 비즈니스 로직 모델 (`business-logic-model.md`): 범용 PriorDistiller(+도메인 분류), WikiPriorLinker(임베딩+LLM), 빌드 통합, CrossWorldWikiExplorer(기획자 전용), 제거 리팩터링
- [x] 비즈니스 규칙 (`business-rules.md`): BR-A1~A16 (title 필수/fallback, 도메인, 엣지 가드, NPC 단일-world 불변식, read-through, 제거 불변식)

---

## 설계 확인 질문 (남은 결정 사항)

> 요구사항 단계에서 대부분 확정됨. 아래는 Unit-A 구현 설계가 갈리는 잔여 결정입니다.

### FD-A Q1 — World 노드 영속화 & 도메인 태그 인덱스
현재 `World` 모델은 있으나 그래프에 저장되지 않습니다. 교차참조(도메인 태그가 겹치는 다른 world 탐색)를 하려면 world 메타데이터를 조회 가능하게 저장해야 합니다. 어떻게 할까요?

A) **World 노드를 그래프에 영속화** — 빌드 시 `World{world_id, name, kind, domain_tags[]}` 노드를 upsert. 교차참조 시 "내 도메인 태그와 겹치는 World 노드"를 조회해 대상 world_id 목록을 얻음
B) World 노드 + 별도 도메인 인덱스(예: 검색엔진에 world-도메인 문서) 둘 다 — 태그 매칭을 검색으로 수행
C) 그래프 영속화 없이, 빌드 시 계산한 world↔도메인 매핑을 호출자가 파라미터로 주입 (저장 안 함)
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 도메인은 태그로서 존재하고, 월드 구분없이 도메인 태그로서 글로벌하게 검색해서 탐색하겠다는거지 world 노드 (그래프 노드일 이유가 별로 없는) 데이터를 추가하는게 맞는지?

### FD-A Q2 — 교차참조 wiki lookup 동작 방식
`CommonsenseWiki`가 현재는 단일 `world_id` 파티션만 검색합니다(`hybrid_search(world_id=...)`). 교차참조 시 어떻게 여러 world의 WikiPrior를 검색하나요?

A) **다중 world 검색** — lookup이 `[현재 world] + 도메인 겹치는 참조 world들`의 각 파티션을 검색해 결과 병합(현재 world 우선, 점수순)
B) lookup은 현재 world만 검색하되, 빌드 시점에 참조 world의 prior를 **인덱스에 교차 태깅**해 한 번에 검색되게 함 (read-through 위배 → 비권장)
C) 단일 합성 쿼리 — 검색 필터를 `world_id IN [...]`로 확장 (어댑터가 다중 world_id 지원하도록)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 하지만 npc 정보 생성을 위해서 검색을 할땐 다중 world이면 안되고, 기획자를 위해서만 필요한 기능임.

### FD-A Q3 — WikiPrior 간 엣지의 범위 (world 경계)
WikiPrior 간 직접 엣지(커뮤니티/cross-domain)는 어느 범위에서 생성하나요?

A) **world 내부만** — 각 world의 prior 집합 안에서만 엣지 생성. 교차참조는 lookup 시점 read-through로 처리(엣지는 world를 넘지 않음)
B) world를 넘어서도 — 도메인 겹치는 다른 world의 prior와도 엣지 연결 (그래프가 world 경계를 넘는 엣지를 가짐)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-A Q4 — 도메인(taxonomy)의 표현
WikiPrior의 도메인(공유 taxonomy)을 코드에서 어떻게 표현하나요?

A) **고정 Enum** — 미리 정한 도메인 집합(예: geography/geology/climate/economy/logistics/culture/history/politics)을 enum으로. LLM이 이 중 선택
B) **개방형 문자열 태그** — `domains: list[str]` 자유 문자열. LLM이 제안하고 사용자가 편집(고정 목록 강제 안 함). 권장 어휘는 프롬프트로 가이드
C) 하이브리드 — 권장 enum + 자유 태그 허용(둘 다 list[str]에 저장)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-A Q5 — WikiPrior 엣지의 모델/방향성
엣지를 어떻게 모델링하나요?

A) **전용 레코드 `WikiPriorLink`(source_id, target_id, relation: str, weight, provenance)** — 그래프엔 엣지로만 저장(노드 없음). 무방향(저장은 단방향, 의미상 대칭)으로 단순화
B) 방향성 있는 typed 엣지 — LLM이 방향/관계유형 판정(예: "A가 B의 원인")을 보존
C) 기존 `Relation` 모델 재사용 (entity용이지만 prior에도 적용)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-A Q6 — Knowledge.title 검색 반영
`title`을 하이브리드 검색 텍스트(`knowledge_doc.text`)에 포함하나요?

A) 예 — title도 검색 텍스트에 포함(제목 키워드로도 검색되게)
B) 아니오 — title은 표시/식별용, 검색 텍스트는 statement(+topic) 유지
X) Other (please describe after [Answer]: tag below)

[Answer]: A
