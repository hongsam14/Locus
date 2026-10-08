"""V5 NFR-6 — TurnGuard's rules as a hypothesis state machine (NFR § 4, NFR review R-06).

No threads: only the order of calls is shuffled, over two sessions. The short write's
wait and timeout need threads and are seen by the example tests (TP-V5-13).
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any

import pytest
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule

from locus.play.base import SessionClosedError
from locus.play.errors import GmBusyError, TurnInProgressError
from locus.play.turn.guard import TurnGuard

SESSIONS = ("a", "b")
sessions = st.sampled_from(SESSIONS)


class GuardMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.guard = TurnGuard()
        self.turn = dict.fromkeys(SESSIONS, False)
        self.leases: dict[str, list[AbstractContextManager[Any]]] = {s: [] for s in SESSIONS}
        self.closes: dict[str, list[AbstractContextManager[Any]]] = {s: [] for s in SESSIONS}

    def _refused(self, s: str) -> type[Exception] | None:
        """What a turn start must raise now, in the guard's order (domain-entities § 1.1)."""
        if self.turn[s]:
            return TurnInProgressError
        if self.closes[s]:
            return SessionClosedError
        if self.leases[s]:
            return GmBusyError
        return None

    # -- turns -------------------------------------------------------------------
    @rule(s=sessions)
    def start_turn(self, s: str) -> None:
        expected = self._refused(s)
        if expected is None:
            self.guard.acquire(s, f"run-{s}")
            self.turn[s] = True
            return
        with pytest.raises(Exception) as err:
            self.guard.acquire(s, f"run-{s}")
        assert type(err.value) is expected  # GmBusyError is a TurnInProgressError

    @rule(s=sessions)
    def end_turn(self, s: str) -> None:
        self.guard.release(s)  # idempotent
        self.turn[s] = False

    # -- leases ------------------------------------------------------------------
    @rule(s=sessions, label=st.sampled_from(("gm", "editor")))
    def enter_lease(self, s: str, label: str) -> None:
        lease = self.guard.hold(s, label=label)
        if self.turn[s]:
            with pytest.raises(TurnInProgressError) as err:
                lease.__enter__()
            assert type(err.value) is TurnInProgressError
            return
        lease.__enter__()  # a close under way does not refuse it
        self.leases[s].append(lease)

    @precondition(lambda self: any(self.leases.values()))
    @rule(data=st.data())
    def exit_lease(self, data: st.DataObject) -> None:
        s = data.draw(st.sampled_from([s for s in SESSIONS if self.leases[s]]))
        self.leases[s].pop().__exit__(None, None, None)

    # -- closes ------------------------------------------------------------------
    @rule(s=sessions)
    def enter_close(self, s: str) -> None:
        close = self.guard.closing(s)
        if self.turn[s]:
            with pytest.raises(TurnInProgressError) as err:
                close.__enter__()
            assert type(err.value) is TurnInProgressError
            return
        close.__enter__()  # leases are not waited for
        self.closes[s].append(close)

    @precondition(lambda self: any(self.closes.values()))
    @rule(data=st.data())
    def exit_close(self, data: st.DataObject) -> None:
        s = data.draw(st.sampled_from([s for s in SESSIONS if self.closes[s]]))
        self.closes[s].pop().__exit__(None, None, None)

    # -- invariants --------------------------------------------------------------
    @invariant()
    def flags_match_the_state(self) -> None:
        for s in SESSIONS:
            assert self.guard.turn_running(s) is self.turn[s]
            # a count: two leases may overlap and only the last one out clears it (R-06)
            assert self.guard.gm_busy(s) is bool(self.leases[s])

    @invariant()
    def a_turn_is_alone(self) -> None:
        """Read from the guard itself, not the model (code review 01 #24)."""
        for s in SESSIONS:
            if self.guard.turn_running(s):
                assert not self.guard.gm_busy(s)

    def teardown(self) -> None:
        for s in SESSIONS:
            while self.leases[s]:
                self.leases[s].pop().__exit__(None, None, None)
            while self.closes[s]:
                self.closes[s].pop().__exit__(None, None, None)
            self.guard.release(s)


TestGuardMachine = GuardMachine.TestCase
