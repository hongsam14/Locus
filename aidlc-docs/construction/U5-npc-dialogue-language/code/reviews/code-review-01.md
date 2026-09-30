# U5 NPC 대화·언어 — Code Review 01

**원하시는 것**: 세계관 자료로 월드를 만들고, 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG. U5는 그 핵심 체험("NPC는 자기 지역이 아는 것과 그 지역 소문만으로, 먼 곳 일은 틀린 채로 말한다")과 ko/en 표시 언어를 맡는다.
**이 리뷰가 하는 것**: 승인된 U5 코드(`git diff 6ef8d38~1..HEAD`, 커밋 6ef8d38..eed2f58)가 그 체험과 언어 규칙을 실제로 지키는지 버그 위주로 확인한다. 코드는 고치지 않았다(리뷰 전용).

**대상**: `locus/play/npc/*`, `locus/play/{models,errors,ports,region_knowledge,wiring}.py`, `locus/play/storage/*`, `locus/play/player/service.py`, `locus/play/rumor/service.py`, `locus/play/turn/advancer.py`, `locus/shared/config/*`, `locus/shared/llm/*`, `locus/localization/*`, `api/*`, `web/src/**`, 테스트. 설계 기준: `functional-design/*`, `nfr/nfr-light.md`, `code/code-summary.md`.
**방법**: `/code-review` max(재현율 우선).
- 탐색 각도 10개를 병렬로 돌렸다: 줄 단위, 제거된 동작, 호출처 추적, 언어 함정, 래퍼, 재사용, 단순화, 효율, 고도(altitude), CLAUDE.md 규약.
- 후보를 중복 제거한 뒤 후보마다 독립 검증자 1명이 CONFIRMED / PLAUSIBLE / REFUTED 중 하나로 판정했다. 동시 에이전트 상한(20) 때문에 정리 후보 2건(아래 C5·C6)의 검증과 마지막 틈 찾기(sweep)는 이 세션이 직접 했다.
- 재현 스크립트는 모두 세션 scratchpad에만 두었다. 저장소 작업 트리는 깨끗하다.

## 1. 지적 (상한 15, 심각도 순)
판정: C = CONFIRMED(입력·결과로 재현), P = PLAUSIBLE(기제는 실재, 발생 조건이 타이밍·설정에 달림).

