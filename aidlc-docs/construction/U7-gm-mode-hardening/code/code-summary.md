# U7 GM 모드·안정화 — Code Summary

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U7 코드 생성을 마쳤습니다. 이 문서는 바뀐 것과 그 검증을 모은 것입니다.
- GM 모드를 플레이 화면과 오가게 했습니다.
- 사건 제안이 월드를 보고, 세계 상태가 지도 위에 보입니다.
- 되먹임 복원·상한, 사건 상태, 계보, 새 지역, 플레이어 로그, 이름, 조정값을 닫았습니다.
- U5·U6 이월 정리도 함께 닫았습니다.

플랜: `construction/plans/U7-gm-mode-hardening-code-generation-plan.md` (11단계, 승인 2026-10-01).

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1) | 결과 (Step 10.1) |
|---|---|---|
| pytest (`-q --no-cov`) | 636 | **730** (+94) |
| vitest | 74 | **90** (+16) |
| mypy (`locus api`) | 11 | 11 (U7 파일 0) |
| ruff · black · tsc | clean | clean |
| 가장 큰 GM 컴포넌트 | `SessionPanel.tsx` 518줄 | `GmHub.tsx` 239줄 (≤ 250, NFR-7) |
| `npm audit --omit=dev` | — | moderate 2 (react-router, U7 이전부터; U7은 의존성 변경 없음). 기록만 하고 CI 강제는 U8(NFR R-07) |

## 2. 바뀐 파일 (95개, +4.4k / −1.1k; 새 21, 삭제 1)
- **새 백엔드 모듈**
  - `locus/shared/text.py`: `one_line`
  - `locus/play/player/log.py`: `player_log`
  - `locus/play/world_state.py`: `summarize_state`, `WorldStateService`
  - `locus/play/event/suggest_context.py`: 지역 선택, 줄 상한, 이름 매칭
- **새 웹 파일**
  - `features/gm/`: `GmHub`, `ManualTurnPanel`, `EventPanel`, `DistortionPanel`, `RumorPanel`, `TimelinePanel`, `PlayerStrip`, `WorldStateOverlay`, `bulk.ts`
  - `ui/CommitRange.tsx`
- **삭제**: `web/src/SessionPanel.tsx`
- **설정**
  - `shared/config/tuning.py`: `WorldTuning`, `PlayTuning` 필드 8개, 기준값 0.45
  - `settings.py`: env 14개, 기동 검증
- **저장**
  - 모델: `RegionDistortion.feedback_share`, 종류 셋, `RegionState`·`WorldState`, `LlmCallFailedError`, `AppraisalOutcome` 정리
  - 포트·어댑터: `message_counts`, `seed_candidates`, `list_deeds` 확장, `delete_rumor` 제거, `UtcDateTime`, 열 추가
- **엔진·서비스**
  - `rumor/{dynamics,feedback,service,generator,spread,promotion}.py`
  - `event/{dynamics,service,suggester}.py`
  - `turn/advancer.py`
  - `distortion_service.py`, `session_service.py`, `player/{movement,service}.py`
  - `npc/{dialogue,prompts}.py`, `gm/narrator.py`, `deeds/service.py`, `base.py`, `wiring.py`
- **월드 빌드**: `world/{build,wiring}.py`, `topology/{weights,builder}.py`, `ontology/{builder,dedup}.py`
- **API**: `routers/{gm,play}.py`, `schemas.py`(`localize_deed_views`, `WorldStateOut`), `errors.py`
- **웹(그 밖)**: `types.ts`, `api/{gm,http}.ts`, `MapOverlay.tsx`, `routes/{GmPage,PlayPage}.tsx`, `features/play/{ActionBar,PlayLog,DialoguePanel}.tsx`, `features/gm/DeedPanel.tsx`, `ui/{Modal,index}.ts(x)`, `i18n.ts`
- **문서**
  - `operations.md`: "GM mode & hardening" 절
  - `env.example`, `CLAUDE.md`
  - X3 BR-X3-5 〔U7 정정〕
  - FD·NFR 〔Step 1.3 정정〕

