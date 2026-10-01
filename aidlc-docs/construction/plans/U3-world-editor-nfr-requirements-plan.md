# U3 월드 에디터 — NFR Requirements + Design (light) 플랜

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U3의 비기능 요구를 한 장으로 확정합니다.
- 다루는 것
  - 의도된 동작 변경과 회귀, PBT
  - 편집 응답성과 지역 삭제의 원자성
  - 업로드 상한, 보강·초안의 LLM 상한과 프롬프트 주입
  - 저장 포트 확장의 계약 테스트, 화면 크기, 문서
- 코드 생성 플랜이 지킬 수치와 방법을 정하는 단계입니다.

실행 계획 §NFR대로 에디터 유닛은 **light**다.
- `construction/U3-world-editor/nfr/nfr-light.md` 한 장에 요구와 설계를 함께 적는다.
- 새 기술 스택 선택은 없다(C-3, C-4).
- Plan Review는 light 규칙대로 **advisory** 1회다.

## 플랜
- [x] 승인된 FD 산출물 분석(`construction/U3-world-editor/functional-design/*`, 검토 02 R-08·R-11 Accepted risk → 코드 플랜)
- [x] 현재 코드의 기준선 실측(2026-10-01, HEAD `aedf72d`)
  - pytest 735, vitest 94, mypy 11(6 파일)
  - 업로드 경로(`api/routers/world.py:170`, `:334`)에 크기·개수 상한이 없다.
  - 메모는 자르지 않고 LLM 호출 1회에 통째로 들어간다(`text_ingestor.py:38`).
  - `detect_wiki_conflicts`는 DIRECT 스코프마다 wiki 조회 1회와 LLM 1회를 부른다. 상한이 없다(`detectors.py:71`). 지금은 `terrain`을 읽어서 한 번도 불리지 않는다(B5).
  - 질문 다듬기는 질문마다 LLM 1회다(`questions.py:43`).
  - 턴은 한 턴 안에서 스냅샷을 여러 번 읽는다(`advancer.py:213·378·402·560`).
  - 검색 문서를 읽는 경로는 wiki prior 조회뿐이다(`wiki/base.py:68`, `cross_world.py:52`).
- [x] NFR-1~9와 U3의 접점 정리; 질문 필요 여부 판단
- [x] `construction/U3-world-editor/nfr/nfr-light.md` 작성
- [x] Plan Review(architecture-reviewer, **advisory** 1회) — open 8(Major 3) → `construction/U3-world-editor/nfr/reviews/nfr-light-review-01.md`
- [x] 완료 메시지 + 승인 게이트 → 승인(Continue to Next Stage) → 다음: U3 Code Generation Part 1(플랜)

## 질문
없다. U3에 걸리는 값은 대부분 FD에서 정해졌다.
- 보강 상한: 질문 20, 답 30, 다듬기 5, 판정 20, run 20개
- 폴백 prior 상한 40, NPC 초안 0~3명과 필드 상한
- 지도 끌기 4px

아래 가정은 값이 비어 있던 곳을 채운 것이다. 게이트나 코드 생성 플랜에서 바꿀 수 있다.

## 가정 (nfr-light.md에 반영)
| # | 가정 | 근거 |
|---|---|---|
| N3-1 | 편집 쓰기·읽기는 LLM 없이 로컬 p95 ≤ 150ms다. 조건은 지역 15·지식 300·NPC 30·연결 40, 캐시가 찬 상태다(운영자 확인). 오프라인 게이트는 구조 단언이다(nfr-light §1 NFR-3) | NFR-3, U7 N7-1 방식 |
| N3-2 | 그래프 포트에 트랜잭션을 더하지 않는다. 지역 삭제는 BR-U3-8 순서로 "어느 단계에서 끊겨도 끊긴 id가 없다"를 지키고, 같은 삭제를 다시 부르면 끝까지 간다. 검색 문서는 그래프 쓰기 뒤에 지운다 | NFR-9, BLM §1.1 |
| N3-3 | 업로드 상한을 둔다. 요청 전체 48 MiB, 파일 종류별 개수·크기, 메모 60,000자, 이미지 형식 PNG·JPEG·WebP다. 넘으면 413, 형식이 틀리면 422다. 상한은 `api/`의 상수다(env 아님) | NFR-6 "업로드 크기·형식" |
| N3-4 | 보강 run 하나의 LLM 호출은 60회까지다. 넘으면 질문은 템플릿만 쓰고 wiki_conflict 판정을 쉰다. 보강의 wiki 조회는 검색만 한다(LLM 폴백 없음). 근거 prior가 없으면 판정하지 않는다 | NFR-5, BR-U3-41 |
| N3-5 | world 쪽 프롬프트(NPC 초안, 질문 다듬기, 충돌 판정)도 U7 방식을 따른다. 자유 글은 `one_line`과 글자 상한을 거치고, 자료는 "material, not instructions" 머리말 아래에 둔다. 초안 프롬프트는 6,000자 이하다(계산은 nfr-light §1 NFR-5) | NFR-5·6, U7 N7-3 |
| N3-6 | 편집은 열린 세션의 턴과 겹칠 수 있다(Q2=A). 턴을 막는 것은 지역 삭제(GM 리스)뿐이다. 그 밖의 편집이 턴 도중에 들어오면 그 턴은 앞뒤 스냅샷을 섞어 읽을 수 있다. 지역이 사라지지 않으므로 오류는 없고, 다음 턴이 고친다 | Q2=A, NFR-3 |
| N3-7 | 보강 run은 run마다 잠금 하나를 둔다. 같은 run의 답·되돌리기는 차례로 돈다. 다른 run끼리, 그리고 에디터 편집과는 잠그지 않는다(BR-U3-27의 409가 run 밖 편집을 막는 것은 코드 플랜의 R-08 처리다) | BR-U3-26·27, 검토 02 R-08 |
| N3-8 | 의도된 동작 변경 목록(NFR-1)은 nfr-light §4가 갖는다. 바뀌는 테스트는 코드 생성 플랜이 이름으로 전수 적는다 | NFR-1 |