| # | 위치 | 지적 | 판정 | 심각도 | 권장 조치 |
|---|---|---|---|---|---|
| 1 | `play/npc/scope.py:37` `_rumor_key`, `:47` `shadowed_sources` | 소문이 원본을 가리는 규칙이 체인의 **첫 고리**(`distorted_from_kind == "knowledge"`)에만 걸린다. 게다가 `_rumor_key`가 지지도 동률을 **왜곡도 높은 순**으로 깨서, 한도(8)가 첫 고리부터 잘라낸다. 그래서 NPC 프롬프트에 원문과 그 왜곡문이 **함께** 들어간다. BR-U5-11 본문 위반이고, 각주가 감수한 "첫 고리 가지치기"와는 다른 경우다 | C (검증자 1 + 탐색 5개 각도 독립 재현) | **high** | 선택된 소문마다 지역 전체 소문 목록(`{r.id: r}`)을 따라 **뿌리 knowledge id**까지 올라가 숨긴다. 순수 함수가 유지되고 스키마 변경도 없다. 소문 원본 계산은 `append_for_turn`의 `seeded`와 같은 헬퍼로 합친다. 테스트 생성기 `rumors_from`이 `kind="rumor"` 체인 고리를 만들게 해 TP-U5-1/4가 이 경우를 잡게 한다 |
| 2 | `web/src/i18n.ts:348`, `web/src/api/http.ts:13` | 웹은 서버의 `TRANSLATION_TARGET_LANG`/`SUPPORTED_LANGS`를 모른다. 그래서 기본 `ko`로 모든 번역 읽기에 `?lang=`을 붙인다. 그 결과 **문서상 유효한 설정**에서 플레이 화면·GM 허브·지역 패널이 모두 400이 된다 | C | medium | 서버의 기본·지원 언어를 노출해(예: `GET /api/meta`) 웹이 그 안에서만 고르게 한다. 아니면 `display_lang`이 미지원 값에 400 대신 서버 기본값을 쓰게 한다. 어느 쪽이든 캐시 키는 오염되지 않게 둔다 |
| 3 | `shared/llm/openai_provider.py:34`, `:78` | `max_retries=0` 때문에 SDK의 서버 지시 백오프(429/5xx의 Retry-After, x-should-retry, 지터)가 **모든** LLM·VLM 호출에서 사라졌다. 남은 것은 tenacity의 고정 1·2초 대기뿐이라, 레이트 리밋에 걸린 호출이 약 3초 만에 실패한다 | C (오프라인 MockTransport 재현) | medium | `with_retry`의 대기가 openai 예외의 `retry-after(-ms)`를 상한·지터와 함께 읽게 하고, `stop_after_delay`로 상한을 명시한다. 아니면 클라이언트를 `max_retries=1`로 두고 상한을 다시 계산한다 |
| 4 | `play/npc/dialogue.py:123` (`:104`에서만 확인) | `say`는 LLM 호출(최대 약 93초) **전에만** 세션이 열렸는지 본다. `_store`의 UoW에서는 다시 보지 않으므로, 그 사이 닫힌 세션에도 대화·메시지가 저장되고 200이 나간다(BR-U5-28은 409) | C | low–medium | `_store`의 UoW 첫머리에서 `u.sessions.get_session`으로 다시 읽어 닫혔으면 `SessionClosedError`를 낸다. `turn` 도장도 다시 읽은 값으로 찍는다. U4 리뷰 #11(턴 루프 경계 재확인)과 같은 형태다 |
| 5 | `web/src/features/play/DialoguePanel.tsx:89`, `web/nginx.conf:6` | 배포 경로의 nginx `/api/`는 기본 `proxy_read_timeout`(60초)을 쓰는데, `say`의 문서화된 상한은 93초다. 느린 LLM에서 브라우저는 504를 받고 패널은 발화를 되돌린다. 그런데 백엔드는 계속 돌아 두 줄을 **커밋한다** | C (ASGI 프로브) | low | nginx `/api/`에 `proxy_read_timeout 120s`를 둔다(operations.md에도 적는다). 패널은 5xx/504/네트워크 오류 때 "저장 안 됨"을 가정하지 말고 이력을 다시 읽는다 |
| 6 | `localization/service.py:142` | 월드 교체의 `purge(kind="knowledge", world_id=W1)`는 in-flight 키를 kind로만 거른다. 그래서 **모든 월드·언어**의 진행 중 지식 번역 표시가 지워지고, 다른 월드의 같은 항목이 두 번 번역된다. BR-U5-26 위반이고, 이 메서드 docstring과도 반대다 | C | low | `ids`가 없고 world/session 필터만 있으면 in-flight를 건드리지 않는다: `if ids is not None or (kind is not None and world_id is None and session_id is None)`. 이 경우를 잡는 테스트를 더한다 |
| 7 | `web/src/features/play/DialoguePanel.tsx:49` | 패널이 이력을 `start`(열린 세션 필수)로만 읽는다. BR-U5-4가 닫힌 세션에 허용한 `history`(`dialogueHistory`)는 어디서도 호출되지 않는다 | C | low | 닫힌 세션이거나 `start`가 409를 주면 `dialogueHistory`로 읽어 **읽기 전용**으로 보여 준다(전송·끝내기 끔). FD §4에 409 전이를 더한다 |
| 8 | `web/src/routes/PlayPage.tsx:198` | 이동할 때 `activeNpcId`를 비우지 않는다. 그래서 패널은 다른 지역에서 **숨겨질 뿐**이고, 그 지역으로 돌아오면 클릭 없이 다시 열리며 `start`를 또 보낸다. 주석은 "이동하면 닫힌다"고 되어 있다 | C (vitest 재현) | low | 보기의 `region_id`가 바뀌면(또는 move 행동 때) `activeNpcId`를 비운다. 주석을 고치고 회귀 테스트를 더한다 |
| 9 | `web/src/features/play/DialoguePanel.tsx:90` (`:97`) | 전송 중에도 입력창이 열려 있고(`inputOff`에 `sending`이 없다), 실패하면 `setDraft(text)`가 무조건 덮어쓴다. 그래서 기다리는 동안 친 다음 문장이 사라진다 | C (vitest 재현) | low | 전송 중에는 입력창을 잠근다(`disabled={inputOff \|\| sending}`, FD의 Sending 상태와 같다). 아니면 `setDraft(d => d.trim() === "" ? text : d)`로 바꾼다 |
| 10 | `shared/llm/openai_provider.py:107` (`retry.py:1-8`) | 이번 diff는 retry.py에 "providers pin `max_retries=0`, 호출당 최악 93초"를 **일반 규칙**으로 적었다. 그러나 같은 파일의 세 번째 클라이언트 `OpenAIEmbeddings`는 SDK 재시도 2회에 **타임아웃이 없다** | C (venv 검사 + MockTransport) | low | 세 클라이언트를 한 헬퍼로 만들어 `timeout=30`·`max_retries=0`을 함께 적용하고 테스트를 넓힌다. 아니면 문서를 "두 chat 클라이언트"로 좁히고 임베딩에 타임아웃이 없다고 적는다 |
| 11 | `web/src/routes/PlayPage.tsx:75`, `web/src/SessionPanel.tsx:95` | 언어를 바꾼 뒤 다시 읽을 때, 응답이 어느 언어로 요청됐는지 확인하지 않는다. 그래서 늦게 온 이전 언어 응답이 새 화면을 덮는다. PlayPage는 세션만 확인하고, SessionPanel은 아무것도 확인하지 않는다 | P (순서를 뒤집은 가짜 fetch로 vitest 재현; 실제로는 클릭과 도착 순서가 맞아야 한다) | low | 새로 고침마다 요청 언어를 잡아 두고 `lang()`과 다르면 버린다. 아니면 세대 카운터를 쓴다(RegionPanel의 `active`와 같은 방식) |
| 12 | `web/src/routes/PlayPage.tsx:121` | 턴 요약(narration)은 서버가 만든 **영어 문장**을 그대로 그려 ko/en 전환을 따르지 않는다. 같은 변경의 알림은 클라이언트에서 `t()`로 번역된다. U4 코드지만 BR-U5-21·US-9.4("모든 화면 하드코딩 영어 없음") 범위이고, U5 정리 표에서 빠졌다 | C | low | `res.changes`를 상태로 두고 `changeTitle`/`changeSummary`/`t("play.quiet")`로 그린다. EX-7에 ko/en 단언을 더한다 |
| 13 | `play/player/service.py:64` | `current_region`이 이미 읽은 세션·스냅샷을 두고도 `region_sources`가 **다시 읽는다**. GET /region마다 PG 트랜잭션 1개와 Neo4j WorldMeta 버전 조회 1개가 늘어난다(행동당 2번 호출된다). 두 조회 사이에 월드가 바뀌면 서로 다른 스냅샷이 섞인 화면이 나오거나, NFR-9 문구 대신 `region not found`가 나온다 | C (효율; 프로브에서 get·version·session이 1·1·1 → 2·2·2) / P (경합) | low | `region_sources`에 이미 읽은 session·snapshot을 받는 형태를 두고, id 기반 래퍼는 `knowledge_for_region`용으로 남긴다. `say`도 같은 경로를 쓴다 |
| 14 | `play/npc/scope.py:64`, `play/rumor/generator.py:29/70` | 생성기는 LLM이 준 **빈** `statement`를 그대로 저장한다(`RumorDraft.statement: str`, 검증 없음). `build_context`는 빈 소문도 골라 그 원본을 숨기므로, NPC는 그 사건을 원문으로도 왜곡문으로도 모르게 된다 | P (기제 재현; LLM이 빈 문장을 주는 경우에만) | low | 생성기에서 빈/공백 문장을 실패로 처리해 체인을 멈춘다. 아니면 `pick_rumors`가 빈 문장을 건너뛰게 한다 |
| 15 | `api/routers/play.py:204` | `say`는 동기 `def` 라우트다. 그래서 LLM 왕복(최대 약 93초) 동안 AnyIO 스레드풀(40) 토큰을 잡고 있고, 이 풀은 턴 폴링을 포함한 모든 동기 라우트가 함께 쓴다 | P (프로브: 동시 45개에서 다른 읽기 1.7ms → 1.8s; 한 사용자는 브라우저 연결 한도로 도달 불가) | low | 세션별 진행 중 `say` 가드(409)를 둔다(`_idle` 리스 방식). 아니면 전용 limiter를 쓰는 async 라우트로 바꾼다. operations.md의 "no rate limit" 감수 위험에 풀 공유를 적는다 |

