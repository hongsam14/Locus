import { useState, type ReactNode } from "react";
import { t } from "../../i18n";
import { Button } from "../../ui";

/** A list that shows its first `limit` items and a [show N more] (V4 § 1.2: three pieces of
 * knowledge, five log lines on a phone). No limit = all of them, no button. */
export function MoreList<T>({
  items,
  limit,
  render,
  className = "",
  testId,
}: {
  items: readonly T[];
  limit?: number;
  render: (item: T) => ReactNode;
  className?: string;
  testId?: string;
}) {
  const [all, setAll] = useState(false);
  const shown = limit != null && !all ? items.slice(0, limit) : items;
  const rest = items.length - shown.length;
  return (
    <>
      <ul className={className} data-testid={testId}>{shown.map(render)}</ul>
      {rest > 0 && (
        <Button size="sm" variant="ghost" className="self-start" onClick={() => setAll(true)}>
          {t("action.showMore", { n: rest })}
        </Button>
      )}
    </>
  );
}
