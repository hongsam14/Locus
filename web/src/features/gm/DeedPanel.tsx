import { useState } from "react";
import { numberWithMeaning, turnAt } from "../../format";
import { useAction } from "../../hooks";
import { t } from "../../i18n";
import type { DeedViewOut } from "../../types";
import { Badge, Button, Card, ConfirmDialog, LocalizedText, StatusView } from "../../ui";
import { english, type NameOf } from "../play/names";
import type { GmRes } from "./useGmData";

/** The GM's view of the player's deeds (US-5.6): what happened, which NPC judged it and how,
 * where its rumors reached — and [never happened], which undoes the deed and every rumor it
 * produced, after asking (V6 BR-V6-13/28: the word is not "cancel"). A refused void stays in
 * the dialog with its sentence (BLM § 6). The judgment's slant is the NPC's own words, shown
 * as they are — it is not an enum (code plan § 1.1 R-01). */
export function DeedPanel({
  deeds,
  closed,
  nameOf = english,
  onVoid,
}: {
  deeds: GmRes<DeedViewOut[]>;
  closed: boolean;
  nameOf?: NameOf;
  /** Resolves when saved; a refusal rejects and is told in the dialog. */
  onVoid(deedId: string): Promise<unknown>;
}) {
  const [asking, setAsking] = useState<DeedViewOut | null>(null);
  const voidDeed = useAction((id: string) => onVoid(id), { onDone: () => setAsking(null) });
  const activeRumors = (v: DeedViewOut) => v.rumors.filter((r) => r.active !== false).length;

  if (!deeds.data) {
    return <StatusView state={deeds.state === "error" ? "error" : "loading"} error={deeds.error} onRetry={deeds.reload} skeleton="cards" />;
  }
  return (
    <section data-testid="deed-panel" className="flex flex-col gap-1.5">
      <h2 className="sr-only">{t("tab.deeds")}</h2>
      {deeds.data.length === 0 && (
        <p data-testid="deed-none" className="text-sm text-muted">{t("empty.deeds")}</p>
      )}
      {deeds.data.map((v) => (
        <Card key={v.deed.id} data-testid={`deed-${v.deed.id}`} tabIndex={-1}
          className={`flex flex-col gap-1 text-sm ${v.deed.voided ? "opacity-60" : ""}`}>
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
            <Badge tone="event">{t(`deed.kind.${v.deed.kind}`)}</Badge>
            <span>{nameOf("regions", v.deed.region_id, "name", v.deed.region_name ?? v.deed.region_id)}</span>
            <span>{turnAt(v.deed.turn)}</span>
            {v.deed.witnessed_npc_ids.length > 0 && (
              <span data-testid={`deed-witnesses-${v.deed.id}`}>
                {t("deed.witnesses")}:{" "}
                {v.deed.witnessed_npc_ids
                  .map((id, i) => nameOf("npcs", id, "name", v.deed.witness_names?.[i] ?? id))
                  .join(", ")}
              </span>
            )}
            {v.deed.voided && <Badge data-testid={`deed-voided-${v.deed.id}`}>{t("deed.voided")}</Badge>}
          </div>
          <LocalizedText ko={v.deed.text_ko} original={v.deed.text} />
          {v.deed.declaration && (
            <span className="text-xs text-muted">
              {t("deed.declaration")}: {v.deed.declaration}
            </span>
          )}
          {v.appraisals.length > 0 && (
            <ul data-testid={`deed-appraisals-${v.deed.id}`} className="flex flex-col text-xs">
              {v.appraisals.map((a) => (
                <li key={a.id}>
                  <b>{nameOf("npcs", a.npc_id, "name", a.npc_name ?? a.npc_id)}</b>{" "}
                  {a.noteworthy ? t("label.noteworthy") : t("label.notNoteworthy")}{" · "}
                  {t("label.salience")} {numberWithMeaning("salience", a.salience)}
                  {a.slant ? ` · ${t("label.slant")}: ${a.slant}` : ""}
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
              {t("deed.reached")}:{" "}
              {v.reached_region_ids.map((id, i) => nameOf("regions", id, "name", v.reached_region_names[i] ?? id)).join(" · ")}
              {" — "}
              {t("label.rumorsLive", { live: activeRumors(v), all: v.rumors.length })}
            </span>
          )}
          {!v.deed.voided && (
            <Button size="sm" variant="danger" className="self-start" data-testid={`void-${v.deed.id}`} disabled={closed}
              onClick={() => {
                voidDeed.clearError();
                setAsking(v);
              }}>
              {t("deed.void")}
            </Button>
          )}
        </Card>
      ))}
      <ConfirmDialog
        open={asking != null}
        title={t("confirm.voidDeedTitle")}
        tone="danger"
        confirmLabel={t("deed.voidConfirmBtn")}
        cancelLabel={t("action.cancel")}
        busy={voidDeed.busy}
        error={voidDeed.error}
        onConfirm={() => {
          if (asking) void voidDeed.run(asking.deed.id);
        }}
        onCancel={() => setAsking(null)}
      >
        <span data-testid="void-confirm">{asking ? t("confirm.voidDeed", { n: activeRumors(asking) }) : ""}</span>
      </ConfirmDialog>
    </section>
  );
}
