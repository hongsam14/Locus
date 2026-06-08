# U1 Foundation — Infrastructure Design Plan

논리 컴포넌트를 실제 배포로 매핑합니다. 이미 결정: **로컬 + Docker Compose**(Q11=A), Neo4j 5.x, OpenSearch 2.x, 클라우드 범위 외. 이 인프라는 **전 Unit 공유**입니다. 아래 열린 선택만 확인합니다. 각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료".

> N/A(범위 외): 메시징/큐, 로드밸런서/API 게이트웨이, 오토스케일, 멀티테넌시 — 단일 인스턴스 로컬 MVP.

---

## Questions

## Question ID-Q1 — 앱(코어/API) 실행 방식
Python 앱·API를 어떻게 띄울까요?

A) Compose에 앱 서비스 포함 + 호스트 실행도 지원 — `docker-compose.yml`에 `app`(api) 서비스, Neo4j/OpenSearch와 함께. 개발 시 호스트에서 `uvicorn` 직접 실행도 가능(의존 컨테이너만 사용) (Recommended — 유연)
B) 의존성만 컨테이너 — Neo4j/OpenSearch만 Compose, 앱은 항상 호스트 실행
C) 전부 컨테이너 — 앱도 항상 Compose로만
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question ID-Q2 — OpenSearch 로컬 보안 설정
로컬 개발 OpenSearch는?

A) 단일 노드 + 보안 플러그인 비활성(TLS/인증 off) — 개발 마찰 최소 (Recommended — 로컬 전용, Security 확장 OFF와 정합)
B) 보안 활성(기본 인증/TLS) — 운영 유사하나 설정 복잡
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question ID-Q3 — 데이터 영속성
컨테이너 데이터 보존은?

A) 명명 볼륨(named volumes) — Neo4j/OpenSearch 데이터 영속, 재기동 보존 (Recommended)
B) 임시(볼륨 없음) — 재기동 시 초기화(테스트 편의)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `infrastructure-design.md` — 논리→인프라 매핑(서비스/포트/이미지/환경변수)
- [ ] `deployment-architecture.md` — Compose 토폴로지·기동 순서·헬스체크
- [ ] `aidlc-docs/construction/shared-infrastructure.md` — 전 Unit 공유 인프라 정의

## Execution Checklist
- [x] 1. ID-Q1~3 반영 (all A)
- [x] 2. infrastructure-design.md 작성
- [x] 3. deployment-architecture.md 작성
- [x] 4. shared-infrastructure.md 작성
