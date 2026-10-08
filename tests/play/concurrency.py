"""V5 overlap-test harness (NFR § 2, NFR review R-02/R-05, code plan R-05).

- ``InterleaveGate`` pauses a thread right after a named store method returns, until a
  second thread reaches the same place (or ``wait_s`` passes), so two requests both read
  before either writes — the overlap the V5 defects need.
- ``BlockingDrafts`` is a fake LLM that holds every draft until released and counts how
  many drafts were in flight at once.
- ``FailingTimeline`` makes timeline writes raise, to see a row and its line roll back
  together.

The patches go on the repository instance and on the stores its units of work hand out,
so a read through ``repo.x`` and through ``uow.<store>.x`` are both seen. Only the named
methods are replaced; the repository keeps its class (``isinstance`` still holds), while
the unit-of-work and store wrappers delegate the rest by ``__getattr__``. Inside an
in-memory unit of work nothing pauses: that block holds the repository lock, so another
thread could never arrive (NFR R-05).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from typing import Any

from locus.play import InMemoryPlayRepository
from locus.play.event.suggester import EventDraft, EventDraftList
from locus.play.models import EventCategory
from locus.play.rumor.generator import RumorDraft

Wrap = Callable[[str, Callable[..., Any], bool], Callable[..., Any]]


class _StorePatch:
    """Replace ``names`` on ``repo`` and on its units of work's stores until ``close``.

    ``wrap(name, original, in_uow)`` returns the replacement for one bound method.
    """

    def __init__(self, repo: Any, names: Iterable[str], wrap: Wrap) -> None:
        self._repo = repo
        self._names = frozenset(names)
        self._wrap = wrap
        self._memory = isinstance(repo, InMemoryPlayRepository)
        self._local = threading.local()
        self._originals: dict[str, Any] = {}
        for name in sorted(self._names | {"uow"}):
            if name in vars(repo):  # another patch is already there: refuse to stack
                raise RuntimeError(f"{name} is already patched")
            self._originals[name] = getattr(repo, name)
        for name in self._names:
            original = self._originals[name]

            def outside(*a: Any, _n: str = name, _o: Any = original, **kw: Any) -> Any:
                return self._wrap(_n, _o, self.in_uow())(*a, **kw)

            setattr(repo, name, outside)
        repo.uow = lambda: _UowProxy(self._originals["uow"](), self)

    def in_uow(self) -> bool:
        return getattr(self._local, "depth", 0) > 0

    def _enter(self) -> None:
        self._local.depth = getattr(self._local, "depth", 0) + 1

    def _leave(self) -> None:
        self._local.depth -= 1

    def _store(self, store: Any) -> Any:
        # In memory every store is the repository itself, already patched.
        return store if self._memory else _StoreProxy(store, self)

    def close(self) -> None:
        for name in self._originals:
            vars(self._repo).pop(name, None)


class _UowProxy:
    def __init__(self, inner: Any, patch: _StorePatch) -> None:
        self._inner = inner
        self._patch = patch

    def __enter__(self) -> _UowProxy:
        self._inner.__enter__()
        self._patch._enter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._patch._leave()
        self._inner.__exit__(exc_type, exc, tb)

    def __getattr__(self, name: str) -> Any:  # sessions, rumors, distortions, ...
        return self._patch._store(getattr(self._inner, name))


class _StoreProxy:
    def __init__(self, store: Any, patch: _StorePatch) -> None:
        self._store = store
        self._patch = patch

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._store, name)
        if name in self._patch._names:
            return self._patch._wrap(name, attr, True)
        return attr


class InterleaveGate:
    """Pause the first call of ``method`` in each of the first two threads, right after
    it returns, until both have arrived or ``wait_s`` passes (NFR § 2.2).

    Fixed code: the second request waits on the session's short write and never reaches
    the gate while the first is held, so the first is let go by the timeout and the two
    run in order. Code without the fix: both read, meet here, then both write.

    ``met`` says whether two threads were inside together; ``arrivals`` counts the
    threads that reached the gate. Use as a context manager, or call ``close``.
    """

    def __init__(self, repo: Any, method: str, *, wait_s: float = 0.5) -> None:
        self.method = method
        self.wait_s = wait_s
        self.arrivals = 0
        self.met = False
        self._seen: set[int] = set()
        self._cond = threading.Condition()
        self._patch = _StorePatch(repo, [method], self._wrap)

    def _wrap(self, name: str, original: Callable[..., Any], in_uow: bool) -> Callable:
        def gated(*a: Any, **kw: Any) -> Any:
            result = original(*a, **kw)
            if not (in_uow and self._patch._memory):
                self._arrive()
            return result

        return gated

    def _arrive(self) -> None:
        me = threading.get_ident()
        with self._cond:
            if me in self._seen or len(self._seen) >= 2:
                return  # only a thread's first call, and only the first two threads
            self._seen.add(me)
            self.arrivals += 1
            if self.arrivals == 2:
                self.met = True
                self._cond.notify_all()
                return
            self._cond.wait_for(lambda: self.arrivals >= 2, timeout=self.wait_s)

    def close(self) -> None:
        self._patch.close()

    def __enter__(self) -> InterleaveGate:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _value(kind: Any) -> str:
    return str(getattr(kind, "value", kind))  # an enum member or its stored value


class FailingTimeline:
    """Timeline writes of ``kinds`` (all kinds when ``None``) raise ``RuntimeError``,
    through the repository and through a unit of work, on either store (code plan R-05)."""

    def __init__(self, repo: Any, kinds: Iterable[str] | None = None) -> None:
        self.kinds = None if kinds is None else {_value(k) for k in kinds}
        self.raised = 0
        self._patch = _StorePatch(repo, ["append_timeline"], self._wrap)

    def _wrap(self, name: str, original: Callable[..., Any], in_uow: bool) -> Callable:
        def failing(entry: Any, *a: Any, **kw: Any) -> Any:
            if self.kinds is None or _value(entry.kind) in self.kinds:
                self.raised += 1
                raise RuntimeError("timeline write failed")
            return original(entry, *a, **kw)

        return failing

    def close(self) -> None:
        self._patch.close()

    def __enter__(self) -> FailingTimeline:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class BlockingDrafts:
    """A fake LLM for ``RumorGenerator`` and ``EventSuggester``: every draft waits until
    ``release()`` (or ``timeout_s``), and ``max_inside`` records the most drafts that were
    in flight at once. ``entered`` is set when the first draft starts."""

    def __init__(
        self,
        *,
        statement: str = "twisted",
        event_region: str = "r1",
        blocked: bool = True,
        timeout_s: float = 5.0,
    ) -> None:
        self.statement = statement
        self.event_region = event_region
        self.timeout_s = timeout_s
        self.entered = threading.Event()
        self.calls = 0
        self.inside = 0
        self.max_inside = 0
        self._open = threading.Event()
        if not blocked:
            self._open.set()
        self._lock = threading.Lock()

    def release(self) -> None:
        self._open.set()

    def block(self) -> None:
        """Hold the drafts that start from now on."""
        self._open.clear()

    def wait_entered(self, count: int = 1, timeout_s: float = 5.0) -> bool:
        """Wait until ``count`` drafts are in flight together."""
        end = time.monotonic() + timeout_s
        while time.monotonic() < end:
            with self._lock:
                if self.inside >= count:
                    return True
            time.sleep(0.005)
        return False

    def structured(self, prompt: str, schema: type, *, system: str | None = None) -> Any:
        with self._lock:
            self.calls += 1
            self.inside += 1
            self.max_inside = max(self.max_inside, self.inside)
        self.entered.set()
        try:
            if not self._open.wait(self.timeout_s):
                raise TimeoutError("BlockingDrafts was never released")
            if schema is EventDraftList:
                return EventDraftList(
                    drafts=[
                        EventDraft(
                            region_id=self.event_region,
                            category=EventCategory.WAR,
                            magnitude=0.5,
                        )
                    ]
                )
            return RumorDraft(statement=self.statement)
        finally:
            with self._lock:
                self.inside -= 1

    def complete(self, prompt: str, *, system: str | None = None) -> str:  # pragma: no cover
        return ""
