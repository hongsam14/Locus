# Phase 2 — Component Dependency

> 의존성 매트릭스 + 통신 패턴 + advance_turn 데이터 흐름. 화살표 = "의존/호출".

## 의존성 매트릭스
| Component | 의존 대상 | 종류 |
|---|---|---|
| C7 session API | C5 GameMasterService | 호출(FastAPI 라우트) |
| C5 GameMasterService | C6 SessionRepository(port) | 포트(영속) |
| C5 GameMasterService | C4 EventSuggester | LLM 제안(graceful) |
| C5 GameMasterService | C3 dynamics (순수) | 결정론 계산 |
| C5 GameMasterService | promotion (순수, 기존) | 승격/강등 |
| C5 GameMasterService | RumorGenerator (기존) | 소문 add/update |
| C5 GameMasterService | WorldLoader (기존) | 캐노니컬 **읽기만**(NFR-P2) |
| C3 dynamics | consensus.propagation.best_path_weights | 토폴로지 전파 재사용 |
| C3 dynamics | models(SessionRumor/ConnectionEdge) | 데이터 |
| C4 EventSuggester | LLMProvider(port) | LLM |
| C6 SessionRepository | C1 SessionEvent + 기존 모델 | 데이터 매핑 |
| C8 web | C7 API(HTTP) | fetch |

- **순환 없음**. 캐노니컬→세션 단방향(세션이 캐노니컬을 읽기 참조). 세션 쓰기는 캐노니컬에 영향 없음(불변식).
- **신규 결합점**: GameMasterService ← EventSuggester(생성자 주입, main.py 와이어링 추가). 나머지는 기존 의존 재사용.

## 통신 패턴
- **포트 추상화**: 영속=SessionRepository(Protocol), LLM=LLMProvider(Protocol). 오프라인 테스트는 in-memory/mock 주입(NFR-P1).
- **순수 코어**: dynamics·promotion·lifecycle 매핑은 부수효과 없음 — 서비스가 입력 수집→순수 계산→포트로 영속(테스트 용이, PBT NFR-P4).
- **additive**: 기존 포트/라우트/모델 시그니처 불변; 신규 메서드·필드·라우트만 추가(NFR-P5/P6).

## advance_turn 데이터 흐름 (텍스트)
```
API POST /advance-turn
  → GameMasterService.advance_turn
      → repo.list_events(ACTIVE), repo.list_region_distortions, WorldLoader.load(읽기)
      → dynamics.distortion_delta / propagate_delta(best_path_weights) / apply_deltas   [순수]
      → repo.set_region_distortion(*), repo.update_event(contributions, one_shot→RESOLVED)
      → RumorGenerator + repo.upsert_rumor   (주 대상 리전만, 보존형 add/update)
      → dynamics.evolve_support → repo.upsert_rumor(*)   [순수→영속]
      → promotion.evaluate → repo.upsert_rumor(promoted) + timeline(PROMOTE/DEMOTE)
      → repo.bump_turn + repo.append_timeline(EVENT_APPLIED×, ADVANCE_TURN)
  ← TurnResult(turn, applied_event_ids, created_event_ids, promoted_ids, demoted_ids)
```

## 단위 경계 의존 (빌드 순서 강제)
- **P1**(C1/C2/C6/C7-CRUD) → **P2**(C3/C4/C5/C7-suggest+turn) → **P3**(C8).
- P2는 P1의 SessionEvent 모델·Event CRUD·status enum에 의존. P3는 P2의 advance-turn 확장 결과·TS 타입에 의존.
