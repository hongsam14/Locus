# Application Design Plan — Purpose Restructure Cycle (2026-09-29)

**원하시는 것**: 월드를 만들고 그 안에서 소문·사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG로 Locus를 다시 짜는 것(포트폴리오·데모).
**지금 하는 것**: Application Design 계획. 다섯 경계의 실제 패키지 이름·배치, 조립 방식, 포트 분할, 새 컴포넌트(Player·Movement·NPC Dialogue·World File·Editor), API 접두어, 용어, 프론트 화면 구조를 정합니다. 이 답으로 `components.md` / `component-methods.md` / `services.md` / `component-dependency.md` / `application-design.md`를 만들고, Units Generation이 그 위에서 유닛 7개를 확정합니다.

**입력**: 요구사항 FR-A(경계), FR-B~I / 스토리 E7(읽히는 구조) / RE `architecture.md`·`code-quality-assessment.md` §D(부채: 비대한 포트, 파사드 과잉, 조립 루트 하나, 역방향 의존) / 사용자 선호(DI, 기능별 단일 책임 서비스, 도메인 패턴 — 메모리).

**산출물 위치**: `aidlc-docs/inception/application-design/purpose-restructure/`.

답은 `[Answer]:` 뒤에 글자로 적어 주세요. 대화창에서 답하셔도 되고, **"나머지는 권장대로"**라고 하시면 남은 질문은 권장안으로 진행합니다.

---

## Design Questions

## Question AD-R1 — 최상위 패키지 배치
**배경**: 요구사항 FR-A1은 경계 다섯 개(월드 구성 / 지역 지식 계산 / 플레이 / 로컬라이징 / 공용)를 요구하고, 스토리 US-7.1은 "`locus/` 최상위만 보고 구조를 짚는다"를 수용 기준으로 둡니다. 지금 `locus/`에는 하위 패키지 14개가 평평하게 있습니다. 이 답에 따라 파일 이동 범위(U1의 크기), import 경로, README 디렉터리 절이 정해집니다.

A) **다섯 패키지로 완전히 접는다** *(권장)*: `locus/world/`(ingestion, topology, ontology, wiki, augmentation, editor, worldfile, demo), `locus/knowledge/`(consensus, loader, query), `locus/play/`(session, player, rumor, event, turn, npc, gm, storage), `locus/localization/`(translation), `locus/shared/`(models, config, llm, storage ports·Neo4j·OpenSearch 어댑터·mapping). — 최상위 5개만 보인다. 이동 범위가 가장 크지만(모든 import 경로), 목적이 배치로 가장 뚜렷하다. **권장 이유**: US-7.1의 수용 기준을 그대로 만족한다.
B) **네 경계만 접고 공용은 평평하게 둔다**: `locus/{world,knowledge,play,localization}` + `locus/{models,config,llm,storage}` 그대로. — 최상위가 8개다. 이동이 조금 줄지만 "공용"이 경계로 보이지 않는다.
C) **경계별 별도 배포 패키지**(`locus-world`, `locus-play` …). — 분리는 가장 강하지만 단일 저장소·단일 배포인 이 프로젝트에는 과하다. 빌드 설정과 버전 관리가 늘어난다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 다섯 패키지로 완전히 접기 (대화창 답변, 2026-09-29)

## Question AD-R2 — 조립 루트(Composition Root)
**배경**: 지금 `api/main.py::_wire_default` 하나가 캐노니컬·세션·번역을 함께 만들어 `app.state`에 넣고, 라우터는 문자열 이름으로 꺼냅니다(RE §D). FR-A3은 "경계마다 조립 함수, 한 경계가 없어도 다른 경계는 503이 되지 않음"을 요구합니다. 이 답에 따라 DI 구조와 테스트에서 경계를 따로 띄우는 방법이 정해집니다.