### 지적별 재현 상황
1. **체인 원본 노출**: 패키지 데모 aldermoor에서 GM이 Riverton을 재생성하면, 원본 4개 × 3고리로 지지도가 같은 소문 12개가 생긴다. 선택된 8개는 3·2번째 고리뿐이어서 hidden = {}이다. 그 결과 Riverton 원문 4개가 FACTS에, 그 왜곡문이 RUMORS에 함께 들어간다. 턴을 두 번 돌려도 지지도가 지역 단위로 함께 움직여(0.15 → 0.1) 동률이 유지된다. 합성 예(원본 3 × 3고리, 기본 한도)에서도 원문 1개가 자기 왜곡문 둘과 함께 보인다. 기존 PBT 생성기는 `kind="knowledge"` 소문만 만들어 이 경우를 만들지 못한다. FD 1차 검토 R-02가 "체인이면 원본까지"를 권했으나 채택되지 않았다.
2. **서버 언어 무시**: `TRANSLATION_TARGET_LANG=en`, `SUPPORTED_LANGS=en`은 기동 검사를 통과한다. 새 브라우저는 `?lang=ko`를 보내고, `/region`·`/regions/{r}/knowledge`·`/rumors`·`/events`·`/knowledge`가 모두 400 `unsupported lang: ko`를 준다. PlayPage의 `Promise.all`이 실패해 화면에 오류만 남는다. `SUPPORTED_LANGS=ko`면 토글의 en을 누르는 순간 같은 일이 생기고, 그 선택이 localStorage에 남는다. U5 전에는 `?lang=`을 보내지 않아 서버 기본값이 적용됐다.
3. **Retry-After 상실**: 429와 `retry-after: 4`를 받으면 이전 설정은 4.0초 뒤 성공하고, 지금은 3.0초 뒤 `RateLimitError`가 난다. 헤더가 없어도 이전 설정은 SDK 재시도로 약 7.5초를 버텼지만 지금은 3초다. `say`는 500을 준다(`PLAY_ERRORS` 밖). 재생성은 `llm_incomplete`가 되고, 턴은 `llm_failed` 회로를 끊는다. "전체 생성"(동시 5)과 번역 워밍(2)은 같은 박자로 재시도한다. 설계(NFR-5, 플랜 2.3)는 93초 상한만 평가했고 Retry-After는 언급하지 않았다.
4. **닫힌 세션에 저장**: `complete()` 안에서 세션을 닫는 가짜 LLM으로 재현했다. `say`가 200을 주고, 닫힌 세션의 이력에 두 줄이 생긴다(첫 대화면 새 대화 행까지). `say`는 TurnGuard를 잡지 않으므로(BR-U5-27) GM 닫기도, 확인된 월드 교체의 `_close_if_replaced`도 이를 막지 못한다. 고친 형태를 scratch 플러그인으로 걸어 보니 기존 대화·API 테스트 85개가 통과했다.
5. **프록시 타임아웃**: LLM이 30초 타임아웃을 두 번 내고 세 번째 시도가 63초에 시작되면, 60초에 nginx가 504를 준다. 패널은 발화를 지우고 입력창에 되돌리지만, 서버는 두 줄을 저장한다. 플레이어가 다시 보내면 플레이어 줄이 중복되고 LLM이 두 번 불린다. 두 번째 프롬프트에는 숨겨진 첫 NPC 답까지 들어간다. 패널을 다시 열면 "되돌린" 대화가 보인다. uvicorn은 연결이 끊겨도 동기 워커를 취소하지 않는다. Vite 개발 프록시에는 타임아웃이 없다.
6. **in-flight 과다 삭제**: W2 항목을 워밍하는 중에 W1을 교체하면 in-flight가 `{('knowledge','k-w2','statement','ko')}`에서 `set()`이 된다. W2를 다시 읽으면 워밍이 또 예약되어 LLM이 2회 불린다. 첫 워밍이 실패하는 경로에서는 `_release`가 새 워밍의 키까지 지워 3회가 된다. BR-U5-33(정리된 원본의 고아 행 1개)과는 다른 경우다. 세션 범위 정리는 in-flight를 건드리지 않는다.
7. **닫힌 세션 이력**: `say`(200) → 닫기(200) → region(200) → `start`(**409**) → `history`(200, 2줄). 화면에서는 NPC 카드에 "대화 2"와 켜진 말하기 버튼이 보이고, 누르면 빈 잠긴 패널에 `409 Conflict: session is closed`가 뜬다. 끝내기는 켜져 있어서 누르면 "턴 진행 중" 토스트가 뜬다.
8. **패널 재등장**: A에서 Mara와 대화를 연다 → B로 이동하면 패널이 사라진다 → A로 돌아오면 패널이 저절로 다시 뜬다. 이때 `startDialogue`가 2번째로 불리고 말하기 버튼은 비활성이 된다. 두 번째 `start`는 멱등이라 행이 새로 생기지는 않는다. FD §4에서 Closed → Loading 전이는 "말하기 클릭"뿐이다.
9. **입력 덮어쓰기**: Q1을 보내고, 기다리는 동안 Q2를 친다. Q1이 실패하면 입력창이 Q1으로 바뀌고 Q2는 사라진다(`{"disabledWhileSending":false,...,"afterFailure":"Q1"}`).
10. **임베딩 클라이언트**: `OpenAIEmbeddingProvider`를 풀어 보면 `max_retries=2`, `timeout=None`이다. 429가 오면 `embed` 한 번에 HTTP 요청이 9번 나간다(chat은 3번). 네트워크가 멈추면 관련 prior 검색·지식 편집·import의 워커가 무기한 막힌다. 대화 경로는 embed를 쓰지 않으므로 NFR-5 자체는 유지된다. operations.md의 "Both OpenAI clients set `max_retries=0`"도 틀렸다(클라이언트는 셋이다).
11. **언어 경합**: 행동 뒤 ko로 새로 고치는 중에 en으로 바꾸고, ko 응답이 늦게 도착하면 영어 라벨 아래 한국어 `statement_ko`가 남는다. en 읽기는 번역 캐시 조회를 건너뛰어 더 빨리 끝나므로, ko → en 전환에서 일어나기 쉽다.
12. **narration**: ko 화면에서 이동하면 알림은 "Hollow / 1건 승격, 2건 신규 소문"인데, 같은 화면의 narration은 "Hollow: 2 new rumors, 1 promoted"다. 언어를 바꿔도 narration은 그대로다.
13. **이중 조회**: 첫 `get` 직후 월드를 바꾸면 facts는 v2에서, npcs는 v1에서 온다. 플레이어 지역이 삭제되면 `region not found: a`가 나온다(둘 다 404지만 NFR-9 문구가 아니다). `say`의 이중 조회는 NFR-3이 "2회 이하"로 허용했다.
14. **빈 소문**: 빈 문장 고리 1개를 넣은 프로브의 결과는 FACTS `(nothing in particular)`, RUMORS `- [rumor] `다. "시장이 불탔다"가 프롬프트에서 사라진다.
15. **스레드풀**: UI는 패널당 한 번에 하나만 보내고 브라우저 연결도 호스트당 6개라, 한 사용자로는 40에 닿지 않는다. 여러 클라이언트나 스크립트(인증 없는 8000번 포트)가 필요하다. 턴 실행기와 번역 워밍은 자기 스레드를 쓴다.

