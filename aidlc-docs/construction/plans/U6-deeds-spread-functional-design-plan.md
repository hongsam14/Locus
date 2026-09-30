# U6 행적·전파 — Functional Design 플랜

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U6의 기능 설계입니다. 플레이어가 한 일(도착·발언·선언)을 행적으로 남깁니다. 대화한 NPC는 그 행적이 전할 만한지 판단합니다. 전할 만한 행적은 소문이 되어 연결을 따라 턴마다 더 왜곡되며 퍼집니다. GM은 행적을 보고 취소할 수 있습니다. 이 단계에서는 그 규칙과 데이터·API·화면을 문서로 고정합니다. 레거시 Locus와 갈라지는 유닛입니다.

근거
- **단위 정의**: `inception/application-design/purpose-restructure/unit-of-work.md` U6. 스토리는 US-4.4·4.5·5.6·6.5·8.6이다.
- **요구와 가정**: 요구 FR-C8·C9·C10·D6·E7, FR-D2 보강. 가정 A-6(대화하지 않은 행적은 소문이 되지 않는다)과 A-7(선언은 판정 없이 서술만).
- **앱 설계**: `component-methods.md` "play — 변경 (2026-09-29)"에 P1·P2·P16·P17·P19·P8·P13·P6·S2가 있다. `services.md` §5.1~5.5도 본다.

현재 코드(U4·U5 뒤)
- `TurnAdvancer`: `_start`가 요청 안에서 즉시 상태와 타임라인을 쓰고 202를 돌려준다. 배경 실행은 턴마다 사건 계산 → 사건 지역의 캐노니컬 소문 초안(LLM, `LlmBudget`) → 한 트랜잭션(되먹임·감쇠·가지치기·승격) 순서로 돈다. `EndTalk`는 1턴이고 `NPC_TALKED`를 남긴다.
- `RumorGenerator.generate_chain`: 왜곡 단계 하나에 LLM 1회를 쓴다.
- `SessionRumor`: 기원을 나타내는 필드가 없다.
- `regenerate_region`: 승격되지 않은 소문을 모두 지운다.
- `NpcDialogueService`: 판단(`appraise`)이 없다.
- `ensure_play_schema`: `session_rumors`에 열을 더한 선례가 있다(`ALTER TABLE … ADD COLUMN`).

## 플랜
- [x] 상위 산출물·현재 코드 분석(위 근거)
- [x] 질문(아래 FD-U6 Q1~Q3) 답 수집·분석
- [x] `construction/U6-deeds-spread/functional-design/domain-entities.md`
  - 모델: `Deed`·`DeedAppraisal`·`DeclareAction`·`Narration`·`SpreadTarget`·`DeedView`
  - `SessionRumor`에 기원 필드 셋을 더한다.
  - `TimelineKind`에 `DEED_RECORDED`·`DEED_APPRAISED`·`DEED_VOIDED`·`RUMOR_SPREAD`·`ACTION_DECLARED`를 더한다.
  - `DeedStore` 포트, `PlayUnitOfWork.deeds`, 테이블 `deeds`·`deed_appraisals`, 열 추가
  - `PlayTuning`과 env, 오류
- [x] `.../business-logic-model.md`
  - 선언: 서술 → 기록 → 1턴
  - 대화 마침: 발언 요약 + 판단(LLM 1회) → 1턴
  - 턴 루프의 두 단계: 행적 씨앗과 전파
  - `plan_spread`(순수), 취소, 재생성 보존
  - NPC 컨텍스트에 자기 판단 행적을 넣는다. 사건 제안 컨텍스트에 최근 행적을 넣는다.
  - LLM 없을 때, API(`act{declare}`, `GET deeds`, `POST deeds/{d}/void`)
- [x] `.../business-rules.md`
  - BR-U6-*
  - Testable Properties
    - PBT-03 전파 불변식: 대상 가중치 ≥ 기준, 왜곡도 단조, `(origin_deed_id, region_id)` 중복 없음, 캐노니컬 기원은 전파하지 않음
    - NPC 아는 범위 불변식 확장
    - 생성기 재사용(PBT-07)
  - 예제: US-6.5 시나리오, 예산, 취소
