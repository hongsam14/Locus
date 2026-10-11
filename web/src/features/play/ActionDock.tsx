import { useEffect, useRef, useState } from "react";
import type { DescribedError } from "../../errors";
import { t } from "../../i18n";
import type { MoveOption, TurnRun } from "../../types";
import { Button, Dialog } from "../../ui";
import { DeclareForm, TurnStatus, lockedProps, type Held } from "./ActionBar";
import { MovePanel } from "./MovePanel";
import { english, type NameOf } from "./names";

/** A phone's actions (V4 Q3=A, frontend-components § 3.3): a bar fixed to the bottom with
 * [wait], [declare] and [move], each 44px or taller, above the safe area. [declare] opens a
 * sheet with the declaration box — it closes when the server takes the line and stays open
 * when it refuses; [move] opens a sheet with the move list, which closes on a choice. The
 * move sheet is the page's to open as well (a press on the small map, BR-V4-14), so its
 * state comes from outside. A sheet's content exists only while it is open (BR-V4-25). */
export function ActionDock({
  running,
  slow = false,
  error,
  refusal,
  onRecheck,
  held = null,
  onHeldRecheck,
  onClearRefusal,
  disabled,
  locked = false,
  closed = false,
  maxChars = 300,
  onWait,
  onDeclare,
  moves,
  nameOf = english,
  onMove,
  moveOpen,
  onMoveOpenChange,
  highlightId = null,
}: {
  running: TurnRun | null;
  slow?: boolean;
  error?: DescribedError;
  refusal?: DescribedError;
  onRecheck?: () => void;
  held?: Held;
  onHeldRecheck?: () => void;
  /** A refusal belongs to the action it answered: opening the declare sheet clears it. */
  onClearRefusal?: () => void;
  disabled: boolean; // the session closed
  locked?: boolean; // a turn runs: the actions keep their focus (BR-V4-24)
  closed?: boolean;
  maxChars?: number;
  onWait: () => void;
  onDeclare: (text: string) => Promise<boolean>;
  moves: MoveOption[];
  nameOf?: NameOf;
  onMove: (regionId: string) => void;
  moveOpen: boolean;
  onMoveOpenChange: (open: boolean) => void;
  highlightId?: string | null;
}) {
  const [declareOpen, setDeclareOpen] = useState(false);
  // the page keeps room under itself for the bar as tall as it is now — a slow turn or an
  // error makes it taller (code review 01 #17); without ResizeObserver the layout's 7rem stays
  const bar = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const el = bar.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const root = document.documentElement.style;
    const observer = new ResizeObserver(() => root.setProperty("--dock-h", `${el.offsetHeight}px`));
    observer.observe(el);
    return () => {
      observer.disconnect();
      root.removeProperty("--dock-h");
    };
  }, []);
  return (
    <>
      <div ref={bar} data-testid="action-dock"
        className="fixed inset-x-0 bottom-0 z-40 flex flex-col gap-2 border-t border-line-strong bg-surface px-4 pt-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] shadow-pop">
        {/* a refused declaration is said in its sheet, which stays open */}
        <TurnStatus running={running} slow={slow} error={error} refusal={declareOpen ? undefined : refusal}
          onRecheck={onRecheck} held={held} onHeldRecheck={onHeldRecheck} className="empty:-mt-2" />
        <div className="grid grid-cols-3 gap-2">
          <Button data-testid="dock-wait" disabled={disabled} {...lockedProps(locked, onWait)}>
            {t("action.wait")}
          </Button>
          <Button variant="primary" data-testid="dock-declare" disabled={closed}
            onClick={() => {
              onClearRefusal?.();
              setDeclareOpen(true);
            }}>
            {t("action.declare")}
          </Button>
          <Button data-testid="dock-move" disabled={closed} onClick={() => onMoveOpenChange(true)}>
            {t("action.move")}
          </Button>
        </div>
      </div>
      <Dialog open={declareOpen} onOpenChange={setDeclareOpen} variant="sheet" testId="declare-sheet"
        title={t("action.declare")}>
        {refusal && <TurnStatus running={null} refusal={refusal} />}
        <DeclareForm disabled={disabled} locked={locked} closed={closed} maxChars={maxChars}
          onDeclare={async (text) => {
            const accepted = await onDeclare(text);
            if (accepted) setDeclareOpen(false);
            return accepted;
          }} />
      </Dialog>
      {/* the sheet itself takes focus, not its first [move] (code review 01 #6) */}
      <Dialog open={moveOpen} onOpenChange={onMoveOpenChange} variant="sheet" testId="move-sheet" initialFocus="content"
        title={t("label.whereToGo")}>
        <MovePanel bare moves={moves} nameOf={nameOf} highlightId={highlightId} disabled={disabled} locked={locked}
          onMove={(id) => {
            onMoveOpenChange(false);
            onMove(id);
          }} />
      </Dialog>
    </>
  );
}
