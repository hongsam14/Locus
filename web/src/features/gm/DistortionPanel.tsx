import { t } from "../../i18n";
import { CommitRange } from "../../ui";

/** The selected region's distortion. The slider saves on mouse, touch, keyboard or blur
 * (BR-U7-24); the feedback share — what strong rumors added — shows when there is one. */
export function DistortionPanel({
  regionName,
  value,
  share,
  closed,
  onCommit,
}: {
  regionName: string;
  value: number;
  share: number;
  closed: boolean;
  onCommit: (v: number) => Promise<boolean> | boolean | void;
}) {
  return (
    <>
      <div className="text-xs text-ink-soft">
        {t("gm.region")} {regionName}
      </div>
      <label className="text-xs flex items-center gap-2">
        {t("gm.distortion")} {value.toFixed(2)}
        <CommitRange
          data-testid="distortion-slider"
          min={0}
          max={1}
          step={0.05}
          value={value}
          disabled={closed}
          onCommit={onCommit}
        />
      </label>
      {share > 0 && (
        <div data-testid="distortion-feedback" className="text-xs text-ink-soft">
          {t("gm.feedbackShare", { share: share.toFixed(2) })}
        </div>
      )}
    </>
  );
}
