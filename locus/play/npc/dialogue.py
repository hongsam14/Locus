"""NpcDialogueService — talk to the people of the player's region (U5; FR-C4, US-4.1..4.3).

``start`` opens (or reopens) the one conversation a session has with an NPC — no LLM,
so the dialogue screen opens even without a provider. ``say`` builds the NPC's
bounded context from the NPC's own region (``region_sources`` + the pure
``build_context``), makes **exactly one** LLM call outside any transaction, and then
stores the player's line and the NPC's answer — creating the conversation if needed —
in **one** unit of work (BR-U5-3). The answer is generated directly in the display
language: no translation step (A-1).

Race: two first messages to the same NPC can both see "no conversation". The loser's
unit of work fails on the unique (session, npc) pair; because PostgreSQL aborts the
transaction and the in-memory twin restores its state on an exception, recovery
happens *outside* it — re-read the winner's conversation and append in a second unit
of work, so the loser's answer is not lost (plan review R-03).
"""

from __future__ import annotations

import logging

from locus.knowledge.cache import SnapshotSource
from locus.play.base import SessionAppService, SessionClosedError
from locus.play.deeds.caps import LINE_MAX, SLANT_MAX, cap
from locus.play.deeds.service import DeedService
from locus.play.errors import (
    ConversationExistsError,
    InvalidActionError,
    LlmCallFailedError,
    LlmUnavailableError,
)
from locus.play.models import (
    AppraisalDraft,
    AppraisalDraftItem,
    AppraisalOutcome,
    Conversation,
    DeedAppraisal,
    GameSession,
    Message,
    NpcReply,
    Player,
    ScopeLimits,
    SessionStatus,
)
from locus.play.npc.prompts import (
    appraisal_prompt,
    appraisal_system_prompt,
    fallback_text,
    system_prompt,
    user_prompt,
)
from locus.play.npc.scope import build_context
from locus.play.player import movement
from locus.play.ports import PlayRepository
from locus.play.region_knowledge import SessionKnowledgeService
from locus.play.turn.budget import LlmBudget
from locus.shared.config.tuning import PlayTuning
from locus.shared.llm.base import LLMProvider
from locus.shared.models import NPC, WorldSnapshot
from locus.shared.models.util import clamp01

# Facts the NPC weighs a deed against (BLM §3.2: at most 8).
APPRAISAL_FACTS = 8
# What the player is told when the NPC's LLM call fails (BR-U7-27): fixed, so the
# provider's own error text never reaches the response.
NPC_UNAVAILABLE = "the NPC could not answer right now; try again"

logger = logging.getLogger(__name__)


