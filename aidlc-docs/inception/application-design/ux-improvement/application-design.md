# UX Improvement — Application Design (Consolidated)

## Decisions (AD-UX)
| Q | 답 | 결정 |
|---|---|---|
| Q1 | A | Translator = 신규 `locus/translation/` (LLMProvider 재사용) |
| Q2 | **C** | 번역은 **별도 캐시 테이블**(`translations`) — 병렬 ko 필드 아님 |
| Q3 | A | 세션 콘텐츠는 **생성 시점** 번역(캐시 워밍) |
| Q4 | B | 캐노니컬 Knowledge는 **조회 시점 번역 + 세션 캐시**(그래프 불변) |
| Q5 | A | 백엔드가 `TurnResult.region_changes`(지역별 구조화 변동) 셰이핑 |
| Q6 | B | 전체생성 빈지역 판정 = 기존 distortions+listRumors(프론트) |
| Q7 | A | UI 라벨 = 경량 중앙 사전(의존성 없음) |
| Q8 | A | 원문 = 항목별 "원문 보기" 토글 |
| Q9 | C | Doodly = 로컬 번들 폰트 + CSS 스케치 요소 |

**아키텍처 통찰**: Q2=C + Q4=B ⇒ **단일 번역 캐시 테이블**이 세션 콘텐츠(생성 시 채움)와 캐노니컬 지식(조회 시 지연 채움)을 통합 수용. 저장은 정규화, 응답은 en+ko 비정규화.

## Components (요약)
- **Backend [X1]**: C1 Translator · C2 Translation 엔티티+Repo(`translations`) · C3 TranslationService(캐시우선) · C4 생성훅 · C5 조회 enrichment(캐노니컬 지연번역) · C6 RegionTurnChange 셰이핑 · C7 API(en+ko, region_changes) · C8 Wiring/Config.
- **Frontend [X2]**: C9 Design System(Tailwind+Doodly, 로컬 폰트, 공용 프리미티브).
- **Frontend [X3]**: C10 i18n 사전 · C11 LocalizedText(원문 토글) · C12 전체생성(병렬+확인) · C13 지역 재생성 개선 · C14 NotificationCenter(지역별 알림) · C15 api/types.

## Services
- S1 TranslationService(캐시우선·회복력) · S2 생성 파이프라인 통합 · S3 조회 로컬라이제이션(localize_many, 캐노니컬 지연) · S4 TurnAdvancer 변동 셰이핑 · S5 프론트 전체생성 오케스트레이션 · S6 프론트 알림.

## Dependencies / Data Flow
- `LLMProvider → Translator → TranslationService ↔ Translation cache`. 생성 시 워밍(C4), 조회 시 enrichment(C5, 캐노니컬 포함). API가 en+ko·region_changes 반환. 프론트는 C9 프리미티브 위에서 C11/C12/C13/C14 구성. (상세: component-dependency.md)

## 매핑
- **FR 커버리지**: FR-UX1.*(C9,C11) · FR-UX2.1/2.2/2.3(C12,S5) · FR-UX2.4/2.5(C13) · FR-UX2.6(C6,C14,S4,S6) · FR-UX3.1(C10) · FR-UX3.2/3.3/3.5(C1,C2,C3,C4) · FR-UX3.4/Q8(C5,C11) · FR-UX3.6(C5,Q4=B).
- **NFR/SEC**: NFR-UX2(캐시·localize_many) · NFR-UX3(포트 유지) · SEC-A(입력검증) · SEC-B(로컬 폰트/보안헤더) · SEC-C(번역 폴백·에러) · SEC-D(의존성) · SEC-E(병렬/배치 상한).

## Unit Mapping (Units Generation에서 확정)
- **X1 Localization Backend** (C1–C8) → **X2 Frontend Design System** (C9) → **X3 Frontend UX Features** (C10–C15).
- 순서 근거: X3는 X1의 ko 데이터 + X2의 프리미티브에 의존. (대안: X2·X3 병합.)

## Open → Functional Design
- `source_hash` 무효화 규칙(어떤 필드 변경 시 재번역), 번역 실패 폴백 표기 방식.
- 캐노니컬 Knowledge 번역 대상 필드(title/content/둘 다) 및 캐시 키 범위(world vs session).
- `region_changes` 지역 귀속 세부(rumors_added의 소스, feedback_regions 표기).
- 전체생성 "빈 지역" 정확 정의(active 소문 0? 승격 포함?), 병렬 상한 값.
- Doodly 토큰 구체값(폰트/색/테두리) 및 프리미티브 API.
