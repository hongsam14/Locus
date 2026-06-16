# S2 (Rumor Engine) — Business Logic Model (Functional Design)

Unit **S2**. RumorGenerator(LLM) · PromotionPolicy(순수) · GameMasterService(턴 오케스트레이터) · SessionQueryEngine(캐노니컬+세션 오버레이) + 세션 API 확장 + 와이어링.
확정 답: FD-S2 Q1=A / Q2=direct+propagated+세션Rumor / Q3=A / Q4=A / Q5=A / Q6=A / Q7=A.
의존(무변경 재사용): `WorldLoader`, `ConsensusEngine`, `QueryEngine`/`canonical_known`, `LLMProvider`, S1 `SessionRepository`/모델.

---

## 1. RumorGenerator (`locus/session/rumor_generator.py`)

```python
class RumorGenerator:
    def __init__(self, llm: LLMProvider) -> None: ...

    def generate_chain(
        self, *, source_text: str, source_id: str, source_kind: str,
        source_confidence: float, region_id: str, session_id: str,
        degrees: list[float],
    ) -> list[SessionRumor]:
        ...
```
- degree 오름차순 체인. 단계별:
  - `prev_text` = step0이면 `source_text`, 이후엔 직전 단계 `statement`(Q3=A 텍스트 계보).
  - LLM 호출 → `RumorDraft.statement`(프롬프트에 degree 명시: degree↑ = 세부변경→과장→부분오류→거의 허구, FR-R2.4).
  - `distorted_from_id/kind` = step0 → `source_id/source_kind`; step i>0 → 직전 SessionRumor `id`/`"rumor"`.
  - `confidence` = `source_confidence * (1 - degree[i])` (FR-R2.6).
  - `support` = 0.0, `promoted` = False (Q5=A).
- **graceful(NFR-R4)**: 한 단계 LLM 실패 → 그 단계와 이후 단계 중단(체인은 직전 텍스트에 의존), 성공한 앞 단계만 반환. 호출자(GameMaster)가 부분 결과를 저장·기록.
- LLM 외 순수 계산(degree/confidence)은 분리되어 테스트 가능.

## 2. PromotionPolicy (`locus/session/promotion.py`, 순수)

```python
DEFAULT_PROMOTION_THRESHOLD = 0.6

def evaluate(rumors: list[SessionRumor], threshold: float = DEFAULT_PROMOTION_THRESHOLD) -> PromotionResult:
    promoted = [r.id for r in rumors if r.support >= threshold and not r.promoted]
    demoted  = [r.id for r in rumors if r.support <  threshold and r.promoted]
    return PromotionResult(promoted_ids=promoted, demoted_ids=demoted)
```
- 순수 함수. **전이만** 산출(이미 승격+여전히 충족 → 변화 없음). PBT 대상(NFR-R5): support≥threshold ⟺ 승격 후보; 멱등; 경계값 threshold 포함.

## 3. GameMasterService (`locus/session/game_master.py`) — 턴 오케스트레이터

```python
class GameMasterService:
    def __init__(self, repo: SessionRepository, generator: RumorGenerator,
                 loader: WorldLoader, params: ConsensusParams = DEFAULT_PARAMS) -> None: ...
```
협력: SessionRepository(영속), RumorGenerator(LLM), `WorldLoader`+`ConsensusEngine`(캐노니컬 소스 읽기 — read-only), PromotionPolicy(순수).

### 3.1 generate_rumors(session_id, region_id, *, degrees=None) -> list[SessionRumor]
1. 세션 확인(없으면 LookupError) · 세션 OPEN 아니면 거부(BR-S2-9).
2. 리전 distortion `d` = `repo.get_region_distortion(session_id, region_id)`(S1이 0.3 시드). degrees 미지정 시 `[f*d for f in DEFAULT_CHAIN_FRACTIONS]`(Q1=A).
3. **소스 수집(Q2)**: `WorldLoader.load(world)` + `ConsensusEngine.resolve(region)` →
   - `view.direct`(direct Knowledge) + `view.propagated`(원거리 전파 지식) → 각각 `(text=statement, id=knowledge_id, kind="knowledge", conf=confidence)`.
   - `repo.list_rumors(session_id, region_id)`(기존 세션 Rumor) → `(text=statement, id=rumor.id, kind="rumor", conf=confidence)`.
4. 각 소스마다 `generator.generate_chain(...)` → 체인 생성. 모든 결과를 `repo.upsert_rumor`.
5. `append_timeline(GENERATE, summary, payload={"rumor_ids":[...], "source_ids":[...], "region_id":...})`(현재 turn). LLM 부분 실패 시 부분 ids + `payload["skipped"]` 기록(graceful).
6. 반환: 생성된 SessionRumor 목록.

### 3.2 regenerate_region(session_id, region_id) -> list[SessionRumor]
- Q4=A: `repo.list_rumors(session_id, region_id)` 전부 `delete_rumor`(승격 포함) → `generate_rumors(...)` 재호출 → `append_timeline(REGENERATE, payload={"deleted":[...],"rumor_ids":[...]})`.

### 3.3 adjust_support(session_id, rumor_id, support) -> SessionRumor
- 0~1 클램프/검증 → 해당 rumor `support` 갱신 `upsert_rumor` → `append_timeline(ADJUST_SUPPORT, payload={"rumor_id":...,"support":value})`. (승격/강등은 advance_turn에서만 반영, FR-R3.4.)