## 2. 상한 아래 — 정리(cleanup) 지적
모두 검증 CONFIRMED이고 심각도는 low다. 정확성 지적이 우선이라 상한 밖에 두었다.

| # | 위치 | 지적 | 권장 조치 |
|---|---|---|---|
| C1 | `play/npc/dialogue.py:64`, `api/routers/play.py:186`, `web/src/routes/PlayPage.tsx:68` | `npcs_here`는 NPC마다 `get_conversation`을 따로 부른다. 부를 때마다 트랜잭션이 하나씩 열리고 모든 메시지를 검증하는데, 쓰는 것은 `len()`뿐이다(N+1). 웹은 이 요청을 `refresh()`마다 보낸다: 마운트 2회, 행동당 2회, 언어 전환 1회, `say` 뒤 1회. 그러나 개수가 바뀌는 것은 `say`뿐이다. EndTalk도 전체 대화를 읽어 개수만 센다. `list_conversations`는 프로덕션 호출처가 없다 | 포트에 `message_counts(session_id)`(LEFT JOIN + GROUP BY)를 두고 `npcs_here`·EndTalk에 쓴다. 웹은 세션·지역이 바뀔 때만 읽고, `say` 뒤에는 로컬 값을 +2 한다 |
| C2 | `api/routers/world.py:107` | 교체 정리가 id와 문장이 **같은** 재적재(에디터 "데모 월드 불러오기", World File 재 import)에서도 그 월드의 번역을 전부 지운다. 적중은 `source_hash`가 이미 가리므로 낡은 행이 나갈 일은 없다. 결과는 LLM 전체 재번역(데모 기준 20회)과 한국어가 영어로 떨어지는 공백뿐이다. 코드는 BR-U5-23(b)를 그대로 따랐으므로 **설계 규칙 조정**이 필요하다 | 새 월드에 **없는** knowledge id만 지운다(id-diff). 프로브 결과: 데모 재적재에서 0행·0회, 3개 삭제 + 1개 수정 교체에서 정확히 6행을 지우고 수정 항목만 재번역했다. BR-U5-23(b) 문구도 함께 고친다 |
| C3 | `play/npc/dialogue.py:109`, `play/storage/postgres_repo.py:497` | `say`마다 대화 전체를 읽는다(LIMIT 없음). 1000번째 `say`에서는 1998행을 읽고 그중 10개만 쓴다. `say` 한 번은 tx 6·sql 10–12이고, 세션 2회·스냅샷 2회·메시지마다 존재 확인 SELECT가 붙는다. 영향은 LLM 왕복 대비 ms 단위다 | `recent_messages(conversation_id, limit)`를 둔다. 이미 읽은 session/snapshot을 `region_sources`에 넘기고, 대화 존재 확인은 `_store`당 한 번만 한다 |
| C4 | `play/player/service.py:33/42`, `play/npc/dialogue.py:176-190`, `play/turn/advancer.py:227-235` | `PlayService.params`는 이제 아무도 읽지 않는다(호출자가 준 값이 조용히 무시된다). `_require_player`가 그대로 복사됐다. "NPC가 이 지역에 있다" 규칙이 세 곳에 있다. 알 수 없는 NPC는 start/say에서 404, EndTalk에서 400이다. 다만 이 차이는 설계(BLM §5, BR-U5-28)와 U4 테스트에 문서화돼 있어 **계약 변경**이다. advancer의 폴백은 실행될 수 없다 | `params`를 없애고, `_require_player`를 `SessionAppService`로 올린다. `npc_in_region` 헬퍼를 공유하되 각자 문서화된 상태 코드를 유지하고, advancer의 죽은 폴백을 지운다 |
| C5 | `play/storage/postgres_repo.py:467-491`, `:923-934`, `play/npc/dialogue.py:83-92/122-130` | 첫 메시지 경합을 부품 다섯 개로 막는다: 선조회, IntegrityError를 제약 이름으로 판별(SQLite는 **메시지 문자열**로), 전용 예외, 서비스 재시도 두 곳 | `INSERT … ON CONFLICT (session_id, npc_id) DO NOTHING` + SELECT로 멱등 get-or-create를 `_store`의 UoW 안에서 한다. 선례는 `shared/storage/sql.py::upsert_stmt`다. SQLite 프로브에서 두 번 create가 같은 행을 돌려줬고, PG 컴파일도 확인했다 |
| C6 | `api/deps.py:80-82`, `play/npc/dialogue.py:139-145`, `api/schemas.py:168-170`, `shared/config/settings.py:100`, `web/src/i18n.ts:333` | 표시 언어 규칙(기본값, strip/lower, 허용 목록)이 `display_lang`과 `resolve_lang`에 두 번 있다. `resolve_lang`의 유일한 프로덕션 호출처는 이미 `display_lang` 결과를 넘긴다. `enrichment_for`에 이미 어긋난 세 번째 사본(strip 없음)이 있다. 테스트 전용 `Settings.model_construct()` 폴백이 있다. "원문은 영어" 판정이 서비스(`enrich`)가 아니라 API에 있다. `isLang`이 `LANGS`를 중복한다 | 규칙 하나(`resolve_display_lang`)를 shared에 두고, `say`는 이미 결정된 lang을 받는다. 원문 언어 판정은 `TranslationService.enrich`로 옮기고, `isLang`은 `LANGS`에서 파생한다 |

