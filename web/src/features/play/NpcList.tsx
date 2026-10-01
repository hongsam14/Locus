import { t } from "../../i18n";
import type { NPC } from "../../types";
import { Badge, Button } from "../../ui";

/** The people of the current region, one card each with a "talk" button (US-4.1).
 * Taken out of `RegionScene` (U5). `counts` (message count per NPC id, from
 * `GET .../npcs`) marks the NPCs the player has already talked to. The button stays
 * usable without an LLM: the history still opens and `DialoguePanel` locks the input
 * (BR-U5-29). */
export function NpcList({
  npcs,
  counts = {},
  activeNpcId = null,
  onTalk,
}: {
  npcs: NPC[];
  counts?: Record<string, number>;
  activeNpcId?: string | null;
  onTalk?: (npcId: string) => void;
}) {
  if (npcs.length === 0) return <p className="text-xs text-ink-soft">—</p>;
  return (
    <ul className="flex flex-wrap gap-2" data-testid="npc-list">
      {npcs.map((n) => {
        const count = counts[n.id] ?? 0;
        const active = n.id === activeNpcId;
        return (
          <li
            key={n.id}
            data-testid={`npc-${n.id}`}
            className={`sketch-border px-2 py-1 text-sm flex flex-col gap-1 ${active ? "bg-highlight" : "bg-paper"}`}
          >
            <span>
              <b>{n.name}</b> <span className="text-ink-soft">· {n.role}</span>
              {count > 0 && (
                <>
                  {" "}
                  <Badge data-testid={`npc-${n.id}-talked`}>{t("dialogue.has", { n: count })}</Badge>
                </>
              )}
            </span>
            {n.description && <span className="text-xs text-ink-soft max-w-60">{n.description}</span>}
            {onTalk && (
              <Button
                size="sm"
                data-testid={`npc-${n.id}-talk-btn`}
                disabled={active}
                onClick={() => onTalk(n.id)}
                className="self-start"
              >
                {t("npc.talk")}
              </Button>
            )}
          </li>
        );
      })}
    </ul>
  );
}