- [x] `.../frontend-components.md`: `ActionBar` 선언 입력, `NarrationCard`, 소문 "행적" 배지, GM `DeedPanel`(판단·도달 지역·취소), i18n 키(ko·en)
- [ ] Plan Review(architecture-reviewer, adversarial ≤ 2) → `construction/U6-deeds-spread/functional-design/reviews/functional-design-review-NN.md`
- [ ] 완료 메시지 + 승인 게이트 → 다음: U6 NFR(light)

## 질문 (대화창에서 2개, 1개로 나눠 묻는다)

### FD-U6 Q1 한 행적을 누가 판단하는가 (FR-C10, US-4.4, US-5.6)
배경
- 도착과 선언 행동은 그 지역 NPC 모두가 본 일이다. 플레이어가 같은 지역에서 NPC 둘과 차례로 대화하면, 둘 다 같은 행적을 판단할 수 있다.
- 발언은 대화 상대 한 명만 들었으므로 그 NPC만 판단한다. 이 부분은 선택지와 무관하다.
- US-5.6은 GM 패널에 "판단한 NPC·판단 내용"을 보이라고 하고, US-8.6은 "같은 행적은 같은 지역에 두 번 퍼지지 않는다"를 요구한다.
- 이 답은 판단의 저장 모양(행적당 하나인지 여럿인지), 씨앗 규칙, GM 패널, PBT 불변식을 정한다.

선택지
- A. 대화한 NPC마다 판단하고, 씨앗은 한 행적에 하나 — **권장**. 누구에게 말하느냐가 의미를 가진다. 수다스러운 여관 주인에게 말하면 퍼지고, 입 무거운 대장장이에게만 말하면 묻힌다.
  - 결과: 판단은 모두 기록되어 GM 패널에 보인다. 가장 먼저 "전할 만하다"고 한 판단 하나만 소문 씨앗이 된다. 불변식 "(행적, 지역) 중복 없음"은 그대로다.
  - 비용: 대화를 마칠 때마다 판단 LLM 1회.
- B. 한 행적은 처음 대화한 NPC 하나만 판단
  - 결과: 가장 단순하다. 두 번째 NPC는 자기에게 한 발언만 판단하므로, 첫 NPC가 "전할 것 없다"고 하면 그 도착·선언은 다시 기회가 없다.
  - 비용: A와 같은 호출 수에 판단 행이 적다.
- C. 대화한 NPC마다 판단하고 각자 씨앗
  - 결과: 같은 행적이 한 지역에서 여러 판본으로 퍼진다.
  - 비용: 불변식을 "(행적, NPC, 지역) 중복 없음"으로 바꿔야 하고, 행적 하나가 만드는 소문 수가 NPC 수만큼 는다. 지역당 상한(US-8.6)과 부딪친다.
- X. Other (please specify)

[Answer]: X — A와 C의 하이브리드. "대화는 A(1대1 communication이니까). 행동은 C(목격을 모두가 하기 때문)". 해석: `statement`는 들은 NPC 한 명이 판단하고 씨앗 하나. `arrival`·`declared_action`은 목격한 NPC마다 판단하고, 전할 만하다는 판단마다 그 NPC의 판본이 씨앗이 된다. 행동 행적의 불변식은 `(행적, 판단한 NPC, 지역)` 중복 없음이다. 판본마다 따로 퍼지며, 비용은 지역·턴당 전파 상한과 지역당 활성 상한이 묶는다.

### FD-U6 Q2 턴 LLM 예산을 무엇에 먼저 쓰는가 (FR-E7, US-8.6, NFR-5)
배경
- 턴당 LLM 예산은 `LLM_MAX_CALLS_PER_TURN`(8)이고, 지금은 사건 지역의 캐노니컬 소문 초안이 다 쓴다.
- U6에서 새로 드는 호출은 넷이다. 선언 서술과 대화 마침 판단은 행동 1회에 각 1회다. 행적 씨앗은 0회다(NPC의 `retelling`이 곧 소문 문장이다). 전파는 대상 지역 하나에 1회다.
- 설계 원칙(services §5.5)은 "모든 새 호출은 턴 예산 안"이다. 서술과 판단은 행동 자체라 건너뛸 수 없으므로 어느 선택지에서든 먼저 예약한다.
- 이 답은 사건이 많은 턴에 내 행적과 캐노니컬 소문 중 무엇이 늦어지는지를 정한다.

