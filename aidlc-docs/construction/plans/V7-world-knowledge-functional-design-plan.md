# V7 월드·지식 정확성 — Functional Design Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**지금 하는 것**: Construction V7(실행 7/9), Functional Design. "지역마다 NPC가 다르게 안다"를 바르게 하고, 제작자의 손작업과 월드를 지키는 규칙을 정한다. 백엔드만 바뀐다.

**입력**:
- 요구사항 `inception/requirements/follow-up-requirements.md`
  - FR-C6: 합의는 출처 순서와 무관하다.
  - FR-C7: 다른 프로세스의 교체 중 캐시
  - FR-C8: 백업이 실패하면 교체하지 않는다.
  - FR-C9: 다시 빌드해도 NPC·씨앗을 잃지 않는다.
  - FR-C10: 중복 id, 라벨 없는 삭제
  - FR-C12: 보강 질문의 입력 칸
- 역공학 `code-quality-assessment.md`: RE-W01, W02, W03, W04, W18, U8 #10, U8 #13
- Application Design(승인) `inception/application-design/follow-up/`
  - `components.md`, `component-methods.md` § 2~4, `services.md` S4·S7
  - Q3=A: 다시 빌드할 때 옛 NPC·씨앗을 (이름, 단계)로 이어 붙이고, 못 맞춘 것은 경고로 남긴다.
  - 설계 리뷰가 이 FD에 넘긴 것
    - R-02: `_backup`의 "미설정"과 "실패" 구별, 옛 스냅샷을 캐시가 아니라 로더로 읽기
    - R-05: 라벨 인자 호출부 11곳과 테스트 대역 두 곳
    - R-06: 실제 `compute_consensus` 시그니처
    - R-08: WorldMeta를 마지막에 쓸 때의 실패 경로와 `ok`
- 유닛 `unit-of-work.md` V7
  - 완료 조건
    - 연결 순서를 섞어도 합의 결과가 같다(속성 테스트).
    - 교체 중 다른 프로세스의 캐시가 연결 없는 스냅샷을 잡지 않는다.
    - 백업이 실패하면 옛 월드가 남는다.
    - 다시 빌드한 뒤 옛 NPC·씨앗이 남거나 경고로 보고된다.
    - 중복 id World File을 거절한다. 라벨 없는 삭제가 다른 라벨을 지우지 않는다.
    - 엔티티 보강 질문에 제목 칸이 없다.
- PBT 확장: Partial이다. PBT-02/03/07/08/09는 지킨다. FR-C6은 PBT-03(속성)이다.

**산출물 위치**: `aidlc-docs/construction/V7-world-knowledge/functional-design/`
- `business-logic-model.md`: 합의 출처 고르기, 캐시와 저장 순서, 백업 게이트, 이어 붙이기, 중복 id, 라벨 있는 읽기·삭제, 보강 입력 칸
- `business-rules.md`: BR-V7-*, 테스트 계획 TP-V7-*, 속성 PBT-V7-*
- `domain-entities.md`: `best_origins` 결과, `CarryOver`, `BackupResult`, `NEEDS` 표, 리포트 칸

---

## 계획 (checkbox)

- [x] 1. 질문(아래)의 답을 받고, 모호함이 있으면 다시 묻는다 — Q1 = A, 모호한 답 없음(2026-10-08)
- [x] 2. `domain-entities.md`를 쓴다
- [x] 3. `business-logic-model.md`를 쓴다
- [x] 4. `business-rules.md`를 쓴다(BR-V7-01..22, TP-V7-1..14, PBT-V7-1..5)
- [x] 5. 설계 검토자 리뷰(adversarial, 최대 2회) 뒤 승인 — 1차 미흡(R-01..R-08 고침) → 2차 통과, R-09·R-10·S-1은 코드 계획으로(2026-10-11 승인)

---

## 이 계획이 스스로 정한 것 (질문하지 않음)

Application Design(승인)이 정했거나, 코드 사실에서 하나로 정해지는 것이다.

- **합의 출처**(FR-C6, RE-W01, R-06)
  - 시그니처는 그대로 둔다: `compute_consensus(region_id, *, snapshot=None, regions=None, connections=None, scopes=None, knowledge_by_id=None, params=DEFAULT_PARAMS)`.
  - 4단계(전파)에서 순수 함수 `best_origins(pw, region_direct, exclude=region_id)`를 부른다.
    - 지식마다 경로 가중 `pw[출처]`가 가장 큰 출처를 고른다.
    - 가중이 같으면 지역 id가 작은 쪽을 고른다.
  - 그 결과로 propagated / hearsay / unknown을 나눈다.
  - `unknown_count`는 지식 하나를 한 번만 센다. 셈 대상은 직접·이어받음·전역으로 이미 정해지지 않았고, 가장 강한 출처도 hearsay 문턱 아래인 지식이다. 지금은 (출처, 지식) 쌍마다 세어 부풀려진다.
  - `best_path_weights`(최대곱 Dijkstra)는 값이 순서와 무관하므로 바꾸지 않는다.
