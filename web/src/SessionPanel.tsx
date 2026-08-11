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
  const closed = session.status === "closed";

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

  return (
    <div data-testid="session-panel" style={{ padding: 12, minWidth: 320, borderTop: "1px solid #eee" }}>
      <h3>GameMaster · turn {session.turn}</h3>
      {error && <div style={{ color: "#c0392b" }}>{error}</div>}

      <button
        data-testid="advance-turn-btn"
        onClick={() => run(() => api.advanceTurn(session.id))}
        disabled={closed}
      >
        Advance Turn
      </button>
      <button
        data-testid="suggest-events-btn"
        onClick={() => run(() => api.suggestEvents(session.id, 1))}
        disabled={closed}
        style={{ marginLeft: 6 }}
      >
        Suggest events
      </button>

      {/* Session-wide event list (FD-P3 Q3=A) */}
      <h4 style={{ marginBottom: 4, marginTop: 12 }}>Events</h4>
      <ul data-testid="events" style={{ listStyle: "none", padding: 0, fontSize: 13 }}>
        {events.map((ev) => (
          <li
            key={ev.id}
            data-testid={`event-${ev.id}`}
            style={{ borderBottom: "1px solid #eee", padding: "6px 0" }}
          >
            <span
              data-testid={`event-status-${ev.id}`}
              style={{
                background:
                  ev.status === "active" ? "#2980b9" : ev.status === "suggested" ? "#f39c12" : "#888",
                color: "#fff",
                borderRadius: 4,
                padding: "1px 6px",
                fontSize: 11,
                marginRight: 6,
              }}
            >
              {ev.status}
            </span>
            <span style={{ color: "#999", fontSize: 11 }}>
              {ev.region_id} · {ev.category} · m{ev.magnitude.toFixed(2)} · {ev.lifecycle}{" "}
            </span>
            {ev.description}
            <span style={{ marginLeft: 6 }}>
              {ev.status === "suggested" && (
                <>
                  <button
                    data-testid={`approve-${ev.id}`}
                    onClick={() => run(() => api.approveEvent(session.id, ev.id))}
                    disabled={closed}
                  >
                    Approve
                  </button>
                  <button
                    data-testid={`discard-${ev.id}`}
                    onClick={() => run(() => api.discardEvent(session.id, ev.id))}
                    disabled={closed}
                  >
                    Discard
                  </button>
                </>
              )}
              {ev.status === "active" && (
                <button
                  data-testid={`resolve-${ev.id}`}
                  onClick={() => run(() => api.resolveEvent(session.id, ev.id))}
                  disabled={closed}
                >
                  Resolve
                </button>
              )}
            </span>
          </li>
        ))}
      </ul>

      {/* GameMaster region controls (target = selected map region) */}
      {!regionId && (
        <div data-testid="gm-no-region" style={{ color: "#888", fontSize: 12, marginTop: 8 }}>
          Select a region on the map to manage its rumors and events.
        </div>
      )}
      {regionId && (
        <div data-testid="gm-region" style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, color: "#666" }}>region {regionId}</div>
          <label style={{ fontSize: 12, display: "block", margin: "4px 0" }}>
            distortion {distortion.toFixed(2)}
            <input
              data-testid="distortion-slider"
              type="range"
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
          <button
            data-testid="generate-btn"
            onClick={() => run(() => api.generateRumors(session.id, regionId))}
            disabled={closed}
          >
            Generate rumors
          </button>
          <button
            data-testid="regen-btn"
            onClick={() => run(() => api.regenRumors(session.id, regionId))}
            disabled={closed}
          >
            Regenerate
          </button>

          {/* Event create form (target = selected region) */}
          <div data-testid="event-form" style={{ marginTop: 8, fontSize: 12 }}>
            <select
              data-testid="event-category"
              value={evCategory}
              disabled={closed}
              onChange={(e) => setEvCategory(e.target.value as EventCategory)}
            >
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <input
              data-testid="event-description"
              placeholder="description"
              value={evDescription}
              disabled={closed}
              onChange={(e) => setEvDescription(e.target.value)}
            />
            <label>
              m{evMagnitude.toFixed(2)}
              <input
                data-testid="event-magnitude"
                type="range"
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
            >
              <option value="">default</option>
              <option value="one_shot">one_shot</option>
              <option value="persistent">persistent</option>
            </select>
            <button
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
              Create event
            </button>
          </div>

          <ul style={{ listStyle: "none", padding: 0, marginTop: 8 }}>
            {rumors.map((r) => (
              <li
                key={r.id}
                data-testid={`rumor-${r.id}`}
                style={{ borderBottom: "1px solid #eee", padding: "6px 0", fontSize: 13 }}
              >
                {r.promoted && (
                  <span
                    data-testid={`promoted-${r.id}`}
                    style={{ background: "#27ae60", color: "#fff", borderRadius: 4, padding: "1px 6px", fontSize: 11, marginRight: 6 }}
                  >
                    PROMOTED
                  </span>
                )}
                <span style={{ color: "#999", fontSize: 11 }}>d{r.distortion_degree.toFixed(2)} </span>
                {r.statement}
                <div>
                  <label style={{ fontSize: 11, color: "#666" }}>
                    support {r.support.toFixed(2)}
                    <input
                      // remount when support changes after a refresh so the
                      // uncontrolled thumb reflects the latest value
                      key={`${r.id}-${r.support}`}
                      data-testid={`support-${r.id}`}
                      type="range"
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
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <h4 style={{ marginBottom: 4 }}>Timeline</h4>
      <ul data-testid="timeline" style={{ listStyle: "none", padding: 0, fontSize: 12 }}>
        {timeline.map((t) => (
          <li key={t.id} style={{ borderBottom: "1px solid #f3f3f3", padding: "3px 0" }}>
            <b>t{t.turn}</b> · {t.kind} · {t.summary}
          </li>
        ))}
      </ul>
    </div>
  );
}
