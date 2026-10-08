import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { ActionBar, type Held } from "../features/play/ActionBar";
import { ActionDock } from "../features/play/ActionDock";
import { DialoguePanel } from "../features/play/DialoguePanel";
import { MovePanel } from "../features/play/MovePanel";
import { HomeLink, PlayHeader } from "../features/play/PlayHeader";
import { PlayLayout } from "../features/play/PlayLayout";
import { PlayLog } from "../features/play/PlayLog";
import { PlayMap } from "../features/play/PlayMap";
import { KnownHere, PeopleHere, SceneText } from "../features/play/RegionScene";
import { ResultBand } from "../features/play/ResultBand";
import { TalkSheet } from "../features/play/TalkSheet";
import {
  NARROW,
  WIDE,
  useHeldRereads,
  useMedia,
  usePlaySession,
  useResource,
  useTurnRun,
  useWorldNames,
} from "../hooks";
import { t, useLang } from "../i18n";
import { AppShell } from "../layout";
import { InlineError, StatusView } from "../ui";

interface Talk {
  sessionId: string;
  regionId: string;
  npcId: string;
}

/** The talk a history entry carries (BLM § 2.5, R-11): ours only when it names this session
 * and place — anything else in `state` is ignored, never acted on. */
function talkOf(state: unknown): Talk | null {
  const talk = (state as { talk?: Partial<Talk> } | null)?.talk;
  return talk && typeof talk.sessionId === "string" && typeof talk.regionId === "string" && typeof talk.npcId === "string"
    ? (talk as Talk)
    : null;
}

type Knobs = { pollMs?: number; maxPolls?: number; heldRetryMs?: number };

/** `/play/:sessionId` (V4 FR-S2, BLM § 2): one session's screen, put together from the play
 * parts. Without a session it says so and points home. One screen per session (`key`): the
 * talk, the pointed-at row and the talked-to counts never carry over to another. */
export function PlayPage(knobs: Knobs) {
  const { sessionId = "" } = useParams();
  useLang(); // labels follow the display language
  if (!sessionId) {
    return (
      <AppShell>
        <div data-testid="play-page" className="mx-auto w-full max-w-[1240px] break-keep px-4 pt-6 [overflow-wrap:break-word]">
          <section data-testid="play-empty" className="flex max-w-xl flex-col items-start gap-3">
            <h1 className="font-heading text-2xl">{t("empty.noSession")}</h1>
            <p className="text-muted">{t("hint.startFromDemo")}</p>
            <HomeLink />
          </section>
        </div>
      </AppShell>
    );
  }
  return <PlayScreen key={sessionId} sessionId={sessionId} {...knobs} />;
}