- **캐시와 저장 순서**(FR-C7, RE-W02, RE-W03, R-08)
  - `persist_graph`는 이 순서로 쓴다: 노드(WorldMeta 제외) → 엣지 → 임베딩·색인 → **WorldMeta**.
  - 노드·엣지 쓰기가 실패하면 지금처럼 거기서 멈춘다. WorldMeta는 쓰지 않고, error 경고라 리포트는 `ok=false`다.
  - 색인이 실패해도 그래프는 다 써졌으므로 WorldMeta를 쓴다. 색인 실패는 지금처럼 error 경고다(`ok=false`).
  - WorldMeta 쓰기가 실패하면 error 경고다.
  - `WorldCache`는 버전을 모르는(WorldMeta가 없는) 스냅샷을 캐시하지 않는다. 교체 중의 반쪽 스냅샷은 그 한 번만 쓰이고 다음 읽기가 다시 불러온다.
    - 버전을 읽을 수 있는 캐시에만 건다. 로더에 `version()`이 없거나 `check_version=False`면 지금처럼 캐시한다(FD 리뷰 01 R-01).
    - 비용: WorldMeta가 없는 옛 월드(U2 이전)는 읽을 때마다 불러온다. 다시 빌드하면 없어진다.
  - 캐시 hit의 버전 읽기가 실패하면 miss처럼 다룬다. 항목을 버리고 새로 불러오며, 캐시하지 않는다(RE-W03).
- **백업 게이트**(FR-C8, RE-W04, R-02)
  - `_backup`은 셋 가운데 하나를 돌려준다.
    - 미설정(`exporter`나 `backup_dir`가 없음): 통과. 지금의 CLI·테스트 빌더가 그대로 돈다.
    - 성공: 경로
    - 실패: `BackupFailedError`
  - 실패면 **지우기 전에** 멈춘다. 옛 월드를 그대로 두고, 리포트는 `ok=false`, stage `backup`, error 경고다. 빌드와 World File 불러오기가 같다.
- **이어 붙이기**(FR-C9, RE-W18, Q3=A)
  - 지우기 전에 옛 스냅샷을 **캐시를 거치지 않고 새로** 읽는다(빌더가 가진 캐시를 무효화한 뒤 `get`, FD 리뷰 01 R-08). 캐시는 직접 편집 직후의 NPC·씨앗을 놓칠 수 있다(R-02). 읽지 못하면 백업 실패와 같이 교체하지 않는다(FD 작성 중 정함: 백업 미설정이면 NPC·씨앗이 어디에도 남지 않기 때문).
  - 순수 함수 `carry_over(old, new_regions, world_id)`가 옛 NPC의 집 지역과 옛 씨앗의 지역을 새 지역에 맞춘다.
    - 맞추는 열쇠는 옛 지역의 (이름, 단계)다. 이름은 NFKC, 대소문자 무시, 공백을 하나로 모아 비교한다.
    - 같은 열쇠의 새 지역이 여럿이면 부모 지역의 (이름, 단계)로 한 번 더 가른다.
    - 그래도 하나로 정해지지 않거나 없으면 붙이지 않고 경고를 남긴다. 그 NPC·씨앗은 백업에만 남는다.
  - 붙인 NPC·씨앗은 id를 그대로 둔다. 그래서 번역도 그대로 남는다(교체 뒤 번역 정리는 새 월드의 id를 남긴다, V3).
  - 붙인 NPC·씨앗은 새 월드와 **같은 `persist_graph` 호출**에서 쓴다. WorldMeta가 그 뒤에 마지막으로 써진다.
  - 리포트에 `carried_npcs`, `carried_seeds`와 못 붙인 것의 경고가 실린다. 빌드 자체는 NPC를 만들지 않는다.
  - README의 "NPC가 만들어집니다"를 고친다: "빌드는 지역·연결·지식을 만들고, NPC와 사건 씨앗은 에디터에서 더하며, 다시 빌드해도 남는다".
