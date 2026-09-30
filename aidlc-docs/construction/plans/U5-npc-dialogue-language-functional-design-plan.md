# U5 NPC 대화·언어 — Functional Design 플랜

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U5 — 플레이어가 지역 NPC와 대화하고, NPC는 자기 지역에서 알 수 있는 것만 알며(소문은 왜곡된 대로), 화면은 한국어·저장은 영어인 언어 경계를 완성하는 설계. 이 단계는 그 규칙과 데이터·API·화면을 문서로 고정한다.

근거: `inception/application-design/purpose-restructure/unit-of-work.md` U5, `unit-of-work-story-map.md`(US-4.1~4.3, 6.1 완성, 9.1~9.4), 요구 FR-C4·F4·F5·G1~G5, 가정 A-1, component-methods P2(ConversationStore)·P3(`conversations`·`messages`)·P12(`NpcScope.build_context`)·P13(`NpcDialogueService`)·P14(`source` 태그)·L4(`enrich` 중복 억제·`purge`), services.md §3.5·§3.8. 현재 코드: `locus/play/region_knowledge.py`(`knowledge_for_region` = direct+inherited+global + 활성 소문, `source` 태그 `rumor`/`rumor:promoted` **이미 구현**), `locus/localization/service.py`(`enrich` 캐시 우선·백그라운드 워밍·**in-flight 중복 억제 이미 구현**; `purge` 없음), `api/routers/knowledge.py`(캐노니컬 질의 응답 번역 **이미 적용**), U4의 `RegionView`(facts/hearsay/rumors 번역 필드), `web/src/i18n.ts`(ko 전용 사전), U4 `EndTalkAction`(턴 1 소모, 대화 없음).

## 플랜
- [x] 상위 산출물·현재 코드 분석(위 근거)
- [x] 질문(아래 FD-U5 Q1~Q4) 답 수집·분석
- [x] `construction/U5-npc-dialogue-language/functional-design/domain-entities.md` — `Conversation`·`Message`·`NpcContext`·`ScopeLimits`·`NpcReply`, `TimelineKind.NPC_TALKED`, `ConversationStore` 포트·`PlayUnitOfWork.conversations`, 테이블, `PlayTuning`/`Settings` 추가(컨텍스트 한도·언어), 오류
- [x] `.../business-logic-model.md` — `NpcScope.build_context`(순수·불변식), `NpcDialogueService.start/say/history`(프롬프트 가드·표시 언어 직접 생성·LLM 1회), `EndTalk` → `NPC_TALKED` 타임라인(U4 `_start` 확장), 표시 언어 결정, `TranslationService.purge` + 호출 지점(조립 루트), API(`npcs/{n}/start|say|history`, `lang`), 프롬프트 설계(`play/npc/prompts.py`), LLM 없을 때
- [ ] `.../business-rules.md` — BR-U5-*, Testable Properties(PBT-03 아는 범위 불변식 `context ids ⊆ known ∪ region rumors`, 생성기 재사용 PBT-07; 왜곡 전언 표현 예제)
- [ ] `.../frontend-components.md` — `NpcList`(RegionScene NPC 카드 "말하기")·`DialoguePanel`(이력·입력·전송·LLM 1회)·언어 토글·i18n 전 라벨(+en 사전)
- [ ] Plan Review(architecture-reviewer, adversarial ≤ 2) → `construction/U5-npc-dialogue-language/functional-design/reviews/functional-design-review-NN.md`
- [ ] 완료 메시지 + 승인 게이트 → 다음: U5 NFR(light)

## 질문 (대화창에서 2개씩)