function PlayScreen({ sessionId, pollMs = 700, maxPolls = 120, heldRetryMs = 1000 }: Knobs & { sessionId: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const wide = useMedia(WIDE);
  const narrow = useMedia(NARROW);
  const play = usePlaySession(sessionId);
  const { session, view } = play;
  const worldId = session?.world_id ?? null;
  const regionId = view?.region_id ?? null;
  const { nameOf } = useWorldNames(worldId);
  // the small map's regions and ways, once per world (BLM § 2.1)
  const world = useResource(worldId ? ["map", worldId] : null, () => api.exportWorld(worldId as string));
  const turn = useTurnRun(sessionId, { reload: play.reload, pollMs, maxPolls });
  // held with no run of ours: a GM write or an editor lease; read again 1 s × 5, then offer
  // [check again] (BR-V4-19, code review 01 #1). The header says gm_busy itself.
  const heldNow = !!view && (view.turn_running || !!view.gm_busy) && !turn.running;
  const heldReads = useHeldRereads(heldNow, play.reload, heldRetryMs, 5, play.pending);
  const held: Held = !heldNow ? null : heldReads.stuck ? "stuck" : view?.gm_busy ? null : "waiting";
  const closed = session?.status === "closed";
  const locked = turn.running != null || turn.acting || !!view?.turn_running || !!view?.gm_busy;

  // talked-to counts (U5): read per place, best effort; a spoken line adds two (U5 C1)
  const npcs = useResource(regionId ? ["npcs", sessionId, regionId] : null, () => api.listNpcs(sessionId));
  const [spoken, setSpoken] = useState<Record<string, number>>({});
  useEffect(() => setSpoken({}), [npcs.data]);
  const counts = useMemo(() => {
    const base: Record<string, number> = {};
    for (const n of Array.isArray(npcs.data) ? npcs.data : []) base[n.npc.id] = n.message_count;
    for (const [id, n] of Object.entries(spoken)) base[id] = (base[id] ?? 0) + n;
    return base;
  }, [npcs.data, spoken]);

  // the talk (Q5=A, BLM § 2.5): wide = screen state, no history; narrower = the router's
  // history entry, so back closes the sheet and stays on the page
  const [columnTalk, setColumnTalk] = useState<string | null>(null);
  const stateTalk = talkOf(location.state);
  const sheetTalk =
    stateTalk && stateTalk.sessionId === sessionId && stateTalk.regionId === regionId ? stateTalk.npcId : null;
  const talkNpc = view?.npcs.find((n) => n.id === (wide ? columnTalk : sheetTalk)) ?? null;
  const here = `${location.pathname}${location.search}`;
  const pushed = useRef(false); // this screen pushed the talk entry: closing pops it
  const now = useRef({ here, stateTalk, sheetTalk, columnTalk, regionId });
  now.current = { here, stateTalk, sheetTalk, columnTalk, regionId };

  function openTalk(npcId: string) {
    if (!regionId) return;
    if (wide) setColumnTalk(npcId);
    else {
      pushed.current = true;
      navigate(here, { state: { talk: { sessionId, regionId, npcId } } });
    }
  }
  function closeTalk() {
    if (wide) setColumnTalk(null);
    else if (stateTalk) {
      // an entry this screen did not push (a restored tab) is cleared in place, so the
      // close never leaves the page
      if (pushed.current) navigate(-1);
      else navigate(here, { replace: true, state: null });
      pushed.current = false;
    }
  }

  // moving closes the talk (U5 #8) and forgets the pointed-at row
  const [highlight, setHighlight] = useState<string | null>(null);
  const [moveOpen, setMoveOpen] = useState(false);
  const lastRegion = useRef(regionId);
  useEffect(() => {
    const prev = lastRegion.current;
    lastRegion.current = regionId;
    if (prev === null || prev === regionId) return;
    setColumnTalk(null);
    setHighlight(null);
    if (now.current.stateTalk) {
      navigate(now.current.here, { replace: true, state: null });
      pushed.current = false;
    }
  }, [regionId, navigate]);

  // a width change carries an open talk across: sheet → column, column → sheet
  const lastWide = useRef(wide);
  useEffect(() => {
    if (lastWide.current === wide) return;
    lastWide.current = wide;
    const { here: at, sheetTalk: sheet, columnTalk: column, regionId: rid } = now.current;
    if (wide && sheet) {
      setColumnTalk(sheet);
      navigate(at, { replace: true, state: null });
      pushed.current = false;
    } else if (!wide && column && rid) {
      setColumnTalk(null);
      pushed.current = true;
      navigate(at, { state: { talk: { sessionId, regionId: rid, npcId: column } } });
    }
  }, [wide, navigate, sessionId]);

  async function endTalk(npcId: string) {
    closeTalk();
    await turn.act({ type: "end_talk", npc_id: npcId }); // the judgment lands in the result band
  }
  const move = (id: string) => void turn.act({ type: "move", to_region_id: id });

  let body;
  if (play.state === "loading") body = <StatusView state="loading" skeleton="cards" />;
  else if (!view || !session) {
    body = (
      <div data-testid="play-error">
        <InlineError error={play.error ?? { title: t("error.unknown.title") }} onRetry={play.reload} />
      </div>
    );
  } else {
    const actionProps = {
      running: turn.running,
      slow: turn.slow,
      error: turn.error,
      refusal: turn.refusal,
      onRecheck: turn.recheck,
      held,
      onHeldRecheck: heldReads.retry,
      disabled: closed,
      locked,
      closed,
      maxChars: view.declare_max_chars ?? 300,
      onWait: () => void turn.act({ type: "wait" }),
      onDeclare: (text: string) => turn.act({ type: "declare", text }),
    };
    const dialogue = talkNpc && (
      <DialoguePanel
        key={talkNpc.id}
        sessionId={sessionId}
        npc={talkNpc}
        nameOf={nameOf}
        bare={!wide}
        llmAvailable={view.llm_available}
        busy={locked}
        readOnly={closed}
        onClose={closeTalk}
        onEndTalk={() => void endTalk(talkNpc.id)}
        onSpoke={() => setSpoken((c) => ({ ...c, [talkNpc.id]: (c[talkNpc.id] ?? 0) + 2 }))}
        onClosed={play.reload}
      />
    );
    body = (
      <>
        {play.error && (
          <div data-testid="play-error">
            <InlineError error={play.error} onRetry={play.reload} />
          </div>
        )}
        <PlayLayout
          wide={wide}
          narrow={narrow}
          s={{
            header: <PlayHeader view={view} closed={closed} nameOf={nameOf} />,
            result: <ResultBand outcome={turn.outcome} nameOf={nameOf} onClose={turn.clearOutcome} />,
            scene: <SceneText view={view} nameOf={nameOf} />,
            actions: !narrow && <ActionBar {...actionProps} />,
            dock: narrow && (
              <ActionDock {...actionProps} onClearRefusal={turn.clearRefusal} moves={view.moves} nameOf={nameOf}
                onMove={move} moveOpen={moveOpen}
                onMoveOpenChange={setMoveOpen} highlightId={highlight} />
            ),
            map: world.state === "error" && !world.data ? null : (
              <PlayMap view={view} regions={world.data?.regions ?? null} connections={world.data?.connections ?? []}
                nameOf={nameOf}
                onPickReachable={(id) => {
                  setHighlight(id);
                  if (narrow) setMoveOpen(true);
                }} />
            ),
            moves: !narrow && (
              <MovePanel moves={view.moves} disabled={closed} locked={locked} onMove={move} nameOf={nameOf}
                highlightId={highlight} />
            ),
            people: wide && dialogue ? dialogue : (
              <PeopleHere view={view} nameOf={nameOf} counts={counts} activeNpcId={talkNpc?.id ?? null}
                talkOff={view.llm_available ? null : t("notice.talkNeedsKey")} onTalk={openTalk} />
            ),
            knowledge: <KnownHere view={view} compact={narrow} />,
            log: <PlayLog entries={play.log} nameOf={nameOf} compact={narrow} />,
          }}
        />
        {!wide && (
          <TalkSheet npc={talkNpc} nameOf={nameOf} onClose={closeTalk}>
            {dialogue}
          </TalkSheet>
        )}
      </>
    );
  }

  return (
    <AppShell sessionId={sessionId} worldId={worldId} llmOff={view ? !view.llm_available : false}>
      {/* Korean breaks between words, not inside one; a long unbroken token still wraps */}
      <div data-testid="play-page" className="mx-auto w-full max-w-[1240px] break-keep px-4 pb-12 pt-4 [overflow-wrap:break-word]">
        {body}
      </div>
    </AppShell>
  );
}