- **중복 id**(FR-C10, U8 #10)
  - `duplicate_ids(file)`는 절 사이와 절 안에서 두 번 이상 나온 id를 돌려준다. 대상 절은 regions, entities, relations, knowledge, priors, npcs, event_seeds다.
  - 불러오기는 재매핑 **뒤에**, 아무것도 쓰기 전에 검사한다. 있으면 `ok=false`이고 그 id들을 경고로 돌려준다. 옛 월드는 그대로다.
- **라벨 있는 읽기·삭제**(FR-C10, R-05)
  - `get_node`와 `delete_node`에 선택 인자 `label`을 더한다. 테스트 대역 두 곳(`tests/shared/storage/fakes.py`, `tests/world/services/test_services.py`)도 바꾼다.
  - production 호출부 12곳(FD 리뷰 01 R-05가 셈을 바로잡음): 라벨을 아는 9곳은 넘긴다.
    - `editor/writes.py`의 `node`와 `delete_held`, `editor/regions.py`의 삭제 셋(씨앗 `EventSeed`, NPC `NPC`, 지역 `Region`), `augmentation/apply.py`의 다시 가리키기(기대 라벨)·되돌리기(스냅숏 라벨)·추가 노드 삭제(스냅숏 라벨)
  - "이 id의 노드가 무엇이든"을 묻는 곳은 라벨 없이 둔다.
    - `own_label`(다른 라벨이 이미 그 id를 쓰는지 확인), `bundle.delete_any`(지식 또는 엔티티), `apply._nodes`(스냅숏)
    - 중복 id를 막으면 이곳들의 모호함은 생기지 않는다.
- **보강 질문의 입력 칸**(FR-C12, U8 #13)
  - `NEEDS`를 (이슈 종류, **대상 종류**)로 찾는다.
  - 엔티티 대상의 고치기는 설명(statement 칸 → `description`)과 확신만 받는다. 제목 칸이 없다.
  - 지식 대상은 지금처럼 문장·제목·확신을 받는다.
  - 아무것도 바꾸지 않는 고치기·더하기·다시 가리키기 답(빈 칸뿐이거나 지금 값과 같음)은 쓰기 전에 400 `invalid_request`로 거절한다. 변경 기록을 남기지 않고 질문은 열린 채다.
  - 확인(이대로 둔다)은 거절하지 않는다(FD 리뷰 01 R-03).
- **시험**
  - 합의: 속성 테스트 PBT-03. 연결·스코프·지식 순서를 섞어도 결과가 같고, 고른 출처의 가중이 최대이며, `unknown_count`가 같다. hypothesis를 쓴다.
  - 캐시: 다른 프로세스 교체를 흉내 낸다(노드만 쓴 상태에서 읽기 → 캐시되지 않음 → 다 쓴 뒤 새 버전).
  - 백업 실패, 이어 붙이기, 중복 id, 라벨 있는 삭제, 보강 칸은 인메모리 대역으로 시험한다.

---

## 질문

답은 `[Answer]:` 뒤에 적거나 대화창에서 주세요. 고정 선택지 `X. Other (please specify)`는 그대로 둡니다.

### Q1. "이곳 NPC가 아는 것"의 목록 순서

**배경**:
- 합의 결과의 각 목록은 지금 입력 순서를 따른다. 직접은 스코프 순서, 전파·전언은 경로 탐색 순서다.
- 그래서 같은 월드도 로드할 때마다 순서가 달라질 수 있다. FR-C6의 "로드할 때마다 같은 지역 지식"은 순서까지 고정해야 채워진다.
- 이 순서는 플레이어가 본다. 휴대폰 플레이 화면은 "아는 것"을 3개 보이고 [더 보기]로 늘린다(V4). 그래서 순서가 곧 플레이어가 먼저 읽는 것이다.
- 이 답에 기대는 것: 합의 결과의 목록 정렬, 속성 테스트의 "같다"의 뜻, 플레이 화면과 GM 지식 접힘의 첫 줄.

A. 확실한 것부터 — 각 목록 안에서 확신도(전파·전언은 경로를 거친 유효 확신도)가 높은 것부터, 같으면 지식 id 순
   - 플레이어가 먼저 보는 3개가 그 지역 사람들이 가장 확실히 아는 것이 된다.
   - 순서가 입력과 무관하게 고정된다.
   - 비용: 지금 보이는 순서와 달라진다. 순서를 단언한 기존 테스트 몇 개를 고친다.
   - (권장: 플레이어가 먼저 읽는 것이 가장 믿을 만한 것이어서 TRPG 장면으로 자연스럽고, 순서 고정도 함께 이룬다)
B. 지식 id 순 — 각 목록을 지식 id 순으로만 고정한다.
   - 순서는 고정된다.
   - 비용: id는 사람에게 뜻이 없어서, 휴대폰에서 먼저 보이는 3개가 우연히 정해진다.
C. 지금 순서를 그대로 두고, 같음은 집합으로만 본다.
   - 화면 순서가 지금과 같다.
   - 비용: 로드마다 순서가 바뀔 수 있는 문제가 남는다. FR-C6의 "같은 지역 지식"은 내용만 채운다.
X. Other (please specify)

[Answer]: A (대화창, 2026-10-08) — 확실한 것부터
