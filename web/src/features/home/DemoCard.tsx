import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { openSessionsOf, statusOf, useReplaceConfirm } from "../../api/http";
import { t } from "../../i18n";
import type { DemoInfo } from "../../types";
import { Button, Card, Modal } from "../../ui";

/** One manifest demo (U8, BLM §2, BR-U8-19..22): [play now] loads it if needed, starts a
 * session at its start region and opens the player screen; [view in editor] opens it,
 * loading only when it is not there yet. A replace asks first, then asks again to close
 * open sessions; a failed step stops on the card and nothing done is undone. */
export function DemoCard({
  demo,
  exists,
  onLoaded,
}: {
  demo: DemoInfo;
  exists: boolean;
  onLoaded: () => void;
}) {
  const navigate = useNavigate();
  const worldId = demo.name; // a demo loads into its own name (BR-U8-3)
  const [busy, setBusy] = useState(false);
  const [askExisting, setAskExisting] = useState(false); // "this world, or fresh?"
  const replace = useReplaceConfirm(); // "replace?" then "close N sessions?" (C8)
  const [after, setAfter] = useState<"play" | "edit">("play"); // what a yes goes on to
  const [error, setError] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [startMissing, setStartMissing] = useState(false);
  // the server said the world is there although the list did not (the list was still on
  // its way, failed, or is stale): from then on this card treats it as there
  const [foundThere, setFoundThere] = useState(false);
  const there = exists || foundThere;

  /** Load the demo; false (and the card says why) when it did not load cleanly. Only a
   * [load fresh] the designer confirmed replaces: a first load sends replace=false, so a
   * world the screen did not know about is never replaced unasked (U8 review #1). */
  async function load(confirm: boolean, after: "play" | "edit", fresh: boolean): Promise<boolean> {
    try {
      const report = await api.loadDemo(worldId, demo.name, { replace: fresh, confirm });
      if (!report.ok) {
        const errs = report.warnings.filter((w) => w.severity === "error").map((w) => w.message);
        setWarnings([...errs.slice(0, 3), ...(report.backup_path ? [t("demo.backup", { path: report.backup_path })] : [])]);
        setError(t("demo.loadFailed"));
        return false;
      }
      onLoaded();
      return true;
    } catch (e) {
      if (openSessionsOf(e)?.busy) setError(t("demo.busy")); // mid-turn: no question
      else if (replace.sessionsAsked(e, confirm)) setAfter(after);
      else if (!fresh && statusOf(e) === 409) {
        setFoundThere(true); // "world already exists": ask, or open it as it is
        if (after === "play") setAskExisting(true);
        else navigate(`/editor/${encodeURIComponent(worldId)}`); // never reloads (BR-U8-21)
      } else setError(String(e));
      return false;
    }
  }

  function askFresh() {
    setAfter("play");
    replace.askReplace();
  }

  async function play(reload: boolean, confirm = false) {
    setBusy(true);
    setError(null);
    setWarnings([]);
    setStartMissing(false);
    try {
      if ((!there || reload) && !(await load(confirm, "play", reload))) return;
      try {
        const out = await api.startSession(worldId, {
          name: t("demo.playerName"),
          start_region_id: demo.start_region_id,
        });
        navigate(`/play/${encodeURIComponent(out.session.id)}`);
      } catch (e) {
        // an edited world may have lost the demo's start region (FD R-03)
        if (there && !reload && [400, 404].includes(statusOf(e) ?? 0)) setStartMissing(true);
        else setError(String(e));
      }
    } finally {
      setBusy(false);
    }
  }

  async function edit(confirm = false) {
    if (there) {
      navigate(`/editor/${encodeURIComponent(worldId)}`); // never reloads (BR-U8-21)
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (await load(confirm, "edit", false)) navigate(`/editor/${encodeURIComponent(worldId)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card data-testid={`demo-card-${demo.name}`} className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-baseline gap-2">
        <strong className="font-display text-lg">{demo.title}</strong>
        {there && <span className="text-xs text-ink-soft">{t("demo.loaded")}</span>}
      </div>
      {demo.description && <p className="text-sm">{demo.description}</p>}
      {demo.credits && <p className="text-xs text-ink-soft" data-testid={`demo-credits-${demo.name}`}>{demo.credits}</p>}
      <div className="flex flex-wrap gap-2">
        <Button variant="primary" data-testid={`demo-play-${demo.name}`} disabled={busy}
          onClick={() => (there ? setAskExisting(true) : play(false))}>
          {t("demo.play")}
        </Button>
        <Button data-testid={`demo-edit-${demo.name}`} disabled={busy} onClick={() => edit()}>
          {t("demo.edit")}
        </Button>
      </div>
      {askExisting && (
        <div className="flex flex-wrap items-center gap-2 text-sm" data-testid="demo-ask">
          <span>{t("demo.existing", { title: demo.title })}</span>
          <Button size="sm" variant="primary" data-testid="demo-keep" onClick={() => { setAskExisting(false); play(false); }}>
            {t("demo.keep")}
          </Button>
          <Button size="sm" data-testid="demo-reload" onClick={() => { setAskExisting(false); askFresh(); }}>
            {t("demo.reload")}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setAskExisting(false)}>{t("action.cancel")}</Button>
        </div>
      )}
      {startMissing && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-danger" data-testid="demo-start-missing">
          <span>{t("demo.startMissing")}</span>
          <Button size="sm" onClick={askFresh}>{t("demo.reload")}</Button>
        </div>
      )}
      {error && (
        <div className="text-sm text-danger" data-testid={`demo-error-${demo.name}`}>
          {error}
          {warnings.map((w) => <div key={w} className="text-xs">{w}</div>)}
        </div>
      )}
      <Modal open={replace.open} confirmTone="danger" busy={busy} title={t("demo.play")}
        onCancel={replace.cancel}
        onConfirm={() => {
          const confirm = replace.answer();
          if (after === "edit") void edit(confirm);
          else void play(true, confirm);
        }}>
        <span data-testid="demo-confirm">
          {replace.ask === "replace" ? t("demo.replaceConfirm", { title: demo.title })
            : t("demo.closeSessions", { n: replace.sessions })}
        </span>
      </Modal>
    </Card>
  );
}
