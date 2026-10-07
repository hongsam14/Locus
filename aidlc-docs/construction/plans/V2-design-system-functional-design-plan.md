# V2 디자인 시스템 — Functional Design Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V2(실행 2/9), Functional Design. 네 화면이 모두 올라설 디자인 기반을 정한다. 시안을 골라 토큰·글꼴·프리미티브·배치 틀·지도·표기 규칙·오류 문장을 정한다.

**입력**:
- 요구사항 `inception/requirements/follow-up-requirements.md`: FR-D1~D9, FR-S5·S6, FR-C13(도구), NFR-3·4·7. 결정 CQ1=A(TRPG·판타지), CQ2=A(톤 하나), CQ3=A(HTML 시안), CQ4=A(홈·플레이만 휴대폰).
- 설계 `inception/application-design/follow-up/{components,component-methods,component-dependency}.md` § 1 웹, § 7 `api/errors.py`.
- 유닛 `unit-of-work.md` V2, 맵 `unit-of-work-story-map.md`, 의존 `unit-of-work-dependency.md` § 3·4.
- 역공학 `inception/reverse-engineering/screen-inventory.md`(UX-01~42), `code-quality-assessment.md`(RE-F09).
- 이 단계에서 닫을 리뷰 지적:
  - Units R-01: 새 폴더와 옮길 파일을 구분하고, `layout.ts`·`i18n.ts`가 폴더 이름과 겹치는 문제를 정한다.
  - Units R-05(c): RE-F09(`capabilities.ts`)를 V2에 넣을지 정한다.
  - Requirements R-01(공유 대화상자 교체)과 R-05(대비 확인 방법, 폭 상한 값)는 이 FD와 NFR light에서 정한다.

**산출물 위치**: `aidlc-docs/construction/V2-design-system/functional-design/`

---

## 계획 (checkbox)

- [x] 1. 시안 세 안을 비공개 Artifact 캔버스 하나에 그린다(FR-D1, C-1). 안마다 네 장을 둔다: 홈(1280), 플레이(1280), 플레이(390 휴대폰), 토큰·프리미티브 견본. 데모 Emberleaf의 실제 내용을 쓴다. 저장소에는 시안 코드를 두지 않는다
- [x] 2. 질문 Q1(시안)·Q2(문체)의 답을 받고, 모호함이 있으면 다시 묻는다
- [x] 3. `business-logic-model.md`를 쓴다
  - 토큰 체계(의미 이름 → 값)
  - 표기 규칙의 흐름(enum 라벨, 플레이어용 말 단계, GM·에디터용 숫자와 뜻, 날짜)
  - 오류 응답 → 사용자 문장 고르기(`code` 우선, 상태 코드 다음, 원문은 접어 둠)
  - 요청 도우미의 상태 흐름(`useResource`: 취소·늦은 답 버리기, `useAction`: 이중 실행 막기)
  - 지도 좌표 정규화와 라벨·표식 배치
- [x] 4. `business-rules.md`를 쓴다(BR-V2-*)
  - 원색 값·원문 enum·`String(e)` 금지
  - 대비 기준과 확인 방법(토큰 쌍 계산; 요구사항 리뷰 R-05)
  - 브레이크포인트와 옆 패널 폭 상한 값(요구사항 리뷰 R-05)
  - 라벨이 가려지지 않는 규칙, 안내를 한 화면에 한 번만 보이는 규칙, 비활성 상태 토큰
- [x] 5. `domain-entities.md`를 쓴다
  - 토큰 목록과 값
  - `EnumKind` 값 전체와 ko/en 라벨
  - 오류 코드 목록(`ERROR_CODES`: 예외 → 상태·`code`)과 사전 문장
  - `DescribedError`
- [x] 6. `frontend-components.md`를 쓴다
  - 프리미티브·배치 틀·지도·도우미의 props와 상태
  - **파일 이동 표**(Units R-01): 새 폴더 `layout/`·`map/`·`format/`·`errors/`·`hooks/`·`i18n/`. 기존 `layout.ts`→`map/`, `i18n.ts`→`i18n/`(같은 import 경로 유지), `MapOverlay.tsx`·`viz.ts`→`map/`. `types.ts`는 그대로 둔다
  - 공유 `Dialog`로 바꿀 곳(요구사항 리뷰 R-01): `Modal`, `MapCanvas` Dialog, `BuildPanel`, `NewSessionForm`
  - RE-F09 `capabilities.ts`를 `useResource` 위로 옮긴다(Units R-05(c): V2에 넣음)
- [x] 7. 테스트 계획(TP-V2-*)을 적는다. PBT 대상 함수가 있으면 fast-check를 들일지 정한다(NFR-6, PBT-09)
- [x] 8. 설계 검토자 리뷰(adversarial) 뒤 승인 (iter 2 READY, 승인 2026-10-07T12:22:02Z)

