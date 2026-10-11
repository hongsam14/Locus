import { useEffect, useRef } from "react";
import { enumLabel } from "../../format";
import { t } from "../../i18n";
import type { MoveOption } from "../../types";
import { Button } from "../../ui";
import { lockedProps } from "./ActionBar";
import { english, type NameOf } from "./names";

/** Move options from the current region (FR-C2): cost in turns, blocked ones greyed. The
 * list is the only way to move; the small map only points at a row (V4 Q4=A).
 *
 * V4: names from the map; the way in words and "N turns"; a blocked row stays, grey, with
 * the dictionary's reason and no button — the server's `reason` is code-like English and
 * never shown (BR-V4-13). `highlightId` marks the row the map pointed at and scrolls to it.
 * `bare` drops the heading (the move sheet has its own title). */
export function MovePanel({
  moves,
  disabled,
  onMove,
  nameOf = english,
  highlightId = null,
  bare = false,
  locked = false,
}: {
  moves: MoveOption[];
  disabled: boolean;
  onMove: (regionId: string) => void;
  nameOf?: NameOf;
  highlightId?: string | null;
  bare?: boolean;
  locked?: boolean; // a turn runs: [move] is off but keeps its focus (BR-V4-24)
}) {
  const rows = useRef<Record<string, HTMLLIElement | null>>({});
  useEffect(() => {
    if (highlightId) rows.current[highlightId]?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [highlightId]);

  return (
    <section className="flex flex-col gap-2" aria-labelledby={bare ? undefined : "where-to-go"} data-testid="move-panel">
      {!bare && <h2 id="where-to-go" className="font-heading text-xl">{t("label.whereToGo")}</h2>}
      {moves.length === 0 && <p className="text-sm text-muted">—</p>}
      <ul className="flex flex-col gap-1">
        {moves.map((m) => {
          const lit = m.region_id === highlightId;
          return (
            <li
              key={m.region_id}
              ref={(el) => {
                rows.current[m.region_id] = el;
              }}
              data-testid={`move-${m.region_id}`}
              data-highlight={lit || undefined}
              className={
                `flex min-h-11 flex-wrap items-center gap-x-3 gap-y-1 rounded-md px-2 py-1 text-sm ` +
                `${lit ? "bg-sunken ring-2 ring-accent" : ""} ${m.passable ? "" : "text-muted"}`
              }
            >
              <span className="min-w-0 flex-1">
                <b className={m.passable ? "text-fg" : ""}>{nameOf("regions", m.region_id, "name", m.region_name)}</b>{" "}
                <span className="text-muted">
                  {enumLabel("travelBy", m.kind)}
                  {m.passable && <> · {t("unit.turns", { n: m.cost_turns })}</>}
                </span>
                {!m.passable && (
                  <span className="block text-xs" data-testid={`move-${m.region_id}-blocked`}>
                    {t("notice.moveBlocked")}
                  </span>
                )}
              </span>
              {m.passable && (
                <Button size="sm" variant="primary" data-testid={`move-${m.region_id}-btn`} disabled={disabled}
                  {...lockedProps(locked, () => onMove(m.region_id))}>
                  {t("action.move")}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