A) **경계별 `wiring.py` + 컨테이너 객체** *(권장)*: 각 경계에 `assemble_<boundary>(settings, shared) -> <Boundary>Container`(dataclass, 서비스 필드 타입 명시)를 두고, `api/main.py`는 컨테이너 넷을 만들어 라우터에 주입한다. 라우터는 `Depends`로 자기 컨테이너만 받는다. — 타입이 살고, 테스트는 컨테이너 하나만 fake로 만들면 된다. `app.state` 문자열 조회가 사라진다. **권장 이유**: DI 선호와 맞고, FR-A3의 "경계 독립 기동"이 자연히 나온다.
B) **단일 `main.py`를 유지하고 함수만 경계별로 나눈다**: `_wire_world()`, `_wire_play()` … 가 `app.state`에 넣는 방식은 그대로. — 변경이 작지만 문자열 조회와 단일 루트가 남는다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 경계별 wiring + 타입 컨테이너 (대화창 답변, 2026-09-29)

## Question AD-R3 — 저장소 포트 분할
**배경**: `SessionRepository`는 약 27개 메서드로 세션·소문·왜곡도·타임라인·사건·번역 6가지 관심사를 한 Protocol에 담고 있습니다(RE §D). FR-A4는 관심사별 분할을 요구하고, 이번에 Player·대화 이력이 더해집니다. 이 답에 따라 포트 수, 어댑터 구조, 트랜잭션 경계가 정해집니다.

A) **Protocol은 관심사별로 나누고, PostgreSQL 어댑터는 하나가 모두 구현한다** *(권장)*: `SessionStore`, `RumorStore`, `EventStore`, `DistortionStore`, `TimelineStore`, `PlayerStore`, `ConversationStore`(play) + `TranslationStore`(localization). `PostgresPlayRepository` 한 클래스가 play 포트 7개를 구현해 같은 엔진·트랜잭션을 공유한다. 인메모리 어댑터도 같은 구조. — 소비자는 필요한 포트만 받고(인터페이스 분리), 턴 저장은 하나의 트랜잭션에 묶을 수 있다. **권장 이유**: 분리와 트랜잭션 단일성을 둘 다 얻는다.
B) **Protocol과 어댑터를 모두 나눈다**(포트마다 어댑터 클래스). — 가장 깔끔하지만 턴 저장을 한 트랜잭션으로 묶으려면 UnitOfWork를 따로 만들어야 한다.
C) **지금처럼 하나로 둔다**(번역만 분리). — 변경이 가장 작지만 FR-A4를 만족하지 않는다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — Protocol은 나누고 PG 어댑터는 하나 (대화창 답변, 2026-09-29)

## Question AD-R4 — GameMaster 파사드 처리
**배경**: `GameMasterService`는 하위 서비스 5개(Rumor·Event·Distortion·Feedback·Turn)에 넘기기만 하는 파사드입니다(`_repo` 미사용, `**kwargs`로 타입 소실 — RE §D). 사용자 선호는 DI와 기능별 단일 책임 서비스입니다. 이번에 GM 모드는 "플레이 화면에서 드나드는 모드"가 됩니다. 이 답에 따라 play 경계의 서비스 구성과 라우터 주입 방식이 정해집니다.

A) **파사드를 없애고 라우터가 단일 책임 서비스를 직접 받는다** *(권장)*: `RumorService`, `EventService`, `DistortionService`, `TurnAdvancer`(턴 오케스트레이터), 새 `PlayService`(플레이어 행동), `NpcDialogueService`. GM 라우터는 필요한 서비스를 컨테이너에서 받는다. — 레이어 하나가 줄고 타입이 산다. **권장 이유**: 넘기기만 하는 층은 DI에서 얻는 것이 없다.
B) **파사드를 남기되 턴 오케스트레이션만 맡긴다**(`TurnAdvancer`를 흡수해 `GameMaster`로 이름 유지). — "GameMaster"라는 도메인 이름이 코드에 남는다. 대신 다른 서비스로의 위임은 없앤다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 없애고 라우터가 서비스를 직접 받기 (대화창 답변, 2026-09-29)

