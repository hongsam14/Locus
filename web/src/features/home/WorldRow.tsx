import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { describeError, type DescribedError } from "../../errors";
import { formatDate } from "../../format";
import { t } from "../../i18n";
import type { WorldInfo } from "../../types";
import { Badge, Button, Card, InlineError } from "../../ui";
import { openLatestFirst } from "./sessions";

/** One of the designer's worlds (BLM § 1.3): its name in the display language, regions, last
 * edit, and its open sessions as a neutral badge (UX-14). [continue] reads the sessions only
 * when pressed and goes to the latest open one; a failed read is a line in the row. */
export function WorldRow({
  world,
  busy,
  onStart,
  onStale,
}: {
  world: WorldInfo;
  busy: boolean;
  onStart: (worldId: string) => void;
  onStale: () => void;
}) {
  const navigate = useNavigate();
  const [going, setGoing] = useState(false);
  const [error, setError] = useState<DescribedError | null>(null);
  const id = world.id;
  const openCount = world.open_sessions ?? 0;

  async function resume() {
    setGoing(true);
    setError(null);
    try {
      const latest = openLatestFirst(await api.listSessions(id))[0];
      if (latest) navigate(`/play/${encodeURIComponent(latest.id)}`);
      else onStale(); // the list was behind: read it again, and the button goes
    } catch (e) {
      setError(describeError(e));
    } finally {
      setGoing(false);
    }
  }

  const facts = [
    t("home.regions", { n: world.region_count }),
    world.updated_at ? t("home.updated", { when: formatDate(world.updated_at) }) : null,
  ].filter(Boolean);
  return (
    <Card as="article" data-testid={`world-row-${id}`} className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <h3 className="font-heading text-lg">{world.name_ko || world.name}</h3>
          <code className="text-xs text-muted">{id}</code>
        </div>
        <span className="text-xs text-muted">{facts.join(" · ")}</span>
      </div>
      {openCount > 0 && <Badge className="self-start sm:self-auto" data-testid={`world-open-${id}`}>{t("label.openSessions", { n: openCount })}</Badge>}
      <div className="flex flex-wrap gap-2">
        {openCount > 0 && (
          <Button variant="primary" busy={going} data-testid={`world-continue-${id}`} onClick={resume}>
            {t("action.continue")}
          </Button>
        )}
        <Button variant={openCount > 0 ? "secondary" : "primary"} data-testid={`world-start-${id}`} disabled={busy}
          onClick={() => onStart(id)}>
          {t("action.newSession")}
        </Button>
        <Button variant="ghost" data-testid={`world-edit-${id}`} onClick={() => navigate(`/editor/${encodeURIComponent(id)}`)}>
          {t("home.edit")}
        </Button>
      </div>
      {error && (
        <div className="basis-full" data-testid={`world-error-${id}`}>
          <InlineError error={error} onRetry={resume} />
        </div>
      )}
    </Card>
  );
}
