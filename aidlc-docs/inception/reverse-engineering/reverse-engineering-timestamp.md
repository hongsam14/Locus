# Reverse Engineering Metadata

**Analysis Date**: 2026-09-29T02:29:54Z
**Analyzer**: AI-DLC (Purpose Restructure Cycle)
**Workspace**: /home/thinkpad/Desktop/src/Locus
**Codebase Snapshot**: commit `ee61277` (main, clean), last code change 2026-08-19
**Total Files Analyzed**: 172 source/test files (.py/.ts/.tsx) + build·infra·docs files (pyproject, requirements, Dockerfiles, docker-compose, env.example, README, CLAUDE.md, examples/)

## Method
- 세 영역을 병렬로 정독했다.
  1. 캐노니컬 파이프라인
  2. 세션·번역·API
  3. 프론트엔드·테스트·도구
- 호출 지점을 grep으로 교차 확인했다.
- 오프라인 실행 결과: pytest 281 passed (87% cov), vitest 24 passed, tsc/ruff/black clean, mypy 16 errors.
- 인메모리 시뮬레이션으로 결함 5건을 재현했다(A1, A2, A7, B3, C1/C2). 스크래치 스크립트는 세션 스크래치패드에만 두었고, 프로젝트 파일은 고치지 않았다.

## Artifacts Generated
- [x] business-overview.md (+ 목적 지도 절)
- [x] architecture.md
- [x] code-structure.md
- [x] api-documentation.md
- [x] component-inventory.md
- [x] technology-stack.md
- [x] dependencies.md
- [x] code-quality-assessment.md
