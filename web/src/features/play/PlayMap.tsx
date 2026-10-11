import { useMemo } from "react";
import { t } from "../../i18n";
import { WorldMap } from "../../map";
import type { ConnectionEdge, Region, RegionView } from "../../types";
import { english, type NameOf } from "./names";

/** The small map of the play screen (V4 Q4=A, BR-V4-14): a close-up of where the player is
 * and where they can go, names from the map. It is for looking only — pressing a region
 * moves no one; pressing a reachable one points at its row in the move list
 * (`onPickReachable`; a phone opens the move sheet there). `regions` null = the world's
 * map is still on its way. */
export function PlayMap({
  view,
  regions,
  connections,
  nameOf = english,
  background = null,
  onPickReachable,
}: {
  view: RegionView;
  regions: Region[] | null;
  connections: ConnectionEdge[];
  nameOf?: NameOf;
  background?: string | null;
  onPickReachable: (regionId: string) => void;
}) {
  const named = useMemo(
    () => (regions ?? []).map((r) => ({ ...r, name: nameOf("regions", r.id, "name", r.name) })),
    [regions, nameOf],
  );
  const neighbors = view.moves.map((m) => m.region_id).join("|");
  const reachable = view.moves.filter((m) => m.passable).map((m) => m.region_id);
  const reachableKey = reachable.join("|");
  // one object per place and set of ways out, so the map does not refit on every render
  const focus = useMemo(() => ({ id: view.region_id, neighbors: neighbors ? neighbors.split("|") : [] }),
    [view.region_id, neighbors]);
  const reachableIds = useMemo(() => (reachableKey ? reachableKey.split("|") : []), [reachableKey]);
  return (
    <section data-testid="play-map" aria-label={t("label.map")}>
      {regions === null ? (
        <div role="status" aria-label={t("label.loading")} className="aspect-[16/10] w-full rounded-lg bg-sunken" />
      ) : (
        <WorldMap
          mode="play"
          label={t("label.map")}
          regions={named}
          connections={connections}
          playerRegionId={view.region_id}
          reachableIds={reachableIds}
          focus={focus}
          background={background}
          onSelect={(id) => {
            if (reachableIds.includes(id)) onPickReachable(id);
          }}
        />
      )}
    </section>
  );
}
