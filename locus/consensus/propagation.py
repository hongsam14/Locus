"""Max-product weighted reachability over the topology (U5, FD5-Q1=A).

best_path_weights returns, for every region reachable from ``start_id``, the
maximum product of CONNECTED_TO weights along any path (start itself = 1.0).
Roads (high weight) keep the product high → reach far; mountains/cut-offs
(low weight) collapse it → rumor/unknown. Pure.
"""

from __future__ import annotations

import heapq
from collections import defaultdict

from ..models import ConnectionEdge


def best_path_weights(start_id: str, connections: list[ConnectionEdge]) -> dict[str, float]:
    adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for c in connections:
        adj[c.source_region_id].append((c.target_region_id, c.weight))

    best: dict[str, float] = {start_id: 1.0}
    heap: list[tuple[float, str]] = [(-1.0, start_id)]  # max-heap via negation
    while heap:
        neg_w, node = heapq.heappop(heap)
        w = -neg_w
        if w < best.get(node, 0.0):
            continue
        for nbr, edge_w in adj[node]:
            nw = w * edge_w
            if nw > best.get(nbr, 0.0):
                best[nbr] = nw
                heapq.heappush(heap, (-nw, nbr))
    return best
