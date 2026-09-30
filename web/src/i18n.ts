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
  "augment.revert": "마지막 되돌리기",
  "augment.status": "상태: {status} · 라운드 {round}",
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

  // timeline (kind -> template; payload fields interpolated)
  "timeline.session_started": "{player_name} 도착 · {region_name}",
  "timeline.session_closed": "세션 종료",
  "timeline.player_moved": "이동: {from_region_name} → {to_region_name} ({cost_turns}턴)",
  "timeline.player_waited": "대기 · {region_name}",
  "timeline.npc_talked": "대화: {npc_name} · {region_name}",
  "timeline.turn_run_failed": "턴 처리 실패",
  "timeline.generate": "소문 생성 · 지역 {region_id}",
  "timeline.regenerate": "소문 재생성 · 지역 {region_id}",
  "timeline.promote": "승격: {rumor_id}",
  "timeline.demote": "강등: {rumor_id}",
  "timeline.prune": "소멸: {rumor_id}",
  "timeline.adjust_support": "공신력 조정: {rumor_id}",
  "timeline.advance_turn": "턴 {turn} 진행",
  "timeline.set_distortion": "왜곡 설정 · 지역 {region_id}",
  // NOTE: event_created is reused by the backend for create/suggest/approve with
  // distinct summaries — no template here so those fall back to the summary and
  // stay distinguishable (review #3). Single-action event kinds keep templates.
  "timeline.event_applied": "이벤트 적용: {event_id}",
  "timeline.event_resolved": "이벤트 해소: {event_id}",

  // notification segments (per-region turn change)
  "notif.title": "지역 {region_id}",
  "notif.promoted": "{n}건 승격",
  "notif.demoted": "{n}건 강등",
  "notif.pruned": "{n}건 소멸",
  "notif.rumors_added": "{n}건 신규 소문",
  "notif.events_applied": "이벤트 {n} 적용",
  "notif.events_resolved": "이벤트 {n} 해소",
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
  "augment.revert": "Revert last",
  "augment.status": "status: {status} · round {round}",
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

  "timeline.session_started": "{player_name} arrived · {region_name}",
  "timeline.session_closed": "session closed",
  "timeline.player_moved": "moved: {from_region_name} → {to_region_name} ({cost_turns} turn(s))",
  "timeline.player_waited": "waited · {region_name}",
  "timeline.npc_talked": "spoke with {npc_name} · {region_name}",
  "timeline.turn_run_failed": "turn failed",
  "timeline.generate": "rumors generated · region {region_id}",
  "timeline.regenerate": "rumors regenerated · region {region_id}",
  "timeline.promote": "promoted: {rumor_id}",
  "timeline.demote": "demoted: {rumor_id}",
  "timeline.prune": "faded: {rumor_id}",
  "timeline.adjust_support": "support adjusted: {rumor_id}",
  "timeline.advance_turn": "turn {turn} advanced",
  "timeline.set_distortion": "distortion set · region {region_id}",
  "timeline.event_applied": "event applied: {event_id}",
  "timeline.event_resolved": "event resolved: {event_id}",

  "notif.title": "region {region_id}",
  "notif.promoted": "{n} promoted",
  "notif.demoted": "{n} demoted",
  "notif.pruned": "{n} faded",
  "notif.rumors_added": "{n} new rumor(s)",
  "notif.events_applied": "{n} event(s) applied",
  "notif.events_resolved": "{n} event(s) resolved",
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
  const key = `timeline.${kind}`;
  if (lookup(key) == null) return summary || kind;
  return t(key, { ...payload, turn });
}
