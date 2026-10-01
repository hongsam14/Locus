// Lightweight i18n (X3 / C10, extended by U5): two dictionaries (ko, en) and the
// display language as module state, remembered in localStorage. No library (FD-U5
// frontend §2.2): ~150 keys do not justify i18next. Korean is the default (Q2=A).
// UI static labels + timeline kind templates (F2a) + notification segments.
import { useSyncExternalStore } from "react";
import type { Lang } from "./types";

type Params = Record<string, unknown>;

export const LANGS: readonly Lang[] = ["ko", "en"];
const STORAGE_KEY = "locus.lang";

const ko = {
  // navigation / display language
  "nav.editor": "에디터",
  "nav.gm": "GM",
  "nav.play": "플레이",
  "nav.gmLocked": "세션을 선택하면 열립니다",
  "lang.label": "표시 언어",

  // shared fragments
  "common.loading": "불러오는 중…",
  "common.turn": "턴 {n}",
  "label.decay": "감쇠",
  "badge.hearsay": "전언",
  "badge.rumor": "소문",

  // editor toolbar / editor screen
  "toolbar.worldId": "월드 id",
  "toolbar.load": "불러오기",
  "toolbar.loadDemo": "데모 월드 불러오기",
  "toolbar.pickMap": "지도:",
  "editor.enterWorldId": "world id를 입력하세요",
  "editor.working": "작업 중…",
  "editor.noWorld": "불러온 월드가 없습니다. {loadDemo} 또는 {load}을(를) 누르세요.",
  "editor.emptyWorld":
    "월드 {world}에 지역이 0개입니다. 데모를 불러오거나(위 버튼 또는 아래 명령) 빌드한 뒤 다시 불러오세요. world id가 맞는지 확인하세요.",
  "editor.status":
    "월드 {world} · 지역 {regions} · 연결 {connections} · 엔티티 {entities} · 지식 {knowledge}",
  "editor.replaceTitle": "월드 교체",
  "editor.replaceConfirm": "닫고 교체",
  "editor.replaceBody":
    "이 월드에 열린 세션이 {n}개 있습니다. 데모를 불러오면 그 세션을 닫고 월드를 교체합니다. 계속할까요?",

  // region knowledge panel (editor / GM)
  "region.title": "지역 지식",
  "region.unique": "고유 {n}",
  "region.shared": "공유 {n}",
  "region.empty": "이 지역에 알려진 것이 없습니다",

  // knowledge augmentation
  "augment.title": "지식 보강",
  "augment.start": "실행 시작",
  "augment.revert": "되돌리기",
  "augment.status": "상태: {status} · 답 {answers}/30",
  "augment.none": "열린 질문이 없습니다 🎉",

  // session bar
  "session.title": "세션",
  "session.new": "새 세션",
  "session.close": "닫기",
  "session.none": "— 없음 —",
  "session.play": "플레이 시작",
  "session.playTitle": "새 플레이 세션",
  "session.name": "이름",
  "session.startRegion": "시작 지역",
  "session.pickRegion": "지역을 고르세요",

  // GameMaster / SessionPanel labels
  "gm.title": "GameMaster · 턴 {turn}",
  "gm.loading": "세션을 불러오는 중…",
  "gm.retry": "다시 시도",
  "gm.noSessionHint": "세션이 없으면 에디터에서 새 세션을 시작하세요.",
  "gm.world": "월드 {world}",
  "gm.worldCounts": "지역 {regions} · 연결 {connections}",
  "gm.advanceTurn": "턴 진행",
  "gm.suggestEvents": "이벤트 제안",
  "gm.events": "이벤트",
  "gm.timeline": "타임라인",
  "gm.region": "지역",
  "gm.distortion": "왜곡",
  "gm.generate": "소문 생성",
  "gm.regen": "재생성",
  "gm.generateAll": "전체 생성",
  "gm.regenAll": "전체 재생성",
  "gm.createEvent": "이벤트 생성",
  "gm.eventDescription": "설명",
  "gm.lifecycleDefault": "기본",
  "gm.approve": "승인",
  "gm.discard": "폐기",
  "gm.resolve": "해소",
  "gm.support": "공신력",
  "gm.promoted": "승격됨",
  "gm.noRegion": "지도에서 지역을 선택해 소문·이벤트를 관리하세요.",

  // actions
  "action.original": "원문",
  "action.translated": "번역",
  "action.confirm": "확인",
  "action.cancel": "취소",
  "action.close": "닫기",

  // confirms
  "confirm.regen": "이 지역 소문을 재생성합니다. 승격된 소문은 보존됩니다.",
  "confirm.regenAll": "모든 지역 소문을 재생성합니다(덮어쓰기). 승격된 소문은 보존됩니다.",

  // progress
  "progress.done": "{done}/{total} 완료",
  "progress.failed": "{failed}건 실패",
  "notif.noTargets": "생성할 빈 지역이 없습니다",

  // player mode (U4)
  "play.title": "플레이어 모드",
  "play.noSession": "세션을 선택하거나 에디터에서 플레이를 시작하세요.",
  "play.npcs": "이곳의 사람들",
  "play.facts": "아는 것",
  "play.hearsay": "들은 이야기",
  "play.hearsayHint": "이 지역에 희미하게 닿은 이야기입니다. 사람들이 다 아는 것은 아닙니다.",
  "play.rumors": "떠도는 소문",
  "play.moves": "갈 수 있는 곳",
  "play.move": "이동",
  "play.turns": "{n}턴",
  "play.blocked": "지나갈 수 없음",
  "play.wait": "기다리기 (1턴)",
  "play.running": "세계가 움직이는 중… ({n}턴)",
  "play.turnInProgress": "턴이 진행 중입니다",
  "play.sessionClosed": "세션이 종료되었습니다",
  "play.gmMode": "GM 모드",
  "gm.backToPlay": "플레이로 돌아가기",
  "gm.playerStatus": "{name} · {region} · {turn}턴",
  "gm.running": "(진행 중)",
  "gm.stateToggle": "세계 상태",
  "gm.stateLegend": "왜곡도(색) · 활성/승격 소문(숫자)",
  "gm.feedbackShare": "되먹임 몫 {share}",
  "gm.suggestN": "개수",
  "dialogue.failed": "지금은 대답을 듣지 못했어요. 다시 말해 보세요.",
  "play.turnDone": "턴 {n} 완료",
  "play.runFailed": "턴 처리에 실패했습니다",
  "play.budget": "LLM 예산이 다해 일부 소문을 건너뛰었습니다",
  "play.llmFailed": "LLM 호출이 실패해 남은 소문 생성을 멈췄습니다",
  "play.noLlm": "LLM 키가 없어 소문·대화가 생성되지 않습니다. 이동과 지도는 동작합니다.",
  "play.log": "여정 기록",
  "play.quiet": "조용하다",

  // NPC dialogue (U5)
  "npc.talk": "말하기",
  "dialogue.title": "대화 · {name}",
  "dialogue.has": "대화 {n}",
  "dialogue.you": "나",
  "dialogue.empty": "아직 나눈 말이 없습니다.",
  "dialogue.placeholder": "무엇을 물어볼까요?",
  "dialogue.send": "보내기",
  "dialogue.sending": "답을 기다리는 중…",
  "dialogue.end": "대화 끝내기 (1턴)",
  "dialogue.noLlm": "LLM 키가 없어 대화할 수 없습니다. 지난 대화는 볼 수 있습니다.",

  // deeds & spread (U6)
  "play.declare": "선언하기 (1턴)",
  "play.declarePlaceholder": "무엇을 하시겠습니까?",
  "play.chars": "{n}/{max}자",
  "play.narrationTitle": "세계의 응답",
  "play.narrationFallback": "서술을 만들 LLM이 없어 행동만 기록했습니다",
  "badge.deed": "행적",
  "deed.title": "행적",
  "deed.kind.arrival": "도착",
  "deed.kind.statement": "발언",
  "deed.kind.declared_action": "선언",
  "deed.declaration": "선언 원문",
  "deed.witnesses": "목격",
  "deed.appraisals": "판단",
  "deed.salience": "열의",
  "deed.reached": "도달 지역",
  "deed.void": "취소",
  "deed.voidTitle": "행적 취소",
  "deed.voidConfirmBtn": "없던 일로 하기",
  "deed.voidConfirm": "이 행적과 그 소문 {n}건을 없던 일로 합니다. 되돌릴 수 없습니다.",
  "deed.voided": "취소됨",
  "deed.none": "아직 행적이 없습니다",

  // timeline (kind -> template; payload fields interpolated)
  "timeline.session_started": "{player_name} 도착 · {region_name}",
  "timeline.session_closed": "세션 종료",
  "timeline.player_moved": "이동: {from_region_name} → {to_region_name} ({cost_turns}턴)",
  "timeline.player_waited": "대기 · {region_name}",
  "timeline.npc_talked": "대화: {npc_name} · {region_name}",
  "timeline.action_declared": "선언 · {region_name}",
  "timeline.deed_recorded": "발언 기록 · {npc_name}",
  "timeline.deed_appraised": "{npc_name}의 판단 · {region_name}",
  "timeline.deed_seeded": "행적 소문 · {region_name}",
  "timeline.rumor_spread": "소문 전파: {from_region_name} → {region_name}",
  "timeline.deed_voided": "행적 취소",
  "timeline.turn_run_failed": "턴 처리 실패",
  "timeline.generate": "소문 생성 · {region}",
  "timeline.regenerate": "소문 재생성 · {region}",
  "timeline.promote": "소문 승격 · {region}",
  "timeline.demote": "소문 강등 · {region}",
  "timeline.prune": "소문 소멸 · {region}",
  "timeline.adjust_support": "공신력 조정 · {region}",
  "timeline.advance_turn": "턴 {turn} 진행",
  "timeline.set_distortion": "왜곡 설정 · {region} → {degree}",
  // U7 (BR-U7-8): event_created is a GM's own creation only; suggestions and approvals
  // have their own kinds (older lines with suggested/approved flags map onto them).
  "timeline.event_created": "{category} 이벤트 생성 · {region}",
  "timeline.event_suggested": "{region}에 {category} 사건이 제안되었다",
  "timeline.event_approved": "{region}의 {category} 사건을 승인했다",
  "timeline.event_discarded": "{region}의 {category} 제안을 버렸다",
  "timeline.event_applied": "이벤트 적용 · {region}",
  "timeline.event_resolved": "이벤트 해소 · {region}",
  "timeline.gm_session_started": "GM 세션 시작",
  "log.deed_seeded": "{region}에 당신에 대한 이야기가 돌기 시작했다",
  "log.rumor_spread": "당신에 대한 이야기가 {region}까지 왔다",

  // notification segments (per-region turn change)
  "notif.title": "지역 {region_id}",
  "notif.promoted": "{n}건 승격",
  "notif.demoted": "{n}건 강등",
  "notif.pruned": "{n}건 소멸",
  "notif.rumors_added": "{n}건 신규 소문",
  "notif.events_applied": "이벤트 {n} 적용",
  "notif.events_resolved": "이벤트 {n} 해소",

  // U3 world editor (frontend-components §4)
  "home.title": "월드",
  "home.empty": "아직 월드가 없습니다.",
  "home.edit": "편집",
  "home.startSession": "세션 시작",
  "home.loadDemo": "데모 불러오기",
  "home.buildFromSources": "자료로 만들기",
  "home.regions": "지역 {n}",
  "home.updated": "수정 {when}",
  "home.openSessions": "열린 세션 {n}",
  "home.newWorldId": "새 월드 id",
  "map.tool.select": "선택·이동",
  "map.tool.addRegion": "지역 추가",
  "map.tool.connect": "연결 긋기",
  "map.hint.select": "지역을 누르면 고르고, 끌면 옮깁니다",
  "map.hint.addRegion": "빈 곳을 누르면 그 자리에 지역을 만듭니다",
  "map.hint.connect": "잇고 싶은 지역 둘을 차례로 누르세요",
  "map.hint.connectSecond": "{name}에서 이을 지역을 누르세요",
  "editor.tab.region": "지역",
  "editor.tab.unscoped": "스코프 없음 {n}",
  "editor.tab.augment": "보강",
  "editor.tab.wiki": "wiki",
  "editor.pickRegion": "지도에서 지역을 고르세요",
  "editor.region.title": "지역",
  "editor.region.add": "새 지역",
  "editor.region.name": "이름",
  "editor.region.level": "단계",
  "editor.region.parent": "부모",
  "editor.region.noParent": "— 없음 —",
  "editor.region.description": "설명",
  "editor.region.save": "저장",
  "editor.region.delete": "지역 삭제",
  "editor.connection.title": "연결",
  "editor.connection.add": "새 연결",
  "editor.connection.kind": "종류",
  "editor.connection.weight": "통하는 정도",
  "editor.connection.save": "저장",
  "editor.connection.delete": "연결 삭제",
  "editor.connection.none": "연결이 없습니다",
  "editor.connection.prior": "근거: {effect}",
  "editor.connection.brokenPrior": "저장되지 않은 근거 ({id})",
  "editor.knowledge.title": "이곳의 지식",
  "editor.knowledge.add": "지식 추가",
  "editor.knowledge.titleLabel": "제목",
  "editor.knowledge.statement": "진술",
  "editor.knowledge.edit": "고치기",
  "editor.knowledge.save": "저장",
  "editor.knowledge.delete": "지식 삭제",
  "editor.knowledge.none": "이곳에 붙은 지식이 없습니다",
  "editor.scopes": "스코프",
  "editor.scopes.save": "스코프 저장",
  "editor.npc.title": "주민",
  "editor.npc.add": "NPC 추가",
  "editor.npc.name": "이름",
  "editor.npc.role": "역할",
  "editor.npc.description": "설명",
  "editor.npc.traits": "특성(쉼표로)",
  "editor.npc.save": "저장",
  "editor.npc.delete": "NPC 삭제",
  "editor.npc.none": "이곳에 사는 NPC가 없습니다",
  "editor.npcDraft.suggest": "NPC 제안",
  "editor.npcDraft.accept": "받아들이기",
  "editor.npcDraft.failed": "제안을 받지 못했어요. 잠시 뒤 다시 해 보세요.",
  "editor.npcDraft.none": "제안이 없습니다",
  "editor.unscoped.title": "스코프 없는 지식",
  "editor.unscoped.none": "모든 지식이 어느 지역엔가 붙어 있습니다",
  "editor.unscoped.pick": "지역 고르기",
  "editor.unscoped.assign": "지정",
  "editor.saved": "저장했습니다",
  "delete.title": "삭제할까요?",
  "delete.confirm": "삭제",
  "delete.knowledge": "지식 \"{name}\"을(를) 지웁니다.",
  "delete.npc": "NPC \"{name}\"을(를) 지웁니다. 세션의 대화 기록은 남습니다.",
  "delete.connection": "{a}–{b} ({kind}) 연결의 두 방향을 지웁니다.",
  "delete.prior": "근거 \"{name}\"을(를) 지웁니다. 이를 가리키던 연결·지식은 \"저장되지 않은 근거\"가 됩니다.",
  "delete.region.title": "{name} 지역 삭제",
  "delete.region.children": "자식 지역 {n}곳은 위 지역 밑으로 옮깁니다: {names}",
  "delete.region.connections": "연결 {n}개를 지웁니다",
  "delete.region.npcs": "NPC {n}명을 지웁니다: {names}",
  "delete.region.unscope": "지식 {n}개는 스코프 없음이 됩니다: {names}",
  "delete.region.scopeRemoved": "지식 {n}개는 이 지역 스코프만 빠집니다",
  "delete.region.entities": "엔티티 {n}개의 위치를 비웁니다",
  "delete.region.blocked": "열린 세션의 플레이어가 이곳에 있어 지울 수 없습니다: {ids}. GM 화면에서 세션을 닫거나 플레이어를 옮기세요.",
  "delete.region.done": "지웠습니다: 자식 {children} 옮김 · NPC {npcs} · 연결 {connections} · 스코프 없음 {unscoped}",
  "augment.find": "빈틈 찾기",
  "augment.target.knowledge": "지식",
  "augment.target.entity": "엔티티",
  "augment.target.region": "지역",
  "augment.target.npc": "NPC",
  "augment.target.connection": "연결",
  "augment.action.confirm": "맞음",
  "augment.action.edit": "고치기",
  "augment.action.remove": "지우기",
  "augment.action.add": "추가",
  "augment.action.ignore": "무시",
  "augment.statement": "진술",
  "augment.region": "지역",
  "augment.ref": "새 대상",
  "augment.changed": "바뀐 것",
  "augment.reverted": "되돌림",
  "augment.ignored": "무시한 질문",
  "augment.unignore": "다시 묻기",
  "augment.converged": "더 물을 것이 없습니다",
  "augment.stopped": "이번 실행의 답 한도에 닿았습니다. 새로 찾기를 누르세요.",
  "augment.budget": "이번 실행의 LLM 한도를 다 썼습니다: 질문은 기본 문장으로 묻고 지형 충돌은 쉬어 갑니다.",
  "augment.lost": "보강 기록이 사라졌어요(서버 재시작). 새로 찾아 주세요.",
  "augment.conflict": "되돌릴 수 없습니다: {reason}",
  "wiki.title": "상식 근거",
  "wiki.condition": "조건",
  "wiki.effect": "효과",
  "wiki.domains": "도메인",
  "wiki.confidence": "신뢰도",
  "wiki.refs": "참조 {n}",
  "wiki.broken": "저장되지 않은 근거",
  "wiki.none": "저장된 근거가 없습니다",
  "wiki.delete": "삭제",
  "build.title": "자료로 월드 만들기",
  "build.worldId": "월드 id",
  "build.name": "이름",
  "build.description": "설명",
  "build.memoText": "메모(직접 쓰기)",
  "build.memos": "메모 파일(.txt/.md)",
  "build.maps": "구조화 지도(JSON)",
  "build.images": "지도 이미지",
  "build.conceptArts": "컨셉 아트",
  "build.submit": "만들기",
  "build.working": "만드는 중… LLM이 자료를 읽느라 수십 초 걸립니다",
  "build.replaceConfirm": "같은 id의 월드가 있습니다. 교체할까요?",
  "build.closeSessions": "열린 세션 {n}개를 닫고 진행할까요?",
  "build.report.title": "빌드 리포트",
  "build.report.ok": "완료",
  "build.report.failed": "문제가 있었습니다",
  "build.report.counts": "지역 {regions} · 연결 {connections} · 엔티티 {entities} · 지식 {knowledge} · 보강 {corroborations} · 근거 {priors}",
  "build.report.unscoped": "스코프 없음 {n}",
  "build.report.calls": "LLM {llm} · 임베딩 {embedding}",
  "build.report.replaced": "교체함 · 닫은 세션 {n}",
  "build.report.backup": "백업: {path}",
  "file.save": "저장(내려받기)",
  "file.load": "불러오기",
  "file.build": "자료로 만들기",
  "file.replaceConfirm": "이 월드를 파일 내용으로 교체할까요?",
  "file.closeSessionsConfirm": "열린 세션 {n}개를 닫고 교체할까요?",
  "file.openSessions": "열린 세션 {n}개",
};

