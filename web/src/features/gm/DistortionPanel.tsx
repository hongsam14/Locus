import { useEffect, useState } from "react";
import { numberWithMeaning } from "../../format";
import { t } from "../../i18n";
import { CommitRange } from "../../ui";

/** The chosen region's distortion (V6 BR-V6-11/25): the number with its meaning, following
 * the thumb while it moves; saved on mouse, touch, keyboard or blur (BR-U7-24). The part that
 * strong rumors added shows when there is one. A refused save puts the thumb back. */
export function DistortionPanel({
  value,
  share,
  closed,
  onCommit,
}: {
  value: number;
  share: number;
  closed: boolean;
  onCommit: (v: number) => Promise<boolean> | boolean | void;
}) {
  const [shown, setShown] = useState(value);
  useEffect(() => setShown(value), [value]);
  return (
    <div className="flex flex-col gap-1 text-sm">
      <label className="flex flex-col gap-1">
        <span data-testid="distortion-label" className="font-bold">
          {t("label.distortion")} {numberWithMeaning("distortion", shown)}
        </span>
        <CommitRange
          data-testid="distortion-slider"
          min={0}
          max={1}
          step={0.05}
          value={value}
          disabled={closed}
          onCommit={onCommit}
          onDraft={setShown}
        />
      </label>
      {share > 0 && (
        <span data-testid="distortion-feedback" className="text-xs text-muted">
          {t("label.share")} {numberWithMeaning("share", share)}
        </span>
      )}
    </div>
  );
}
