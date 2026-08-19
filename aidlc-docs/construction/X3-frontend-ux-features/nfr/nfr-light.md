# X3 Frontend UX Features — NFR (light)

- **NFR-UX1 (Usability)**: 전체 생성·재생성은 진행률(progress-bar+N/M)·완료/부분실패 요약을 제공하고 UI를 블로킹하지 않음. 파괴적 작업은 Modal 확인.
- **NFR-UX4 (Testability)**: 신규 동작(전체생성 빈지역 판정·병렬, 알림 지역별 렌더, 원문 토글, 타임라인 i18n, 백엔드 regen 승격 보존) 테스트 추가. 기존 vitest + pytest GREEN 유지, tsc/vite clean.
- **SEC-E**: 전체 생성/재생성 동시 요청 상한(청크). LLM 비용 남용 방지.
- **SEC-A**: 백엔드 regen 변경은 기존 입력 검증·계약 유지(가산).
- **PBT**: 프론트 UI = N/A. 백엔드 regen 승격 보존은 단위 테스트로 커버(순수 로직 소폭).
