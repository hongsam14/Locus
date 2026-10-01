import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api";
import { t } from "../../i18n";
import type { Player } from "../../types";
import { Button } from "../../ui";

/** Where the player stands, seen from the GM screen (US-5.1, BR-U7-21/22): name, region,
 * turn and whether a turn is running, with the way back to play. A GM session without a
 * player shows nothing. Re-read whenever `rev` changes. */
export function PlayerStrip({
  sessionId,
  turn,
  regionNames,
  rev,
  onPlayer,
}: {
  sessionId: string;
  turn: number;
  regionNames: Record<string, string>;
  rev: number;
  onPlayer?: (player: Player | null) => void;
}) {
  const navigate = useNavigate();
  const [player, setPlayer] = useState<Player | null>(null);
  const [running, setRunning] = useState(false);
  const seq = useRef(0);
  useEffect(() => {
    const mine = ++seq.current;
    Promise.all([
      Promise.resolve()
        .then(() => api.getPlayer(sessionId))
        .catch(() => null), // 404: a GM session without a player
      Promise.resolve()
        .then(() => api.listTurnRuns(sessionId, "running")) // FD review R-08
        .catch(() => []),
    ]).then(([p, runs]) => {
      if (mine !== seq.current) return;
      const found = p && typeof p === "object" && "region_id" in p ? (p as Player) : null;
      setPlayer(found);
      setRunning(Array.isArray(runs) && runs.length > 0);
      onPlayer?.(found);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- onPlayer is a notifier
  }, [sessionId, rev]);

  if (!player) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 px-3 py-1 text-sm">
      <span data-testid="gm-player-status">
        {t("gm.playerStatus", {
          name: player.name,
          region: regionNames[player.region_id] ?? player.region_id,
          turn,
        })}
        {running ? ` ${t("gm.running")}` : ""}
      </span>
      <Button
        size="sm"
        data-testid="gm-back-to-play"
        onClick={() => navigate(`/play/${encodeURIComponent(sessionId)}`)}
      >
        {t("gm.backToPlay")}
      </Button>
    </div>
  );
}