## Question AD-R5 — 플레이어 행동과 턴 엔진의 관계
**배경**: FR-C3은 "이동·대화 마침·기다리기가 턴을 소모하고, 턴이 소모될 때 기존 턴 엔진이 돈다"입니다. 이동 비용은 연결 가중치에 따라 여러 턴일 수 있습니다(A-5, 공식은 FD). 지금 `advance_turn`은 한 턴을 처리합니다. 이 답에 따라 새 컴포넌트의 책임과 턴 엔진 변경 범위가 정해집니다.

A) **`PlayService`가 행동을 턴 비용으로 바꾸고 `TurnAdvancer.advance_turn`을 비용만큼 반복 호출한다** *(권장)*: 턴 엔진은 그대로 "한 턴"만 알고, 행동·이동 규칙(`movement.py` 순수 함수)은 PlayService에 있다. 결과는 여러 `TurnResult`를 플레이어 시점 요약으로 접는다. — 턴 엔진 변경이 없어 기존 테스트가 산다. 비용이 큰 이동은 LLM 호출이 그만큼 늘어나므로 NFR-5 상한과 함께 본다. **권장 이유**: 책임이 나뉘고 기존 엔진을 건드리지 않는다.
B) **턴 엔진을 확장해 행동을 입력으로 받는다**(`advance_turn(action)`). — 호출이 한 번이지만 엔진이 플레이어 규칙을 알게 되어 결합이 늘고, GM 수동 턴과 경로가 갈린다.
X) Other (please describe after [Answer]: tag below)

[Answer]: B — 턴 엔진을 확장해 행동을 입력으로 (대화창 답변, 2026-09-29). 설계 반영: `TurnAdvancer.advance(session_id, action: PlayerAction | None)`; GM 수동 턴은 `action=None`(또는 `Wait`)으로 같은 진입점을 쓴다. 이동 규칙은 `movement.py` 순수 함수로 두고 엔진이 호출한다. 여러 턴 비용은 엔진 안에서 반복 처리하고 하나의 `ActionResult`로 돌려준다.

## Question AD-R6 — API 접두어
**배경**: FR-A6은 경계에 맞는 접두어를 요구하고 Q4=A로 호환을 깰 수 있습니다. 지금은 `/api/query`, `/api/authoring`, `/api/session`입니다. 세션 지역 지식 API는 유지해야 합니다(FR-F5). 이 답에 따라 라우터 파일 구성과 프론트 `api.ts` 구조가 정해집니다.

A) **네 접두어** *(권장)*: `/api/world`(빌드·편집·World File·NPC 편집·보강·wiki), `/api/knowledge`(캐노니컬 지역 지식·비교 — 외부 소비자용), `/api/play`(세션·플레이어·이동·행동·대화·세션 지역 지식), `/api/gm`(사건·소문·왜곡도·수동 턴·타임라인·세계 상태). — 화면 셋(에디터·플레이어·GM)과 1:1로 읽힌다. **권장 이유**: 관람자가 라우터 이름만 보고 화면을 떠올릴 수 있다.
B) **세 접두어**: `/api/world`, `/api/knowledge`, `/api/play`(GM 도구도 `/api/play/.../gm/...` 하위). — play 경계와 1:1이지만 GM 경로가 깊어진다.
C) **지금 접두어 유지**. — 프론트 변경이 줄지만 경계와 이름이 어긋난다(FR-A6 미충족).
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 네 접두어 world / knowledge / play / gm (대화창 답변, 2026-09-29)

## Question AD-R7 — 캐노니컬 "거리 소문"의 새 이름
**배경**: 요구사항 §4에 따라 `rumor`는 세션 LLM 소문에만 쓰고, 캐노니컬의 "연결이 약해 소문으로만 아는 지식"(`ConsensusView.rumors`, `ScopeType` 확장)은 다른 이름이 필요합니다. 함께 바꾸는 것: 캐노니컬 `distortion_degree` → `path_decay`, 보강 `session` → `augmentation_run`(이 둘은 질문 없이 진행). 이 답에 따라 `ScopeType`·`KnowledgeView`·NPC 화면 라벨이 정해집니다.

