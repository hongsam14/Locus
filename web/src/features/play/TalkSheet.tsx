import type { ReactNode } from "react";
import { t } from "../../i18n";
import type { NPC } from "../../types";
import { Dialog } from "../../ui";
import { english, type NameOf } from "./names";

/** A talk on a middle or narrow screen (V4 Q5=A, BLM § 2.5): the dialogue fills the screen.
 * The page decides when it is open (the router's `state.talk`); Esc, [close] and the
 * browser's back all close it through `onClose`. The title names the NPC, so the panel
 * inside goes `bare`. */
export function TalkSheet({
  npc,
  nameOf = english,
  onClose,
  children,
}: {
  npc: NPC | null;
  nameOf?: NameOf;
  onClose: () => void;
  children?: ReactNode;
}) {
  return (
    // the panel puts focus on [close], then the input — never on [end talk] (review 01 #6)
    <Dialog open={npc != null} onOpenChange={(open) => !open && onClose()} variant="full" testId="talk-sheet"
      initialFocus="none"
      title={npc ? t("dialogue.title", { name: nameOf("npcs", npc.id, "name", npc.name) }) : ""}>
      {children}
    </Dialog>
  );
}
