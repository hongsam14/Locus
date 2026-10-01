"""Small reference values shared by the world editor and the wiki views (U3).

``ConnectionKey`` names one connection — two regions and a kind, no direction — and
``NameRef`` pairs an id with the name a designer reads (domain-entities §2.1·§2.2).
They live here, not in ``world/editor``, because the wiki's reference view (§5) uses
them too and the wiki is built before the editor package.
"""

from __future__ import annotations

from locus.shared.models import ConnectionEdge, ConnectionKind
from locus.shared.models.graph import LocusModel


class ConnectionKey(LocusModel):
    """One connection = two regions + a kind (no direction, A3-3)."""

    world_id: str
    a_region_id: str
    b_region_id: str
    kind: ConnectionKind

    @classmethod
    def of(cls, edge: ConnectionEdge) -> "ConnectionKey":
        """The key of an edge, either direction; the smaller id comes first so both
        directions of a pair give the same key."""
        a, b = sorted((edge.source_region_id, edge.target_region_id))
        return cls(world_id=edge.world_id, a_region_id=a, b_region_id=b, kind=edge.kind)

    def normalized(self) -> "ConnectionKey":
        a, b = sorted((self.a_region_id, self.b_region_id))
        return self.model_copy(update={"a_region_id": a, "b_region_id": b})


class NameRef(LocusModel):
    id: str
    name: str