### 3.4 set_region_distortion(session_id, region_id, degree) -> None
- `repo.set_region_distortion` → `append_timeline(SET_DISTORTION, payload={"region_id":...,"degree":...})`.

### 3.5 advance_turn(session_id, *, promotion_threshold=0.6) -> TurnResult
1. `rumors = repo.list_rumors(session_id)`.
2. `res = PromotionPolicy.evaluate(rumors, promotion_threshold)`.
3. 적용: promoted_ids → `promoted=True` upsert; demoted_ids → `promoted=False` upsert.
4. 전이별 `append_timeline(PROMOTE/DEMOTE, payload={"rumor_id":...})`(현재 turn).
5. `turn = repo.bump_turn(session_id)` → `append_timeline(ADVANCE_TURN, turn=new, payload={"promoted":[...],"demoted":[...]})`.
6. 반환 `TurnResult(session_id, turn, promoted_ids, demoted_ids)`.

> 패턴: 기존 `PipelineOrchestrator`와 동일한 "단일 오케스트레이터"(AD-R Q3=A). 각 동작 = 1 타임라인 항목.

## 4. SessionQueryEngine (`locus/session/query.py`)

```python
class SessionQueryEngine:
    def __init__(self, repo: SessionRepository, loader: WorldLoader,
                 params: ConsensusParams = DEFAULT_PARAMS) -> None: ...

    def knowledge_for_region(self, session_id: str, region_id: str) -> QueryResult: ...
```
1. 세션→`world_id`. `loader.load(world)`; region 미존재 → LookupError.
2. `view = ConsensusEngine(kg, topo, params).resolve(region_id)`.
3. **캐노니컬**: `canonical = canonical_known(view)`(direct+inherited+global; propagated/auto-rumor 제외, Q7=A/FR-R5.1).
4. **세션 오버레이**: `rumors = repo.list_rumors(session_id, region_id)`.
   - `promoted=True` → `KnowledgeView(knowledge_id=r.id, statement=r.statement, scope_type="direct", is_rumor=True, distortion_degree=r.distortion_degree, confidence=r.confidence)` (Q6=A: direct-like, 출처가 소문임은 `is_rumor=True`로 투명).
   - `promoted=False` → 동일하나 일반 rumor view(`scope_type="direct"` 유지, is_rumor=True) — items엔 포함, unique/shared 분류에선 보조.
5. `items = canonical + promoted_views + rumor_views`.
6. `unique_ids` = direct(region-specific) + 승격 rumor ids(direct-like); `shared_ids` = inherited + global. (비승격 rumor는 items엔 있으나 shared/unique 비포함 — 보조 소문.)
7. 반환 `QueryResult(world_id, region_id, items, shared_ids, unique_ids)`.
- 비세션(캐노니컬) 쿼리는 기존 `QueryEngine` 그대로(회귀 없음, FR-R5.2).

## 5. API 라우터 확장 (`api/routers/session.py`) — S2 추가 라우트
서비스는 `app.state`(`game_master`, `session_query`)에서 주입.
```
POST /api/session/sessions/{sid}/regions/{rid}/rumors          -> list[SessionRumor]  (generate)
POST /api/session/sessions/{sid}/regions/{rid}/rumors/regen     -> list[SessionRumor]  (regenerate)
PUT  /api/session/sessions/{sid}/rumors/{rumor_id}/support      -> SessionRumor        (body: {support})
PUT  /api/session/sessions/{sid}/regions/{rid}/distortion       -> RegionDistortion    (body: {degree})
POST /api/session/sessions/{sid}/advance-turn                   -> TurnResult
GET  /api/session/sessions/{sid}/regions/{rid}/knowledge        -> QueryResult         (NPC view)
```
- 없는 세션/리전 → 404. 닫힌 세션에 쓰기 동작 → 409(BR-S2-9). support/degree 범위 밖 → 422.

## 6. 와이어링 (`api/main.py`)
- `app.state.game_master = GameMasterService(session_repo, RumorGenerator(llm), loader)`.
- `app.state.session_query = SessionQueryEngine(session_repo, loader)`.
- 기존 graph/search/llm/loader/session_repo 재사용. `_STATE_KEYS`에 `game_master`/`session_query` 추가.

## 7. 테스트 모델 (NFR-R5/R6)
- **RumorGenerator**: mock LLM으로 체인 길이/`distorted_from` 계보/confidence=conf×(1−degree)/graceful(중간 실패 시 앞 단계만) 검증.
- **PromotionPolicy**: 순수 단위 + PBT(경계 threshold, 멱등, 전이 정확성).
- **GameMasterService**: in-memory repo + fake loader + mock generator로 generate/regenerate(전체 삭제)/adjust_support/advance_turn(승격·강등·turn++·타임라인) 검증.
- **SessionQueryEngine**: fake loader(ConsensusView 구성) + in-memory repo로 propagated/auto-rumor 제외 + 승격 direct-like + 비승격 rumor 포함 검증.
- **canonical_known**: 순수 helper 단위(기존 view_items 무회귀).
- **API**: TestClient happy/404/409/422.
