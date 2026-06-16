# S1 — Business Rules (Functional Design)

Unit **S1 (Session Foundation & Infra)**. FR-R1 + NFR-R1/R2/R3.
확정 답: FD-S1 Q1=B / Q2=A / Q3=A / Q4=A / Q5=A.

세션 생애주기·불변식·레이어 격리·graceful 규칙. (소문 생성/승격/턴 로직 규칙은 S2.)

---

## 세션 생애주기

- **BR-S1-1 (시작 상태)**: `start_session`으로 만든 GameSession은 `status=OPEN`, `turn=0`, `created_at`=DB now, `closed_at=None`. (FR-R1.1, FD-S1 Q4=A)
- **BR-S1-2 (world 검증)**: `start_session(world_id)`은 캐노니컬(Neo4j)에 그 world의 데이터(Region)가 존재할 때만 성공한다. 미존재 → 거부(404/`WorldNotFoundError`). 잘못된 world_id로 만든 세션을 방지한다. (FD-S1 Q2=A, FR-R1.1)
- **BR-S1-3 (기본 distortion 생성)**: 세션 시작 시 그 world의 **모든 region에 RegionDistortion row를 명시 생성**하며 기본값은 `DEFAULT_DISTORTION_DEGREE = 0.3`(약한 왜곡)이다. 이후 미설정 region은 존재하지 않는다. (FD-S1 Q1=B)
- **BR-S1-4 (종료)**: `close_session`은 `status=CLOSED`, `closed_at`=now로 설정한다. 이미 CLOSED면 멱등(변경 없이 현재 상태 반환). (FR-R1.1)
- **BR-S1-5 (종료 후 불변)**: CLOSED 세션은 읽기 전용 이력이다. 종료된 세션에 대한 변경 동작(소문/턴/distortion 쓰기, S2)은 거부된다. S1은 라이프사이클/조회만 노출.
- **BR-S1-6 (이력 보존)**: 한 world는 여러 GameSession 이력을 보유한다. 새 세션 시작이 이전 세션의 rumor/timeline/승격을 변경하거나 삭제하지 않는다. (FR-R1.1, CL-C1)

## 식별자 / 시간

- **BR-S1-7 (id)**: GameSession/SessionRumor/TimelineEntry의 `id`는 기존 `new_id()`(uuid4)로 애플리케이션이 생성한다. DB 시퀀스/serial을 쓰지 않는다. (FD-S1 Q4=A)
- **BR-S1-8 (타임스탬프)**: `created_at`/`closed_at`은 DB 서버 시간(`server_default=now()` / 종료 시 now)이다. In-memory 어댑터는 결정론 테스트를 위해 단조 증가 clock으로 동등 계약을 흉내 낸다. (FD-S1 Q4=A)

## 불변식 (데이터)

- **BR-S1-9 (참조만)**: 세션 레코드는 캐노니컬 노드를 **id 문자열로 참조만** 한다. 캐노니컬 Knowledge/Region을 복사·스냅샷하지 않는다. (FR-R1.2)
- **BR-S1-10 (degree/support/confidence 범위)**: `distortion_degree`·`support`·`confidence`는 `[0,1]`로 강제(클램프 또는 검증). 범위 밖 값은 거부 또는 클램프.
- **BR-S1-11 (distorted_from 종류)**: SessionRumor의 `distorted_from_kind` ∈ {`knowledge`, `rumor`}이며 `distorted_from_id`는 같은 종류의 유효 id를 가리킨다(연쇄 왜곡 허용). (값 채움은 S2)
- **BR-S1-12 (distortion 유일성)**: `(session_id, region_id)`당 RegionDistortion은 정확히 하나(PK). `set_region_distortion`은 upsert.
- **BR-S1-13 (타임라인 정렬)**: `list_timeline`은 항상 `turn` 오름차순, 동률 시 `created_at` 오름차순으로 반환한다. (FR-R4.2)

## 레이어 격리 (NFR-R2)

- **BR-S1-14 (캐노니컬 불변)**: 세션 레이어의 어떤 쓰기도 Neo4j/OpenSearch 캐노니컬 데이터를 변경하지 않는다. 캐노니컬 접근은 읽기 전용. (NFR-R2)
- **BR-S1-15 (세션 격리)**: 모든 rumor/distortion/timeline 조회·쓰기는 `session_id` 범위로 격리된다. 한 세션의 데이터가 다른 세션에 노출되지 않는다.
- **BR-S1-16 (포트 추상화)**: 세션 영속화는 `SessionRepository` 포트 뒤에서만 일어난다. 도메인 모델·서비스는 SQLAlchemy/PostgreSQL에 비종속이며, in-memory 어댑터로 완전 대체 가능하다. (NFR-R1)

## graceful / 운영

- **BR-S1-17 (idempotent schema)**: `ensure_schema`는 여러 번 호출해도 안전(`IF NOT EXISTS`). 기존 데이터/스키마를 파괴하지 않는다. (NFR-R3)
- **BR-S1-18 (조회 graceful)**: 없는 session/rumor 조회는 예외가 아닌 `None`/빈 목록 또는 명시적 404로 처리한다(메서드 계약대로). 호출자는 부분 실패에서 계속 진행 가능.
- **BR-S1-19 (인프라 공존)**: PostgreSQL 추가는 기존 Neo4j/OpenSearch 스택과 공존한다. 세션 DB 미가용 시 캐노니컬 빌드/쿼리 경로는 영향받지 않는다(분리 기동). (NFR-R3)

## 정리 (Neo4j Rumor 제거)

- **BR-S1-20 (Rumor 제거 무영향)**: 미사용 Neo4j `Rumor` 모델/매핑/경로 제거는 실동작에 영향이 없다(현재 `rumors=[]`). 관련 직렬화/매핑 **전용** 테스트만 삭제한다. (AD-R Q6=A, FD-S1 Q5=A)
- **BR-S1-21 (auto-rumor view 유지)**: consensus의 거리 기반 propagated 분류(`KnowledgeView.is_rumor`/`distortion_degree`, `ScopeLink.is_rumor`)는 Neo4j `Rumor` 노드와 무관하므로 **유지**한다. 해당 테스트도 유지. (기획자용 분류)
- **BR-S1-22 (회귀)**: Rumor 제거 후 캐노니컬 경로 기존 테스트는 GREEN을 유지하고 ruff/black은 클린이어야 한다. (NFR-R6)