선택지
- A. 행적 전파가 캐노니컬 새 소문보다 먼저 — **권장**. US-6.5의 "두세 턴 뒤 이웃 지역에서 듣는다"가 사건 개수에 흔들리지 않는다.
  - 결과: 사건이 여럿 걸린 턴에는 캐노니컬 새 소문 일부가 다음 턴으로 밀린다. 지금도 예산이 모자라면 그렇게 밀린다.
  - 비용: 전파는 지역·턴당 1개 상한이 있어 한 턴에 많아야 지역 수만큼이다.
- B. 캐노니컬이 먼저(지금 순서 유지), 행적 전파는 남은 예산
  - 결과: U4 동작이 그대로다. 사건이 많은 턴에는 내 행적이 늦게 퍼진다. 데모에서 사건 씨앗과 겹치면 US-6.5가 기대보다 늦게 보일 수 있다.
- C. 예산을 반씩 나누고, 남는 몫은 다른 쪽으로 넘긴다
  - 결과: 둘 다 굶지 않는다. 대신 규칙 하나와 조정값 하나가 는다.
  - 비용: 테스트할 경계가 늘어난다.
- X. Other (please specify)

[Answer]: A — 행적 전파가 먼저(서술·판단은 행동 자체라 먼저 예약).

### FD-U6 Q3 선언 서술을 어떤 언어로 만들고 남기는가 (FR-C9, US-4.5, US-9.x)
배경
- 선언의 결과 서술은 플레이어가 바로 읽는 글이면서, 행적 기록(GM 패널, 사건 제안 컨텍스트, NPC 판단의 입력)이기도 하다.
- 저장 텍스트는 영어가 원칙이다(C-1). U5 대화는 표시 언어로 생성해 번역하지 않는 예외다(A-1).
- 다른 행적의 텍스트는 영어다. 도착은 결정적 영어 문장이고, 발언 요약은 판단 호출이 영어로 만든다.
- 이 답은 서술 프롬프트의 출력 모양, 행적 텍스트의 언어, GM 패널의 번역 경로를 정한다.

선택지
- A. 한 번의 호출로 두 가지를 만든다 — **권장**. 즉시성과 기록 언어의 일관성을 둘 다 지킨다.
  - 결과: 플레이어에게 보일 서술은 표시 언어로, 행적 기록은 영어 한 줄로 만든다(구조화 출력). 플레이어는 곧바로 한국어 서술을 보고, 행적은 모두 영어로 남아 번역 캐시가 GM 패널을 한국어로 보여 준다.
  - 비용: 출력이 한 줄 는다.
- B. 표시 언어로 서술하고 그 글을 그대로 행적으로 남긴다(`lang` 기록, U5 대화와 같은 방식)
  - 결과: 가장 단순하다. 다만 행적 텍스트가 언어별로 섞이고, GM 패널과 사건 제안 프롬프트에 한국어 행적이 섞인다.
- C. 영어로 서술하고 번역 캐시로 보여 준다
  - 결과: 저장은 일관된다. 번역이 비동기라 방금 선언한 결과가 처음에는 영어로 보일 수 있다.
- X. Other (please specify)

[Answer]: A — 한 호출로 표시 언어 서술과 영어 기록을 함께 만든다.

