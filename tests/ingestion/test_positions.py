"""U10 backend additions — Region.position from map input + round-trip."""

from __future__ import annotations

from locus.ingestion.structured_map_ingestor import (
    StructuredMapIngestor,
    geojson_centroid,
    normalize_positions,
)
from locus.storage import graph_mapping as gm


def test_locus_map_explicit_xy_position() -> None:
    doc = {"regions": [{"name": "A", "level": "town", "x": 0.25, "y": 0.75}]}
    res = StructuredMapIngestor().parse(doc, world_id="w")
    pos = res.region_hints[0].position
    assert pos is not None and abs(pos.x - 0.25) < 1e-9 and abs(pos.y - 0.75) < 1e-9


def test_geojson_centroid_and_normalization() -> None:
    assert geojson_centroid({"type": "Point", "coordinates": [10.0, 20.0]}) == (10.0, 20.0)
    poly = {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2]]]}
    cx, cy = geojson_centroid(poly)
    assert abs(cx - 1.0) < 1e-9 and abs(cy - 1.0) < 1e-9

    coords = normalize_positions([(0.0, 0.0), (10.0, 10.0), None])
    assert coords[0].x == 0.0 and coords[0].y == 1.0  # y inverted (south -> bottom)
    assert coords[1].x == 1.0 and coords[1].y == 0.0  # north -> top
    assert coords[2] is None


def test_geojson_ingest_assigns_positions() -> None:
    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "South", "level": "town"},
                "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
            },
            {
                "type": "Feature",
                "properties": {"name": "North", "level": "town"},
                "geometry": {"type": "Point", "coordinates": [0.0, 10.0]},
            },
        ],
    }
    res = StructuredMapIngestor().parse(doc, world_id="w")
    by_name = {r.name: r for r in res.region_hints}
    assert by_name["North"].position.y < by_name["South"].position.y  # north is higher (smaller y)


def test_region_position_round_trip() -> None:
    from locus.models import Coord, Provenance, Region, RegionLevel, SourceKind

    r = Region(
        world_id="w",
        name="A",
        level=RegionLevel.TOWN,
        position=Coord(x=0.3, y=0.6),
        provenance=Provenance(source=SourceKind.INPUT),
    )
    back = gm.node_to_region(gm.region_to_node(r))
    assert back.position is not None
    assert abs(back.position.x - 0.3) < 1e-9 and abs(back.position.y - 0.6) < 1e-9
