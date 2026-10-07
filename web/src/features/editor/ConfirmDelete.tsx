import { t } from "../../i18n";
import type { ConnectionKey, Region, RegionDeletePlan } from "../../types";
import { ConfirmDialog } from "../../ui";

const names = (refs: { name: string }[]) => refs.map((r) => r.name).join(", ");

/** A connection of the doomed region, named by the region at its other end and its kind. */
function connectionNames(plan: RegionDeletePlan, regions: Region[]): string {
  const name = (id: string) => regions.find((r) => r.id === id)?.name ?? id;
  const other = (k: ConnectionKey) => (k.a_region_id === plan.region_id ? k.b_region_id : k.a_region_id);
  return plan.connections.map((k) => `${name(other(k))} (${k.kind})`).join(", ");
}

/** Every delete is confirmed (BR-U3-32). A region shows its delete plan — what moves,
 * what goes, what becomes unscoped, each by count and name (U3 review S25) — and cannot
 * be confirmed while a player of an open session stands there (BR-U3-9/16). */
export function ConfirmDelete({
  open,
  title,
  message,
  plan,
  regions = [],
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title?: string;
  message?: string;
  plan?: RegionDeletePlan | null;
  regions?: Region[]; // names the far end of each connection that goes
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const blocked = (plan?.blocked_by_sessions.length ?? 0) > 0;
  return (
    <ConfirmDialog
      open={open}
      title={plan ? t("delete.region.title", { name: plan.region_name }) : (title ?? t("delete.title"))}
      tone="danger"
      confirmLabel={t("delete.confirm")}
      busy={busy}
      confirmDisabled={blocked}
      onConfirm={onConfirm}
      onCancel={onCancel}
    >
      <div data-testid="confirm-delete" className="flex flex-col gap-1">
        {message && <p>{message}</p>}
        {plan && (
          <ul className="list-disc pl-4 text-xs" data-testid="delete-plan">
            {plan.children.length > 0 && (
              <li>{t("delete.region.children", { n: plan.children.length, names: names(plan.children) })}</li>
            )}
            {plan.connections.length > 0 && (
              <li>{t("delete.region.connections", { n: plan.connections.length,
                names: connectionNames(plan, regions) })}</li>
            )}
            {plan.npcs.length > 0 && (
              <li>{t("delete.region.npcs", { n: plan.npcs.length, names: names(plan.npcs) })}</li>
            )}
            {plan.knowledge_to_unscope.length > 0 && (
              <li>
                {t("delete.region.unscope", {
                  n: plan.knowledge_to_unscope.length,
                  names: names(plan.knowledge_to_unscope),
                })}
              </li>
            )}
            {plan.knowledge_scope_removed.length > 0 && (
              <li>{t("delete.region.scopeRemoved", { n: plan.knowledge_scope_removed.length,
                names: names(plan.knowledge_scope_removed) })}</li>
            )}
            {plan.entities_unlocated.length > 0 && (
              <li>{t("delete.region.entities", { n: plan.entities_unlocated.length,
                names: names(plan.entities_unlocated) })}</li>
            )}
            {(plan.seed_ids?.length ?? 0) > 0 && ( // U8 (BR-U8-14): its event seeds go too
              <li data-testid="delete-plan-seeds">{t("delete.region.seeds", { n: plan.seed_ids?.length ?? 0 })}</li>
            )}
          </ul>
        )}
        {blocked && (
          <p className="text-danger" data-testid="delete-blocked">
            {t("delete.region.blocked", { ids: plan?.blocked_by_sessions.join(", ") ?? "" })}
          </p>
        )}
        {error && <p className="text-danger">{error}</p>}
      </div>
    </ConfirmDialog>
  );
}
