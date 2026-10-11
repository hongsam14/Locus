## Review

**Verdict:** READY
**Reviewer:** product-lead-reviewer
**Stage:** Requirements Analysis — Follow-up cycle
**Reviewed artifact:** `aidlc-docs/inception/requirements/follow-up-requirements.md`
**Class:** advisory
**Iteration:** 1
**Date:** 2026-10-07T05:23:31Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/inception/requirements/follow-up-requirements.md > §6 FR-S4(P1) vs FR-D4·D5·D6·D8·S5·S6·C12(P0), §8 R-3 | 에디터 화면(FR-S4)만 P1로 넘길 수 있다고 하지만, 에디터를 넘기면 어디까지가 넘어가는지 정해져 있지 않다. FR-D4는 "대화상자 넷·알림 셋·select 18번"을 모두 바꾸라고 하고, FR-D5는 에디터 390px 세로 쌓기, FR-S5·S6은 "네 화면 모두", FR-D8·FR-C12는 에디터 값(UX-23)·보강 질문 칸을 P0로 둔다. FR-S4가 빠지면 에디터가 옛 프리미티브와 새 프리미티브에 걸친 채 남거나, P0 항목이 사실상 에디터 작업을 끌어들인다. QA가 "P1을 넘긴 상태"의 합격선을 쓸 수 없다. | P1을 넘길 때 에디터에서 그래도 하는 것(프리미티브 교체, 공통 상태, enum 표기, 390px 쌓기)과 넘기는 것(FR-S4 목록 항목)을 가르는 문장을 FR-S4나 §8 R-3에 넣는다. FR-D5·S5·S6의 "네 화면"이 P1 분리 뒤에도 유효한지 적는다. | New |
| R-02 | Major | aidlc-docs/inception/requirements/follow-up-requirements.md > FR-L2, FR-L3, §5 흐름 1 | Q4=A의 목표는 "키 없이 연 데모가 처음부터 한국어"인데, FR-L3의 범위는 "지역명, 설명, NPC, 지식, 씨앗"이다. UX-05가 짚은 **데모 카드 제목·설명**(`manifest.json`의 `title`/`description`, World File 밖이다)과 홈의 월드 이름은 FR-L2의 번역 종류에도 FR-L3의 번역 파일에도 없다. 홈이 첫 화면이므로 \"홈·플레이·GM이 한국어\"라는 FR-L3 합격 문장이 카드 때문에 깨진다. 데모 월드에는 엔티티 8개·관계 2개·priors 2개도 있는데 화면에 나오는지, 번역 대상인지 말이 없다. | 번역 대상 목록에 매니페스트 카드 문구(title·description·credits)와 월드 이름을 넣거나 명시적으로 뺀다. 엔티티·관계가 화면에 나오는 곳이 있는지 확인해 대상 여부를 적는다. FR-L3 합격 조건에 "홈 데모 카드가 한국어"를 더한다. | New |
| R-03 | Minor | aidlc-docs/inception/requirements/follow-up-requirements.md > §2 Q5, §9, FR-C14 | Q5=A는 "이월 전부"인데 `next-cycle.md`의 이월 중 "§3 상한 밖 정확성 22건, §2 정리 11건", 설계 메모 3·4·6~10은 FR-C에도 §9 범위 밖에도 이름이 없다(메모 1·2·5·11·13·12만 처리됨). FR-C14가 "RE의 low"만 말한다. 추적표 끝줄이 이월 전체를 덮는 듯 보인다. | §9나 FR-C14에 U8 리뷰 이월 가운데 이번에 안 하는 것(§3 22건, §2 11건, 메모 3·4·6~10)을 명시적으로 `next-cycle.md`행으로 적는다. | New |
| R-04 | Minor | aidlc-docs/inception/requirements/follow-up-requirements.md > FR-C9 | "소스로 다시 빌드해도 NPC·씨앗을 잃지 않는다"의 방법(이어 붙이기 / 빌드가 생성 / 둘 다)을 FD로 미뤘다. 이것은 구현 방법이 아니라 제작자가 보는 동작(빌드 결과에 NPC가 새로 생기는가, 옛 것이 남는가)이고 README 문장도 이에 따라 달라진다. 합격 기준은 "잃지 않는다"만 있어 검증 가능하긴 하다. | FD 전에 사람이 정할 제품 결정임을 표시하거나, 최소 동작(옛 월드의 NPC·씨앗이 새 월드에 그대로 있다)을 못 박는다. | New |
| R-05 | Minor | aidlc-docs/inception/requirements/follow-up-requirements.md > NFR-3, NFR-7, FR-D5, FR-D7 | 검증 수단이 없는 수치·표현이 있다. NFR-3 대비 4.5:1은 axe·자동 검사가 범위 밖(Q7=B)인데 누가 어떻게 재는지 없다. NFR-7은 브라우저 5종인데 NFR-2의 사람 확인은 1280/390px만 말한다. FR-D5 "폭 상한", FR-D7 "라벨이 가려지지 않게"에는 값이나 판정 방법이 없다. | NFR-2 확인 목록에 대비 확인 방법(토큰 쌍 계산 또는 도구 한 번)과 확인할 브라우저·기기를 적는다. FR-D5의 폭 상한은 FD에서 정할 값임을 적는다. | New |
| R-06 | Minor | aidlc-docs/inception/requirements/follow-up-requirements.md > C-3, C-4, FR-T1 | FR-T1은 2026-10-19 시한이 있는 P0인데 `ci.yml`은 PR #4(미병합)의 `feat/purpose-restructure`에만 있다. 어느 브랜치에서 수정·검증하는지가 C-3의 "첫 커밋 전에 묻는다"에 걸려 있어, 시한 항목이 열린 질문에 막힌다. | C-3 질문을 FR-T1 착수 전(Workflow Planning 때)에 하도록 순서를 적고, 병합 전후 어느 쪽이든 FR-T1 합격(러너·액션 버전 아래 네 잡 통과)이 같음을 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| Q1~Q9, CQ1~CQ4 답과 §2 결정 기록 대조 | 13/13 일치 | OK, 모순 없음 |
| UX-01~42가 FR에 닿는지(§10 추적표) | UX-26만 범위 밖, 나머지 모두 매핑 | OK |
| #5(a), #9~#15, RE-W01·02·04·18, RE-P01~04·06, RE-F01~05, RE-T01·02·03·08·12 ID 해소 | 모두 `code-quality-assessment.md`·`next-cycle.md`에 있음 | OK |
| FR-C1의 "RE-P07"(재생성 겹침)이 Q5=A 목록 밖 | 의도적 제외로 보임 | 이상 없음 |
| Emberleaf 수치(지역 12, NPC 15, 지식 23, 씨앗 3) | World File에서 일치 | OK |
| 글꼴 760 kB, JS gzip 96.6 kB, dev audit 5건 | RE 문서와 일치(next-cycle의 4건은 RE가 5건으로 정정) | OK |
| 데모 카드 문구의 출처 | `manifest.json`의 title/description, FR-L2·L3 대상 아님 | R-02 확인 |
| U8 이월 중 §3 22건·§2 11건·메모 3·4·6~10의 행방 | FR·§9 어디에도 없음 | R-03 확인 |
| User Stories 생략 제안 | 페르소나 같음, 수용 기준은 FR·UX 표 | 타당. 단 R-01·R-05 수준의 합격선은 FD에서 닫아야 함 |

### Summary

Q&A 답과의 모순이 없고 UX·RE ID가 모두 해소되며 범위·범위 밖 구분이 분명해 엔지니어링이 시작할 수 있다. 사람이 승인 때 따져 볼 것은 에디터를 P1로 넘길 때의 경계(R-01)와, 키 없는 데모의 한국어 약속에서 빠진 데모 카드 문구(R-02)다. 나머지는 FD에서 닫을 수 있는 Minor다.
