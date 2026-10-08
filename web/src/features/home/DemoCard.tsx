import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { openSessionsOf, statusOf, useReplaceConfirm } from "../../api/http";
import { describeError, type DescribedError } from "../../errors";
import { useResource, useWorldNames } from "../../hooks";
import { t } from "../../i18n";
import type { DemoInfo } from "../../types";
import { Badge, Button, Card, ConfirmDialog, InlineError } from "../../ui";
import { openLatestFirst } from "./sessions";

type After = "play" | "edit" | "stay"; // what a yes to "replace?" goes on to

/** One manifest demo; the card owns its world (V4 Q1=A, BLM § 1.2, BR-V4-05). By state:
 * - new (not there): [play now] loads it, starts at its start region and opens play;
 * - loaded, no open session: [play now] starts a session at once, nothing asked;
 * - resume (open sessions): [continue] the latest, or [new session];
 * - sessions unread: the loaded buttons and a line with [retry], no [continue].
 * [view in editor] never reloads (BR-U8-21). [reload the demo] asks "replace?", then "close N
 * sessions?" (C8). A world the list did not know answers 409 and is asked about (U8 #1). */
export function DemoCard({
  demo,
  held,
  regionCount,
  onLoaded,
}: {
  demo: DemoInfo;
  held: boolean;
  regionCount?: number;
  onLoaded: () => void;
}) {
  const navigate = useNavigate();
  const worldId = demo.name; // a demo loads into its own name (BR-U8-3)
  const title = demo.title_ko || demo.title;
  const [busy, setBusy] = useState(false);
  const [askExisting, setAskExisting] = useState(false); // "this world, or fresh?" (409 only)
  const replace = useReplaceConfirm();
  const [after, setAfter] = useState<After>("play");
  const [error, setError] = useState<DescribedError | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [startMissing, setStartMissing] = useState(false);
  // the server said the world is there although the list did not (the list was still on
  // its way, failed, or is stale): from then on this card treats it as there
  const [foundThere, setFoundThere] = useState(false);
  const there = held || foundThere;
  const sessions = useResource(there ? ["sessions", worldId] : null, () => api.listSessions(worldId));
  const { names } = useWorldNames(there ? worldId : null);
  const open = sessions.data ? openLatestFirst(sessions.data) : [];
  const mode = !there
    ? "new"
    : sessions.state === "error"
      ? "unread"
      : sessions.data === undefined
        ? "reading"
        : open.length > 0
          ? "resume"
          : "loaded";
  const startName = names?.regions?.[demo.start_region_id]?.name; // no English export (R-03)
  const meta = there
    ? [regionCount != null ? t("home.regions", { n: regionCount }) : null, startName ? t("label.startAt", { name: startName }) : null]
        .filter(Boolean)
        .join(" · ")
    : "";

  function fail(e: DescribedError, lines: string[] = []) {
    setError(e);
    setWarnings(lines);
  }

  /** Load the demo; false (and the card says why) when it did not load cleanly. Only a
   * reload the designer confirmed replaces: a first load sends replace=false, so a world
   * the screen did not know about is never replaced unasked (U8 review #1). */
  async function load(confirm: boolean, next: After, fresh: boolean): Promise<boolean> {
    try {
      const report = await api.loadDemo(worldId, demo.name, { replace: fresh, confirm });
      if (!report.ok) {
        const errs = report.warnings.filter((w) => w.severity === "error").map((w) => w.message);
        fail({ title: t("demo.loadFailed") }, [
          ...errs.slice(0, 3),
          ...(report.backup_path ? [t("demo.backup", { path: report.backup_path })] : []),
        ]);
        return false;
      }
      onLoaded();
      return true;
    } catch (e) {
      if (openSessionsOf(e)?.busy) fail({ title: t("demo.busy") }); // mid-turn: no question
      else if (replace.sessionsAsked(e, confirm)) setAfter(next);
      else if (!fresh && statusOf(e) === 409) {
        setFoundThere(true); // "world already exists": ask, or open it as it is
        if (next === "play") setAskExisting(true);
        else navigate(`/editor/${encodeURIComponent(worldId)}`); // never reloads (BR-U8-21)
      } else fail(describeError(e));
      return false;
    }
  }

  function begin() {
    setBusy(true);
    setError(null);
    setWarnings([]);
    setStartMissing(false);
  }

  function askFresh(next: After) {
    setAfter(next);
    replace.askReplace();
  }

  async function play(fresh: boolean, confirm = false) {
    begin();
    try {
      if ((!there || fresh) && !(await load(confirm, "play", fresh))) return;
      try {
        const out = await api.startSession(worldId, {
          name: t("demo.playerName"),
          start_region_id: demo.start_region_id,
        });
        navigate(`/play/${encodeURIComponent(out.session.id)}`);
      } catch (e) {
        // an edited world may have lost the demo's start region (FD R-03)
        if (there && !fresh && [400, 404].includes(statusOf(e) ?? 0)) setStartMissing(true);
        else fail(describeError(e));
      }
    } finally {
      setBusy(false);
    }
  }

  async function reloadDemo(confirm = false) {
    begin();
    try {
      if (await load(confirm, "stay", true)) sessions.reload();
    } finally {
      setBusy(false);
    }
  }

  async function edit(confirm = false) {
    if (there) {
      navigate(`/editor/${encodeURIComponent(worldId)}`); // never reloads (BR-U8-21)
      return;
    }
    begin();
    try {
      if (await load(confirm, "edit", false)) navigate(`/editor/${encodeURIComponent(worldId)}`);
    } finally {
      setBusy(false);
    }
  }

  const off = busy || mode === "reading";
  const editButton = (
    <Button data-testid={`demo-edit-${demo.name}`} disabled={off} onClick={() => edit()}>
      {t("demo.edit")}
    </Button>
  );
  const freshButton = (
    <Button variant="ghost" data-testid={`demo-fresh-${demo.name}`} disabled={off} onClick={() => askFresh("stay")}>
      {t("action.reloadDemo")}
    </Button>
  );

  return (
    <Card as="article" data-testid={`demo-card-${demo.name}`} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <h3 className="font-heading text-xl">{title}</h3>
        {there && <Badge>{t("demo.loaded")}</Badge>}
      </div>
      {(demo.description_ko || demo.description) && (
        <p className="line-clamp-3 max-w-prose font-story text-sm sm:line-clamp-none">
          {demo.description_ko || demo.description}
        </p>
      )}
      {meta && <p className="text-xs text-muted" data-testid={`demo-meta-${demo.name}`}>{meta}</p>}
      <div className="flex flex-wrap gap-2">
        {mode === "resume" ? (
          <>
            <Button variant="primary" className="w-full sm:w-auto" data-testid={`demo-continue-${demo.name}`}
              disabled={busy} onClick={() => navigate(`/play/${encodeURIComponent(open[0].id)}`)}>
              {t("action.continue")}
            </Button>
            <Button data-testid={`demo-new-session-${demo.name}`} disabled={busy} onClick={() => play(false)}>
              {t("action.newSession")}
            </Button>
            {editButton}
            {freshButton}
          </>
        ) : (
          <>
            <Button variant="primary" className="w-full sm:w-auto" data-testid={`demo-play-${demo.name}`}
              disabled={off} onClick={() => play(false)}>
              {t("demo.play")}
            </Button>
            {editButton}
            {mode !== "new" && freshButton}
          </>
        )}
      </div>
      {mode === "reading" && (
        <span role="status" aria-label={t("label.loading")} className="block h-3 w-1/2 rounded bg-sunken" />
      )}
      {mode === "unread" && (
        <div className="flex flex-wrap items-center gap-2 text-sm" data-testid={`demo-sessions-error-${demo.name}`}>
          <span className="text-muted">{t("notice.sessionsUnreadable")}</span>
          <Button size="sm" variant="ghost" onClick={sessions.reload}>{t("action.retry")}</Button>
        </div>
      )}
      {askExisting && (
        <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="demo-ask">
          <span>{t("demo.existing", { title })}</span>
          <Button size="sm" variant="primary" data-testid="demo-keep" onClick={() => { setAskExisting(false); play(false); }}>
            {t("demo.keep")}
          </Button>
          <Button size="sm" data-testid="demo-reload" onClick={() => { setAskExisting(false); askFresh("play"); }}>
            {t("demo.reload")}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setAskExisting(false)}>{t("action.cancel")}</Button>
        </div>
      )}
      {startMissing && (
        <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="demo-start-missing">
          <span className="text-danger">{t("demo.startMissing")}</span>
          <Button size="sm" onClick={() => askFresh("play")}>{t("demo.reload")}</Button>
        </div>
      )}
      {error && (
        <div className="flex flex-col gap-1" data-testid={`demo-error-${demo.name}`}>
          <InlineError error={error} />
          {warnings.map((w) => <div key={w} className="text-xs text-muted">{w}</div>)}
        </div>
      )}
      {demo.credits && (
        <p className="text-xs text-muted" data-testid={`demo-credits-${demo.name}`}>{demo.credits_ko || demo.credits}</p>
      )}
      <ConfirmDialog open={replace.open} tone="danger" busy={busy}
        title={after === "stay" ? t("action.reloadDemo") : t("demo.play")} confirmLabel={t("action.confirm")}
        onCancel={replace.cancel}
        onConfirm={() => {
          const confirm = replace.answer();
          if (after === "edit") void edit(confirm);
          else if (after === "stay") void reloadDemo(confirm);
          else void play(true, confirm);
        }}>
        <span data-testid="demo-confirm">
          {replace.ask === "replace" ? t("demo.replaceConfirm", { title })
            : t("demo.closeSessions", { n: replace.sessions })}
        </span>
      </ConfirmDialog>
    </Card>
  );
}
