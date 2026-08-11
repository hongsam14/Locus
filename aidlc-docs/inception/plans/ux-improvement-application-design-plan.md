# UX Improvement — Application Design Plan

## Design Plan (artifacts to generate after answers)
- [x] components.md — 신규/변경 컴포넌트(Translator, 세션 모델 번역 필드, 알림 셰이핑, 프론트 디자인/i18n/알림/전체생성)
- [x] component-methods.md — 메서드 시그니처(비즈니스 룰은 Functional Design에서)
- [x] services.md — 서비스 오케스트레이션(번역 통합, advance_turn 변동 셰이핑, 전체생성 흐름)
- [x] component-dependency.md — 의존/데이터 흐름
- [x] application-design.md — 통합 문서
- [x] 완결성/일관성 검증

---

## Design Questions (AD-UX)

`[Answer]:` 뒤에 알파벳을 적어주세요. (여러 항목이면 `A+B`, 맞는 게 없으면 `X`+설명.) 각 질문에 **권장안**을 표시해 두었습니다.

### AD-UX Q1 — Translator 컴포넌트 배치
번역 로직을 어디에 둘까요?

A) **(권장)** 신규 모듈 `locus/translation/` + `Translator`(기존 `LLMProvider` 포트 재사용, 오프라인 목킹 가능)
B) 기존 `locus/llm/` 하위에 번역 유틸 추가
C) 각 서비스(rumor_generator/event_service)에 인라인 번역 호출
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-UX Q2 — 번역 저장 형태(스키마)
en/ko를 어떻게 저장할까요? (Q12=A 한국어 고정)

A) **(권장)** 병렬 필드: `statement_ko` / `description_ko` / `summary_ko` (평면·단순, 한국어 고정에 정합)
B) 범용 맵 `translations: dict[lang,str]` (다국어 확장 여지, 그러나 이번엔 한국어 고정)
C) 별도 번역 테이블/엔티티
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### AD-UX Q3 — 세션 콘텐츠 번역 시점
소문/이벤트/타임라인 콘텐츠는 언제 번역하나요? (Q9=A와 정합)

A) **(권장)** 생성 시점 동기 번역 — rumor 생성·event 생성·timeline 기록 시 원문+ko 함께 저장
B) 생성 후 별도 번역 패스(배치)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-UX Q4 — 캐노니컬 Knowledge 번역 경계 (FR-UX3.6) ⚠ 핵심 결정
세션 NPC/지역 뷰는 캐노니컬 `Knowledge`(영어, build-world 생성)+소문을 함께 보여줍니다. 캐노니컬 지식의 한국어 표시는?

A) `build-world` 시 캐노니컬 Knowledge(title/content) ko를 그래프에 **가산 저장** — 캐노니컬까지 완전한 한국어 뷰. (빌드 비용·범위↑)
B) **(권장)** 세션 조회 시점에 캐노니컬 텍스트를 번역해 **세션 저장소에 캐시**(캐노니컬 그래프 불변 유지, 재사용).
C) 이번 사이클은 **세션 콘텐츠(소문/이벤트/타임라인)만** 번역; 캐노니컬 Knowledge는 영어 유지(후속 사이클)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### AD-UX Q5 — 지역별 턴 변동 알림 데이터 셰이핑
FR-UX2.6(턴당 지역별 알림)을 위해 변동 요약을 누가 만드나요?

A) **(권장)** 백엔드가 `TurnResult`에 **지역별 구조화 요약** 추가 (예: `region_changes: [{region_id, promoted[], demoted[], pruned[], events_applied[], events_resolved[], rumors_added[]}]`). 프론트는 그대로 렌더.
B) 프론트가 기존 id 리스트 + 지역 조회로 그룹핑(백엔드 무변경, 소문 id→region 매핑 위해 추가 조회 필요)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-UX Q6 — 전체 생성 "빈 지역" 판정 데이터원
전체 루머 생성(빈 지역만, Q5=C)에서 빈 지역을 어떻게 판정하나요?

A) 신규 경량 백엔드 엔드포인트(지역별 소문 유무/개수 요약) 제공
B) **(권장)** 기존 `GET …/distortions`(전 지역 목록) + 지역별 `listRumors` 조합으로 프론트 판정
C) 기존 엔드포인트만으로 프론트 판정(추가 없음)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### AD-UX Q7 — UI 라벨 i18n 방식
정적 UI 라벨(버튼·헤더 등) 한국어화 방식은? (Q12=A 한국어 고정)

A) **(권장)** 경량 중앙 사전(TS 객체, 한국어 고정) — 의존성 없음
B) react-i18next 등 i18n 라이브러리 도입
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-UX Q8 — 원문(영어) 토글 노출 방식 (FR-UX3.4 / Q11=B)
번역본 기본 + 원문 보기를 어떻게?

A) **(권장)** 항목별 "원문 보기" 토글/툴팁(로컬 UI 상태)
B) 전역 언어 토글(전체를 원문/번역으로 전환)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### AD-UX Q9 — "Doodly" 폰트/자산 오프라인 처리 (SEC-B/D, CSP 친화)
손그림 느낌을 어떻게 구현하나요?

A) 손글씨/두들 웹폰트를 **로컬 번들**(자가호스팅, 외부 CDN 없음)
B) 시스템 폰트 + CSS만으로 두들 느낌(스케치 테두리·라운드·기울임 등)
C) 로컬 번들 폰트 + CSS 스케치 요소 **둘 다**
X) Other (please describe after [Answer]: tag below)

[Answer]: C
