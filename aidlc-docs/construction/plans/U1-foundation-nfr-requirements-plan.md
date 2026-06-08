# U1 Foundation — NFR Requirements Plan

U1의 비기능 요구사항·기술 스택 세부를 확정합니다. (Security 확장 OFF, PBT Partial 은 이미 결정.) 각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장 표시.

---

## Questions

## Question NFR1-Q1 — 임베딩 모델
의미 검색용 임베딩 생성은?

A) Provider 추상화 + 기본 OpenAI `text-embedding-3-small` (교체 가능) (Recommended — 기본 OpenAI, 비용↓·품질 충분; provider 추상화로 후일 교체)
B) 로컬 sentence-transformers (예: all-MiniLM) — 오프라인·무비용, 품질·언어 따라 편차
C) 추상화만 두고 기본 미정(주입식)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question NFR1-Q2 — 규모(scale) 기대치 (MVP)
한 세계의 대략적 규모는? (용량 계획 기준)

A) 소규모 — 지역 수십~수백, 지식 수백~수천 노드 (Recommended — MVP, 단일 인스턴스로 충분)
B) 중규모 — 지역 수백~수천, 지식 수만 노드
C) 대규모 — 그 이상(샤딩/튜닝 필요)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question NFR1-Q3 — 성능 목표
응답/처리 목표는?

A) 쿼리 p95 < 1s(MVP 규모), 빌드는 배치(수 분 허용, LLM 호출 시간 지배) (Recommended)
B) 더 엄격 (쿼리 < 200ms 등 — 캐싱·튜닝 추가)
C) 목표 미설정(베스트 에포트)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question NFR1-Q4 — 저장소 버전 고정
컨테이너 이미지 버전은?

A) Neo4j 5.x (Community) + OpenSearch 2.x 고정 (Recommended — 안정 LTS 계열, 참고 프로젝트 호환)
B) 최신 태그(latest) 사용
C) 직접 지정 (X에 기재)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question NFR1-Q5 — LLM/외부 호출 신뢰성
LLM/VLM/임베딩 호출 실패 대응은?

A) 재시도(지수 백오프) + 타임아웃 + 부분 실패 시 graceful degrade(저신뢰 표시·보강 대상화) (Recommended)
B) 단순 실패 전파(재시도 없음)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question NFR1-Q6 — 설정/비밀 관리
API 키·접속 정보 관리는?

A) `.env` + 환경변수 (예: `OPENAI_API_KEY`, Neo4j/OpenSearch 접속) — `env.example` 제공, `.env`는 git 제외 (Recommended — 참고 프로젝트 동일)
B) 비밀 관리 서비스(Vault 등)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `nfr-requirements.md` — U1 NFR(성능/확장/신뢰성/유지보수/품질) 목록
- [ ] `tech-stack-decisions.md` — 버전·라이브러리·근거

## Execution Checklist
- [x] 1. NFR1-Q1~6 반영 (Q3=C 베스트 에포트)
- [x] 2. nfr-requirements.md 작성
- [x] 3. tech-stack-decisions.md 작성
