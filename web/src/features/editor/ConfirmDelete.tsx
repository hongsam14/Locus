import { t } from "../../i18n";
import type { RegionDeletePlan } from "../../types";
import { Modal } from "../../ui";

const names = (refs: { name: string }[]) => refs.map((r) => r.name).join(", ");

/** Every delete is confirmed (BR-U3-32). A region shows its delete plan — what moves,
 * what goes, what becomes unscoped — and cannot be confirmed while a player of an open
 * session stands there (BR-U3-9/16). */
export function ConfirmDelete({
  open,
  title,
  message,
  plan,
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title?: string;
  message?: string;
  plan?: RegionDeletePlan | null;
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const blocked = (plan?.blocked_by_sessions.length ?? 0) > 0;
  return (
    <Modal
      open={open}
      title={plan ? t("delete.region.title", { name: plan.region_name }) : (title ?? t("delete.title"))}
      confirmTone="danger"
      confirmLabel={t("delete.confirm")}
      busy={busy || blocked}
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
              <li>{t("delete.region.connections", { n: plan.connections.length })}</li>
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
              <li>{t("delete.region.scopeRemoved", { n: plan.knowledge_scope_removed.length })}</li>
            )}
            {plan.entities_unlocated.length > 0 && (
              <li>{t("delete.region.entities", { n: plan.entities_unlocated.length })}</li>
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
    </Modal>
  );
}
