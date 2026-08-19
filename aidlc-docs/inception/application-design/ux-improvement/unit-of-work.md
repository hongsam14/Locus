# UX Improvement — Units of Work

결정: UOW-UX Q1=A(3 유닛) / Q2=A(X1→X2→X3 순차).

## X1 — Localization Backend
- **책임**: 번역 계층 + 세션 콘텐츠/캐노니컬 지식 로컬라이제이션 + 턴 변동 지역별 셰이핑.
- **컴포넌트**: C1 Translator · C2 Translation 엔티티+Repo(`translations` 캐시 테이블) · C3 TranslationService(캐시우선·폴백) · C4 생성훅(rumor/event/timeline 워밍) · C5 조회 enrichment(en+ko, 캐노니컬 지연번역 Q4=B) · C6 RegionTurnChange 셰이핑(`TurnResult.region_changes`) · C7 API(en+ko·region_changes) · C8 wiring/config.
- **FR**: FR-UX3.2/3.3/3.5/3.6, FR-UX2.6(백엔드 셰이핑 부분). **NFR/SEC**: NFR-UX2/3, SEC-A/C/E.
- **코드 위치**: `locus/translation/` (신규), `locus/session/{models,repository,memory_repo,rumor_generator,rumor_service,event_service,turn,query}.py`, `locus/storage/postgres_session_repo.py`, `api/routers/session.py`, `api/main.py`, `locus/config/settings.py`. 테스트 `tests/translation/`, `tests/session/`, `tests/storage/`.

## X2 — Frontend Design System
- **책임**: Tailwind 도입 + "Doodly" 디자인 토큰/프리미티브, 앱 전체 재스타일(동작·`data-testid` 계약 보존).
- **컴포넌트**: C9 Design System(tailwind config, index.css, 로컬 번들 폰트, `src/ui/{Button,Panel,Card,Badge,Toast,Modal}`), 기존 컴포넌트 restyle.
- **FR**: FR-UX1.1/1.2/1.3/1.4/1.5. **SEC**: SEC-B(로컬 폰트/헤더), SEC-D(의존성).
- **코드 위치**: `web/tailwind.config.*`, `web/postcss.config.*`, `web/src/index.css`, `web/src/ui/*`, `web/src/*.tsx`(restyle), `web/src/assets/fonts/*`. 테스트 `web/src/__tests__/`.

## X3 — Frontend UX Features
- **책임**: 전체 루머 생성·지역 재생성 개선·지역별 턴 변동 알림·한국어 표시(원문 토글)·UI 라벨 한국어화.
- **컴포넌트**: C10 i18n 사전 · C11 LocalizedText(원문 토글) · C12 전체생성(빈지역 판정+병렬+진행률+확인) · C13 지역 재생성 개선 · C14 NotificationCenter(지역별 알림) · C15 api/types.
- **FR**: FR-UX2.1/2.2/2.3/2.4/2.5/2.6(프론트), FR-UX3.1/3.4. **SEC**: SEC-E(병렬 상한).
- **코드 위치**: `web/src/{i18n.ts,api.ts,types.ts,SessionPanel.tsx,RegionPanel.tsx}`, `web/src/ui/{LocalizedText,NotificationCenter}.tsx`. 테스트 `web/src/__tests__/`.

## Code Organization
- 백엔드 신규 패키지 `locus/translation/`(translator/service/__init__). 세션 계층은 가산 변경. 캐노니컬 그래프 불변.
- 프론트 `web/src/ui/` 공용 프리미티브 신설; 기존 컴포넌트는 재스타일(구조 유지).
