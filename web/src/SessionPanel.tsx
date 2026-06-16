import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import type { GameSession, SessionRumor, TimelineEntry } from "./types";

interface Props {
  session: GameSession;
  regionId: string | null; // GameMaster target = map-selected region
  onChanged?: () => void; // notify parent (e.g. refresh RegionPanel/session)
}

export function SessionPanel({ session, regionId, onChanged }: Props) {
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [rumors, setRumors] = useState<SessionRumor[]>([]);
  const [distortion, setDistortion] = useState(0.3);
  const [error, setError] = useState<string | null>(null);
  const closed = session.status === "closed";

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setTimeline(await api.getTimeline(session.id));
      if (regionId) setRumors(await api.listRumors(session.id, regionId));
      else setRumors([]);
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

      {/* GameMaster region controls (target = selected map region) */}
      {!regionId && (
        <div data-testid="gm-no-region" style={{ color: "#888", fontSize: 12, marginTop: 8 }}>
          Select a region on the map to manage its rumors.
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
