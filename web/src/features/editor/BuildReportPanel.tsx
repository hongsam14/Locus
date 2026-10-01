import { t } from "../../i18n";
import type { BuildReport } from "../../types";
import { Card } from "../../ui";

/** What a build did (US-2.1, BR-U3-35), as the server reported it. */
export function BuildReportPanel({
  report,
  onShowUnscoped,
}: {
  report: BuildReport;
  onShowUnscoped?: () => void;
}) {
  const errors = report.warnings.filter((w) => w.severity === "error");
  const warnings = report.warnings.filter((w) => w.severity !== "error");
  return (
    <Card data-testid="build-report" className="text-sm flex flex-col gap-1">
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
      <button type="button" className="text-left underline" onClick={onShowUnscoped}
        data-testid="build-report-unscoped">
        {t("build.report.unscoped", { n: report.unscoped_knowledge_ids.length })}
      </button>
      <div className="text-xs text-ink-soft">
        {t("build.report.calls", { llm: report.llm_calls, embedding: report.embedding_calls })}
      </div>
      {report.replaced && (
        <div className="text-xs">{t("build.report.replaced", { n: report.closed_session_ids.length })}</div>
      )}
      {report.backup_path && (
        <div className="text-xs">{t("build.report.backup", { path: report.backup_path })}</div>
      )}
      {[...errors, ...warnings].map((w, i) => (
        <div key={i} className={`text-xs ${w.severity === "error" ? "text-danger" : "text-ink-soft"}`}>
          [{w.stage}] {w.message}
        </div>
      ))}
    </Card>
  );
}