A) **`hearsay`(전언)** *(권장)*: `ScopeType.HEARSAY`, `ConsensusView.hearsay`, 화면 라벨 "전해 들은 이야기". — "소문(rumor)"과 뜻이 가까우면서도 다른 단어라 구분이 쉽다. **권장 이유**: NPC 대화에서 "들었다"는 전언 표현(US-4.3)과 자연스럽게 이어진다.
B) **`distant`**: `ScopeType.DISTANT`, 라벨 "먼 곳의 이야기". — 거리 기반이라는 원리를 드러내지만 지식의 성질(불확실)은 덜 보인다.
C) **별도 이름 없이 `scope_type=propagated` + `path_decay` 값으로만 구분**. — enum이 하나 줄지만 화면과 프롬프트에서 매번 값을 해석해야 한다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — hearsay (대화창 답변, 2026-09-29)

## Question AD-R8 — 프론트 화면 구조
**배경**: 지금 `web/`는 라우터 없는 단일 페이지에 패널이 쌓인 구조이고 `SessionPanel`이 518줄입니다. 이번에 에디터 / 플레이어 / GM 모드 세 화면이 필요하고, 포트폴리오라 화면별 URL(스크린샷·링크)이 유용합니다. 이 답에 따라 프론트 의존성, 화면 전환 방식, 컴포넌트 트리가 정해집니다.

A) **`react-router`로 화면 3개(`/editor`, `/play/:sessionId`, `/gm/:sessionId`)를 두고, 상태는 지금처럼 hooks(+ 작은 context)로 관리한다** *(권장)*: 의존성 하나(react-router-dom)가 늘고, 각 화면이 자기 컴포넌트 트리를 가진다. GM 모드 전환은 `/play` ↔ `/gm` 이동이며 세션 상태는 서버에 있어 유지된다. — **권장 이유**: 화면마다 URL이 생겨 README 스크린샷과 데모 안내가 쉽고, god component가 자연히 나뉜다.
B) **라우터 없이 상태 기반 모드 전환**(`mode: 'editor' | 'play' | 'gm'`). — 의존성이 늘지 않지만 URL이 하나라 화면 공유가 어렵고, 전환 상태를 손으로 관리해야 한다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — react-router로 화면 3개 (대화창 답변, 2026-09-29)

---

## 답변 분석 (Step 8)
- AD-R1=A, AD-R2=A, AD-R3=A, AD-R4=A, **AD-R5=B**, AD-R6=A, AD-R7=A, AD-R8=A. 전부 단일 선택이고 서로 어긋나지 않는다. AD-R5만 권장과 다르며(턴 엔진이 행동을 입력으로 받음), AD-R4(파사드 제거)와 함께 보면 `TurnAdvancer.advance(session_id, action)`이 play의 유일한 시간 진행 진입점이 된다 — 일관됨. 후속 질문 없음.

---

## 질문 없이 진행하는 설계 결정 (산출물에 근거와 함께 적음)
- **NPC "아는 범위" 계산**은 play 경계의 순수 모듈(`npc_scope.py`)에 둔다. 입력은 knowledge 경계의 합의 뷰 + play의 활성 소문, 출력은 컨텍스트 항목 목록. NPC 모델 자체는 world(캐노니컬 노드)에 있다.
- **세션 단위 월드 캐시**는 knowledge 경계의 `WorldCache`(로더 앞)로 두고, play가 세션 시작 시 채우고 world가 월드 교체 시 무효화한다(NFR-3, NFR-9).
- **World File import**는 "기존 월드 삭제 → 저장" 순서로 하고, 부분 실패는 리포트로 남긴다(Neo4j 다중 문 트랜잭션 제한).
- **대화 이력**은 세션·NPC별로 전체 저장하고, 프롬프트에는 최근 N턴만 넣는다(N은 FD).
- **조정값 집약**은 `shared/config`에 경계별 설정 dataclass(`WorldTuning`, `KnowledgeTuning`, `PlayTuning`)로 두고 `Settings`가 환경 변수에서 채운다(FR-A7).
- **이벤트 제안 컨텍스트**는 world 경계가 아니라 knowledge 경계의 읽기 API(지역 이름·설명·주요 지식)로 얻는다(FR-D2).