### FD-U5 Q1 표시 언어를 어디서 정하는가 (US-9.2, US-9.4, FR-G3)
배경: 지금은 서버 설정 `TRANSLATION_TARGET_LANG`(기본 `ko`) 하나가 번역 언어를 정하고, NPC 대화는 아직 없다. US-9.2는 "표시 언어를 영어로 바꾸면 영어로 답한다", US-9.4는 "UI 라벨도 함께 바뀐다"를 요구한다. 어디에 언어를 두는지가 API 형태(`lang` 파라미터 유무), 프롬프트, 프론트 토글, 번역 캐시 키(`target_lang`)에 걸린다.
- A. 서버 기본값 + 요청별 덮어쓰기 — `TRANSLATION_TARGET_LANG`이 기본, 대화·화면 조회 요청에 `?lang=ko|en`을 붙이면 그 언어로 답하고 번역한다. 프론트는 언어 토글을 브라우저에 기억해 모든 요청에 붙인다. 결과: US-9.2·9.4 둘째 기준을 충족, 세션에 저장할 것이 없어 되돌리기 쉽다. 비용: 라우트 4개에 파라미터 하나, 프롬프트에 언어 지시 한 줄.
- B. 서버 전역만 — `TRANSLATION_TARGET_LANG`만 쓰고 토글은 두지 않는다. 결과: 구현이 가장 작지만 US-9.2 셋째·US-9.4 둘째 기준은 미충족으로 남고(수용 기준 이탈을 승인에서 기록), 언어를 바꾸려면 서버 재시작.
- C. 세션에 저장 — 세션 시작 폼에서 언어를 고르고 `game_sessions.lang`에 둔다. 결과: 세션마다 언어가 고정되어 일관되지만 테이블·시작 폼·GM 세션 기본값이 늘고, 바꾸려면 새 세션이 필요하다.
- X. Other (please specify)
[Answer]: A

### FD-U5 Q2 UI 라벨 통일 범위 (US-9.4, FR-G5; P1)
배경: `web/src/i18n.ts`는 ko 사전만 있고, 툴바·지역 패널·세션 바(`Session`, `New Session`, `Close`)·보강 패널·에디터 안내문에 영어 라벨이 남아 있다. US-9.4는 (1) 모든 라벨이 사전에서 오고 (2) 영어로 바꾸면 라벨도 바뀐다를 요구한다. 범위가 곧 코드 생성 일의 양이다.
- A. ko 통일 + en 사전까지 — 남은 영어 라벨을 전부 사전으로 옮기고 en 항목도 채워 Q1의 토글로 UI 라벨이 함께 바뀐다. 결과: US-9.4 완료. 비용: 키 약 80개의 en 문구 작성과 컴포넌트 라벨 치환(테스트의 라벨 문자열 단언 일부 갱신).
- B. ko 통일만 — 영어 라벨을 사전으로 옮기되 en 사전은 만들지 않는다. 결과: US-9.4 첫 기준만 충족, 둘째 기준은 U8(데모·문서) 또는 이후로 남긴다(승인에서 기록). 비용 절반.
- X. Other (please specify)
[Answer]: A

### FD-U5 Q3 NPC 컨텍스트 한도 (FR-F4, NFR-5)
배경: NPC 프롬프트에는 지역 지식(direct+inherited+global)·전언·활성 소문·최근 대화가 들어간다. 데모 월드 규모(지역당 지식 3~8, 활성 소문 ≤ 20)에서도 전부 넣으면 프롬프트가 길어지고 비용·지연이 는다. 한도는 순수 함수 `build_context`의 인자(`ScopeLimits`)이자 PBT의 경계값이다. 한도에 걸리면 무엇을 남기는지도 정해야 한다.
- A. facts 12 · hearsay 6 · rumors 8 · 최근 메시지 10 — 우선순위: facts는 direct → inherited → global 순, rumors는 승격 → 지지도 높은 순, 메시지는 최신 순. 결과: 프롬프트 약 1.5k 토큰, 데모 규모에서 거의 잘리지 않음. env 4개(`NPC_MAX_*`).
- B. 더 넉넉히(20 · 10 · 12 · 20) — 결과: 잘림이 거의 없어 답이 풍부하지만 호출당 비용·지연 증가.
- C. 값을 직접 지정한다(적어 주세요).
- X. Other (please specify)
[Answer]: A

