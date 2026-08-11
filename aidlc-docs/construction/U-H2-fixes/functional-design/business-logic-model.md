# U-H2 Fixes — Functional Design (Investigation + Fix)

> 소규모 독립 3건(FR-H6/H7/H8). FR-H7/H8은 **조사 우선** — 아래는 코드 조사 결론과 수정 설계.
> 캐노니컬 데이터 모델 불변; 세션 레이어 무관. 전 항목 가산/최소 침습.

## FR-H6 — SessionPanel.refresh 병렬화 (프론트)
**현황**: `web/src/SessionPanel.tsx`의 `refresh()`가 순차 await 4단(timeline → events → distortions →
rumors). 4-deep 워터폴 — 독립 read인데 직렬로 왕복.
```ts
setTimeline(await api.getTimeline(id));
setEvents(await api.listEvents(id));
const dist = await api.listDistortions(id);
if (regionId) setRumors(await api.listRumors(id, regionId));
```
**수정(BR-H2-1)**: 네 read는 상호 독립 → `Promise.all`로 한 번에. `rumors`는 `regionId` 있을 때만
(없으면 `[]`). 에러 처리·표시 불변.
```ts
const [tl, ev, dist, rm] = await Promise.all([
  api.getTimeline(id), api.listEvents(id), api.listDistortions(id),
  regionId ? api.listRumors(id, regionId) : Promise.resolve([]),
]);
```
왕복 깊이 4→1. 표시 결과 동일(같은 데이터, 같은 setter).

## FR-H7 — orchestrator set_wiki 순서 (조사 결론: **실제 결함 → 수정**)
**조사**: `locus/services/orchestrator.py::build_world`
- L68 `topology = self._topology.build(...)` — TopologyBuilder는 `self._wiki`를 사용(`_wiki_rationale`,
  L91: terrain→prior rationale/`SourceKind.INFERRED_WIKI`).
- L95-98 `set_wiki(...)`는 **L68 이후** 호출 → topology.build 시점엔 wiki=None. **토폴로지 rationale에
  common-sense prior가 절대 반영되지 않음**(항상 INPUT). ontology는 L96 set_wiki → L99 build 순서라 정상.
- 순환 주의: priors는 topology에서 distill(L72)되므로 "이번 빌드의 새 priors"는 topology.build 시점에
  아직 없음. 그러나 wiki는 **OpenSearch 영속 priors**를 읽으므로, **이전 빌드/재빌드 시 이미 쌓인
  이 월드의 priors**를 topology가 활용할 수 있어야 함(UOW-CL1 "런타임 우선" 결정과 정합).
**결함 확정**: topology는 영속 wiki를 쓸 수 있어야 하는데 주입이 늦어 항상 못 씀.
**수정(BR-H2-2)**: wiki 생성 + `topology.set_wiki`/`ontology.set_wiki`를 **topology.build 전으로 이동**.
- 이동 후 순서: (a) ingest → (b) wiki 생성 & set_wiki(topology+ontology) → (c) topology.build(wiki 활용) →
  (d) distill priors(이번 빌드 topology 기반) → (e) persist priors → (f) ontology.build → (g) persist.
- 첫 빌드(빈 wiki): topology는 prior 없음 → 기존과 동일(회귀 0). 재빌드/기존 wiki 보유 월드: topology가
  영속 prior 반영 → 결함 해소. LLM=None이면 wiki 미주입(기존 가드 유지).

## FR-H8 — map_image_ingestor barrier terrain 드롭 (조사 결론: **실제 엣지케이스 → 가시화**)
**조사**: `locus/ingestion/map_image_ingestor.py` L59-74
- L60 `if is_barrier_terrain(kind) and len(between)==2:` → 연결 힌트.
- L69 `elif not is_barrier_terrain(kind):` → area terrain → Region 승격.
- **barrier terrain인데 `between != 2`(0/1/3+)** → 두 분기 모두 탈락 → **조용히 소멸**(힌트·경고 없음).
**결함 확정**: FD-B Q1=B 설계(barrier=정확히 두 지역 사이 연결)의 미처리 엣지케이스. 데이터 손실이
조용함 → 진단 불가.
**수정(BR-H2-3)**: `between != 2`인 barrier terrain을 **`IngestionResult.errors`에 경고로 기록**(graceful
degrade와 동일 채널, 하드 실패 아님). 3+ 지역 pairwise 연결로의 규칙 보강은 범위 밖(설계 의도=정확히 2).
최소 침습으로 "조용한 드롭"만 제거.
```python
for t in ex.terrain:
    if is_barrier_terrain(t.kind):
        if len(t.between) == 2:
            hints.append({...})
        else:
            errors.append(f"barrier terrain '{t.name}' ({t.kind}) skipped: "
                          f"expected 2 bordering regions, got {len(t.between)}")
    else:
        ... area terrain ...
return IngestionResult(world_id=world_id, region_hints=regions, errors=errors)
```
(기존 L48 graceful `errors`와 합류. 정상 경로엔 errors 없음 → 회귀 0.)

## 순서 / 독립성
- 세 항목 상호 독립. 코드젠 순서 무관. U-H1(세션 레이어)과 무관.