## 3. 검증 번호와 테스트
| 검증 | 테스트 |
|---|---|
| TP-U7-1~4 | `tests/play/test_feedback.py` (hypothesis 넷: 범위·기록, 몫 소진 `+1` 턴, 누적 상한, 승격 불변) |
| TP-U7-5 | `test_play_services.py::test_ex8_tp_u7_5_*` |
| TP-U7-6 | `test_player_log.py` (분할 + 부분 수열·위치 PBT) |
| TP-U7-7 | `test_world_state.py` (PBT + 구조 단언: 저장소 5회·스냅샷 1회) |
| TP-U7-8 | `tests/shared/test_config.py::test_tp_u7_8_*`, `test_br_u7_20_*` |
| EX-1~3 | `test_feedback.py` (턴 엔진 통합: 승격 1 + 비승격 감쇠, 몫 수열, 상한) |
| EX-4 | `test_feedback.py::test_br_u7_5_*` |
| EX-5~7 | `test_gm_events.py` |
| EX-8·9 | `test_play_services.py` |
| EX-10 | `test_player_log.py` |
| EX-11 | `test_advance_turn.py::test_ex11_*` |
| EX-12 | `test_config.py` (env → tuning), `test_topology.py::test_u7_*` |
| EX-13·14 | `test_dialogue.py::test_ex13_*`, `test_ex14_*` |
| EX-15 | `test_player_mode.py::test_gm_start_session_records_its_start` |
| 외부 계약 1~7, NFR R-05 | `tests/api/test_gm_mode_api.py` |
| NFR R-03 (주입) | `tests/shared/test_text.py`, `test_dialogue.py::test_nfr_r03_*`, `test_narrator.py::test_review_u6_6_*`, `test_gm_events.py` |
| 화면 (frontend §6) | `web/src/__tests__/gm.test.tsx` 16개 |
| 의도된 변경 (NFR §4) | `U7 intended change` 표시 14곳(파일 12개): `test_rumor_dynamics.py`, `test_advance_turn.py`, `test_player_mode.py`, `test_postgres_repo.py`, `test_repository_contract.py`, `test_models.py`, `test_play_api.py`, `test_play_gm_api.py`, `test_service.py`, `components.test.tsx`, `dialogue.test.tsx`, `deeds.test.tsx` |

