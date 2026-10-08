import { t } from "../../i18n";
import type { NPC } from "../../types";
import { Badge, Button } from "../../ui";
import { english, type NameOf } from "./names";

/** The people of the current region, one card each with a "talk" button (US-4.1).
 * Taken out of `RegionScene` (U5). `counts` (message count per NPC id, from
 * `GET .../npcs`) marks the NPCs the player has already talked to. The button stays
 * usable without an LLM: the history still opens and `DialoguePanel` locks the input
 * (BR-U5-29). V4: names, roles and descriptions from the name map (`nameOf`); `talkOff` is
 * the reason [talk] is off (no AI key, BLM § 2.5), said once above the cards. */
export function NpcList({
  npcs,
  counts = {},
  activeNpcId = null,
  onTalk,
  nameOf = english,
  talkOff = null,
}: {
  npcs: NPC[];
  counts?: Record<string, number>;
  activeNpcId?: string | null;
  onTalk?: (npcId: string) => void;
  nameOf?: NameOf;
  talkOff?: string | null;
}) {
  if (npcs.length === 0) return <p className="text-xs text-muted">—</p>;
  return (
    <>
      {talkOff && <p className="text-sm text-muted" data-testid="talk-off">{talkOff}</p>}
      <ul className="grid gap-2 sm:grid-cols-2" data-testid="npc-list">
        {npcs.map((n) => {
          const count = counts[n.id] ?? 0;
          const active = n.id === activeNpcId;
          return (
            <li
              key={n.id}
              data-testid={`npc-${n.id}`}
              className={`flex min-w-0 flex-col gap-1.5 rounded-lg border border-line-strong p-3 text-sm ${active ? "bg-sunken" : "bg-surface"}`}
            >
              <span>
                <b className="font-heading text-base">{nameOf("npcs", n.id, "name", n.name)}</b>{" "}
                <span className="text-muted">· {nameOf("npcs", n.id, "role", n.role)}</span>
                {count > 0 && (
                  <>
                    {" "}
                    <Badge data-testid={`npc-${n.id}-talked`}>{t("dialogue.has", { n: count })}</Badge>
                  </>
                )}
              </span>
              {n.description && (
                <span className="text-xs text-muted">{nameOf("npcs", n.id, "description", n.description)}</span>
              )}
              {onTalk && (
                <Button
                  size="sm"
                  data-testid={`npc-${n.id}-talk-btn`}
                  disabled={active || talkOff != null}
                  onClick={() => onTalk(n.id)}
                  className="self-start"
                >
                  {t("action.talk")}
                </Button>
              )}
            </li>
          );
        })}
      </ul>
    </>
  );
}
