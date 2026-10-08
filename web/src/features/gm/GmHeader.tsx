import { useState } from "react";
import type { DescribedError } from "../../errors";
import { useAction } from "../../hooks";
import { t } from "../../i18n";
import type { GameSession } from "../../types";
import { Button, ConfirmDialog, InlineError, Select } from "../../ui";
import type { SessionOption } from "./sessionLabel";

/** The GM screen's head (V6 frontend-components § 4, BR-V6-13/26): the world, the session
 * picker in words with ended sessions apart, a session without a player, and an end that
 * asks first — an ended session cannot be opened again (RE-F04, UX-35). While a bulk run
 * goes (`locked`) neither a new session nor an end can start (code plan § 1.1 R-06). */
export function GmHeader({
  session,
  worldName,
  options,
  sessionsError,
  locked = false,
  onRetrySessions,
  onPick,
  onNew,
  onEnd,
}: {
  session: GameSession | null;
  worldName: string;
  options: SessionOption[];
  sessionsError?: DescribedError;
  locked?: boolean;
  onRetrySessions(): void;
  onPick(sessionId: string): void;
  onNew(): Promise<unknown>;
  /** Ends the session; resolves when it is saved (a failure rejects and stays in the dialog). */
  onEnd(): Promise<unknown>;
}) {
  const [asking, setAsking] = useState(false);
  const newSession = useAction(onNew);
  const end = useAction(onEnd, { onDone: () => setAsking(false) });
  const open = session != null && session.status !== "closed";
  return (
    <section data-testid="gm-header" className="flex flex-col gap-2">
      <div className="flex flex-wrap items-end gap-3">
        <h1 className="flex-1 font-heading text-2xl">{t("label.gmHeading", { world: worldName })}</h1>
        <Select
          label={t("label.session")}
          data-testid="session-select"
          value={session?.id ?? ""}
          placeholder={session ? undefined : t("label.loading")}
          options={options}
          onChange={onPick}
        />
        <Button data-testid="session-new-btn" busy={newSession.busy} disabled={locked}
          onClick={() => void newSession.run()}>
          {t("action.newGmSession")}
        </Button>
        {open && (
          <Button variant="danger" data-testid="session-close-btn" disabled={locked}
            onClick={() => {
              end.clearError();
              setAsking(true);
            }}>
            {t("session.end")}
          </Button>
        )}
      </div>
      {sessionsError && (
        <div data-testid="sessions-error" className="flex flex-wrap items-center gap-2 text-sm text-muted">
          {t("notice.sessionsUnread")}
          <Button size="sm" onClick={onRetrySessions}>{t("action.retry")}</Button>
        </div>
      )}
      {newSession.error && <InlineError error={newSession.error} />}
      <ConfirmDialog
        open={asking}
        tone="danger"
        title={t("confirm.endSessionTitle")}
        confirmLabel={t("session.end")}
        cancelLabel={t("action.cancel")}
        busy={end.busy}
        error={end.error}
        confirmTestId="session-close-confirm"
        onConfirm={() => void end.run()}
        onCancel={() => setAsking(false)}
      >
        {t("confirm.endSession")}
      </ConfirmDialog>
    </section>
  );
}

/** An ended session: said once under the head; the record stays readable (BR-V6-12). */
export function ClosedBanner() {
  return (
    <div role="status" data-testid="gm-closed-banner"
      className="rounded-lg border border-line bg-sunken px-4 py-3 text-sm">
      {t("notice.sessionEnded")}
    </div>
  );
}
