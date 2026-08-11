# Unit-A — Business Logic Model (Functional Design)

영역 1+2+3의 비즈니스 로직/알고리즘. 기술 비종속.

## 1. Knowledge `title` 생성 (영역 3)
- **추출 경로**(text_ingestor): 추출 스키마(`KnowledgeExtraction`/관련)에 `title` 추가 → LLM이 statement와 함께 title 생성. (FR-IM3.2)
- **corroboration 경로**(CorroborationGenerator): `CorroborationBatch` 항목에 `title` 추가 → 생성된 corroboration knowledge도 title 보유.
- **augmentation 경로**(Unit-B 범위 아님이나 모델 공유): 사용자가 knowledge 추가/수정 시 title 입력/생성.
- **Fallback**(BR-A2): LLM이 title을 비우면 `statement[:60]`(단어 경계 정리)로 채워 **필수 불변식 보장**.
- **검색**: `knowledge_doc.text`에 title 포함(Q6=A).

## 2. PriorDistiller 범용화 (영역 1, FR-IM1.3a)
- `distill(ingestion, topology, *, world_id)` — 실세계 전용이 아니라 **모든 world**에 적용.
- 각 결과 `WikiPrior`에 `world_id=world_id` 설정.
- **도메인 분류 동시 수행**: distill용 LLM 스키마(`PriorSuggestion`)에 `domains: list[WikiDomain]` 추가 → 증류와 도메인 분류를 **한 번의 LLM 호출**로 처리(비용 절감). 비면 `[OTHER]`.
- graceful: 실패 시 `[]`(기존 BR 유지).

## 3. WikiPriorLinker — WikiPrior 간 엣지 생성 (영역 2, Q6=C(req)/FD-A Q5=A)
입력: 한 world의 `list[WikiPrior]`. 출력: `list[WikiPriorLink]`.
1. **임베딩 후보 선정**(NFR-IM4 가드): 각 prior 임베딩 → 코사인 top-k 유사 prior를 후보로(전수 O(n²) LLM 금지, BR-A7). EmbeddingProvider 없으면 링크 생성 생략(graceful).
2. **LLM 판정**: 각 (prior, 후보) 쌍에 대해 LLM이 관계 유무·라벨(`relation`)·강도(`weight`) 판정. 구조화 출력.
3. **필터**: `weight >= threshold`만 채택(BR-A8). 중복(무방향) 제거.
4. `cross_domain` 플래그 = source/target `domains` 교집합 없음.
5. **범위**: 같은 world 내부만(Q3=A). 후보 선정이 도메인 무관 임베딩 기반이라 cross-domain 링크가 자연 형성.
- graceful: LLM/임베딩 실패 시 해당 쌍 생략, 빌드 계속.

## 4. world 빌드 파이프라인 통합 (영역 1)
`PipelineOrchestrator.build_world(world_id, inputs)` 순서 변경:
1. ingest
2. topology
3. **distill priors**(범용 PriorDistiller, domains 포함)
4. **WikiPriorLinker**로 prior 링크 생성
5. **prior + link 우선 영속화**(graph upsert + search index) — corroboration이 검색으로 찾을 수 있도록
6. ontology.build — corroboration이 **현재 world의 wiki만** 조회(BR-A9, 단일 world `CommonsenseWiki`)
7. 나머지 영속화(regions/entities/knowledge/scopes/relations)
- 결과: **모든 게임 world가 자기 자신의 WikiPrior(+링크)를 보유**(FR-IM1.2/1.3). 별도 real-world 빌드 단계 불필요.

### CLI/서비스 영향
- `build-wiki` 명령/`WikiBuilder`는 **제거**(각 world가 build-world 시 자체 prior 증류). authoring으로 prior 추가/편집은 유지.
  - (대안 검토: build-wiki를 build-world의 얇은 별칭으로 둘 수도 있으나, 클린 컷(Q15=B) 우선 → 제거.)
- `CommonsenseWiki`: `world_id` 기본값(`REALWORLD_WORLD_ID`) 제거 → **필수 인자**. NPC 빌드/런타임은 항상 현재 world로 인스턴스화.

## 5. CommonsenseWiki (NPC 경로) — 단일 world 고정 (CL-A2=A)
- lookup(`lookup_terrain_rule`/`lookup_similar`)은 **현재 world 파티션만** 검색(기존 동작 유지, world_id만 게임 world로). 교차참조 없음(BR-A9).
- LLM fallback(미스 시 추론)도 그대로.

## 6. CrossWorldWikiExplorer — 기획자 교차참조 (영역 1, 신규, CL-A2=A)
NPC 경로와 **완전히 분리된** 기획자 전용 조회. 자동 빌드/런타임에 미사용.
- `world_domains(world_id) -> set[WikiDomain]`: 그 world의 WikiPrior domains 합집합 계산(BR-A11, 미저장).
- `search_related_priors(world_id, query=None, k) -> list[WikiPrior]`:
  1. `domains = world_domains(world_id)`
  2. **전 world 글로벌 검색**: WikiPrior 대상, `domains` 겹치는 것, (query 있으면) 하이브리드 유사도. world 구분 없음.
  3. 현재 world 결과는 제외(또는 표시 분리) → 다른 world의 상식만 반환.
  4. **read-through만**: 복사/물질화 없음(Q3=A, BR-A10). 반환 prior는 출처 world_id 포함.
- 노출: authoring API(예: `GET /worlds/{world_id}/related-priors`) + 선택적 CLI. NPC 데이터에 섞이지 않음.

### 글로벌 검색 구현 노트(포트 영향)
- `SearchRepository.hybrid_search`의 `world_id`를 `str | None`로 확장(None=전 world) **또는** 도메인 필터 가능한 전역 검색 메서드 추가. 어댑터(OpenSearch)는 world_id 미지정 시 파티션 필터 생략, `domains` 필터 적용.
- 그래프 폴백: `GraphRepository`에 도메인 기준 전역 WikiPrior 조회가 필요하면 추가(검색 우선).

## 7. 제거 리팩터링 (영역 1)
- `REALWORLD_WORLD_ID`, `load_bundled_realworld`, `bundled.py`, `examples/realworld_sample/` 삭제.
- `commonsense_wiki/base.py`·`builder.py`·`admin.py`·`distiller.py` 문서/시그니처에서 realworld 가정 제거.
- `WikiAdmin.upsert_prior(prior)`/`list_priors()` → **world_id 명시 인자**로 변경.
- `api/main.py`·`routers/authoring.py`·`__main__.py` 와이어링 갱신.