가벼운 것(검증 투표 없이 목록만): `NpcContext.allowed_ids`는 테스트만 읽는다(`context_ids`와 같은 집합이고 테스트는 동어반복이다). `NpcReply.lang`·`llm_calls`는 늘 `message.lang`·1이다. `_after_replace`는 늘 있는 속성에 `getattr`을 쓰고, 보고서에 이미 있는 `world_id`를 인자로 받는다. `DialoguePanel`의 `loading`은 `!ready && error === null`로 파생할 수 있다. 언어 전환 때 번역 필드가 없는 session·log·npcs까지 다시 읽는다. 첫 `start`에서 같은 대화 행을 세 번 조회한다. `ScopeLimits` 기본값이 `PlayTuning`과 중복된다. `KNOWN_SCOPES`는 `region_known`을 다시 적은 것이다.

## 3. 상한으로 뺀 정확성 지적
| 위치 | 지적 | 판정 |
|---|---|---|
| `play/npc/prompts.py:62-68` | 플레이어 문장에 들어간 줄바꿈이 프롬프트 안에서 `FACTS:`/`RUMORS:` 구역을 **위조**한다. 다음 `say`에서 RECENT CONVERSATION으로 재생될 때 두 번째 `FACTS:` 블록이 된다. UI 입력은 한 줄이라 API 직접 호출만 해당한다. 솔로 게임이라 자기 게임에만 영향이 있지만, U6가 대화 요약을 행적으로 퍼뜨리면 범위가 넓어진다 | P (프롬프트 구조 재현) |

