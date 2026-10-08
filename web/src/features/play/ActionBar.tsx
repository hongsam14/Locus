import { useState, type ReactNode } from "react";
import type { DescribedError } from "../../errors";
import { t } from "../../i18n";
import type { TurnRun } from "../../types";
import { Button, InlineError, Textarea } from "../../ui";

// What the server strips (Python `str.strip`): JS `trim` misses NEL and the separators.
// The trailing branch only starts after a non-space, so a long run of spaces inside the
// text is not re-scanned at every position (linear; U7 review §3 EDGE_SPACE).
const EDGE_SPACE = /^[\s\x1c-\x1f\x85]+|(?<![\s\x1c-\x1f\x85])[\s\x1c-\x1f\x85]+$/g;

/** Characters as the server counts them: code points, not UTF-16 units (U6 review #15). */
export function declaredLength(text: string): number {
  return Array.from(text).length;
}

const oneTurn = () => t("unit.turns", { n: 1 });

/** A button that is off while a turn runs keeps its focus (BR-V4-24): `aria-disabled` and
 * the press ignored, not native `disabled` (which drops focus to the page). */
export function lockedProps(locked: boolean, onClick: () => void) {
  return {
    "aria-disabled": locked || undefined,
    onClick: () => {
      if (!locked) onClick();
    },
  };
}

export type Held = "waiting" | "stuck" | null;

/** Where a turn stands (V4 BLM § 2.2, BR-V4-17/19): running, slow past the poll cap, its
 * check failed (the last two with [check again]), or the session held by other work with no
 * run of ours — past the re-read cap with [check again] too (code review 01 #1). Running,
 * slow and held change inside one live region that is always there, so a screen reader
 * hears them (#26); errors are alerts of their own. The action box and the phone's dock
 * both show it in the place of the actions. `className` evens out the parent's gap when
 * the region is empty. */
export function TurnStatus({
  running,
  slow = false,
  error,
  refusal,
  onRecheck,
  held = null,
  onHeldRecheck,
  className = "",
}: {
  running: TurnRun | null;
  slow?: boolean;
  error?: DescribedError;
  refusal?: DescribedError; // the server refused the action: said once, nothing to check again
  onRecheck?: () => void;
  held?: Held;
  onHeldRecheck?: () => void;
  className?: string;
}) {
  const recheck = onRecheck && (
    <Button size="sm" data-testid="turn-recheck" onClick={onRecheck}>{t("action.recheck")}</Button>
  );
  let state = null;
  if (!error && slow) {
    state = (
      <div data-testid="turn-slow" className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted">{t("notice.turnSlow")}</span>
        {recheck}
      </div>
    );
  } else if (!error && running) {
    state = (
      <span data-testid="turn-progress" className="animate-pulse text-sm text-muted">
        {t("play.running", { n: running.cost_turns })}
      </span>
    );
  } else if (!error && held) {
    state = (
      <div data-testid="turn-held" className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted">{t("notice.sessionHeld")}</span>
        {held === "stuck" && onHeldRecheck && (
          <Button size="sm" data-testid="held-recheck" onClick={onHeldRecheck}>{t("action.recheck")}</Button>
        )}
      </div>
    );
  }
  return (
    <>
      {refusal && (
        <div data-testid="action-error">
          <InlineError error={refusal} />
        </div>
      )}
      {error && (
        <div data-testid="turn-error" className="flex flex-col items-start gap-2">
          <InlineError error={error} />
          {recheck}
        </div>
      )}
      <div role="status" className={className}>{state}</div>
    </>
  );
}

/** The declaration box (US-4.5): free text, the server's length limit, one turn. It is
 * locked while the request is out (U6 review #12) and restored when the server refuses
 * (400 / 409, review R-14). V4: a visible label and the focus ring (BR-V4-23). `extra` sits
 * beside [declare] (the action box puts [wait] there). */
export function DeclareForm({
  disabled,
  locked = false,
  closed = false,
  maxChars = 300,
  onDeclare,
  extra,
}: {
  disabled: boolean; // no new action (the session closed; before V4 also a running turn)
  locked?: boolean; // a turn runs: [declare] is off but keeps its focus (BR-V4-24)
  closed?: boolean; // the session closed: the box locks too (U7 review #7)
  maxChars?: number;
  onDeclare: (text: string) => Promise<boolean>;
  extra?: ReactNode;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const text = draft.replace(EDGE_SPACE, "");
  const length = declaredLength(text);
  const tooLong = length > maxChars;

  async function declare() {
    if (disabled || locked || sending || !text || tooLong) return;
    const kept = draft;
    setSending(true);
    setDraft("");
    try {
      const accepted = await onDeclare(text);
      if (!accepted) setDraft(kept); // the box was locked: nothing typed meanwhile is lost
    } finally {
      setSending(false);
    }
  }

  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        void declare();
      }}
    >
      <Textarea
        label={t("label.declare")}
        data-testid="declare-input"
        value={draft}
        rows={2}
        placeholder={t("play.declarePlaceholder")}
        // typing goes on during a turn; only the request and a closed session lock it
        disabled={closed || sending}
        // no cut: the count below turns red past the limit and [declare] goes off
        onChange={(e) => setDraft(e.target.value)}
      />
      <div className="flex flex-wrap items-center gap-2">
        <span data-testid="declare-count" className={`mr-auto text-xs tabular-nums ${tooLong ? "text-danger" : "text-muted"}`}>
          {t("play.chars", { n: length, max: maxChars })}
        </span>
        <Button type="submit" variant="primary" data-testid="declare-btn" busy={sending}
          aria-disabled={locked || undefined} disabled={disabled || !text || tooLong}>
          {t("action.declare")} · {oneTurn()}
        </Button>
        {extra}
      </div>
    </form>
  );
}

/** The action box of a wide or middle screen (Q4=A, V4 § 3.3): the declaration, [wait], and
 * where the turn stands. An action answers 202 and the turn runs on; the box stays where
 * it is. */
export function ActionBar({
  running,
  disabled,
  closed = false,
  onWait,
  onDeclare,
  maxChars = 300,
  slow = false,
  error,
  refusal,
  onRecheck,
  locked = false,
  held = null,
  onHeldRecheck,
}: {
  running: TurnRun | null;
  disabled: boolean;
  locked?: boolean;
  held?: Held;
  onHeldRecheck?: () => void;
  closed?: boolean;
  onWait: () => void;
  onDeclare?: (text: string) => Promise<boolean>;
  maxChars?: number;
  slow?: boolean;
  error?: DescribedError;
  refusal?: DescribedError;
  onRecheck?: () => void;
}) {
  const wait = (
    <Button type="button" data-testid="wait-btn" disabled={disabled} {...lockedProps(locked, onWait)}>
      {t("action.wait")} · {oneTurn()}
    </Button>
  );
  return (
    <div data-testid="action-bar" className="flex flex-col gap-3 rounded-lg border border-line-strong bg-surface p-4">
      {onDeclare ? (
        <DeclareForm disabled={disabled} locked={locked} closed={closed} maxChars={maxChars} onDeclare={onDeclare}
          extra={wait} />
      ) : (
        <div className="flex">{wait}</div>
      )}
      <TurnStatus running={running} slow={slow} error={error} refusal={refusal} onRecheck={onRecheck} held={held}
        onHeldRecheck={onHeldRecheck} className="empty:-mt-3" />
    </div>
  );
}