type Key = keyof typeof ko;

// `Record<Key, string>` makes a missing or an extra key a type error; the vitest
// key-set test checks the same thing at run time (FD-U5 frontend §2.2).
const en: Record<Key, string> = {
  "nav.editor": "Editor",
  "nav.gm": "GM",
  "nav.play": "Play",
  "nav.gmLocked": "Opens once a session is picked",
  "lang.label": "Display language",

  "common.loading": "Loading…",
  "common.turn": "turn {n}",
  "label.decay": "decay",
  "badge.hearsay": "hearsay",
  "badge.rumor": "rumor",

  "toolbar.worldId": "world id",
  "toolbar.load": "Load",
  "toolbar.loadDemo": "Load demo world",
  "toolbar.pickMap": "Map:",
  "editor.enterWorldId": "Enter a world id",
  "editor.working": "working…",
  "editor.noWorld": "No world loaded. Click {loadDemo} or {load}.",
  "editor.emptyWorld":
    "World {world} has 0 regions. Load the demo (button above or the command below) or build it, then Load. Check the world id matches.",
  "editor.status":
    "world {world} · regions {regions} · connections {connections} · entities {entities} · knowledge {knowledge}",
  "editor.replaceTitle": "Replace world",
  "editor.replaceConfirm": "Close and replace",
  "editor.replaceBody":
    "This world has {n} open session(s). Loading the demo closes them and replaces the world. Continue?",

  "region.title": "Region knowledge",
  "region.unique": "unique {n}",
  "region.shared": "shared {n}",
  "region.empty": "Nothing is known here",

  "augment.title": "Knowledge augmentation",
  "augment.start": "Start run",
  "augment.revert": "Revert",
  "augment.status": "status: {status} · {answers}/30 answers",
  "augment.none": "No open questions 🎉",

  "session.title": "Session",
  "session.new": "New session",
  "session.close": "Close",
  "session.none": "— none —",
  "session.play": "Start playing",
  "session.playTitle": "New play session",
  "session.name": "Name",
  "session.startRegion": "Start region",
  "session.pickRegion": "Pick a region",

  "gm.title": "GameMaster · turn {turn}",
  "gm.loading": "loading session…",
  "gm.retry": "Retry",
  "gm.noSessionHint": "No session? Start one from the editor.",
  "gm.world": "world {world}",
  "gm.worldCounts": "regions {regions} · connections {connections}",
  "gm.advanceTurn": "Advance turn",
  "gm.suggestEvents": "Suggest events",
  "gm.events": "Events",
  "gm.timeline": "Timeline",
  "gm.region": "Region",
  "gm.distortion": "Distortion",
  "gm.generate": "Generate rumors",
  "gm.regen": "Regenerate",
  "gm.generateAll": "Generate all",
  "gm.regenAll": "Regenerate all",
  "gm.createEvent": "Create event",
  "gm.eventDescription": "description",
  "gm.lifecycleDefault": "default",
  "gm.approve": "Approve",
  "gm.discard": "Discard",
  "gm.resolve": "Resolve",
  "gm.support": "Support",
  "gm.promoted": "Promoted",
  "gm.noRegion": "Pick a region on the map to manage its rumors and events.",

  "action.original": "original",
  "action.translated": "translation",
  "action.confirm": "OK",
  "action.cancel": "Cancel",
  "action.close": "Close",

  "confirm.regen": "Regenerate this region's rumors. Promoted rumors are kept.",
  "confirm.regenAll": "Regenerate every region's rumors (overwrite). Promoted rumors are kept.",

  "progress.done": "{done}/{total} done",
  "progress.failed": "{failed} failed",
  "notif.noTargets": "No empty region to generate for",

  "play.title": "Player mode",
  "play.noSession": "Pick a session, or start playing from the editor.",
  "play.npcs": "People here",
  "play.facts": "What is known",
  "play.hearsay": "Things heard",
  "play.hearsayHint": "Faint tales that reached this region. Not everyone here knows them.",
  "play.rumors": "Rumors going around",
  "play.moves": "Where you can go",
  "play.move": "Move",
  "play.turns": "{n} turn(s)",
  "play.blocked": "Impassable",
  "play.wait": "Wait (1 turn)",
  "play.running": "The world is moving… ({n} turn(s))",
  "play.turnInProgress": "A turn is in progress",
  "play.sessionClosed": "The session has ended",
  "play.gmMode": "GM mode",
  "gm.backToPlay": "Back to play",
  "gm.playerStatus": "{name} · {region} · turn {turn}",
  "gm.running": "(running)",
  "gm.stateToggle": "World state",
  "gm.stateLegend": "Distortion (color) · active/promoted rumors (number)",
  "gm.feedbackShare": "Feedback share {share}",
  "gm.suggestN": "Count",
  "dialogue.failed": "No answer right now. Try again.",
  "play.turnDone": "Turn {n} done",
  "play.runFailed": "The turn failed",
  "play.budget": "The LLM budget ran out, so some rumors were skipped",
  "play.llmFailed": "An LLM call failed, so the remaining rumor generation stopped",
  "play.noLlm": "No LLM key: rumors and dialogue are not generated. Moving and the map still work.",
  "play.log": "Journey log",
  "play.quiet": "All is quiet",

  "npc.talk": "Talk",
  "dialogue.title": "Talking with {name}",
  "dialogue.has": "talked · {n}",
  "dialogue.you": "You",
  "dialogue.empty": "Nothing said yet.",
  "dialogue.placeholder": "What do you ask?",
  "dialogue.send": "Send",
  "dialogue.sending": "Waiting for an answer…",
  "dialogue.end": "End talk (1 turn)",
  "dialogue.noLlm": "No LLM key: you cannot talk. Past lines are still shown.",

  "play.declare": "Declare (1 turn)",
  "play.declarePlaceholder": "What do you do?",
  "play.chars": "{n}/{max} chars",
  "play.narrationTitle": "The world answers",
  "play.narrationFallback": "No LLM to narrate: only the action was recorded",
  "badge.deed": "deed",
  "deed.title": "Deeds",
  "deed.kind.arrival": "arrival",
  "deed.kind.statement": "statement",
  "deed.kind.declared_action": "declared",
  "deed.declaration": "declared as",
  "deed.witnesses": "witnessed by",
  "deed.appraisals": "appraisals",
  "deed.salience": "eagerness",
  "deed.reached": "reached",
  "deed.void": "Void",
  "deed.voidTitle": "Void deed",
  "deed.voidConfirmBtn": "Void",
  "deed.voidConfirm": "Void this deed and its {n} rumor(s)? This cannot be undone.",
  "deed.voided": "voided",
  "deed.none": "No deeds yet",

  "timeline.session_started": "{player_name} arrived · {region_name}",
  "timeline.session_closed": "session closed",
  "timeline.player_moved": "moved: {from_region_name} → {to_region_name} ({cost_turns} turn(s))",
  "timeline.player_waited": "waited · {region_name}",
  "timeline.npc_talked": "spoke with {npc_name} · {region_name}",
  "timeline.action_declared": "declared · {region_name}",
  "timeline.deed_recorded": "statement recorded · {npc_name}",
  "timeline.deed_appraised": "{npc_name} appraised · {region_name}",
  "timeline.deed_seeded": "deed rumor · {region_name}",
  "timeline.rumor_spread": "rumor spread: {from_region_name} → {region_name}",
  "timeline.deed_voided": "deed voided",
  "timeline.turn_run_failed": "turn failed",
  "timeline.generate": "rumors generated · {region}",
  "timeline.regenerate": "rumors regenerated · {region}",
  "timeline.promote": "a rumor promoted · {region}",
  "timeline.demote": "a rumor demoted · {region}",
  "timeline.prune": "a rumor faded · {region}",
  "timeline.adjust_support": "support adjusted · {region}",
  "timeline.advance_turn": "turn {turn} advanced",
  "timeline.set_distortion": "distortion set · {region} → {degree}",
  "timeline.event_created": "{category} event created · {region}",
  "timeline.event_suggested": "Suggested a {category} event in {region}",
  "timeline.event_approved": "Approved the {category} event in {region}",
  "timeline.event_discarded": "Discarded the {category} suggestion in {region}",
  "timeline.event_applied": "event applied · {region}",
  "timeline.event_resolved": "event resolved · {region}",
  "timeline.gm_session_started": "GM session started",
  "log.deed_seeded": "Talk about you has started in {region}",
  "log.rumor_spread": "Talk about you has reached {region}",

  "notif.title": "region {region_id}",
  "notif.promoted": "{n} promoted",
  "notif.demoted": "{n} demoted",
  "notif.pruned": "{n} faded",
  "notif.rumors_added": "{n} new rumor(s)",
  "notif.events_applied": "{n} event(s) applied",
  "notif.events_resolved": "{n} event(s) resolved",

  // U3 world editor (frontend-components §4)
  "home.title": "Worlds",
  "home.empty": "No world yet.",
  "home.edit": "Edit",
  "home.startSession": "Start session",
  "home.loadDemo": "Load the demo",
  "home.buildFromSources": "Build from sources",
  "home.regions": "{n} regions",
  "home.updated": "edited {when}",
  "home.openSessions": "{n} open sessions",
  "home.newWorldId": "New world id",
  "map.tool.select": "Select / move",
  "map.tool.addRegion": "Add region",
  "map.tool.connect": "Connect",
  "map.hint.select": "Click a region to pick it, drag to move it",
  "map.hint.addRegion": "Click an empty spot to add a region there",
  "map.hint.connect": "Click two regions in turn to connect them",
  "map.hint.connectSecond": "Now click the region to connect {name} to",
  "editor.tab.region": "Region",
  "editor.tab.unscoped": "Unscoped {n}",
  "editor.tab.augment": "Augment",
  "editor.tab.wiki": "Wiki",
  "editor.pickRegion": "Pick a region on the map",
  "editor.region.title": "Region",
  "editor.region.add": "New region",
  "editor.region.name": "Name",
  "editor.region.level": "Level",
  "editor.region.parent": "Parent",
  "editor.region.noParent": "— none —",
  "editor.region.description": "Description",
  "editor.region.save": "Save",
  "editor.region.delete": "Delete region",
  "editor.connection.title": "Connections",
  "editor.connection.add": "New connection",
  "editor.connection.kind": "Kind",
  "editor.connection.weight": "Weight",
  "editor.connection.save": "Save",
  "editor.connection.delete": "Delete connection",
  "editor.connection.none": "No connections",
  "editor.connection.prior": "Grounds: {effect}",
  "editor.connection.brokenPrior": "Unsaved grounds ({id})",
  "editor.knowledge.title": "Knowledge here",
  "editor.knowledge.add": "Add knowledge",
  "editor.knowledge.titleLabel": "Title",
  "editor.knowledge.statement": "Statement",
  "editor.knowledge.edit": "Edit",
  "editor.knowledge.save": "Save",
  "editor.knowledge.delete": "Delete knowledge",
  "editor.knowledge.none": "No knowledge here",
  "editor.scopes": "Scopes",
  "editor.scopes.save": "Save scopes",
  "editor.npc.title": "Inhabitants",
  "editor.npc.add": "Add NPC",
  "editor.npc.name": "Name",
  "editor.npc.role": "Role",
  "editor.npc.description": "Description",
  "editor.npc.traits": "Traits (comma separated)",
  "editor.npc.save": "Save",
  "editor.npc.delete": "Delete NPC",
  "editor.npc.none": "Nobody lives here yet",
  "editor.npcDraft.suggest": "Suggest NPCs",
  "editor.npcDraft.accept": "Accept",
  "editor.npcDraft.failed": "No suggestions came back. Try again later.",
  "editor.npcDraft.none": "No suggestions",
  "editor.unscoped.title": "Unscoped knowledge",
  "editor.unscoped.none": "Every item is known somewhere",
  "editor.unscoped.pick": "Pick a region",
  "editor.unscoped.assign": "Assign",
  "editor.saved": "Saved",
  "delete.title": "Delete?",
  "delete.confirm": "Delete",
  "delete.knowledge": "This deletes the knowledge \"{name}\".",
  "delete.npc": "This deletes the NPC \"{name}\". Conversations stay in their sessions.",
  "delete.connection": "This deletes both directions of {a}–{b} ({kind}).",
  "delete.prior": "This deletes the grounds \"{name}\". What cited it shows as unsaved grounds.",
  "delete.region.title": "Delete {name}",
  "delete.region.children": "{n} child region(s) move up: {names}",
  "delete.region.connections": "{n} connection(s) are deleted",
  "delete.region.npcs": "{n} NPC(s) are deleted: {names}",
  "delete.region.unscope": "{n} item(s) become unscoped: {names}",
  "delete.region.scopeRemoved": "{n} item(s) lose this scope only",
  "delete.region.entities": "{n} entit(ies) lose their location",
  "delete.region.blocked": "A player of an open session stands here: {ids}. Close the session or move the player first.",
  "delete.region.done": "Deleted: {children} moved · {npcs} NPCs · {connections} connections · {unscoped} unscoped",
  "augment.find": "Find gaps",
  "augment.target.knowledge": "knowledge",
  "augment.target.entity": "entity",
  "augment.target.region": "region",
  "augment.target.npc": "NPC",
  "augment.target.connection": "connection",
  "augment.action.confirm": "Confirm",
  "augment.action.edit": "Edit",
  "augment.action.remove": "Remove",
  "augment.action.add": "Add",
  "augment.action.ignore": "Ignore",
  "augment.statement": "Statement",
  "augment.region": "Region",
  "augment.ref": "New target",
  "augment.changed": "Changes",
  "augment.reverted": "Reverted",
  "augment.ignored": "Ignored",
  "augment.unignore": "Ask again",
  "augment.converged": "Nothing left to ask",
  "augment.stopped": "This run reached its answer limit. Find gaps again.",
  "augment.budget": "This run used its LLM budget: questions use plain wording and terrain checks pause.",
  "augment.lost": "The run is gone (the server restarted). Find gaps again.",
  "augment.conflict": "Cannot revert: {reason}",
  "wiki.title": "Common-sense grounds",
  "wiki.condition": "Condition",
  "wiki.effect": "Effect",
  "wiki.domains": "Domains",
  "wiki.confidence": "Confidence",
  "wiki.refs": "{n} refs",
  "wiki.broken": "Unsaved grounds",
  "wiki.none": "No grounds stored",
  "wiki.delete": "Delete",
  "build.title": "Build a world from sources",
  "build.worldId": "World id",
  "build.name": "Name",
  "build.description": "Description",
  "build.memoText": "Notes (typed)",
  "build.memos": "Note files (.txt/.md)",
  "build.maps": "Structured maps (JSON)",
  "build.images": "Map images",
  "build.conceptArts": "Concept art",
  "build.submit": "Build",
  "build.working": "Building… reading the sources takes tens of seconds",
  "build.replaceConfirm": "A world with this id exists. Replace it?",
  "build.closeSessions": "Close {n} open session(s) and continue?",
  "build.report.title": "Build report",
  "build.report.ok": "Done",
  "build.report.failed": "Something went wrong",
  "build.report.counts": "{regions} regions · {connections} connections · {entities} entities · {knowledge} knowledge · {corroborations} corroborations · {priors} grounds",
  "build.report.unscoped": "{n} unscoped",
  "build.report.calls": "LLM {llm} · embedding {embedding}",
  "build.report.replaced": "replaced · {n} sessions closed",
  "build.report.backup": "Backup: {path}",
  "file.save": "Save (download)",
  "file.load": "Load file",
  "file.build": "Build from sources",
  "file.replaceConfirm": "Replace this world with the file?",
  "file.closeSessionsConfirm": "Close {n} open session(s) and replace?",
  "file.openSessions": "{n} open sessions",
};

