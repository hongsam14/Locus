"""DeedService — what the player did and what the NPCs made of it (U6 P16; BLM §1, §5).

Records deeds and appraisals (FD deviation 13); the turn engine also marks an appraisal
seeded and undoes a failed run's deeds, through this service's store (U3, U7 review §5:
"the one place" was too strong). Reads that other
services need — the current stay, the deeds an NPC has yet to judge, the appraisals
ready to seed a rumor, an NPC's memories, the recent deeds for event suggestion and the
GM's view — live here too, so the stay rule (BR-U6-4) has one definition.
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.play.base import SessionAppService, names_of, region_name
from locus.play.errors import AppraisalExistsError
from locus.play.models import (
    AppraisalOutcome,
    Deed,
    DeedAppraisal,
    DeedKind,
    DeedMemory,
    DeedView,
    GameSession,
    Narration,
    Player,
    TimelineKind,
    TurnRun,
    VoidResult,
)
from locus.play.player import movement
from locus.play.ports import PlayRepository, PlayUnitOfWork
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import NPC, Region, WorldSnapshot


class DeedService(SessionAppService):
    def __init__(self, repo: PlayRepository, snapshots: SnapshotSource, *, tuning: PlayTuning):
        super().__init__(repo)
        self._snapshots = snapshots
        self._tuning = tuning

    # -- writes -------------------------------------------------------------
    def arrival(
        self,
        u: PlayUnitOfWork,
        session: GameSession,
        player: Player,
        region: Region,
        snapshot: WorldSnapshot,
        *,
        run_id: str | None = None,
    ) -> Deed:
        """Record an arrival inside the caller's unit of work (session start, a move)."""
        return u.deeds.record_deed(
            Deed(
                session_id=session.id,
                player_id=player.id,
                region_id=region.id,
                turn=session.turn,
                kind=DeedKind.ARRIVAL,
                text=f"{player.name} arrived in {region.name}.",
                witnessed_npc_ids=[n.id for n in movement.npcs_here(snapshot, region.id)],
                run_id=run_id,
            )
        )

    def record_declaration(
        self,
        run: TurnRun,
        session: GameSession,
        player: Player,
        region: Region,
        witnesses: list[NPC],
        narration: Narration,
        declaration: str,
    ) -> Deed:
        """The declared action as a deed + ``ACTION_DECLARED`` (one unit of work)."""
        with self._repo.uow() as u:
            deed = u.deeds.record_deed(
                Deed(
                    session_id=session.id,
                    player_id=player.id,
                    region_id=region.id,
                    turn=session.turn,
                    kind=DeedKind.DECLARED_ACTION,
                    text=narration.record,
                    declaration=declaration,
                    witnessed_npc_ids=[n.id for n in witnesses],
                    run_id=run.id,
                )
            )
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.ACTION_DECLARED,
                    f"{player.name}: {narration.record}",
                    {
                        "deed_id": deed.id,
                        "region_id": region.id,
                        "region_name": region.name,
                        "narration": narration.text,
                        "lang": narration.lang,
                        "record": narration.record,
                    },
                )
            )
        return deed

    def record_appraisal(
        self,
        run: TurnRun,
        session: GameSession,
        player: Player,
        region: Region,
        npc: NPC,
        outcome: AppraisalOutcome,
    ) -> list[DeedAppraisal]:
        """The talk's statement deed (when there is one) and the NPC's appraisals, with
        their timeline entries, in one unit of work. A repeated (deed, npc) pair can only
        come from a write outside the turn guard; it is dropped and the rest is saved."""
        try:
            return self._store_appraisal(run, session, player, region, npc, outcome)
        except AppraisalExistsError:
            judged = {
                a.deed_id
                for a in self._repo.list_appraisals(
                    session.id, deed_ids=[a.deed_id for a in outcome.appraisals], npc_id=npc.id
                )
            }
            fresh = [a for a in outcome.appraisals if a.deed_id not in judged]
            return self._store_appraisal(
                run, session, player, region, npc, outcome.model_copy(update={"appraisals": fresh})
            )

    def _store_appraisal(
        self,
        run: TurnRun,
        session: GameSession,
        player: Player,
        region: Region,
        npc: NPC,
        outcome: AppraisalOutcome,
    ) -> list[DeedAppraisal]:
        names = {"npc_id": npc.id, "npc_name": npc.name}
        where = {"region_id": region.id, "region_name": region.name}
        with self._repo.uow() as u:
            # stamped with the run, so a run that never advances takes them back (#4)
            appraisals = [a.model_copy(update={"run_id": run.id}) for a in outcome.appraisals]
            if outcome.statement_text is not None:
                statement = u.deeds.record_deed(
                    Deed(
                        session_id=session.id,
                        player_id=player.id,
                        region_id=region.id,
                        turn=session.turn,
                        kind=DeedKind.STATEMENT,
                        text=outcome.statement_text,
                        witnessed_npc_ids=[npc.id],
                        messages_through=outcome.messages_through,
                        run_id=run.id,
                    )
                )
                u.timeline.append_timeline(
                    self._entry(
                        session,
                        TimelineKind.DEED_RECORDED,
                        f"{player.name} told {npc.name}: {statement.text}",
                        {
                            "deed_id": statement.id,
                            "kind": DeedKind.STATEMENT.value,
                            **names,
                            **where,
                        },
                    )
                )
                if outcome.statement_appraisal is not None:
                    appraisals.append(
                        outcome.statement_appraisal.model_copy(
                            update={"deed_id": statement.id, "run_id": run.id}
                        )
                    )
            saved = u.deeds.save_appraisals(appraisals) if appraisals else []
            for a in saved:
                u.timeline.append_timeline(
                    self._entry(
                        session,
                        TimelineKind.DEED_APPRAISED,
                        f"{npc.name} judged a deed ({'tell' if a.noteworthy else 'keep'})",
                        {
                            "deed_id": a.deed_id,
                            "appraisal_id": a.id,
                            "noteworthy": a.noteworthy,
                            "salience": a.salience,
                            **names,
                            **where,
                        },
                    )
                )
        return saved

    # -- reads --------------------------------------------------------------
    def current_stay(self, session_id: str, player: Player) -> list[Deed]:
        """Deeds of the player's present stay, not voided (BR-U6-4). The boundary is the
        latest arrival here **voided or not**, so voiding it never revives an old stay.
        A session from before U6 has no arrival: then every deed here counts."""
        here = self._repo.list_deeds(session_id, region_id=player.region_id, include_voided=True)
        start = max(  # the latest arrival here (U6 review C10)
            (i for i, d in enumerate(here) if d.kind == DeedKind.ARRIVAL.value), default=0
        )
        return [d for d in here[start:] if not d.voided]

    def pending_for(self, session_id: str, player: Player, npc_id: str) -> list[Deed]:
        """Stay deeds this NPC saw and has not judged — newest ``appraisal_max_deeds``
        of them, in time order; older ones stay pending (BR-U6-8)."""
        seen = [d for d in self.current_stay(session_id, player) if npc_id in d.witnessed_npc_ids]
        if not seen:
            return []
        judged = {
            a.deed_id
            for a in self._repo.list_appraisals(
                session_id, deed_ids=[d.id for d in seen], npc_id=npc_id
            )
        }
        pending = [d for d in seen if d.id not in judged]
        limit = self._tuning.appraisal_max_deeds
        return pending[-limit:] if limit else []

    def last_statement(self, session_id: str, npc_id: str) -> Deed | None:
        """The latest statement made to this NPC, voided or not — the summary cursor
        (BR-U6-6)."""
        # statements only, newest first; the listener filter is a JSON column, so it is
        # applied here (U6 review C2)
        said = self._repo.list_deeds(session_id, kind=DeedKind.STATEMENT.value, newest_first=True)
        return next((d for d in said if d.witnessed_npc_ids == [npc_id]), None)

    def seeds_ready(self, session_id: str) -> list[tuple[Deed, DeedAppraisal]]:
        """Appraisals that may seed a rumor now (BR-U6-12), oldest deed first."""
        # one store read with the BR-U6-12 filter (U6 review C2: was every deed and
        # appraisal of the session, every turn)
        return self._repo.seed_candidates(
            session_id, min_salience=self._tuning.deed_seed_min_salience
        )

    def memories(self, session_id: str, player: Player, npc_id: str) -> list[DeedMemory]:
        """What this NPC knows of the traveler (BR-U6-30): deeds it judged (its own
        retelling, or the deed text) and deeds of the present stay it saw but has not
        judged yet. Newest first, ``npc_max_deeds`` of them, never voided."""
        limit = self._tuning.npc_max_deeds
        if not limit:
            return []
        judged_by_me = self._repo.list_appraisals(session_id, npc_id=npc_id)
        deeds = {
            d.id: d
            for d in self._repo.list_deeds(
                session_id,
                include_voided=False,
                deed_ids=sorted({a.deed_id for a in judged_by_me}),
            )
        }
        mine = [a for a in judged_by_me if a.deed_id in deeds]
        out = [
            (
                deeds[a.deed_id],
                DeedMemory(
                    deed_id=a.deed_id, text=a.retelling or deeds[a.deed_id].text, slant=a.slant
                ),
            )
            for a in mine
        ]
        judged = {a.deed_id for a in mine}
        for d in self.current_stay(session_id, player):
            if npc_id in d.witnessed_npc_ids and d.id not in judged:
                out.append((d, DeedMemory(deed_id=d.id, text=d.text)))
        out.sort(key=lambda pair: (pair[0].created_at or 0, pair[0].id), reverse=True)
        return [m for _deed, m in out[:limit]]

    def recent(self, session_id: str, n: int = 5) -> list[tuple[Deed, list[DeedAppraisal]]]:
        """The latest ``n`` deeds that were not voided, newest first (event suggestion)."""
        deeds = self._repo.list_deeds(session_id, include_voided=False, newest_first=True, limit=n)
        by_deed: dict[str, list[DeedAppraisal]] = {d.id: [] for d in deeds}
        if deeds:
            for a in self._repo.list_appraisals(session_id, deed_ids=list(by_deed)):
                by_deed[a.deed_id].append(a)
        return [(d, by_deed[d.id]) for d in deeds]

    def views(self, session_id: str) -> list[DeedView]:
        """Every deed for the GM, newest first, with its appraisals and rumors."""
        self._require_session(session_id)
        deeds = self._repo.list_deeds(session_id)[::-1]
        appraisals: dict[str, list[DeedAppraisal]] = {}
        for a in self._repo.list_appraisals(session_id):
            appraisals.setdefault(a.deed_id, []).append(a)
        rumors: dict[str, list] = {}
        for r in self._repo.list_rumors_by_origin(session_id, include_inactive=True):
            rumors.setdefault(r.origin_deed_id or "", []).append(r)
        return [
            DeedView(
                deed=d,
                appraisals=appraisals.get(d.id, []),
                rumors=rumors.get(d.id, []),
                reached_region_ids=sorted({r.region_id for r in rumors.get(d.id, [])}),
            )
            for d in deeds
        ]

    def names(self, session_id: str) -> tuple[dict[str, str], dict[str, str]]:
        """Region and NPC names of the session's world, for the GM view."""
        session = self._require_session(session_id)
        snapshot = self._snapshots.get(session.world_id)
        return (
            {r.id: r.name for r in snapshot.topo.regions},
            {n.id: n.name for n in snapshot.npcs},
        )

    def void(self, session_id: str, deed_id: str) -> VoidResult:
        """Undo a deed (BR-U6-27). The router holds the GM write lease (`_idle`) from
        here to the commit, so no turn can seed or spread it meanwhile (BR-U6-28)."""
        session = self._require_open(session_id)
        deed = self._repo.get_deed(session_id, deed_id)
        if deed is None:
            raise LookupError(f"deed not found: {deed_id}")
        if deed.voided:
            return VoidResult(deed_id=deed_id)
        names = names_of(self._snapshots.get(session.world_id))  # read before the UoW
        with self._repo.uow() as u:
            deed.voided = True
            deed.voided_turn = session.turn
            u.deeds.update_deed(deed)
            rumors = u.rumors.list_rumors_by_origin(session_id, deed_id=deed_id)
            for r in rumors:
                r.active = False
            if rumors:
                u.rumors.upsert_rumors(rumors)
            regions = sorted({r.region_id for r in rumors})  # names too (U7 review §3)
            u.timeline.append_timeline(
                self._entry(
                    session,
                    TimelineKind.DEED_VOIDED,
                    f"voided deed {deed_id}",
                    {
                        "deed_id": deed_id,
                        "rumor_ids": [r.id for r in rumors],
                        "region_ids": regions,
                        "region_names": [region_name(names, rid) for rid in regions],
                    },
                )
            )
        return VoidResult(deed_id=deed_id, deactivated_rumor_ids=[r.id for r in rumors])
