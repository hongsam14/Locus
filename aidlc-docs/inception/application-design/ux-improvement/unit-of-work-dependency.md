# UX Improvement — Unit Dependency & Build Order

## Dependency Matrix
| Unit | 의존 | 이유 |
|---|---|---|
| X1 Localization Backend | (없음 — 기존 세션/LLM 계층 위 가산) | 독립 착수 가능 |
| X2 Frontend Design System | (없음 — 순수 프론트 스타일) | 독립 착수 가능 |
| X3 Frontend UX Features | **X1**(ko 데이터·region_changes API), **X2**(디자인 프리미티브) | 데이터+UI 토대 필요 |

## Build Order (UOW-UX Q2=A)
```
X1 Localization Backend  ──►  X2 Frontend Design System  ──►  X3 Frontend UX Features
   (백엔드 ko/region_changes)     (Tailwind/Doodly 프리미티브)     (기능 = X1 데이터 + X2 UI)
```
- X1·X2는 상호 독립(백엔드 vs 프론트)이나 AI-DLC per-unit 루프는 순차. X1 먼저(계약 확정) → X2 → X3.

## 교차 계약(Coordination Points)
- **X1→X3**: 세션 응답 en+ko 필드, `TurnResult.region_changes` 스키마(api.ts/types.ts에서 소비).
- **X2→X3**: `src/ui/*` 프리미티브(Toast/Modal/Card 등) API.
- **불변**: 캐노니컬 그래프 스키마, 기존 REST 경로·`data-testid` 계약.

## Rollback
- X1: `translations` 테이블·`region_changes`(응답 전용) 가산 → 되돌리기 용이. X2/X3: 프론트 변경 되돌리기 용이.
