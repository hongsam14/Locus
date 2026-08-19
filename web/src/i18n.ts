// Lightweight Korean i18n dictionary (X3 / C10). Korean-only (Q12=A); no lib.
// UI static labels + timeline kind templates (F2a) + notification segments.

type Params = Record<string, unknown>;

const messages: Record<string, string> = {
  // GameMaster / SessionPanel labels
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

  // confirms
  "confirm.regen": "이 지역 소문을 재생성합니다. 승격된 소문은 보존됩니다.",
  "confirm.regenAll": "모든 지역 소문을 재생성합니다(덮어쓰기). 승격된 소문은 보존됩니다.",

  // progress
  "progress.done": "{done}/{total} 완료",
  "progress.failed": "{failed}건 실패",
  "notif.noTargets": "생성할 빈 지역이 없습니다",

  // timeline (kind -> template; payload fields interpolated)
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

/** Translate a key with {param} interpolation. Unknown keys fall back to the key. */
export function t(key: string, params?: Params): string {
  const tpl = messages[key];
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
  if (messages[key] == null) return summary || kind;
  return t(key, { ...payload, turn });
}