## 가정 (질문하지 않는 것 — 게이트에서 바꿀 수 있다)
| # | 가정 | 근거 |
|---|---|---|
| A6-1 | 서술(선언)과 판단(대화 마침)의 LLM 호출은 배경 턴 실행 안에서 첫 턴의 트랜잭션 전에 한다. 요청은 지금처럼 202로 바로 답한다. 서술은 `TurnRun` 결과에 실려 폴링으로 화면에 온다. 요청이 LLM을 기다리며 최대 93초 막히지 않게 하려는 것이다 | U4 Q4=A, services §4 "LLM은 트랜잭션 밖" |
| A6-2 | 행적 셋. `arrival`은 `Move`로 도착할 때 생기는 결정적 영어 문장이다. `statement`는 대화를 마칠 때 판단 호출이 그 대화의 플레이어 발언을 영어 한 줄로 요약한 것이며, 플레이어가 말하지 않았으면 만들지 않는다. `declared_action`은 선언 서술의 기록이다. 목격자는 그 지역 NPC 전원이고, `statement`만 대화 상대 한 명이다 | FR-C8 |
| A6-3 | 판단 대상은 현재 체류(마지막 도착 이후) 중 이 지역에서 생긴 행적 가운데, 이 NPC가 목격했고 아직 판단하지 않은 것이다. 지역을 떠나면 판단 없는 행적은 기회가 끝난다 | A-6 |
| A6-4 | 씨앗: `noteworthy ∧ salience ≥ deed_seed_min_salience(0.5)`인 판단이 다음 턴 처리 때 행적 지역에 소문 하나로 태어난다. 문장은 `retelling`(영어)이고 **추가 LLM 호출은 없다**(services §5.3의 "retelling 원문의 소문 체인" 대신: NPC의 말이 이미 그 지역의 왜곡이다). 왜곡도는 그 지역 왜곡도이고, 지지도는 `birth_support × (1 + salience)`라 0.2~0.4다. 그래서 강화 없이도 4~8턴을 버티며 이웃으로 퍼질 시간이 있다. 기원 필드는 `origin_kind="deed"`와 `origin_deed_id`이다 | FR-C10, US-6.5 |
| A6-5 | 전파는 한 턴에 한 칸이다. 행적 기원 활성 소문이 있는 지역 X의 이웃 Y 가운데, 막힌 길을 빼고 아직 도달하지 않은 곳이 후보다. 도달 가중치는 `w(Y) = w(X) × edge(X,Y)`이고 원점은 1이다. `w ≥ spread_min_weight(0.15)`이면 대상이 된다. 왜곡도는 `max(부모, 1 − w)`, 지지도는 `부모 × w`다. 지역·턴당 `max_spread_per_region_turn(1)`개까지이며, 대상 하나에 LLM 1회로 부모 문장을 한 단계 왜곡한다. 도달 기록 `(origin_deed_id, region_id)`는 비활성·가지치기된 것도 포함해 영구적이라, 같은 행적은 한 지역에 두 번 오지 않는다 | FR-E7, US-6.5, US-8.6 |
| A6-6 | 캐노니컬 기원 소문은 전파하지 않는다. 재생성은 행적 기원 소문을 지우지 않는다 | services §5.5 |
| A6-7 | 취소: 행적을 `voided`로 바꾸고, 그 행적 기원 소문 전부(전파·승격 포함)를 `active=false`로 둔다. 이후에는 씨앗도 전파도 없다. `DEED_VOIDED`를 남기며 되돌리기는 없다. 진행 중인 턴이 있으면 409다(U4의 GM 쓰기 규칙) | FR-D6, US-5.6 |
| A6-8 | LLM이 없을 때: 선언은 서술 없이 받아들여 선언 원문을 행적으로 남기고, 고정 안내 문구를 붙여 1턴을 쓴다. 대화 마침은 판단 없이 1턴이다. 전파는 멈추고 씨앗은 판단이 없으니 생기지 않는다 | NFR-4 |
| A6-9 | NPC 대화 컨텍스트에 그 NPC가 판단한 행적(`retelling`)을 "들은 나그네 이야기"로 넣는다. 최대 5개이고 `NPC_MAX_DEEDS`로 조정한다 | P12 |
| A6-10 | 사건 제안 컨텍스트에 취소되지 않은 최근 행적 5개를 넣는다(영어 텍스트 + 판단 `retelling`) | FR-D2 보강 |
| A6-11 | 조정값과 env. `spread_min_weight=0.15`, `deed_seed_min_salience=0.5`, `max_spread_per_region_turn=1`, `declare_max_chars=300`에 `npc_max_deeds=5`를 더한다. env는 `SPREAD_MIN_WEIGHT`·`DEED_SEED_MIN_SALIENCE`·`MAX_SPREAD_PER_REGION_TURN`·`DECLARE_MAX_CHARS`·`NPC_MAX_DEEDS` 다섯이다 | S2 |
| A6-12 | 스키마: `deeds`와 `deed_appraisals` 테이블을 새로 만든다. `session_rumors`에 `origin_kind`(기본 `canonical`)·`origin_deed_id`·`spread_from_region_id`를 `ensure_play_schema`가 없으면 더한다(선례 있음, 데이터 보존). 이 밖의 마이그레이션은 없다 | P3, 코드 확인 |
| A6-13 | 화면. `ActionBar`에 선언 입력(글자 수 표시)을 두고, 실행 결과의 서술은 `NarrationCard`로 보인다. 지역 화면과 GM 소문 목록에는 행적 기원 소문에 "행적" 배지를 단다. GM 화면(`GmPage`)에는 `DeedPanel`을 더해 행적·판단·도달 지역과 취소(확인창)를 보인다. GM 화면의 기능별 분할은 U7이다 | F3·F4 |
