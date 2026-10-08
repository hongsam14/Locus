import { useNavigate } from "react-router-dom";
import { turnLabel } from "../../format";
import { t } from "../../i18n";
import { Button, InlineError } from "../../ui";
import type { GmRes, PlayerRead } from "./useGmData";

/** Where the player stands, seen from the GM screen (US-5.1, BR-U7-21/22; V6 BLM § 2): name,
 * region, turn and whether a turn is running — with [check again] then — and the way back to
 * play. A GM session without a player shows nothing. It shows the session's own read
 * (`useGmData.player`): an answer for another session never lands here (#14), and a failed
 * re-read keeps the last player and says so. */
export function PlayerStrip({
  sessionId,
  turn,
  player,
  regionName,
}: {
  sessionId: string;
  turn: number;
  player: GmRes<PlayerRead>;
  /** A region by name: the display language's, else the world's English (V4 BR-V4-11). */
  regionName(regionId: string): string;
}) {
  const navigate = useNavigate();
  const found = player.data?.player ?? null;
  if (!found) {
    return player.error ? (
      <div data-testid="gm-player-error"><InlineError error={player.error} onRetry={player.reload} /></div>
    ) : null;
  }
  const running = (player.data?.running.length ?? 0) > 0;
  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      <span data-testid="gm-player-status">
        {found.name} · {regionName(found.region_id)} · {turnLabel(turn)}
        {running ? ` · ${t("label.turnRunning")}` : ""}
      </span>
      {running && (
        <Button size="sm" data-testid="gm-player-recheck" onClick={player.reload}>
          {t("action.recheck")}
        </Button>
      )}
      {player.error && <span className="text-xs text-danger" data-testid="gm-player-error">{player.error.title}</span>}
      <Button size="sm" className="ml-auto" data-testid="gm-back-to-play"
        onClick={() => navigate(`/play/${encodeURIComponent(sessionId)}`)}>
        {t("gm.backToPlay")}
      </Button>
    </div>
  );
}
