# X2 Frontend Design System — NFR (light)

- **NFR-UX6 (Accessibility)**: 잉크/종이 대비 본문 AA(4.5:1) 이상; 포커스 링·키보드 조작 유지.
- **NFR-UX4 (Testability)**: `data-testid` 보존, 기존 vitest GREEN 유지; tsc/vite 빌드 clean.
- **SEC-B**: 정적 자산(폰트 포함) 로컬 번들, 외부 CDN 호출 없음 → CSP 친화.
- **SEC-D**: 신규 의존성(tailwindcss/postcss/autoprefixer)은 공식 레지스트리·`package-lock.json` 핀; 미사용 의존성 없음; Docker 이미지 `latest` 지양.
- **성능**: Tailwind 빌드 트리셰이킹(content globs)로 CSS 최소화; 번들 폰트는 서브셋(가능 시 한글 서브셋) 권장.
- **PBT**: 해당 없음(UI 전용, 순수 로직 없음) — N/A.
