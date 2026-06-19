# P3 Web UI — NFR (light)

| NFR | P3 적용 | 방법 |
|---|---|---|
| **NFR-P5 회귀** | ✅ | 기존 SessionPanel/RegionPanel/SessionBar 동작·14 vitest 보존; TS 타입·api.ts·라우트 additive. tsc/vite build 클린. |
| **NFR-P2 격리** | ✅ | 신규 distortions 라우트는 세션 레이어 읽기만. 캐노니컬 무관. |
| NFR-P1/P3/P4/P6 | N/A | P3는 UI + 1 read 엔드포인트. 신규 인프라/LLM/순수로직 없음(P1/P2에서 완료). |
