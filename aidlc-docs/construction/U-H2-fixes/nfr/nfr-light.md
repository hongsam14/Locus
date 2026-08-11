# U-H2 Fixes — NFR (light)

| NFR | U-H2 적용 | 방법 |
|---|---|---|
| **NFR-H2 호환/격리** | ✅ | 캐노니컬 데이터 모델·세션 레이어 불변. 정상 입력 산출물 동일(회귀 0). H7=재빌드 시 topology의 wiki 반영, H8=비정상 barrier 가시화, H6=프론트 지연만 변화. |
| **NFR-H3 테스트** | ✅ | 프론트 vitest(refresh 병렬 호출·regionId 분기·에러), pytest(build_world set_wiki 순서·LLM=None, ingestor barrier between≠2 경고). 오프라인. |
| **NFR-H5 확장** | ✅ | Security off · PBT 해당 없음(순수 로직 신규 없음; U-H1에서 커버). |

## 회귀
- 정상 경로 회귀 0. `orchestrator`/`map_image_ingestor` 기존 테스트 유지; 프론트 vitest 유지.
- ruff/black/compileall + tsc/vite build 클린 유지.
