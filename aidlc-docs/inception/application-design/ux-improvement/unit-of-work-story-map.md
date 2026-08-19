# UX Improvement — FR → Unit Story Map

(User Stories 스킵 → 요구사항 FR을 유닛에 매핑.)

## X1 — Localization Backend
| FR | 설명 | 컴포넌트 |
|---|---|---|
| FR-UX3.2 | 콘텐츠 생성 시 en+ko 저장 | C2,C3,C4 |
| FR-UX3.3 | LLMProvider 포트 재사용 번역 | C1 |
| FR-UX3.5 | 번역 저장·재사용(중복 방지) | C2,C3 |
| FR-UX3.6 | 캐노니컬 Knowledge 번역 경계(Q4=B 조회시 캐시) | C5 |
| FR-UX2.6(백엔드) | 지역별 턴 변동 셰이핑 `region_changes` | C6 |
| NFR-UX2/3, SEC-A/C/E | 캐시·포트·입력검증·폴백·상한 | C1,C3,C7 |

## X2 — Frontend Design System
| FR | 설명 | 컴포넌트 |
|---|---|---|
| FR-UX1.1 | Tailwind 디자인 시스템 도입 | C9 |
| FR-UX1.2 | 앱 전체 일관 토큰 적용 | C9 |
| FR-UX1.3 | "Doodly" 스타일(로컬 폰트+CSS 스케치) | C9 |
| FR-UX1.4 | 라이트 단일 테마 | C9 |
| FR-UX1.5 | 동작·`data-testid` 계약 보존 | C9 |
| SEC-B/D | 로컬 폰트/보안헤더·의존성 | C9 |

## X3 — Frontend UX Features
| FR | 설명 | 컴포넌트 |
|---|---|---|
| FR-UX2.1 | 전체 생성(빈 지역만) | C12 |
| FR-UX2.2 | 전체 재생성 확인 게이트 | C12 |
| FR-UX2.3 | 병렬 생성+진행률+부분실패 | C12 |
| FR-UX2.4 | 지역 상세 재생성 강조 배치 | C13 |
| FR-UX2.5 | 재생성 개선(승격 보존·확인) | C13 |
| FR-UX2.6(프론트) | 지역별 턴 변동 알림 | C14 |
| FR-UX3.1 | UI 라벨 한국어화 | C10 |
| FR-UX3.4 / Q8 | ko 기본 표시 + 원문 토글 | C11 |
| SEC-E | 병렬 상한 | C12 |

## 커버리지 검증
- **FR 배정**: FR-UX1.*(X2) · FR-UX2.*(X3, 2.6은 X1 셰이핑+X3 표시) · FR-UX3.*(X1 백엔드 + X3 표시) — **미배정 0**.
- **컴포넌트 배정**: C1–C8→X1, C9→X2, C10–C15→X3 — **미배정 0**.
- **NFR/SEC**: NFR-UX1(X3 진행률)·UX2(X1 캐시)·UX3(X1 포트)·UX4(전 유닛 테스트)·UX5(X1 가산)·UX6(X2 가독성); SEC-A/C/E(X1), SEC-B/D(X2), SEC-E(X3).
