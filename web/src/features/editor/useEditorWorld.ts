import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api";
import { describeError, type DescribedError } from "../../errors";
import { useResource } from "../../hooks";
import type { Norm } from "../../map/geometry";
import type { ConnectionEdge, Region, WorldExport, WorldInfo } from "../../types";
import { createDragSaves } from "./dragSaves";

export interface EditorWorld {
  world: WorldExport | undefined;
  /** The world on the map: the stored one with the dragged spots laid over it. */
  regions: Region[];
  state: "loading" | "ready" | "error";
  missing: boolean; // 404: no such world yet
  error?: DescribedError; // a failed read that is not a 404
  info: WorldInfo | null | undefined;
  selected: string | null;
  connection: ConnectionEdge | null;
  select(regionId: string | null): void;
  selectConnection(c: ConnectionEdge | null): void;
  /** A region was just made: pick it once a world read that started after it answers. */
  created(regionId: string): void;
  notFound: boolean; // the made region was not in the world read after it
  /** A load or a build replaced the world and its read has not answered yet: the map shows
   * the old world, so it is not dragged (code review 01 #2). */
  settling: boolean;
  move(regionId: string, pos: Norm): void;
  dragError?: DescribedError;
  reloadWorld(): void;
  reloadInfo(): void;
  retry(): void;
  /** A World File load or a build replaced the world (FD BLM § 1 item 4, plan § 1.4 R-02). */
  replaced(): void;
  /** A panel's read to repeat: the inspector after a drag save, every panel after a replace. */
  registerReload(panel: Panel, fn: () => void): () => void;
  reloadPanels(...panels: Panel[]): void;
}

export type Panel = "inspector" | "unscoped" | "wiki";

const same = (a: Norm | null | undefined, b: Norm) => a != null && a.x === b.x && a.y === b.y;

/** The editor's world, selection and drags (V8 BLM § 1–4, code plan § 1.1 R-16/R-17, § 1.4
 * R-02/R-04). The page holds it, so the panels can come and go.
 *
 * A region made by the add tool is picked only by a world read that STARTED after it was
 * made: each read carries the create mark it started under (R-04), so an older read landing
 * late never decides — this does not rest on when a reload aborts the read before it. */
