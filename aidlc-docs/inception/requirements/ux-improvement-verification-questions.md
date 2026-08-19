# UX Improvement — Requirements Verification Questions

각 질문의 `[Answer]:` 태그 뒤에 알파벳(A/B/C…)을 적어주세요. 맞는 게 없으면 `X`를 고르고 설명을 덧붙이면 됩니다. 여러 항목을 함께 고르고 싶으면 그렇게 적어주세요 (예: `A+C`).

> **참고 (Workspace Detection 발견사항)**: 현재 `web/` 프론트엔드는 **이미 React + Vite + TypeScript**로 되어 있습니다 (`App.tsx`, `SessionPanel.tsx`, `SessionBar.tsx`, `RegionPanel.tsx`, `MapOverlay.tsx` 등). 다만 **CSS 파일/디자인 시스템이 전혀 없고 인라인 `style={{}}`만** 사용해 시각적으로 "순수 HTML처럼" 보입니다. 그래서 "순수 html"이라는 표현을 restyle/UX 개편으로 해석했는데, 아래 Q1에서 확정해주세요.

---

## A. Frontend 디자인 / UX 개선

## Question 1
현재 프론트엔드는 이미 React이지만 스타일이 거의 없습니다. 개선 범위는?

A) 기존 React 앱을 유지하되, 디자인 시스템·스타일을 입혀 UX를 개편 (컴포넌트 구조는 대체로 재사용)
B) 프론트엔드를 React로 처음부터 재작성 (기존 컴포넌트 폐기)
C) 기존 컴포넌트 유지 + 필요한 화면만 부분 재설계
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
스타일링/디자인 방식은 무엇을 선호하시나요? (빌드·의존성에 영향)

A) Tailwind CSS (유틸리티 우선; devDependency + 설정 추가)
B) React 컴포넌트 라이브러리 (MUI / Chakra / Mantine 등 — 기성 컴포넌트)
C) 가벼운 커스텀 CSS + 디자인 토큰 (CSS Modules/일반 CSS, 무거운 의존성 없음, 오프라인 친화)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
시각 개편 대상 범위는?

A) 앱 전체 (지도 오버레이 / RegionPanel / SessionBar+SessionPanel / Toolbar / AugmentPanel 일관된 디자인 시스템)
B) 게임 세션 UI 중심 (SessionBar + SessionPanel + RegionPanel), 지도/오소링 화면은 최소 손질
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
다크 모드 / 테마 지원이 이번 범위에 포함되어야 하나요?

A) 아니오 — 단일 테마(라이트)로 충분
B) 예 — 라이트/다크 토글 지원
X) Other (please describe after [Answer]: tag below)

[Answer]: A. Doodly했으면 좋겠음.

---

## B. Rumor 생성 방식 개선

> 현재 API: 지역별 `POST …/regions/{rid}/rumors`(생성), `…/rumors/regen`(재생성)이 이미 있고, SessionPanel에 지역별 generate/regen 버튼이 존재합니다.

## Question 5
"전체 루머 생성" 버튼의 동작 범위는?

A) 세션의 **모든 지역** 중 아직 소문이 없는 지역에만 생성 (이미 있는 지역은 건너뜀)
B) **모든 지역**에 대해 생성/재생성 (기존 소문 덮어쓰기)
C) 첫 클릭은 빈 지역만 채우고, 덮어쓰기는 별도 확인 후 실행
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 6
"전체 생성"은 지역 수가 많으면 시간이 걸립니다(지역마다 LLM 호출). 실행 방식/피드백 선호는?

A) 백엔드 배치 엔드포인트 1회 호출로 서버에서 전 지역 처리 (완료 후 결과 반환)
B) 프론트엔드가 지역별 기존 엔드포인트를 병렬 호출(Promise.all)하고 진행 상황 표시
C) 상관없음 — 동작만 되면 됨 (구현은 설계 단계에서 결정)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 7
"지역 상세 재생성 버튼"에 대해 — 현재도 지역별 재생성(regen)이 존재합니다. 이번 요청의 핵심은?

A) 재생성 기능은 이미 충분 — 재설계된 "지역 상세" 뷰에서 눈에 잘 띄게 배치만 개선
B) 재생성 동작 자체도 개선 필요 (예: 승격된 소문 보존, 확인 다이얼로그 등)
X) Other (please describe after [Answer]: tag below)

[Answer]: B. 그리고 여담으로 루머가 승격되면 조용히 승격되는 것이 아니라 사용자(GameMaster)가 인지할 수 있도록 알람이 왔으면 좋겠어.

---

## C. 로컬라이징 (한국어 번역 표시)

> 현재 LLM은 모든 텍스트(소문·지식·이벤트·타임라인)를 영어로 생성합니다.

## Question 8
번역 대상은 무엇인가요?

A) LLM이 생성한 **콘텐츠**만 (소문 텍스트, 지식, 이벤트 설명, 타임라인 등)
B) 콘텐츠 + **UI 라벨**(버튼·헤더 등 정적 텍스트) 모두 한국어화
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 9
콘텐츠 번역은 어디서/언제 수행되나요?

A) 백엔드가 **생성 시점**에 원문+번역을 함께 저장 (읽기는 빠름, 저장소에 번역 필드 추가)
B) 백엔드가 **읽기 요청 시** 번역해서 반환 (저장 스키마 불변, 매 요청마다 번역 비용/캐시 필요)
C) 프론트엔드가 필요 시 번역 엔드포인트를 호출 (표시 직전 번역)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
번역기는 무엇을 쓰나요?

A) 기존 OpenAI LLMProvider 재사용 (별도 서비스/키 불필요, 포트 뒤 추상화 유지)
B) 전용 번역 API (예: DeepL/Google Translate) 도입
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
원문(영어)도 볼 수 있어야 하나요?

A) 아니오 — 번역본만 표시
B) 예 — 번역 표시하되 원문 토글/툴팁 제공
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 12
언어 지원 범위는?

A) 한국어만 (영어→한국어 고정)
B) 일반 다국어 구조 + 언어 선택기 (한국어 우선 구현, 확장 가능)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## D. 확장(Extensions) 옵트인

## Question: Security Extensions
이 작업에 보안 확장 규칙을 강제할까요?

A) Yes — 모든 SECURITY 규칙을 blocking 제약으로 강제 (프로덕션급 권장)
B) No — SECURITY 규칙 생략 (PoC·프로토타입·실험 적합)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question: Property-Based Testing Extension
이 작업에 속성 기반 테스트(PBT) 규칙을 강제할까요?

A) Yes — 모든 PBT 규칙을 blocking 제약으로 강제
B) Partial — 순수 함수와 직렬화 왕복(round-trip)에만 PBT 적용
C) No — PBT 규칙 생략 (단순 CRUD·UI 전용·얇은 통합 계층 적합)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

*(참고: 이전 사이클들은 일관되게 Security=No, PBT=Partial 이었습니다. 이번에도 동일하면 각각 B / B.)*