## 4. 기각
| 위치 | 지적 | 기각 이유 |
|---|---|---|
| `play/storage/postgres_repo.py:467` | 대화 저장소의 두 어댑터 동등성 차이: 없는 세션일 때 KeyError 대 고아 행, `created_at` 무시, id 재사용 | 도달 불가다. 쓰는 곳 둘 다 `_require_open`을 먼저 부르고, id는 uuid4이며, 세션은 삭제되지 않는다. U5 전의 `create_player`/`create_run`도 같은 차이가 있고, U4 리뷰가 "FK 없는 고아 행"으로 넘긴 항목이다. 그 항목을 처리할 때 함께 고친다 |

## 5. 문서 정확도 메모
규약 각도에서 **인용할 수 있는 CLAUDE.md 규칙 위반은 없었다**. 경계 import, ruff/black, `aidlc-docs/` 배치, audit 추가 전용, 테스트 수가 모두 맞다. 사실과 다른 문장만 있다.
- `CLAUDE.md:19`는 "`LangToggle` in `src/i18n.ts`"라고 적는다. 실제는 `features/play/LangToggle.tsx`이고, 모든 화면의 `AppNav`가 그린다.
- `CLAUDE.md:20`은 "`region_sources` = the one consensus resolve per region"이라고 적는다. 그러나 `RumorService._collect_sources`가 따로 resolve한다(direct + propagated). "세 소비자가 공유"로 좁혀 적는 편이 정확하다. code-summary.md의 "지역마다 합의를 한 번만 계산"도 같다.
- 타임라인 `event_created`에 i18n 템플릿이 없어 서버의 영어 요약이 보인다. U5 전부터 있던 공백이다.

