"""Repo-wide pytest configuration: hypothesis profile (PBT-08, NFR R-04).

``print_blob=True`` prints a ``@reproduce_failure`` blob for every failing
example; ``deadline=None`` keeps slow CI machines from flaking property tests.
Re-run one seed with ``pytest --hypothesis-seed=<n>``.
"""

from __future__ import annotations

from hypothesis import settings

settings.register_profile("locus", print_blob=True, deadline=None)
settings.load_profile("locus")
