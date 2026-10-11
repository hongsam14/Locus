import { t } from "../../i18n";
import type { BuildReport } from "../../types";
import { Button, Card } from "../../ui";
import { groupByStage, sessionsNotClosed } from "./buildStages";

/** What a build did (US-2.1, BR-U3-35; V8 frontend-components § 4.6, BR-V8-29/30): the counts,
 * the NPCs and seeds a rebuild carried to the new regions (V7), the open sessions a replace
 * could not close (V6), and the warnings by stage in words — each stage folds the server's own
 * lines. "Known nowhere N" opens that tab (UX-22); with none, or where there is no tab to
 * open (the home), it is not shown. */
export function BuildReportPanel({
  report,
  onShowUnscoped,
}: {
  report: BuildReport;
  onShowUnscoped?: () => void;
}) {
  const unscoped = report.unscoped_knowledge_ids.length;
  const npcs = report.carried_npcs ?? 0;
  const seeds = report.carried_seeds ?? 0;
  const stuck = sessionsNotClosed(report.warnings);
  const groups = groupByStage(report.warnings.filter((w) => w.stage !== "sessions"));
  return (
    <Card data-testid="build-report" className="flex flex-col gap-1 text-sm">
      <strong className={report.ok ? "" : "text-danger"} data-testid="build-report-head">
        {t("build.report.title")}: {report.ok ? t("build.report.ok") : t("build.report.failed")}
      </strong>
      <div>
        {t("build.report.counts", {
          regions: report.regions_created,
          connections: report.connections_created,
          entities: report.entities_created,
          knowledge: report.knowledge_created,
          corroborations: report.corroborations_created,
          priors: report.priors_created ?? 0,
        })}
      </div>
      {(npcs > 0 || seeds > 0) && (
        <div data-testid="build-report-carried">{t("notice.buildCarried", { npcs, seeds })}</div>
      )}
      {unscoped > 0 && onShowUnscoped && (
        <div>
          <Button size="sm" data-testid="build-report-unscoped" onClick={onShowUnscoped}>
            {t("action.showUnscoped", { n: unscoped })}
          </Button>
        </div>
      )}
      <div className="text-xs text-muted">
        {t("build.report.calls", { llm: report.llm_calls, embedding: report.embedding_calls })}
      </div>
      {report.replaced && (
        <div className="text-xs">{t("build.report.replaced", { n: report.closed_session_ids.length })}</div>
      )}
      {stuck > 0 && (
        <div className="text-xs text-danger" data-testid="build-report-sessions">{t("notice.sessionsNotClosed", { n: stuck })}</div>
      )}
      {report.backup_path && (
        <div className="break-all text-xs">{t("build.report.backup", { path: report.backup_path })}</div>
      )}
      {groups.map((g) => (
        <details key={`${g.severity}:${g.stage}`} data-testid={`build-report-stage-${g.stage}`}
          className={`text-xs ${g.severity === "error" ? "text-danger" : "text-muted"}`}>
          <summary className="cursor-pointer">{t("label.stageCount", { stage: g.label, n: g.warnings.length })}</summary>
          <ul className="list-disc break-words pl-4">
            {g.warnings.map((w, i) => <li key={i}>{w.message}</li>)}
          </ul>
        </details>
      ))}
    </Card>
  );
}
