# X1 Localization Backend — NFR (light)

별도 NFR 질문 없이 요구사항 고정값을 반영(이전 사이클 관례).

- **NFR-UX2 (Performance/Cost)**: 번역 캐시 우선 + `localize_many` 배치로 LLM 호출 최소화. 배치 상한 `translation_batch_size`(기본 20, SEC-E).
- **NFR-UX3 (Maintainability)**: 번역은 `LLMProvider` 포트 뒤 `Translator`로 추상화 → 오프라인 목킹. `translation` DI 옵션(미주입 graceful).
- **NFR-UX5 (Compatibility)**: `translations` 테이블·`region_changes` 가산; 캐노니컬 그래프 불변; `ensure_schema` idempotent.
- **SEC-A**: 신규/변경 API 입력 검증(Pydantic), SQLAlchemy 파라미터라이즈드.
- **SEC-C**: 번역/LLM/DB 호출 명시적 에러 처리, fail-safe 원문 폴백, 사용자엔 일반 메시지.
- **SEC-E**: 번역 배치/병렬 상한(비용 폭주 방지).
- **PBT (Partial)**: 순수 함수 대상 — `source_hash` 안정성, `shape_region_changes` 그룹핑(무변동 제외 불변식), 캐시 히트/무효화 판정. 직렬화 왕복(`Translation`/`RegionTurnChange`/`TurnResult`).
- **테스트**: 오프라인 pytest(목 LLM/InMemory repo) GREEN 유지, 신규 동작 커버.
