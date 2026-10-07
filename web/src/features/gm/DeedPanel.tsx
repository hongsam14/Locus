import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { t, useRequestLang } from "../../i18n";
import type { DeedViewOut } from "../../types";
import { conflictKind } from "../../api/http";
import { Badge, Button, Card, LocalizedText, Modal, Panel } from "../../ui";

/** The GM's view of the player's deeds (US-5.6): what happened, which NPC judged it and
 * how, where its rumors reached — and a void that undoes the deed and every rumor it
 * produced. One of the GM hub's panels (U7). It re-reads when `reloadKey` changes (a
 * turn or GM write elsewhere) and after its own void — once each (U6 review C1). */
export function DeedPanel({
  sessionId,
  closed,
  onChanged,
  reloadKey = 0,
}: {
  sessionId: string;
  closed: boolean;
  onChanged?: () => void;
  reloadKey?: number;
}) {
  const requestLang = useRequestLang(); // translated text: re-read when the language changes
  const [deeds, setDeeds] = useState<DeedViewOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<DeedViewOut | null>(null);
  const [busy, setBusy] = useState(false);
  const readSeq = useRef(0);

  const load = useCallback(async () => {
    const mine = ++readSeq.current;
    try {
      const list = await api.listDeeds(sessionId);
      if (mine !== readSeq.current) return; // a newer read (or language) won
      setDeeds(Array.isArray(list) ? list : []);
      setError(null);
    } catch (e) {
      if (mine === readSeq.current) setError(String(e));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- requestLang / reloadKey re-read
  }, [sessionId, requestLang, reloadKey]);

  useEffect(() => {
    void load();
  }, [load]);

  async function voidDeed(view: DeedViewOut) {
    if (busy) return; // one request per confirmation (U6 review #13)
    setBusy(true);
    setNotice(null);
    try {
      await api.voidDeed(sessionId, view.deed.id);
      await load();
      onChanged?.();
    } catch (e) {
      const kind = conflictKind(e);
      if (kind === "closed") {
        setNotice(t("play.sessionClosed")); // not a turn: say so, and let the page re-read
        onChanged?.();
      } else if (kind === "busy") {
        setNotice(t("play.turnInProgress"));
      } else {
        setError(String(e));
      }
    } finally {
      setBusy(false);
      setConfirm(null);
    }
  }

  const activeRumors = (v: DeedViewOut) => v.rumors.filter((r) => r.active !== false).length;

  return (
    <Panel data-testid="deed-panel" title={t("deed.title")} className="min-w-80">
      {error && <div className="text-danger text-sm mb-2">{error}</div>}
      {notice && (
        <div data-testid="deed-notice" className="text-sm mb-2">
          {notice}
        </div>
      )}
      {deeds.length === 0 && !error && (
        <p data-testid="deed-none" className="text-xs text-ink-soft">
          {t("deed.none")}
        </p>
      )}
      <div className="flex flex-col gap-1.5">
        {deeds.map((v) => (
          <Card
            key={v.deed.id}
            data-testid={`deed-${v.deed.id}`}
            className={`flex flex-col gap-1 text-sm ${v.deed.voided ? "opacity-50" : ""}`}
          >
            <div className="flex flex-wrap items-center gap-1.5 text-xs text-ink-soft">
              <Badge tone="event">{t(`deed.kind.${v.deed.kind}`)}</Badge>
              <span>{v.deed.region_name ?? v.deed.region_id}</span>
              <span>t{v.deed.turn}</span>
              {(v.deed.witness_names ?? []).length > 0 && (
                <span>
                  {t("deed.witnesses")}: {(v.deed.witness_names ?? []).join(", ")}
                </span>
              )}
              {v.deed.voided && (
                <Badge data-testid={`deed-voided-${v.deed.id}`}>{t("deed.voided")}</Badge>
              )}
            </div>
            <LocalizedText ko={v.deed.text_ko} original={v.deed.text} />
            {v.deed.declaration && (
              <span className="text-xs text-ink-soft">
                {t("deed.declaration")}: {v.deed.declaration}
              </span>
            )}
            {v.appraisals.length > 0 && (
              <ul data-testid={`deed-appraisals-${v.deed.id}`} className="text-xs flex flex-col">
                {v.appraisals.map((a) => (
                  <li key={a.id}>
                    <b>{a.npc_name ?? a.npc_id}</b> {a.noteworthy ? "✓" : "✗"}{" "}
                    {t("deed.salience")} {a.salience.toFixed(2)}
                    {a.slant ? ` · ${a.slant}` : ""}
                    {a.retelling && (
                      <>
                        {" — "}
                        <LocalizedText ko={a.retelling_ko} original={a.retelling} />
                      </>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {v.reached_region_names.length > 0 && (
              <span data-testid={`deed-reached-${v.deed.id}`} className="text-xs">
                {t("deed.reached")}: {v.reached_region_names.join(" · ")} ({activeRumors(v)}/
                {v.rumors.length})
              </span>
            )}
            {!v.deed.voided && (
              <Button
                size="sm"
                variant="danger"
                data-testid={`void-${v.deed.id}`}
                disabled={closed || busy}
                onClick={() => setConfirm(v)}
                className="self-start"
              >
                {t("deed.void")}
              </Button>
            )}
          </Card>
        ))}
      </div>
      {/* The confirm label is never the Cancel word: both read "취소" in ko (review U6 #2). */}
      <Modal
        open={confirm != null}
        title={t("deed.voidTitle")}
        confirmTone="danger"
        confirmLabel={t("deed.voidConfirmBtn")}
        cancelLabel={t("action.cancel")}
        busy={busy}
        onConfirm={() => {
          if (confirm) void voidDeed(confirm);
        }}
        onCancel={() => setConfirm(null)}
      >
        <span data-testid="void-confirm">
          {confirm ? t("deed.voidConfirm", { n: activeRumors(confirm) }) : ""}
        </span>
      </Modal>
    </Panel>
  );
}