/** Both dictionaries, exported for the key-set test (same keys in ko and en). */
export const dicts: Record<Lang, Record<string, string>> = { ko, en };

function isLang(v: unknown): v is Lang {
  return v === "ko" || v === "en";
}

// Storage can throw (private window, blocked site data) — the language then just
// is not remembered.
function readStoredLang(): Lang | null {
  try {
    const v = globalThis.localStorage?.getItem(STORAGE_KEY);
    return isLang(v) ? v : null;
  } catch {
    return null;
  }
}

let current: Lang = readStoredLang() ?? "ko";
if (typeof document !== "undefined") document.documentElement.lang = current;
const listeners = new Set<() => void>();

// The server's display languages (`GET /api/langs`, review U5 #2). Until they are
// known the client sends no `?lang=` and the server's default applies: a server
// configured for English only must never receive `?lang=ko` and answer 400.
let serverDefault: string | null = null;
let serverLangs: readonly string[] | null = null;

function notify(): void {
  if (typeof document !== "undefined") document.documentElement.lang = current;
  for (const fn of listeners) fn();
}

/** The display language: labels come from its dictionary. Read requests carry it as
 * `?lang=` when the server needs to be told (`requestLang`, `api/http.ts::withLang`). */
export function lang(): Lang {
  return current;
}

