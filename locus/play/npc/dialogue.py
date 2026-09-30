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

from locus.knowledge.cache import SnapshotSource
from locus.play.base import SessionAppService, SessionClosedError
from locus.play.errors import ConversationExistsError, InvalidActionError, LlmUnavailableError
from locus.play.models import (
    Conversation,
    GameSession,
    Message,
    NpcReply,
    Player,
    ScopeLimits,
    SessionStatus,
)
from locus.play.npc.prompts import fallback_text, system_prompt, user_prompt
from locus.play.npc.scope import build_context
from locus.play.ports import PlayRepository
from locus.play.region_knowledge import SessionKnowledgeService
from locus.shared.config.tuning import PlayTuning
from locus.shared.llm.base import LLMProvider
from locus.shared.models import NPC, WorldSnapshot


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
    ) -> None:
        super().__init__(repo)
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
    def npcs_here(self, session_id: str) -> list[tuple[NPC, Conversation | None]]:
        """The people of the player's current region, with their conversation if any."""
        session = self._require_session(session_id)
        player = self._require_player(session_id)
        snapshot = self._snapshots.get(session.world_id)
        here = snapshot.npcs_by_region.get(player.region_id, [])
        return [(npc, self._repo.get_conversation(session_id, npc.id)) for npc in here]

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
        )
        # exactly one LLM call, outside any transaction (BR-U4-14)
        answer = self._llm.complete(user_prompt(ctx, body, lang), system=system_prompt(npc, lang))
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
            context_ids=[k.knowledge_id for k in ctx.facts] + [r.id for r in ctx.rumors],
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

    def _require_player(self, session_id: str) -> Player:
        player = self._repo.get_player(session_id)
        if player is None:
            raise InvalidActionError(f"session has no player: {session_id}")
        return player

    @staticmethod
    def _require_npc_here(snapshot: WorldSnapshot, player: Player, npc_id: str) -> NPC:
        """404 when the NPC is not in this world; 400 when it lives elsewhere (BR-U5-28)."""
        npc = next((n for n in snapshot.npcs if n.id == npc_id), None)
        if npc is None:
            raise LookupError(f"npc not found: {npc_id}")
        if npc.home_region_id != player.region_id:
            raise InvalidActionError(f"npc not here: {npc_id}")
        return npc