export function useEditorWorld(worldId: string, opts: { onReplaced?(): void } = {}): EditorWorld {
  const createMark = useRef(0);
  // every world read this hook asks for; a drag is saved from a read that answered the last
  // one asked, never from a world a write has already changed (code review 01 #2)
  const wantSeq = useRef(0);
  const failedMark = useRef(-1); // the create mark of the last read that failed (review #25)
  const read = useResource(["editor-world", worldId], async () => {
    const mark = createMark.current;
    const seq = wantSeq.current;
    try {
      return { world: await api.exportWorld(worldId), mark, seq };
    } catch (e) {
      if ((e as { name?: unknown } | null)?.name !== "AbortError") failedMark.current = mark;
      throw e;
    }
  });
  const readRef = useRef(read);
  readRef.current = read;
  /** Read the world again; a drag waits for this read (#2). */
  const reloadWorld = useCallback(() => {
    wantSeq.current += 1;
    readRef.current.reload();
  }, []);
  const infoRead = useResource(["editor-world-info", worldId], async () => {
    const all = await api.listWorlds();
    return all.find((w) => w.id === worldId) ?? null;
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [connection, setConnection] = useState<ConnectionEdge | null>(null);
  const [pending, setPending] = useState<{ id: string; mark: number } | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [moved, setMoved] = useState<Record<string, Norm>>({});
  const [dragError, setDragError] = useState<DescribedError>();
  const [replaceSeq, setReplaceSeq] = useState(-1);
  const generation = useRef(0); // a replace or another world: drags from before it are not sent
  const waiters = useRef<Array<() => void>>([]);
  // the world read asked for last when each region's drag saves settled: a read asked after it
  // shows the server's spot, so the overlay goes even if the spots differ (code review 01 #8)
  const savedSeq = useRef(new Map<string, number>());
  const reloads = useRef(new Map<() => void, Panel>());
  const optsRef = useRef(opts);
  optsRef.current = opts;

  /** Repeat the panels' reads: the named ones, or all when none is named. */
  function reloadPanels(...panels: Panel[]) {
    for (const [fn, panel] of reloads.current) if (!panels.length || panels.includes(panel)) fn();
  }

  const world = read.data?.world;
  const worldRef = useRef(world);
  worldRef.current = world;
  const movedRef = useRef(moved);
  movedRef.current = moved;

  /** The last world read asked for has answered (or failed: the world on screen is used). A
   * reload keeps the state "ready"; "loading" with data is another world's read (#37). */
  const settled = () => {
    const r = readRef.current;
    return r.state === "error" || (r.state === "ready" && r.data != null && r.data.seq >= wantSeq.current);
  };
  useEffect(() => {
    if (!settled()) return;
    const ready = waiters.current;
    waiters.current = [];
    for (const go of ready) go();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [read.data, read.state]);
  const worldSettled = () => (settled() ? Promise.resolve() : new Promise<void>((go) => waiters.current.push(go)));

  const saves = useMemo(
    () =>
      createDragSaves({
        // the whole region goes, so it is taken from a read that answered every write before
        // the drag — a rename or an answer is not written back (code review 01 #2)
        save: (regionId, pos) => {
          const mine = generation.current;
          const send = () => {
            if (mine !== generation.current) return undefined; // a replace came first: not into the new world
            const region = worldRef.current?.regions.find((r) => r.id === regionId);
            return region ? api.updateRegion(worldId, { ...region, position: pos }) : undefined;
          };
          // sent at once when the world on screen is the last one asked for; else after it
          return settled() ? Promise.resolve(send()) : worldSettled().then(send);
        },
        // the inspector re-reads its region, so a save there never writes the old spot back
        onSaved: (regionId) => {
          savedSeq.current.set(regionId, wantSeq.current);
          reloadPanels("inspector");
        },
        onFailed: (regionId, err) => {
          savedSeq.current.set(regionId, wantSeq.current);
          setMoved(({ [regionId]: _gone, ...rest }) => rest);
          setDragError(describeError(err));
          reloadWorld();
        },
      }),
    // a new world gets its own queue
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [worldId],
  );

  // another world: nothing of the last one stays (FD BLM § 1 item 4, "world id changes")
  useEffect(() => {
    setSelected(null);
    setConnection(null);
    setPending(null);
    setNotFound(false);
    setMoved({});
    setDragError(undefined);
    savedSeq.current.clear();
    return () => {
      generation.current += 1;
      saves.clear();
    };
  }, [worldId, saves]);

  // a made region: decided by a read that started after it was made (R-04)
  useEffect(() => {
    if (!pending) return;
    if (read.state === "error") {
      // the read that started under this mark failed: stop waiting, the world's error shows.
      // An error left from an earlier read does not decide (code review 01 #25)
      if (failedMark.current >= pending.mark) setPending(null);
      return;
    }
    if (!read.data || read.data.mark < pending.mark) return;
    if (read.data.world.regions.some((r) => r.id === pending.id)) {
      setSelected(pending.id);
      setConnection(null);
    } else {
      setNotFound(true);
    }
    setPending(null);
  }, [read.data, read.state, pending]);

  // a region a load, a build or an edit removed is no longer selected — not while a made
  // region is still awaited (UX-25: that read is the one that decides)
  useEffect(() => {
    if (pending || !world) return;
    if (selected && !world.regions.some((r) => r.id === selected)) setSelected(null);
    if (connection && !world.connections.some((c) => sameEdge(c, connection))) setConnection(null);
  }, [world, pending, selected, connection]);

  // a dragged spot is dropped once no save of it is out or waiting, and the stored world holds
  // it — or the world was read again after its saves settled: then the stored spot is the
  // server's, whatever wrote it (an inspector save, another tab; code review 01 #8)
  const readSeqNow = read.data?.seq ?? -1;
  useEffect(() => {
    if (!world) return;
    setMoved((m) => {
      let changed = false;
      const next = { ...m };
      for (const [id, pos] of Object.entries(m)) {
        if (saves.busy(id)) continue;
        const stored = world.regions.find((r) => r.id === id)?.position;
        const after = savedSeq.current.get(id);
        if (same(stored, pos) || (after != null && readSeqNow > after)) {
          delete next[id];
          changed = true;
        }
      }
      return changed ? next : m;
    });
  }, [world, saves, readSeqNow]);

  const regions = useMemo(
    () => (world?.regions ?? []).map((r) => (moved[r.id] ? { ...r, position: moved[r.id] } : r)),
    [world, moved],
  );

  const select = useCallback((regionId: string | null) => {
    setPending(null); // the designer's own pick wins over an awaited one
    setNotFound(false);
    setSelected(regionId);
    setConnection(null);
  }, []);
  const selectConnection = useCallback((c: ConnectionEdge | null) => {
    setPending(null);
    setNotFound(false);
    setConnection(c);
    if (c) setSelected(c.source_region_id);
  }, []);
  const created = useCallback(
    (regionId: string) => {
      createMark.current += 1;
      setNotFound(false);
      setPending({ id: regionId, mark: createMark.current });
      reloadWorld(); // starts after the mark: its answer carries it
    },
    [reloadWorld],
  );
  const move = useCallback(
    (regionId: string, pos: Norm) => {
      setDragError(undefined);
      setMoved((m) => ({ ...m, [regionId]: pos }));
      saves.move(regionId, pos);
    },
    [saves],
  );

  const replaced = useCallback(() => {
    setPending(null);
    setNotFound(false);
    setConnection(null);
    setMoved({});
    setDragError(undefined);
    generation.current += 1;
    saves.clear();
    reloadWorld();
    setReplaceSeq(wantSeq.current); // no drag until this read answers (#2)
    infoRead.reload();
    reloadPanels(); // a selected region that stays reads its new content (R-02)
    optsRef.current.onReplaced?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [saves, reloadWorld, infoRead.reload]);
  const registerReload = useCallback((panel: Panel, fn: () => void) => {
    reloads.current.set(fn, panel);
    return () => {
      reloads.current.delete(fn);
    };
  }, []);

  const status = read.error?.status;
  return {
    world,
    regions,
    state: read.state,
    missing: read.state === "error" && status === 404,
    error: read.state === "error" && status !== 404 ? read.error : undefined,
    info: infoRead.state === "error" ? null : infoRead.data,
    selected,
    connection,
    select,
    selectConnection,
    created,
    notFound,
    settling: (replaceSeq > (read.data?.seq ?? -1) && read.state !== "error") || (read.state === "loading" && read.data != null),
    move,
    dragError,
    reloadWorld,
    reloadInfo: infoRead.reload,
    retry: () => {
      reloadWorld();
      infoRead.reload();
    },
    replaced,
    registerReload,
    reloadPanels,
  };
}

function sameEdge(a: ConnectionEdge, b: ConnectionEdge): boolean {
  return a.source_region_id === b.source_region_id && a.target_region_id === b.target_region_id && a.kind === b.kind;
}