## 4. 이월 결정의 구현 위치
| 출처 | 위치 |
|---|---|
| FD R-01 | `DistortionService(repo, snapshots)`, `WorldStateService`, `wiring.py` |
| FD R-02 | `SessionService.start_session` (`player: null`) |
| FD R-03·R-07·R-09 | Step 1.3 정정(BLM §1.5·§10·§4.4, TP-U7-2, EX-8) |
| FD R-05 | 각 단계에 호출처를 적었다 (§5) |
| FD R-06 | `suggest_context.pick_brief_regions` |
| FD R-08 | `PlayerStrip` → `listTurnRuns(sid, "running")` |
| NFR R-01 | `suggest_context`의 글자 상한, `CONTEXT_MAX` 21,000, 상한까지 채운 40지역 단언 |
| NFR R-02 | `ConversationStore.message_counts` (두 어댑터 + 계약) |
| NFR R-03 | `shared/text.one_line` + 모든 프롬프트 삽입 |
| NFR R-04 | `Settings._tuning_is_consistent`, 표 env는 `dict[str, float]` |
| NFR R-05·R-06·R-07 | 구조 단언(§3), 기준선(§1), npm audit(§1) |
| U6 #5·#7·#8·#9·#10~#15 | `GmHub.generateAll`, 제안 프롬프트·`_SYSTEM`, `_start`, `_narrate`, `PlayPage`·`conflictKind`, `DeedPanel`, `ActionBar`, `Modal.busy`, `movement.validate_action` |
| U6 #1 남은 결정 | `advancer._scene`: `shadowed_sources` + `pick_facts(hidden=)` |
| U6 C1~C16 | C1 `DeedPanel` key/`reloadKey` · C2 `seed_candidates`, `list_deeds` 확장 · C3·C4 `_draft_spread`, `neighbour_map` · C5 `appraise(objects)` · C6 `AppraisalOutcome` · C7 청구 한 곳 · C8 `SCENE_*` = narrator 한도 · C9 씨앗 왜곡도 · C10 `current_stay` · C11 `_is_unique_violation` · C12 `localize_deed_views` · C13 (#1) · C14 `narrate` 폴백 · C15 `StaticSnapshots` · C16 `UtcDateTime` |
| U5 C1·C4·대화 500·줄바꿈 위조 | `message_counts` + 웹 +2, `base._require_player`·`PlayService(params)` 제거, `LlmCallFailedError` 503, `one_line` |

## 5. 설계 이탈 (완결 목록)
- **플랜 R-01 (승인 때 Accepted risk)**: 이름 변경·메서드 제거의 호출처 수정은 플랜의 원칙("같은 하위 단계에서 고친다")에 따라 앞당긴다. 옮긴 항목은 아래에 적는다.
- 웹 새 파일(`features/gm/*`, `ui/CommitRange.tsx`)은 Step 8에서 만든다. 빈 TSX 파일은 tsc `isolatedModules`와 vitest의 빈 스위트 규칙에 걸리기 때문이다.
- **Step 3로 당긴 것 (플랜 R-01)**: 6.1의 재생성 비활성화 전환(`rumor/service.py`의 `delete_rumor` → `active=False` 저장, `deactivated_ids`, 페이로드 `deactivated`)과 그 호출처(`api/routers/gm.py`, 테스트 다섯 곳)를 `delete_rumor` 제거·개명과 같은 단계(3)에서 고쳤다. 6.1에는 이름 페이로드만 남는다.
- **C2 질의 모양**: `DeedStore`에 `seed_candidates`를 두고, `npc_memories`·`recent_deeds` 대신 `list_deeds(kind=, deed_ids=, newest_first=, limit=)`로 넓혔다. 발언 커서(`last_statement`)는 NPC 필터가 JSON 열이라 SQL로 걸지 않고 `kind=statement`로 줄인 뒤 거른다.
- **`one_line`과 탭 (4.1)**: 플랜 이월 표는 "탭 제외"였으나 탭도 공백 하나로 접는다. 탭은 프롬프트 구역을 열지 못하지만, 공백 접기(`str.split`)가 이미 탭을 공백으로 다루므로 규칙을 하나로 둔다.
- **`region_feedback`의 분모 (4.2)**: 승격 소문은 강한 소문에서도, 밀도의 분모에서도 뺀다(FD BLM §1.2 그대로).

- **Step 5로 당긴 것**: GM 왜곡도 설정이 몫을 0으로 하고 `feedback_share_cleared`를 남기는 부분(6.3의 일부, BR-U7-5). 몫 통합 테스트와 같은 단계에서 GREEN이 되게 했다. 지역 확인(404)과 생성자 주입은 6.3에 남는다.
- **5.2 (플랜 검토 R-04)**: 새 키워드 인자는 `distortion_delta(max_delta=)` 하나다. `propagate_delta(min_weight=)`·`evolve_support(reinforce=)`는 이미 있었고 엔진이 tuning 값을 넘긴다.
- **5.4 장면 가리기 (플랜 검토 R-05)**: `pick_rumors` → `shadowed_sources(picked, [*src.rumors, *src.lineage])` → `pick_facts(hidden=)`.
- **5.4 C4**: `spread.neighbour_map(edges)`를 새로 두고, `plan_spread`가 `reach`·`neighbours`를 선택 인자로 받는다(엔진이 원점별로 메모).
- **5.4 C7**: 청구는 갈래 앞 한 곳에서 `run.cost_turns`로 한다. 대기·선언·대화 마침의 비용은 `action_cost`가 이미 1이다.

- **Step 6으로 당긴 것 (플랜 R-01)**: `LlmCallFailedError` → 503 매핑(7.1)과 NPC 목록 라우터의 개수 형태(7.3)를 대화 서비스 변경과 같은 단계에서 고쳤다.
- **6.7 C5 (플랜 검토 R-02)**: `appraise(session, player, npc, snapshot, *, budget)`. 테스트 13곳은 헬퍼 `_appraise(gm, session_id, npc_id, budget=)` 하나로 모았다.
- **6.7 `npcs_here` 반환형**: `(NPC, Conversation | None)` 대신 `(NPC, int | None)`(메시지 수, 대화 없으면 None). 라우터 응답 모양은 그대로다.
- **6.7·6.8 정규화 범위**: NPC 대화·판단 프롬프트, 서술 프롬프트·폴백 기록, 소문 왜곡 프롬프트(`rumor/generator.py`)의 모든 삽입 글이 `one_line`을 지난다.
- **6.2 제안기 시그니처**: `EventSuggester.suggest(*, context, turn, n)`. 지역 목록은 컨텍스트 안에 있다.

- **8.2 테스트 이름**: `components.test.tsx`는 `GmHub`을 그대로 렌더한다(옛 `SessionPanel` 단언 그대로, describe 이름만 바뀜).
- **8.2 `bulk.ts`**: `mapLimit`·`BULK_LIMIT`을 `features/gm/bulk.ts`로 뺐다(가장 큰 GM 컴포넌트 ≤ 250줄, NFR-7).
- **8.4 지도 표시**: `MapOverlay`에 `markerId`(붉은 고리 + "●"), `regionFill`, `regionBadge` 선택 prop을 더했다. 오버레이는 훅 `useWorldState` + 순수 `overlayOf` + 토글·범례 `WorldStateOverlay`로 나눴다.
- **8.5 닫힌 세션**: `conflictKind`가 409를 "closed"/"busy"로 가른다. 닫힌 세션이면 행동·이동·선언이 잠긴다.
- **8.7 지난 기록**: `event_created` + `suggested/approved` 플래그 줄(U7 이전)은 각각 제안·승인 문구로, 플레이어 없는 `session_started`는 "GM 세션 시작"으로 읽는다.
- **변이 하나는 겉으로 같다**: `voidDeed`의 재진입 가드를 지워도 모달의 `busy`가 두 번째 클릭을 막는다(이중 방어). 모달 쪽 변이는 테스트가 잡는다.


## 6. 변이 확인
| 단계 | 변이 | 결과 |
|---|---|---|
| 4 | 상한 무시, 몫에 delta 기록, 복원이 덜 빠짐, 승격 소문 셈, 로그가 지역 무시, 사건 줄 중복, 비활성 소문 셈, 플레이어 지역 우선 없음, 모호한 이름 매칭 | 9/9 잡음 |
| 5 | #8 다시 읽기 없음, #9 장면이 try 안, #14 규칙이 validate_action 밖, 장면 가리기 없음, 되먹임 지역 면제, 몫 미기록, GM 설정이 몫 유지, one_shot 해소 줄 없음 | 8/8 잡음 |
| 6 | SUGGESTED 해소 허용, 폐기 줄 없음, n 검사 없음, 이름 매칭 없음, 승인을 created로, 재생성 비활성화 없음, 목록이 저장 행만, 없는 지역 설정 허용, NPC 목록이 대화 읽기, 대화 실패 누출, 질문·최근 줄·판단·서술 줄바꿈 유지, GM 시작 기록 없음, 로그 필터 없음, dedup 기준 무시 | 17/17 잡음(둘은 테스트를 조인 뒤) |
| 8 | CommitRange 중복 저장·키 저장 없음, 제안에 해소 버튼, 전체 생성이 행적 소문 셈, 선언 상자 미잠금, UTF-16 세기, 닫힘을 진행 중으로, 모달 busy 없음, 대화 뒤 목록 재조회, 닫힌 세션 미잠금, 지역 이름 없음, 상태 미조회, 띠가 전체 실행 조회 | 13/14 잡음(재진입 가드는 모달과 이중 방어라 겉으로 같음) |


## 9. 승인 뒤 리뷰 후속 수정 (2026-10-01, `code-review-01` 사람의 선택 A)
| 리뷰 # | 고친 곳 | 테스트 (변이 확인) |
|---|---|---|
| 1 | `ui/CommitRange.tsx`: 사용자가 움직였을 때(`onChange`)만 저장한다 | `gm.test.tsx` "#1" (반올림된 값으로 blur·pointerUp·Tab) |
| 2 | `play/turn/guard.py`: GM 쓰기는 서로 세션을 나눈다(보유자 수). 턴만 모두를 막는다 | `test_turn_guard.py::test_u7_review_2_*`, `test_gm_mode_api.py::test_u7_review_2_*`(다섯 쓰기가 barrier에서 만나야 통과) |
| 3 | `locus/__main__.py`가 `tuning=settings.world_tuning()`을 넘긴다. `WorldBuilder.from_factory`의 `tuning`을 필수로 바꿨다 | `test_cli.py::test_u7_review_3_*` |
| 4 | `CommitRange`는 저장이 성공했을 때만 `saved`를 옮긴다(거절하면 손잡이를 되돌린다). `GmHub.run`이 성공 여부를 돌려준다. `DistortionPanel`에 `key={regionId}`를 준다 | `gm.test.tsx` "#4" |
| 5 | `_fail`이 `restored_region_id`를 싣고 `player_log`가 그 줄로 위치를 되돌린다. BR-U7-13을 〔리뷰 후속 정정〕으로 고쳤다. PBT 생성기에 실패 복원 줄을 넣었다 | `test_player_log.py::test_review_u7_5_*` ×2 |
| 11 | `GmPage.onDeedChanged`가 세션을 다시 읽는다. `GmHub.run`·`advance`는 닫힌 세션 409에서 `onChanged`를 부른다 | `gm.test.tsx` "#11" ×2 (GmHub, GmPage) |

- 게이트: pytest 735, vitest 94, ruff·black·tsc clean, mypy 11
- 의도된 변경: `test_deeds_api.py`(GM 리스 공유), `test_player_mode.py`(`restored_region_id` 페이로드)
- 변이 확인: 8건(배타 리스, CLI 기본 조정값, 복원 무시, 변화 없는 저장, 거절도 저장, 닫힘 미통지 ×2, 페이지 미재조회) 모두 잡음
- 나머지(#6~#10, #12~#15, §3 12건, 정리 19건, 설계 메모 둘: GM 설정과 ACTIVE 사건 기여, `TOPOLOGY_DEFAULT_BASE`)는 U3 FD 이월 목록으로 간다(리뷰 기록 §8)

## 7. 운영자 실행으로 남긴 것
이 호스트의 7474/7687은 다른 프로젝트가 쓴다. 그래서 compose를 띄우는 라이브 확인은 운영자가 돌린다.
```bash
docker compose up -d neo4j opensearch postgres
locus init-schema --play          # region_distortions.feedback_share is added to an existing DB
uvicorn api.main:app --port 8000 & (cd web && npm run dev)
# 1) /play/<sid> → "GM 모드" → /gm/<sid>: 플레이어 띠(이름·지역·턴)와 지도 고리
# 2) 사건 제안(n=2) → 하나 승인·하나 폐기 → 타임라인에 제안·승인·폐기, 지역 이름
# 3) 턴 3회 → "세계 상태": 사건 지역에서 연결을 따라 색이 번진다(US-5.5)
# 4) "플레이로 돌아가기" → 지역 화면이 GM에서 바꾼 것을 보인다(US-5.1)
# 5) p95: /state, /log, /distortions ≤ 100 ms (타임라인 3,000줄, 지역 15, 활성 소문 300)
```

## 8. 넘기는 것
- **U3(월드 에디터)**
  - `WorldTuning`(가중치 표·dedup)은 env로만 바뀐다. 에디터에서 표를 보이거나 바꿀지는 U3에서 정한다.
  - 에디터가 지역을 지우면 그 왜곡도 행은 목록에서 빠지고 DB에 남는다(BR-U7-18). 정리 방식은 U3에서 정한다.
- **U8(데모·배포·문서)**
  - 라이브 시나리오에 GM 왕복과 세계 상태 확인(§7)을 넣는다.
  - `npm audit`의 react-router moderate 2건을 CI에서 다룬다.
