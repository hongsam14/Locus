import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type {
  EventCategory,
  EventLifecycle,
  GameSession,
  SessionEvent,
  SessionRumor,
  TimelineEntry,
} from "./types";
import { t, timelineText } from "./i18n";
import {
  Badge,
  Button,
  Card,
  Field,
  LocalizedText,
  Modal,
  NotificationCenter,
  Panel,
  Range,
} from "./ui";
import type { Notif } from "./ui";
import type { RegionTurnChange, TurnResult } from "./types";

const EVENT_TONE: Record<string, "neutral" | "event" | "danger"> = {
  active: "event",
  suggested: "danger",
  resolved: "neutral",
};

const BULK_LIMIT = 5; // max concurrent region ops (SEC-E)
let _notifSeq = 0;

// Run fn over items with bounded concurrency (SEC-E; review #4).
async function mapLimit<T, R>(items: T[], limit: number, fn: (x: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const idx = next++;
      out[idx] = await fn(items[idx]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return out;
}

// Build the per-region notification body from a RegionTurnChange (FR-UX2.6).
function changeSummary(rc: RegionTurnChange): string {
  const segs: string[] = [];
  if (rc.promoted.length) segs.push(t("notif.promoted", { n: rc.promoted.length }));
  if (rc.demoted.length) segs.push(t("notif.demoted", { n: rc.demoted.length }));
  if (rc.pruned.length) segs.push(t("notif.pruned", { n: rc.pruned.length }));
  if (rc.rumors_added.length) segs.push(t("notif.rumors_added", { n: rc.rumors_added.length }));
  if (rc.events_applied.length) segs.push(t("notif.events_applied", { n: rc.events_applied.length }));
  if (rc.events_resolved.length)
    segs.push(t("notif.events_resolved", { n: rc.events_resolved.length }));
  return segs.join(", ");
}

interface Props {
  session: GameSession;
  regionId: string | null; // GameMaster target = map-selected region
  onChanged?: () => void; // notify parent (e.g. refresh RegionPanel/session)
}

const CATEGORIES: EventCategory[] = [
  "war",
  "plague",
  "politics",
  "disaster",
  "festival",
  "discovery",
];

export function SessionPanel({ session, regionId, onChanged }: Props) {
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [rumors, setRumors] = useState<SessionRumor[]>([]);
  const [events, setEvents] = useState<SessionEvent[]>([]);
  const [distortions, setDistortions] = useState<Record<string, number>>({});
  const [distortion, setDistortion] = useState(0.3);
  const [evCategory, setEvCategory] = useState<EventCategory>("war");
  const [evDescription, setEvDescription] = useState("");
  const [evMagnitude, setEvMagnitude] = useState(0.5);
  const [evLifecycle, setEvLifecycle] = useState<EventLifecycle | "">("");
  const [error, setError] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notif[]>([]);
  const [progress, setProgress] = useState<{ done: number; total: number; failed: number } | null>(
    null,
  );
  const [confirm, setConfirm] = useState<{ message: string; onConfirm: () => void } | null>(null);
  const closed = session.status === "closed";

  // Memoized so NotificationCenter's auto-dismiss effect deps stay stable and its
  // timers don't reset on every SessionPanel re-render (review #5).
  const addNotif = useCallback(
    (n: Omit<Notif, "id">) => setNotifications((cur) => [...cur, { ...n, id: `n${_notifSeq++}` }]),
    [],
  );
  const dismissNotif = useCallback(
    (id: string) => setNotifications((cur) => cur.filter((n) => n.id !== id)),
    [],
  );

  const refresh = useCallback(async () => {
    setError(null);
    try {
      // These reads are independent — load them in parallel (round-trip depth 1)
      // instead of a 4-deep await waterfall (FR-H6 / BR-H2-1).
      const [tl, ev, dist, rm] = await Promise.all([
        api.getTimeline(session.id),
        api.listEvents(session.id),
        api.listDistortions(session.id),
        regionId ? api.listRumors(session.id, regionId) : Promise.resolve([]),
      ]);
      setTimeline(tl);
      setEvents(ev);
      const map: Record<string, number> = {};
      for (const d of dist) map[d.region_id] = d.distortion_degree;
      setDistortions(map);
      setRumors(rm);
      if (regionId) {
        setDistortion(map[regionId] ?? 0.3); // reflect real per-region distortion
      }
    } catch (e) {
      setError(String(e));
    }
  }, [session.id, regionId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function run(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      await refresh();
      onChanged?.();
    } catch (e) {
      setError(String(e));
    }
  }

  // Advance a turn and surface per-region change notifications (FR-UX2.6).
  async function advance() {
    setError(null);
    try {
      const result = (await api.advanceTurn(session.id)) as TurnResult;
      for (const rc of result.region_changes ?? []) {
        const body = changeSummary(rc);
        if (body) addNotif({ region_id: rc.region_id, title: t("notif.title", { region_id: rc.region_id }), body });
      }
      await refresh();
      onChanged?.();
    } catch (e) {
      setError(String(e));
    }
  }

  // Run an op over many regions with bounded concurrency + progress (FR-UX2.3 / SEC-E).
  // Assumes the caller has already gated on `progress` (in-flight guard, review #2).
  async function runBulk(ids: string[], op: (rid: string) => Promise<unknown>, label: string) {
    setError(null);
    let done = 0;
    let failed = 0;
    setProgress({ done, total: ids.length, failed });
    for (let i = 0; i < ids.length; i += BULK_LIMIT) {
      const chunk = ids.slice(i, i + BULK_LIMIT);
      await Promise.all(
        chunk.map((rid) =>
          op(rid)
            .catch(() => {
              failed += 1;
            })
            .finally(() => {
              done += 1;
              setProgress({ done, total: ids.length, failed });
            }),
        ),
      );
    }
    setProgress(null);
    const ok = ids.length - failed;
    addNotif({
      region_id: "bulk",
      title: label,
      body: `${t("progress.done", { done: ok, total: ids.length })}${failed ? ` · ${t("progress.failed", { failed })}` : ""}`,
    });
    await refresh();
    onChanged?.();
  }

  // "Generate all" — only regions that currently have no rumors (Q5=C / Q6=B).
  async function generateAll() {
    if (progress != null) return; // in-flight guard (review #2)
    setProgress({ done: 0, total: 0, failed: 0 }); // gate the button during the pre-scan
    try {
      const ids = Object.keys(distortions);
      const counts = await mapLimit(ids, BULK_LIMIT, (rid) =>
        api
          .listRumors(session.id, rid)
          .then((rs) => [rid, rs.length] as const)
          .catch(() => [rid, 1] as const),
      );
      const empty = counts.filter(([, n]) => n === 0).map(([rid]) => rid);
      if (empty.length === 0) {
        setProgress(null);
        addNotif({ region_id: "bulk", title: t("gm.generateAll"), body: t("notif.noTargets") });
        return;
      }
      await runBulk(empty, (rid) => api.generateRumors(session.id, rid), t("gm.generateAll"));
    } catch (e) {
      setProgress(null);
      setError(String(e));
    }
  }

  const ask = (message: string, onConfirm: () => void) => setConfirm({ message, onConfirm });

  return (
    <Panel
      data-testid="session-panel"
      title={`GameMaster · turn ${session.turn}`}
      className="min-w-80"
    >
      {error && <div className="text-danger mb-2">{error}</div>}

      <div className="flex flex-wrap gap-2">
        <Button
          variant="primary"
          data-testid="advance-turn-btn"
          onClick={advance}
          disabled={closed}
        >
          {t("gm.advanceTurn")}
        </Button>
        <Button
          data-testid="suggest-events-btn"
          onClick={() => run(() => api.suggestEvents(session.id, 1))}
          disabled={closed}
        >
          {t("gm.suggestEvents")}
        </Button>
        <Button
          data-testid="generate-all-btn"
          onClick={generateAll}
          disabled={closed || progress != null}
        >
          {t("gm.generateAll")}
        </Button>
        <Button
          variant="danger"
          data-testid="regen-all-btn"
          onClick={() =>
            ask(t("confirm.regenAll"), () =>
              runBulk(
                Object.keys(distortions),
                (rid) => api.regenRumors(session.id, rid),
                t("gm.regenAll"),
              ),
            )
          }
          disabled={closed || progress != null}
        >
          {t("gm.regenAll")}
        </Button>
      </div>
      {progress && (
        <div data-testid="generate-progress" className="mt-2">
          <div className="h-1.5 sketch-border overflow-hidden">
            <div
              className="h-full bg-ink"
              style={{ width: `${progress.total ? (progress.done / progress.total) * 100 : 0}%` }}
            />
          </div>
          <div className="text-xs text-ink-soft mt-0.5">
            {t("progress.done", { done: progress.done, total: progress.total })}
            {progress.failed ? ` · ${t("progress.failed", { failed: progress.failed })}` : ""}
          </div>
        </div>
      )}

      {/* Session-wide event list (FD-P3 Q3=A) */}
      <h4 className="font-display text-base mt-3 mb-1">{t("gm.events")}</h4>
      <div data-testid="events" className="flex flex-col gap-1.5 text-sm">
        {events.map((ev) => (
          <Card key={ev.id} data-testid={`event-${ev.id}`} className="flex flex-wrap items-center gap-1.5">
            <Badge data-testid={`event-status-${ev.id}`} tone={EVENT_TONE[ev.status] ?? "neutral"}>
              {ev.status}
            </Badge>
            <span className="text-ink-soft text-xs">
              {ev.region_id} · {ev.category} · m{ev.magnitude.toFixed(2)} · {ev.lifecycle}
            </span>
            <LocalizedText
              testId={`event-desc-${ev.id}`}
              ko={ev.description_ko}
              original={ev.description}
            />
            {ev.status === "suggested" && (
              <>
                <Button
                  size="sm"
                  data-testid={`approve-${ev.id}`}
                  onClick={() => run(() => api.approveEvent(session.id, ev.id))}
                  disabled={closed}
                >
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  data-testid={`discard-${ev.id}`}
                  onClick={() => run(() => api.discardEvent(session.id, ev.id))}
                  disabled={closed}
                >
                  Discard
                </Button>
              </>
            )}
            {ev.status === "active" && (
              <Button
                size="sm"
                data-testid={`resolve-${ev.id}`}
                onClick={() => run(() => api.resolveEvent(session.id, ev.id))}
                disabled={closed}
              >
                Resolve
              </Button>
            )}
          </Card>
        ))}
      </div>

      {/* GameMaster region controls (target = selected map region) */}
      {!regionId && (
        <div data-testid="gm-no-region" className="text-ink-soft text-xs mt-2">
          {t("gm.noRegion")}
        </div>
      )}
      {regionId && (
        <div data-testid="gm-region" className="mt-3 flex flex-col gap-2">
          <div className="text-xs text-ink-soft">
            {t("gm.region")} {regionId}
          </div>
          <label className="text-xs flex items-center gap-2">
            {t("gm.distortion")} {distortion.toFixed(2)}
            <Range
              data-testid="distortion-slider"
              min={0}
              max={1}
              step={0.05}
              value={distortion}
              disabled={closed}
              onChange={(e) => setDistortion(Number(e.target.value))}
              onMouseUp={(e) =>
                run(() =>
                  api.setDistortion(session.id, regionId, Number((e.target as HTMLInputElement).value)),
                )
              }
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="primary"
              data-testid="generate-btn"
              onClick={() => run(() => api.generateRumors(session.id, regionId))}
              disabled={closed || progress != null}
            >
              {t("gm.generate")}
            </Button>
            <Button
              data-testid="regen-btn"
              onClick={() =>
                ask(t("confirm.regen"), () => run(() => api.regenRumors(session.id, regionId)))
              }
              disabled={closed || progress != null}
            >
              {t("gm.regen")}
            </Button>
          </div>

          {/* Event create form (target = selected region) */}
          <Card data-testid="event-form" className="flex flex-wrap items-center gap-2 text-xs">
            <select
              data-testid="event-category"
              value={evCategory}
              disabled={closed}
              onChange={(e) => setEvCategory(e.target.value as EventCategory)}
              className="sketch-border bg-paper-card px-1.5 py-1"
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <Field
              data-testid="event-description"
              placeholder="description"
              value={evDescription}
              disabled={closed}
              onChange={(e) => setEvDescription(e.target.value)}
            />
            <label className="flex items-center gap-1">
              m{evMagnitude.toFixed(2)}
              <Range
                data-testid="event-magnitude"
                min={0}
                max={1}
                step={0.05}
                value={evMagnitude}
                disabled={closed}
                onChange={(e) => setEvMagnitude(Number(e.target.value))}
              />
            </label>
            <select
              data-testid="event-lifecycle"
              value={evLifecycle}
              disabled={closed}
              onChange={(e) => setEvLifecycle(e.target.value as EventLifecycle | "")}
              className="sketch-border bg-paper-card px-1.5 py-1"
            >
              <option value="">default</option>
              <option value="one_shot">one_shot</option>
              <option value="persistent">persistent</option>
            </select>
            <Button
              size="sm"
              variant="primary"
              data-testid="event-create-btn"
              disabled={closed}
              onClick={() =>
                run(() =>
                  api.createEvent(session.id, {
                    region_id: regionId,
                    category: evCategory,
                    description: evDescription,
                    magnitude: evMagnitude,
                    lifecycle: evLifecycle || null,
                  }),
                )
              }
            >
              {t("gm.createEvent")}
            </Button>
          </Card>

          <div className="flex flex-col gap-1.5">
            {rumors.map((r) => (
              <Card key={r.id} data-testid={`rumor-${r.id}`} className="text-sm">
                <div className="flex items-center gap-1.5">
                  {r.promoted && (
                    <Badge data-testid={`promoted-${r.id}`} tone="promoted">
                      {t("gm.promoted")}
                    </Badge>
                  )}
                  <span className="text-ink-soft text-xs">d{r.distortion_degree.toFixed(2)}</span>
                  <LocalizedText
                    testId={`rumor-text-${r.id}`}
                    ko={r.statement_ko}
                    original={r.statement}
                  />
                </div>
                <label className="text-xs text-ink-soft flex items-center gap-2 mt-1">
                  {t("gm.support")} {r.support.toFixed(2)}
                  <Range
                    // remount when support changes after a refresh so the
                    // uncontrolled thumb reflects the latest value
                    key={`${r.id}-${r.support}`}
                    data-testid={`support-${r.id}`}
                    min={0}
                    max={1}
                    step={0.05}
                    defaultValue={r.support}
                    disabled={closed}
                    onMouseUp={(e) =>
                      run(() =>
                        api.setSupport(session.id, r.id, Number((e.target as HTMLInputElement).value)),
                      )
                    }
                  />
                </label>
              </Card>
            ))}
          </div>
        </div>
      )}

      <h4 className="font-display text-base mt-3 mb-1">{t("gm.timeline")}</h4>
      <ul data-testid="timeline" className="list-none p-0 m-0 text-xs flex flex-col">
        {timeline.map((entry) => (
          <li key={entry.id} className="border-b border-line py-1">
            <b>t{entry.turn}</b>{" · "}
            {timelineText(entry.kind, entry.payload, entry.turn, entry.summary)}
          </li>
        ))}
      </ul>

      <Modal
        open={confirm != null}
        title={t("gm.regen")}
        confirmTone="danger"
        confirmLabel={t("action.confirm")}
        cancelLabel={t("action.cancel")}
        onConfirm={() => {
          confirm?.onConfirm();
          setConfirm(null);
        }}
        onCancel={() => setConfirm(null)}
      >
        {confirm?.message}
      </Modal>
      <NotificationCenter items={notifications} onDismiss={dismissNotif} />
    </Panel>
  );
}
