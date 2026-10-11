import { Link } from "react-router-dom";
import { enumLabel, turnLabel } from "../../format";
import { t } from "../../i18n";
import type { RegionView } from "../../types";
import { english, type NameOf } from "./names";

/** [home] as a link: a closed session and an empty `/play` lead back to the demo cards. */
export function HomeLink() {
  return (
    <Link to="/" data-testid="play-home-link"
      className="inline-flex min-h-11 items-center rounded-md border border-line-strong bg-surface px-4 text-fg hover:bg-bg sm:min-h-9">
      {t("action.goHome")}
    </Link>
  );
}

/** The top of the play screen (V4 frontend-components § 3.3): where the region sits, its
 * name, level and the turn; a closed session's line with [home]; the GM-at-work notice.
 * `level_path` runs from the top ancestor down to the region itself, so the path above the
 * title is all but its last step. Names come from the name map by id (BLM § 2.7). */
export function PlayHeader({
  view,
  closed,
  nameOf = english,
}: {
  view: RegionView;
  closed: boolean;
  nameOf?: NameOf;
}) {
  const ids = view.level_path_ids ?? [];
  const above = view.level_path
    .map((name, i) => (ids[i] ? nameOf("regions", ids[i], "name", name) : name))
    .slice(0, -1);
  return (
    <header className="flex flex-col gap-1.5">
      {above.length > 0 && (
        <p className="text-xs text-muted" data-testid="region-path">{above.join(" › ")}</p>
      )}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h1 className="font-heading text-2xl text-balance sm:text-3xl" data-testid="region-title">
          {nameOf("regions", view.region_id, "name", view.region_name)}
        </h1>
        <span className="text-sm text-muted" data-testid="region-meta">
          {enumLabel("regionLevel", view.level)} · {turnLabel(view.turn)}
        </span>
      </div>
      {closed && (
        <div role="status" data-testid="closed-banner"
          className="flex flex-wrap items-center gap-3 rounded-lg border border-line-strong bg-sunken px-3 py-2 text-sm">
          <span className="flex-1">{t("notice.sessionClosed")}</span>
          <HomeLink />
        </div>
      )}
      {!closed && view.gm_busy && (
        <p role="status" data-testid="gm-busy-notice"
          className="rounded-lg border border-tint-info-line bg-tint-info px-3 py-2 text-sm text-info">
          {t("notice.gmBusy")}
        </p>
      )}
    </header>
  );
}