class NpcDialogueService(SessionAppService):
    def __init__(
        self,
        repo: PlayRepository,
        snapshots: SnapshotSource,
        region_knowledge: SessionKnowledgeService,
        llm: LLMProvider | None,
        tuning: PlayTuning,
        *,
        default_lang: str,
        supported_langs: tuple[str, ...],
        deeds: DeedService | None = None,
    ) -> None:
        super().__init__(repo)
        self._deeds = deeds  # U6: deed memories and appraisals; None turns them off
        self._snapshots = snapshots
        self._region_knowledge = region_knowledge
        self._llm = llm  # None without a provider: only `say` refuses (BR-U5-29)
        self._tuning = tuning
        self._default_lang = default_lang.lower()
        self._supported = tuple(lang.lower() for lang in supported_langs)

    @property
    def llm_available(self) -> bool:
        return self._llm is not None

    # -- reads ---------------------------------------------------------------
    def npcs_here(self, session_id: str) -> list[tuple[NPC, int | None]]:
        """The people of the player's current region, each with its message count —
        ``None`` when there is no conversation yet. One count query for the region
        instead of one conversation read per NPC (U5 review C1, BR-U7-26)."""
        session = self._require_session(session_id)
        player = self._require_player(session_id)
        snapshot = self._snapshots.get(session.world_id)
        here = snapshot.npcs_by_region.get(player.region_id, [])
        counts = self._repo.message_counts(session_id)
        return [(npc, counts.get(npc.id)) for npc in here]

    def history(self, session_id: str, npc_id: str) -> Conversation:
        """The whole conversation (closed sessions allowed, no LLM; BR-U5-4)."""
        self._require_session(session_id)
        conv = self._repo.get_conversation(session_id, npc_id)
        if conv is None:
            raise LookupError(f"no conversation with {npc_id}")
        return conv

    # -- actions -------------------------------------------------------------
    def start(self, session_id: str, npc_id: str) -> Conversation:
        """Open or reopen the conversation with an NPC of the player's region (BR-U5-2)."""
        session = self._require_open(session_id)
        player = self._require_player(session_id)
        self._require_npc_here(self._snapshots.get(session.world_id), player, npc_id)
        existing = self._repo.get_conversation(session_id, npc_id)
        if existing is not None:
            return existing
        try:
            with self._repo.uow() as u:
                return u.conversations.create_conversation(
                    Conversation(session_id=session_id, npc_id=npc_id, started_turn=session.turn)
                )
        except ConversationExistsError:  # a concurrent start won: use its conversation
            winner = self._repo.get_conversation(session_id, npc_id)
            if winner is None:  # pragma: no cover - defensive
                raise
            return winner

    def say(self, session_id: str, npc_id: str, text: str, *, lang: str | None = None) -> NpcReply:
        """Ask an NPC something: one LLM call, one unit of work (BR-U5-3/16)."""
        lang = self.resolve_lang(lang)
        body = (text or "").strip()
        if not body:
            raise InvalidActionError("empty message")
        if len(body) > self._tuning.npc_max_message_chars:
            raise InvalidActionError(f"message too long (max {self._tuning.npc_max_message_chars})")
        if self._llm is None:
            raise LlmUnavailableError("npc dialogue needs an LLM provider (set OPENAI_API_KEY)")
        session = self._require_open(session_id)
        player = self._require_player(session_id)
        snapshot = self._snapshots.get(session.world_id)
        npc = self._require_npc_here(snapshot, player, npc_id)

        # reads + the pure scope, outside any transaction
        conv = self._repo.get_conversation(session_id, npc_id)
        src = self._region_knowledge.region_sources(
            session_id, npc.home_region_id, session=session, snapshot=snapshot
        )
        ctx = build_context(
            npc=npc,
            facts=src.facts,
            rumors=src.rumors,
            recent=conv.messages if conv else [],
            limits=ScopeLimits.from_tuning(self._tuning),
            lineage=src.lineage,
            deeds=self._deeds.memories(session_id, player, npc_id) if self._deeds else (),
        )
        # exactly one LLM call, outside any transaction (BR-U4-14). The prompt is built
        # first: a bug there is ours, not "say it again" (U7 review §3, like U6 #9)
        prompt, system = user_prompt(ctx, body, lang), system_prompt(npc, lang)
        try:
            answer = self._llm.complete(prompt, system=system)
        except Exception as exc:  # BR-U7-27: 503, nothing stored, no provider text out
            logger.exception("npc dialogue call failed for %s/%s", session_id, npc_id)
            raise LlmCallFailedError(NPC_UNAVAILABLE) from exc
        answer = (answer or "").strip() or fallback_text(lang)  # never break the conversation

        try:
            npc_msg = self._store(session, npc_id, conv, body, answer, lang)
        except ConversationExistsError:
            # A concurrent first message created it after our read. Our unit of work
            # was rolled back, so re-read and append in a fresh one (R-03).
            conv = self._repo.get_conversation(session_id, npc_id)
            if conv is None:  # pragma: no cover - defensive
                raise
            npc_msg = self._store(session, npc_id, conv, body, answer, lang)
        return NpcReply(
            message=npc_msg,
            lang=lang,
            llm_calls=1,
            context_ids=[k.knowledge_id for k in ctx.facts]
            + [r.id for r in ctx.rumors]
            + [d.deed_id for d in ctx.deeds],
        )

    # -- U6 appraisal (BLM §3.2) ---------------------------------------------
    def appraise(
        self,
        session: GameSession,
        player: Player,
        npc: NPC,
        snapshot: WorldSnapshot,
        *,
        budget: LlmBudget,
    ) -> AppraisalOutcome:
        """What this NPC makes of the traveler's deeds after a talk: at most one LLM
        call, **no writes** (DeedService stores the outcome, FD deviation 13). The caller
        hands over what it already read (U6 review C5).

        No judgement at all — no call, nothing recorded — unless the player said something
        new to this NPC since the last talk ended (BR-U6-7: "talked" means new words). A
        missing judgement in the model's answer is "not noteworthy" (BR-U6-10, review
        R-16), so the same NPC never judges the same deed twice.
        """
        outcome = AppraisalOutcome()
        if self._deeds is None:
            return outcome
        session_id, npc_id = session.id, npc.id
        conv = self._repo.get_conversation(session_id, npc_id)
        last = self._deeds.last_statement(session_id, npc_id)
        cursor = last.messages_through if last is not None else None
        new_lines = [
            m
            for m in (conv.messages if conv else [])
            if m.role == "player"
            and m.created_at is not None
            and (cursor is None or m.created_at > cursor)
        ]
        if not new_lines:
            return outcome
        if self._llm is None or budget.exhausted:
            return outcome  # deeds stay pending for a later talk (BR-U6-24, NFR R-04)
        pending = self._deeds.pending_for(session_id, player, npc_id)
        refs = {f"d{i + 1}": deed for i, deed in enumerate(pending)}
        keep = self._tuning.npc_max_recent_messages
        shown = new_lines[-keep:] if keep else []
        src = self._region_knowledge.region_sources(
            session_id, npc.home_region_id, session=session, snapshot=snapshot
        )
        # The same source hiding as `say` (BR-U5-11): a fact this NPC only knows through a
        # distorted rumor stays hidden here too, or a retelling could pass the original on
        # undistorted (U6 code review #1). Only the facts go into the prompt.
        known = build_context(
            npc=npc,
            facts=src.facts,
            rumors=src.rumors,
            recent=[],
            limits=ScopeLimits(
                facts=APPRAISAL_FACTS, rumors=self._tuning.npc_max_rumors, recent_messages=0
            ),
            lineage=src.lineage,
        ).facts
        prompt = appraisal_prompt(known, shown, list(refs.items()))
        system = appraisal_system_prompt(npc)
        budget.take(1)
        try:
            draft = self._llm.structured(prompt, AppraisalDraft, system=system)
        except Exception:
            return outcome.model_copy(update={"llm_calls": 1, "llm_failed": True})
        items: dict[str, AppraisalDraftItem] = {}
        for item in draft.appraisals:
            if item.ref in refs or item.ref == "statement":
                items.setdefault(item.ref, item)

        def judged(ref: str, deed_id: str) -> DeedAppraisal:
            item = items.get(ref) or AppraisalDraftItem(ref=ref)
            retelling = cap(item.retelling, LINE_MAX)
            noteworthy = bool(item.noteworthy) and bool(retelling)  # BR-U6-11
            return DeedAppraisal(
                session_id=session_id,
                deed_id=deed_id,
                npc_id=npc_id,
                noteworthy=noteworthy,
                salience=clamp01(item.salience),
                slant=cap(item.slant, SLANT_MAX),
                retelling=retelling if noteworthy else "",
                turn=session.turn,
            )

        summary = cap(draft.summary, LINE_MAX) or None
        statement = judged("statement", "")  # bound to the new deed on save
        if summary is None:  # nothing worth noting was said: nothing to tell (BR-U6-9, #3)
            statement = statement.model_copy(
                update={"noteworthy": False, "salience": 0.0, "slant": "", "retelling": ""}
            )
        return AppraisalOutcome(
            statement_text=summary or f"{player.name} talked with {npc.name}.",
            appraisals=[judged(ref, deed.id) for ref, deed in refs.items()],
            statement_appraisal=statement,
            messages_through=max(m.created_at for m in new_lines if m.created_at is not None),
            llm_calls=1,
        )

    # -- helpers ------------------------------------------------------------
    def resolve_lang(self, lang: str | None) -> str:
        """The display language (default = TRANSLATION_TARGET_LANG). The API validates
        at the edge too; this guards direct callers (CLI, tests)."""
        chosen = (lang or self._default_lang).strip().lower()
        if chosen not in self._supported:
            raise InvalidActionError(f"unsupported lang: {chosen}")
        return chosen

    def _store(
        self,
        session: GameSession,
        npc_id: str,
        conv: Conversation | None,
        player_text: str,
        npc_text: str,
        lang: str,
    ) -> Message:
        with self._repo.uow() as u:
            # The LLM call took up to a minute and `say` holds no turn lock: the GM (or a
            # confirmed world replace) may have closed the session meanwhile. Re-check
            # inside the transaction so a closed session never gains lines (review U5 #4).
            current = u.sessions.get_session(session.id)
            if current is None or current.status == SessionStatus.CLOSED.value:
                raise SessionClosedError(f"session is closed: {session.id}")
            if conv is None:
                conv = u.conversations.create_conversation(
                    Conversation(session_id=session.id, npc_id=npc_id, started_turn=session.turn)
                )
            u.conversations.append_message(
                Message(
                    conversation_id=conv.id,
                    role="player",
                    text=player_text,
                    lang=lang,
                    turn=session.turn,
                )
            )
            return u.conversations.append_message(
                Message(
                    conversation_id=conv.id, role="npc", text=npc_text, lang=lang, turn=session.turn
                )
            )

    @staticmethod
    def _require_npc_here(snapshot: WorldSnapshot, player: Player, npc_id: str) -> NPC:
        """404 when the NPC is not in this world; 400 when it lives elsewhere (BR-U5-28)."""
        npc = movement.find_npc(snapshot, npc_id)
        if npc is None:
            raise LookupError(f"npc not found: {npc_id}")
        if npc.home_region_id != player.region_id:
            raise InvalidActionError(f"npc not here: {npc_id}")
        return npc
