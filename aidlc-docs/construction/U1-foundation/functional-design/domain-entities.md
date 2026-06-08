# U1 Foundation — Domain Entities & Graph Schema

기술 무관 도메인 스키마. 결정 반영: FD1-Q1=A(world_id 파티션) · Q2=A(UUID+유니크) · Q3=A(SCOPED_TO 관계+상속 순회) · **Q4=B(별도 `:Rumor` 라벨)** · Q5=A(Knowledge+Entity+WikiPrior 색인) · Q6=A(표준).

## Partitioning
- 모든 노드는 `world_id` 속성 보유. 가상 세계는 고유 id, 실세계 Wiki는 예약 id **`__realworld__`**.
- 교차 비교/매칭은 world_id 필터로 수행. (FD1-Q1=A)

## Node Labels

### :World  *(메타)*
`world_id`(PK), `name`, `kind`(`game`|`realworld`), `created_at`.

### :Region
`id`(UUID,PK), `world_id`, `name`, `level`(`continent`|`province`|`town`|`district`), `description`, `attributes`(json: 지형 유형 등), `source`, `provenance`.
- 유니크: `(world_id, level, natural_key)`.

### :Entity  *(장소·인물·사건·사물·관습·지형)*
`id`(UUID,PK), `world_id`, `name`, `entity_type`(`place`|`person`|`event`|`object`|`custom`|`terrain`), `description`, `confidence`(0~1), `source`, `provenance`, `embedding_ref`.
- 유니크: `(world_id, entity_type, natural_key)`.

### :Knowledge  *(지식 항목/사실)*
`id`(UUID,PK), `world_id`, `statement`, `topic`, `confidence`(0~1, 기본/원본), `source`(`input`|`inferred-wiki`|`augmentation`), `provenance`, `embedding_ref`.

### :Rumor  *(왜곡 변형 — Q4=B)*
`id`(UUID,PK), `world_id`, `statement`(변형된 내용), `distortion_note`, `confidence`(0~1), `source`, `provenance`, `embedding_ref`.
- 항상 하나의 원본을 `DISTORTED_FROM`으로 참조(:Knowledge 또는 :Rumor).

### :WikiPrior  *(실세계 prior — world_id=`__realworld__`)*
`id`(UUID,PK), `prior_type`(`terrain_rule`|`climate`|`logistics`|`fact`), `condition`, `effect`, `description`, `confidence`, `provenance`, `embedding_ref`.
- 예: `condition="두 지역 사이 산맥"`, `effect="연결 강도 0.3배, 정보 전파 지연"`.

## Relationships

| 관계 | from → to | 속성 |
|---|---|---|
| `:CONTAINS` | Region → Region | (계층 트리) |
| `:CONNECTED_TO` | Region → Region | `weight`(0~1), `kind`(`adjacent`\|`route`\|`river`\|`blocked`), `rationale`, `wiki_prior_ref?`, `source` |
| `:SCOPED_TO` | Knowledge\|Rumor → Region | `confidence`(0~1), `scope_type`(`direct`\|`inherited`\|`propagated`) |
| `:ABOUT` | Knowledge\|Rumor → Entity | — |
| `:RELATED_TO` | Entity → Entity | `relation_type`, `confidence`, `source` |
| `:DISTORTED_FROM` | Rumor → Knowledge\|Rumor | `distortion_degree`(0~1) |
| `:DERIVED_FROM` | Knowledge\|Region\|CONNECTED_TO → WikiPrior | `rationale` (고증/가중 근거, FR-C3/B3) |
| `:LOCATED_IN` | Entity → Region | (엔티티의 소속 지역) |

- 계층 상속(FD1-Q3=A): 특정 Region 쿼리 시 `SCOPED_TO`(direct) + 조상 `CONTAINS` 경로의 지식을 `inherited`로 합산.

## Search Index (OpenSearch, FD1-Q5=A)
색인 대상: **:Knowledge, :Entity, :WikiPrior** (+ 일관성을 위해 :Rumor도 동일 색인 — Q4=B 보완, 검색 시 `is_rumor` 필드로 구분).
`SearchDoc`: `id`, `world_id`, `label`, `text`(name/statement+description), `embedding`(vector), `meta`.

## Pydantic Models (`locus/models/`)
- 그래프: `World`, `Region`, `ConnectionEdge`, `Entity`, `Relation`, `Knowledge`, `Rumor`, `WikiPrior`, `ScopeLink`.
- 공통: `Provenance`(source, generated_by, refs, note), `EntityType`/`RegionLevel`/`ScopeType`/`PriorType`(Enum).
- 집계/IO: `IngestionResult`, `RegionTopology`, `KnowledgeGraph`, `ConsensusView`, `QueryResult`, `RegionDiff`, `SearchDoc`, `SearchHit`.
- 보강(차순 U7): `AugmentationQuestion`, `AugmentationAnswer`, `Issue`, `ChangeSet`.
- 모두 Pydantic v2, `model_config = ConfigDict(frozen=False, extra="forbid")`, 직렬화 round-trip 보장(PBT 대상).