## Execution Checklist (승인 뒤 실행)
- [x] 1. AD-R1~R8 답 분석 — 모두 단일·일관, 후속 질문 없음 (AD-R5=B만 비권장)
- [x] 2. `components.md` — S1~S5 / K1~K6 / W1~W12 / P1~P15 / L1~L5 / A1~A7 / F1~F7
- [x] 3. `component-methods.md` — 시그니처·타입
- [x] 4. `services.md` — 조립, 경계별 서비스, 흐름 9개, 트랜잭션·동시성 원칙
- [x] 5. `component-dependency.md` — 경계 행렬, 컴포넌트 그래프, 통신 패턴, 데이터 흐름, RE 부채 15건 → 새 위치
- [x] 6. `application-design.md` — 통합 + 트리 + 라우터 표 + 용어 매핑 + 커버리지
- [x] 7. 검증 — FR-A1~A7 전부 충족, E7 스토리 매핑, RE 부채 전부 새 위치 있음
- [x] 8. `aidlc-state.md`·`audit.md` 갱신, 완료 메시지 (2026-09-29)

---

## 변경 요청 (2026-09-29, 산출물 생성 뒤) — "플레이어의 행동이 소문으로 퍼질 수 있다"

**배경**: 지금 설계에서 소문(`SessionRumor`)의 원천은 캐노니컬 지식(direct + hearsay)과 기존 소문, 그리고 사건이 지역 왜곡도를 바꿔 유발하는 재생성뿐이다. 플레이어는 세계를 보고 듣기만 한다. 사용자 피드백: 플레이어의 행동 자체가 소문으로 퍼질 수 있어야 하며, 이것이 레거시 Locus와 갈라지는 지점이다. 이를 반영하려면 **세션 기원 소문 원천(플레이어 행적)**과 그 **전파 방식**을 정해야 한다. 요구사항(FR-C8·FR-E7 추가)과 스토리(E4·E6 추가)에도 부록으로 반영한다.

## Question AD-R9 — 무엇이 "행적(deed)"이 되는가
**배경**: 플레이어 상태는 이름·위치·턴만 있다(A-3, 스탯·전투 없음). 지금 행동은 `Move`·`Wait`·`EndTalk`이고, 대화는 자유 텍스트다. 행적이 되는 범위에 따라 새 모델(`Deed`)의 생성 지점, LLM 호출 수, 플레이어가 세계에 영향을 주는 방식이 정해진다.

A) **자동 행적만**: 지역 도착(`Move`)과 대화에서 플레이어가 NPC에게 **말한 내용**(주장·질문 요약)이 행적이 된다. — 새 UI 없음. 플레이어는 "어디에 나타났고 무엇을 물었는가"로 소문이 된다. 플레이어가 NPC에게 거짓을 말하면 그 거짓이 소문으로 퍼질 수 있다(의도적 소문 뿌리기 가능). LLM 호출: 대화 마침 때 요약 1회.
B) **A + 자유 텍스트 행동 선언** *(권장)*: 플레이어가 "시장 광장에서 도둑을 붙잡았다"처럼 행동을 선언하면 LLM GM이 결과를 짧게 서술하고(판정 없음, 서술만) 그 결과가 행적이 된다. — TRPG의 핵심 감각("내가 한 일이 이야기가 된다")이 생긴다. 새 행동 `Declare(text)`, 새 UI(행동 입력), LLM 호출 1회/선언. 스탯이 없으므로 성공·실패는 LLM 서술에 맡기고 GM 모드에서 취소할 수 있다. **권장 이유**: "월드를 구성하고 동적인 TableRPG를 플레이"(Q1)에 가장 가깝다.
C) **자유 텍스트 선언만** (도착·대화는 행적이 아님). — 플레이어가 명시적으로 한 일만 소문이 된다. 조용히 다니면 흔적이 없다. 구현은 B보다 작다.
X) Other (please describe after [Answer]: tag below)