## 6. 확인한 것
| 검사 | 값 |
|---|---|
| U5 테스트 파일(`test_dialogue`·`test_npc_scope`·`test_dialogue_api`·`test_purge`·`test_config`) | 59 passed |
| `ruff check` / `black --check` (바뀐 .py 43개) | clean |
| `tests/test_boundaries.py` | 4 passed (play → localization import 없음) |
| CLAUDE.md 테스트 수 | 545 + 56 = 601 일치 |
| i18n 키 | ko·en 129개 동일. 코드가 쓰는 `t()` 키는 모두 사전에 있고, 보간 인자도 템플릿과 일치 |

## 7. 남은 결정 (사람이 고른다)
U5 코드는 승인됐다(eed2f58). 위 지적을 고치면 **승인된 코드를 바꾸게 된다**. 선택지와 결과:
- **A. #1–#4를 지금 이 브랜치에서 고치고 게이트를 다시 돈다.** #1은 이 유닛의 핵심 체험(BR-U5-11, US-4.3/6.1)을 데모의 평범한 GM 경로에서 깨뜨린다. #2는 문서가 허용한 설정에서 화면을 통째로 막는다. 둘 다 원하시는 것에 직접 닿는다. 비용: Code Generation 재작업, 코드 게이트 재확인, 테스트 생성기 보강(체인 고리). 되돌리기 쉽다(커밋 단위).
- **B. 전부 감수 위험으로 기록하고 U6로 간다.** 비용은 없다. 대신 #1 때문에 NPC가 원문을 말하는 채로 U6(행적 전파)가 그 위에 쌓이고, U6의 대화 요약이 원문을 퍼뜨릴 수 있다.
- **C. 섞는다.** #1–#4는 지금 고치고, #5–#15와 정리 C1–C6은 U6/U7 백로그로 넘긴다. #2의 해법(서버 언어 노출)은 API 계약을 더하므로 설계 한 줄이 필요하다.