/** Switch the display language, remember it, and re-render every `useLang()` user. */
export function setLang(next: Lang): void {
  if (!isLang(next) || next === current) return;
  current = next;
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, next);
  } catch {
    /* not remembered; the switch still applies to this page */
  }
  notify();
}

/** Adopt the server's languages. A remembered language the server does not take falls
 * back to the server default (for this page; the stored choice is kept). */
export function configureLangs(defaultLang: string, supported: readonly string[]): void {
  serverDefault = defaultLang.trim().toLowerCase();
  serverLangs = supported.map((l) => l.trim().toLowerCase());
  const known = serverLangs;
  if (!known.includes(current)) {
    const fallback = isLang(serverDefault) ? serverDefault : LANGS.find((l) => known.includes(l));
    if (fallback) current = fallback;
  }
  notify();
}

/** The `?lang=` value to send, or `null` to let the server default apply: unknown
 * server languages, a language the server does not take, or the default itself. */
export function requestLang(): Lang | null {
  if (serverLangs === null || !serverLangs.includes(current)) return null;
  return current === serverDefault ? null : current;
}

/** Languages the toggle offers: the dictionaries the server also takes. */
export function availableLangs(): Lang[] {
  const known = serverLangs;
  return known === null ? [...LANGS] : LANGS.filter((l) => known.includes(l));
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Subscribe a component to the display language (re-renders on `setLang`). */
export function useLang(): Lang {
  return useSyncExternalStore(subscribe, lang, lang);
}

const requestKey = () => requestLang() ?? "";

/** The language the server is asked for (`""` = its default). Screens that show
 * translated data re-read when this changes — not merely when the labels change. */
export function useRequestLang(): string {
  return useSyncExternalStore(subscribe, requestKey, requestKey);
}

const availableKey = () => availableLangs().join(",");

/** Re-render when the offered languages change (after `configureLangs`). */
export function useAvailableLangs(): Lang[] {
  const key = useSyncExternalStore(subscribe, availableKey, availableKey);
  return key ? (key.split(",") as Lang[]) : [];
}

function lookup(key: string): string | undefined {
  return dicts[current][key] ?? dicts.ko[key];
}

/** Translate a key with {param} interpolation: the current language's dictionary,
 * then Korean, then the key itself (a missing key never blanks the screen). */
export function t(key: string, params?: Params): string {
  const tpl = lookup(key);
  if (tpl == null) return key;
  return tpl.replace(/\{(\w+)\}/g, (_, k) => {
    const v = params?.[k];
    return v == null ? `{${k}}` : String(v);
  });
}

/** Localize a timeline entry from its kind + payload (F2a). When no template
 * exists for the kind (e.g. event_created, reused for create/suggest/approve),
 * falls back to the entry's own summary so distinct actions stay legible. */
export function timelineText(
  kind: string,
  payload: Params,
  turn: number,
  summary?: string,
): string {
  let k = kind;
  // older lines: one kind for create/suggest/approve, told apart by a flag (pre-U7)
  if (k === "event_created" && payload.suggested) k = "event_suggested";
  else if (k === "event_created" && payload.approved) k = "event_approved";
  else if (k === "session_started" && payload.player_name == null) k = "gm_session_started";
  const key = `timeline.${k}`;
  if (lookup(key) == null) return summary || kind;
  return t(key, { ...payload, turn, region: regionOf(payload) });
}

/** A line as the player reads it: its own wording when it has one (`log.*`), else the
 * timeline's (U7, FR-C6). */
export function logText(kind: string, payload: Params, turn: number, summary?: string): string {
  const key = `log.${kind}`;
  if (lookup(key) != null) return t(key, { ...payload, turn, region: regionOf(payload) });
  return timelineText(kind, payload, turn, summary);
}

// FR-D3: the region by name; its id for a line written before names, "—" for none.
function regionOf(payload: Params): string {
  const name = payload.region_name ?? payload.region_id;
  return name == null ? "—" : String(name);
}
