# UX Improvement — Integration (live) Test Instructions

실 인프라(Neo4j/OpenSearch/PostgreSQL/OpenAI) 필요. 오프라인은 목으로 대체 검증됨.

## Setup
```bash
cp env.example .env   # NEO4J_PASSWORD/SESSION_DB_PASSWORD/OPENAI_API_KEY, TRANSLATION_ENABLED=true
docker compose up -d neo4j opensearch postgres
locus init-schema && locus build-world --world demo --demo
uvicorn api.main:app --port 8000
cd web && npm run dev   # http://localhost:5173
```

## Scenarios
- **UX-A 로컬라이제이션(X1)**: 세션 시작 → 지역 지식/소문 조회. 첫 조회는 원문(영어), 잠시 후 재조회 시 **한국어** 표시(백그라운드 워밍). "원문" 토글로 영어 확인. `translations` 테이블에 캐시 적재 확인.
- **UX-B 캐노니컬 지식 번역(Q4=B)**: NPC 지식 뷰의 캐노니컬 항목이 world 캐시로 한국어화, 새 세션에서도 재사용(중복 번역 없음).
- **UX-C 전체 생성(X3)**: 여러 지역 → "전체 생성" → 소문 없는 지역만 병렬 생성(진행바 N/M), 완료 요약 토스트. 재클릭 시 이미 채워진 지역 스킵.
- **UX-D 전체/지역 재생성(X3)**: "전체 재생성"/지역 재생성 → 확인 모달 → 실행. **승격된 소문 보존**, 비승격만 교체(무증식).
- **UX-E 턴 변동 알림(X3)**: 이벤트 생성 후 advance-turn → 변동 지역마다 우상단 토스트(승격/소멸/이벤트 등), 수초 후 자동 소멸.
- **UX-F 타임라인 i18n(X3)**: 타임라인이 한국어 템플릿으로 렌더(이벤트 create/suggest/approve는 구분 유지).
- **UX-G Doodly UI(X2)**: 종이+잉크 모노 테마, Gaegu 손글씨 제목(한글 렌더), 스케치 테두리/그림자. 외부 폰트 CDN 호출 0(네트워크 탭 확인).

## Verify
- 캐노니컬 그래프 불변, 세션 계층만 가산(translations/region_changes). ko 미해결 시 원문 표시(graceful). 번역 비활성(`TRANSLATION_ENABLED=false`) 시 전면 영어.
