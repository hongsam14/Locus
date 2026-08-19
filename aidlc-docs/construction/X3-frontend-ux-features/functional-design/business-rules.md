# X3 Frontend UX Features — Business Rules

## 로컬라이제이션 표시 (BR-X3-1..4)
- **BR-X3-1** UI 정적 라벨은 i18n 사전(`t()`)의 한국어 값으로 렌더(Q8=B/Q12=A). 미정의 key는 원문 fallback.
- **BR-X3-2** LLM 콘텐츠(소문/이벤트/지식)는 ko가 있으면 ko 기본 표시, 없으면 원문(FR-UX3.4). 항목별 "원문" 토글로 원문↔번역 전환(Q11=B/Q5=A).
- **BR-X3-3** 타임라인은 `kind`+`payload`를 i18n 템플릿으로 한국어 렌더(F2a/Q4=A). LLM 번역 사용 안 함.
- **BR-X3-4** ko는 X1 백엔드가 조회 응답에 실어주며(캐시 워밍 후 표시), 첫 조회는 원문일 수 있음(X1 read-lazy). 프론트는 재조회 시 자연히 ko 반영.

## 전체 생성 / 재생성 (BR-X3-5..9)
- **BR-X3-5** "전체 생성"은 세션 전체 지역 중 **소문이 없는 지역에만** 생성(Q5=C). 지역·유무 판정은 distortions + 지역별 listRumors(Q6=B).
- **BR-X3-6** "전체 재생성"(덮어쓰기)은 **별도 버튼 + Modal 확인** 후 실행(Q3=A). 첫 클릭 즉시 덮어쓰지 않음(FR-UX2.2).
- **BR-X3-7** 전체 작업은 **병렬(Promise.all) + 진행률(progress-bar + N/M)**, 부분 실패는 개별 집계 후 요약 토스트(Q2=A, FR-UX2.3). 동시 요청 상한(청크, SEC-E).
- **BR-X3-8** 지역 재생성(단건)은 Modal 확인 + "승격 소문 보존" 안내(FR-UX2.5/Q6=A).
- **BR-X3-9 (백엔드)** `regenerate_region`은 **승격된 소문을 보존**하고 비승격만 삭제·재생성한다(Q6=A). 전체 재생성도 동일 규칙(Q7=A). 오프라인 테스트로 보존 검증.

## 턴 변동 알림 (BR-X3-10..12)
- **BR-X3-10** `advance-turn` 응답 `region_changes`에서 **변동 지역마다 알림 1건**(FR-UX2.6). 변동 없는 지역 무알림(백엔드가 이미 제외).
- **BR-X3-11** 알림은 우상단 fixed 토스트 스택, 지역 요약(승격/강등/소멸/이벤트 적용·해소/신규 소문 건수, i18n). 자동 소멸(수초) + 수동 닫기(Q1=A).
- **BR-X3-12** 알림 문구의 대상 id·건수는 `region_changes` 필드에서 파생; 프론트는 추가 조회 없이 렌더.

## 계약/품질 (BR-X3-13..14)
- **BR-X3-13** 기존 `data-testid`·핸들러·API 계약 보존. 신규 testid 부여(generate-all-btn/regen-all-btn/generate-progress/notif-*/orig-toggle-*).
- **BR-X3-14** X2 프리미티브(Button/Modal/Toast/Card/Badge/Field/Range) 재사용. vitest GREEN 유지 + 신규 동작 테스트, tsc/vite build clean.
