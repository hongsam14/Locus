# UX Improvement — Component Dependencies & Data Flow

## Dependency Matrix (신규/변경 → 의존)
| Component | 의존 |
|---|---|
| C1 Translator | `LLMProvider`(포트) |
| C2 Translation Repo | `SessionRepository`(포트) + postgres/memory 구현 |
| C3 TranslationService | C1 Translator, C2 Repo |
| C4 Generation hooks | C3 (RumorService/EventService/TurnAdvancer 내부 DI) |
| C5 Read enrichment | C3, WorldLoader(캐노니컬 Knowledge 텍스트) |
| C6 RegionTurnChange | (없음 — 순수 셰이핑, 기존 TurnResult 데이터) |
| C7 API | C5, C6, 기존 세션 서비스 |
| C8 Wiring/Config | C1,C3, settings |
| C9 Design System | Tailwind(빌드), 로컬 폰트 자산 |
| C10 i18n | (없음) |
| C11 LocalizedText | C9, types(ko 필드) |
| C12 전체생성 | api.ts(listDistortions/listRumors/generate), C9 Modal |
| C13 지역 재생성 | api.ts(regen), C9 Modal |
| C14 NotificationCenter | types(region_changes), C9 Toast |
| C15 api/types | 백엔드 응답 계약(C7) |

## 데이터 흐름
```
LLMProvider ──► C1 Translator ──► C3 TranslationService ◄──► C2 Translation cache (Postgres/memory)
                                        ▲                         │
             생성시(C4) ───────────────┘        조회시(C5)◄──────┘  (+ 캐노니컬 Knowledge 지연 번역)
                                        │
                                   C7 API (en+ko DTO, region_changes)
                                        │
             ┌──────────────────────────┼───────────────────────────┐
             ▼                          ▼                            ▼
     C11 LocalizedText          C14 NotificationCenter        C12/C13 생성·재생성
        (ko + 원문 토글)          (region_changes→지역별 알림)     (병렬+진행률·확인 모달)
                     \___________ C9 Design System (Tailwind/Doodly 프리미티브) __________/
                                        │  C10 i18n(UI 라벨)
```

## 통신 패턴
- 백엔드 내부: 동기 메서드 호출(포트 뒤 I/O). 번역은 캐시 우선으로 LLM 호출 최소화(NFR-UX2).
- 프론트↔백엔드: 기존 REST(JSON). 응답에 ko 동봉·`region_changes` 추가(가산, 후방호환).
- 프론트 병렬: 전체 생성만 Promise.all(상한, SEC-E). 알림은 turn 응답 1건에서 파생.

## 후방호환/불변
- 캐노니컬 그래프(Neo4j/OpenSearch) 스키마 불변(Q4=B). 세션 PostgreSQL은 `translations` 테이블·`region_changes`(응답 전용) 가산.
- 기존 `data-testid`/API 계약 보존(FR-UX1.5). 번역 미구성 시 원문 폴백(graceful).