[Answer]: B (대화창 선택지 "(1)" = 자동 행적 + 자유 텍스트 행동 선언) **+ 조건** — "하지만 모든 행적이 소문이 되면 이상하기 때문에(실제 세계에서 한 사람의 대화와 행동이 모든 소문이 되는게 말이 안됨) '행동'의 attribute가 존재해야 함. 그리고 그것은 대화를 한 npc가 결정함." (2026-09-29) → 설계 반영: 행적(`Deed`)은 기록되지만 소문이 되는지는 **대화한 NPC의 판단(`DeedAppraisal`: noteworthy · salience · slant · retelling)**이 정한다. 대화하지 않은 행적은 소문이 되지 않는다(가정 A-6).

## Question AD-R10 — 행적이 어떻게 퍼지는가
**배경**: 지금 세션 소문은 **지역에 갇혀 있다**. 지역마다 그 지역의 합의 뷰에서 소문을 만들고, 지역 사이를 건너가는 것은 캐노니컬 hearsay 계산(경로 가중치)뿐이다. 행적은 캐노니컬에 없으므로, 다른 지역이 알게 하려면 **세션 기원 내용이 토폴로지를 따라 퍼지는 새 메커니즘**이 필요하다. 이 답에 따라 `TurnAdvancer` 안의 새 단계, 소문 모델의 원천 종류, US-6.1의 범위가 정해진다.

A) **토폴로지 전파** *(권장)*: 행적은 발생 지역에서 소문으로 태어나고, 턴마다 연결 가중치를 따라 이웃 지역으로 퍼진다. 도달 가중치 `w`(최대 곱 경로)가 기준 이상이면 그 지역에 `1 − w`만큼 더 왜곡된 소문이 생긴다(사건 전파 `propagate_delta`와 같은 원리, 소문 왜곡 체인 재사용). 퍼진 소문은 지지도·가지치기·승격 규칙을 그대로 따른다. — 먼 지역 NPC가 플레이어의 행적을 틀리게 전한다(US-6.1이 플레이어 자신의 일로 확장). 새 단계 "소문 전파"가 턴 루프에 들어가고, 지역당 상한·LLM 예산이 전파에도 걸린다. **권장 이유**: "소문이 지형을 따라 퍼진다"는 목적 문장을 플레이어의 일에도 그대로 적용한다.
B) **발생 지역에만**: 행적은 그 지역 소문이 되고 다른 지역으로 퍼지지 않는다. — 구현이 작다. 대신 플레이어가 다른 지역에 가면 자기 일을 아무도 모른다. 사건 전파와 비대칭이다.
C) **전파는 하되 LLM 없이**: 이웃 지역에는 원문 그대로(왜곡 없이) 복사되고 왜곡도만 표시한다. — LLM 비용이 없지만 "틀리게 전한다"는 감각이 약하다. NPC 대화 때 왜곡도를 프롬프트에 넣어 말투로만 흐리게 한다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 토폴로지를 따라 턴마다 왜곡되며 전파 (대화창 답변, 2026-09-29)

**답변 분석**: AD-R9=B+조건, AD-R10=A. 조건("NPC가 정한다")은 B를 좁히는 것이라 모순이 아니다. 후속 질문 없음. 반영 범위: 요구사항 부록 A(FR-C8·C9·C10·E7·D6, 가정 A-6·A-7), 스토리 +5(US-4.4·4.5·5.6·6.5·8.6), 설계 산출물 5종 "변경" 절.

**질문 없이 반영하는 것**: 행적은 GM 사건 제안 컨텍스트에도 들어간다(플레이어의 일이 사건을 낳을 수 있음). 행적은 세션 레이어에만 있고 캐노니컬은 바꾸지 않는다. 승격된 행적 소문은 기존 승격 규칙대로 "세션 안의 사실"이 된다.