### FD-U5 Q4 번역 정리(`purge`)의 트리거 (FR-G4, US-9.3 넷째 기준)
배경: 소문을 재생성하거나 지식을 지우면 `translations` 행이 고아로 남는다(RE C9). `TranslationStore`에는 `purge`가 없다. play·world는 localization을 import하지 않으므로(경계 규칙) 정리 호출은 조립 루트(`api/`)나 CLI에 두어야 한다.
- A. 삭제·재생성 라우트에서 즉시 정리 — gm 재생성/소문 삭제·(U3) 에디터 삭제 라우트가 응답 전에 `loc.translations.purge(kind, ids)`를 부른다. 결과: 고아 행이 생기지 않고 추가 운영 절차가 없다. 비용: 라우트마다 한 줄, 삭제 id를 서비스가 돌려주도록 `regenerate_region` 반환에 `deleted` 포함(타임라인 payload에 이미 있음).
- B. CLI 배치 — `locus localization purge --world <id>`가 존재하지 않는 원본 id의 행을 훑어 지운다. 결과: 라우트는 그대로, 운영자가 주기적으로 돌린다. 데모에서는 잊히기 쉽다.
- C. 둘 다 — A + B.
- X. Other (please specify)
[Answer]: A

## 가정 (질문하지 않는 것)
| # | 가정 | 근거 |
|---|---|---|
| A5-1 | 대화 단위 = (세션, NPC)당 하나(`get_or_create`), 메시지 누적; `history`는 그 대화 전체 | P2 |
| A5-2 | `say` 1회 = LLM `complete` 1회, 턴 소모 0; `EndTalk`(U4, 1턴)이 `NPC_TALKED` 타임라인(메시지 수·NPC 이름)을 남긴다. 대화 호출 상한은 두지 않는다(플레이어 속도 = 상한) | FR-C4, services §3.5 |
| A5-3 | LLM 제공자가 없으면 `start`/`say`는 503(소문 생성과 같은 패턴), `history`는 200; `RegionView.llm_available=false`가 화면 안내 | NFR-4, U4 Q6 |
| A5-4 | 프롬프트 가드: 시스템 문에 "컨텍스트에 없는 것은 모른다고 하거나 소문대로 말한다, 지어내지 않는다"; 소문은 승격이면 사실처럼, 왜곡도 ≥ 0.5면 전언 표현("들었다", "확실하진 않지만"), 그 사이는 중립 | US-4.3 |
| A5-5 | 컨텍스트의 지식·소문은 영어 원문, 답은 표시 언어로 직접 생성(A-1); 대화문은 번역 캐시에 넣지 않는다 | FR-G3 |
| A5-6 | 플레이어가 NPC의 지역에 없으면 400; 닫힌 세션 409; 진행 중 턴 실행이 있어도 대화는 허용(읽기 + 대화 저장만, 턴 상태를 바꾸지 않음) | services §3.5, U4 가드 범위 |
| A5-7 | `NpcScope.build_context`는 `locus/play/npc/scope.py`의 순수 함수; 입력 = `region_known(view)`·`view.hearsay`·활성 소문·최근 메시지·NPC; `allowed_ids` = 입력 지식 id ∪ 소문 id; PBT: 출력 id ⊆ allowed_ids, 한도 이하, 우선순위 순 | FR-F4, PBT-03 |
| A5-8 | `conversations`(id, session_id, npc_id UNIQUE(session_id, npc_id), started_turn, created_at)·`messages`(id, conversation_id idx, role, text, turn, created_at) — PostgreSQL 추가만; 인메모리 트윈 동일 계약 | P3 |
| A5-9 | `enrich`의 중복 억제는 이미 있으므로(in-flight) FR-G4 잔여는 `purge`만 | 코드 확인 |
| A5-10 | 프론트: RegionScene NPC 카드에 "말하기" → `DialoguePanel`(이력·입력·전송·진행 표시), 대화 종료 버튼 = `EndTalk` 행동(U4 `act`) | F3 |