---

## 이 계획이 스스로 정한 것 (질문하지 않음)

- **폴더 겹침(Units R-01)**: `web/src/i18n.ts`를 `web/src/i18n/index.ts`로 옮기면 `./i18n` import가 그대로 풀린다. `web/src/layout.ts`(지도 자동 배치)는 지도 기능이므로 `map/autoLayout.ts`로 옮긴다. 그러면 새 `layout/` 폴더와 겹치지 않는다.
- **RE-F09(Units R-05(c))**: `useResource`를 만들면서 `capabilities.ts`의 실패 캐시를 함께 고친다. 같은 코드를 만지므로 FR-C14 규칙에 맞는다.
- **시안에 쓴 한국어 지명**: 시안은 음역(예: 솔트웨이크 항구)으로 보인다. 실제 번역 방식은 V3(데모 한국어판)에서 정한다.

---

## 질문

답은 `[Answer]:` 뒤에 적거나 대화창에서 주세요.

### Q1
**세 시안 가운데 어느 것으로 하시겠습니까?** (FR-D1, CQ3=A)

**배경**
- 시안은 비공개 Artifact 캔버스 하나에 세 줄로 놓았다. 각 줄은 홈, 플레이, 휴대폰 플레이, 토큰·프리미티브 견본이다.
- 세 안은 모두 TRPG·판타지 톤(CQ1=A) 안의 해석이고, 테마는 하나다(CQ2=A).
  - A: 지도 제작자의 양피지(밝음, 따뜻한 종이, 청록 강조, 붉은 인장은 위험에만)
  - B: 등불 아래 선술집(어두움, 호두나무 바탕, 촛불 호박색 강조)
  - C: 채색 필사본(밝고 깨끗함, 남색 강조, 금박은 장식에만)
- 고른 안의 색·글꼴·모양이 V2 토큰이 되고, V4·V6·V8 화면이 모두 그 위에 선다. 코드는 고른 뒤에만 쓴다(FR-D1).

A) **A 지도 제작자의 양피지** — 지금의 종이 느낌을 이어 가서 바뀜이 가장 덜 낯설다. 지도와 손글씨 기록 같은 TRPG 핸드아웃 분위기다. 밝아서 오래 읽기 좋다.
B) **B 등불 아래 선술집** — 게임 화면처럼 몰입감이 가장 크다. 어두운 바탕이라 지도·사진·배지의 색이 잘 보인다. 대신 밝은 곳·휴대폰에서 글이 길면 눈이 피로할 수 있고, 인쇄·캡처가 어둡다.
C) **C 채색 필사본** — 읽기와 조작이 가장 분명하다. 판타지 느낌은 제목 글꼴과 금박 장식에서 온다. 셋 가운데 분위기는 가장 차분하다.
X) Other (please specify) — 섞기(예: "A의 색 + C의 글꼴")나 고칠 점을 적어 주시면, 그 안을 고쳐 다시 보여 드린다.

[Answer]: B — 등불 아래 선술집 (대화창 답변, 2026-10-07). 고칠 점 없이 그대로.

### Q2
**화면 문장의 문체를 어떻게 하시겠습니까?** (FR-L1, FR-D9)

**배경**
- 지금 사전은 대부분 합니다체(예: "세션이 종료되었습니다")이고, 해요체가 조금 섞여 있다.
- V2에서 오류·안내 문장을 새로 쓰고, V4·V6·V8에서 화면 문구를 모두 다시 쓴다. 문체를 지금 정하지 않으면 유닛마다 달라진다.
- 시안은 A 문체로 썼다.

A) **글의 종류마다 문체를 나눈다** — 버튼은 짧은 동사형("기다리기", "이동"), 안내·오류는 해요체("세션이 닫혔어요"), 이야기(내레이션·여정 기록)는 해라체("당신은 항구에 닿았다"). 게임 속 이야기와 앱의 안내가 구별된다. 규칙이 셋이라 사전 키마다 종류를 적어 둔다.
B) **모두 합니다체** — 지금과 가장 가깝고 격식 있다. 이야기 문장도 "~했습니다"가 되어 TRPG 서술 느낌이 약하다.
C) **모두 해요체** — 친근하고 하나로 단순하다. 이야기 문장도 "~했어요"가 되어 서술 느낌이 약하다.
X) Other (please specify)

- **권장: A.** 플레이어가 게임 속 이야기와 앱의 안내를 한눈에 구별합니다. 버튼은 짧아 휴대폰 폭에서도 줄이 넘치지 않습니다.

[Answer]: A — 글의 종류마다 문체를 나눈다 (대화창 답변, 2026-10-07)
