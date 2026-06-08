"""Structured map ingestion: Locus Map JSON + GeoJSON (US-1.3).

Pure parsing (no LLM). Invalid items are rejected into ``errors`` while valid
ones continue (BR-U2-7, graceful).
"""

from __future__ import annotations

from ..models import Coord, IngestionResult, Provenance, Region, RegionLevel, SourceKind

_GENERATED_BY = "structured-map"


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT, generated_by=_GENERATED_BY)


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _explicit_position(raw: dict) -> Coord | None:
    """Read an explicit x/y or position {x,y} from a Locus Map region. Pure."""
    pos = raw.get("position")
    if isinstance(pos, dict) and "x" in pos and "y" in pos:
        return Coord(x=_clamp01(pos["x"]), y=_clamp01(pos["y"]))
    if raw.get("x") is not None and raw.get("y") is not None:
        return Coord(x=_clamp01(raw["x"]), y=_clamp01(raw["y"]))
    return None


def geojson_centroid(geometry: dict) -> tuple[float, float] | None:
    """Average of all coordinate pairs in a GeoJSON geometry (lon, lat). Pure."""
    if not isinstance(geometry, dict):
        return None
    coords: list[tuple[float, float]] = []

    def _walk(node) -> None:
        if (
            isinstance(node, (list, tuple))
            and len(node) == 2
            and all(isinstance(v, (int, float)) for v in node)
        ):
            coords.append((float(node[0]), float(node[1])))
        elif isinstance(node, (list, tuple)):
            for child in node:
                _walk(child)

    _walk(geometry.get("coordinates"))
    if not coords:
        return None
    return (sum(c[0] for c in coords) / len(coords), sum(c[1] for c in coords) / len(coords))


def normalize_positions(points: list[tuple[float, float] | None]) -> list[Coord | None]:
    """Normalize (lon, lat) centroids into [0,1] (y inverted so north=top). Pure."""
    present = [p for p in points if p is not None]
    if not present:
        return [None] * len(points)
    xs = [p[0] for p in present]
    ys = [p[1] for p in present]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    rx, ry = (maxx - minx) or 1.0, (maxy - miny) or 1.0
    out: list[Coord | None] = []
    for p in points:
        if p is None:
            out.append(None)
        else:
            out.append(Coord(x=_clamp01((p[0] - minx) / rx), y=_clamp01(1.0 - (p[1] - miny) / ry)))
    return out


def _coerce_level(value: object, where: str, errors: list[str]) -> RegionLevel | None:
    if value is None:
        return RegionLevel.TOWN
    try:
        return RegionLevel(str(value))
    except ValueError:
        errors.append(f"{where}: invalid level {value!r}")
        return None


class StructuredMapIngestor:
    def parse(self, doc: dict, *, world_id: str) -> IngestionResult:
        if not isinstance(doc, dict):
            return IngestionResult(
                world_id=world_id, errors=["structured map must be a JSON object"]
            )
        if doc.get("type") == "FeatureCollection":
            return self._parse_geojson(doc, world_id)
        return self._parse_locus_map(doc, world_id)

    # -- Locus Map JSON --------------------------------------------------- #
    def _parse_locus_map(self, doc: dict, world_id: str) -> IngestionResult:
        errors: list[str] = []
        regions: list[Region] = []
        name_set: set[str] = set()

        for i, raw in enumerate(doc.get("regions", [])):
            where = f"regions[{i}]"
            name = (raw or {}).get("name")
            if not name:
                errors.append(f"{where}: missing 'name'")
                continue
            level = _coerce_level(raw.get("level"), where, errors)
            if level is None:
                continue
            attrs = dict(raw.get("attributes", {}) or {})
            if raw.get("parent"):
                attrs["parent_name"] = raw["parent"]
            regions.append(
                Region(
                    world_id=world_id,
                    name=name,
                    level=level,
                    attributes=attrs,
                    position=_explicit_position(raw),
                    provenance=_prov(),
                )
            )
            name_set.add(name)

        hints: list[dict] = []
        for j, conn in enumerate(doc.get("connections", [])):
            where = f"connections[{j}]"
            frm, to = (conn or {}).get("from"), (conn or {}).get("to")
            if not frm or not to:
                errors.append(f"{where}: missing 'from'/'to'")
                continue
            hints.append({"from": frm, "to": to, "kind": conn.get("kind", "adjacent")})
        if hints and regions:
            regions[0].attributes.setdefault("connection_hints", hints)

        return IngestionResult(world_id=world_id, region_hints=regions, errors=errors)

    # -- GeoJSON ---------------------------------------------------------- #
    def _parse_geojson(self, doc: dict, world_id: str) -> IngestionResult:
        errors: list[str] = []
        regions: list[Region] = []
        centroids: list[tuple[float, float] | None] = []
        for i, feat in enumerate(doc.get("features", [])):
            where = f"features[{i}]"
            props = (feat or {}).get("properties") or {}
            name = props.get("name")
            if not name:
                errors.append(f"{where}: missing properties.name")
                continue
            level = _coerce_level(props.get("level"), where, errors)
            if level is None:
                continue
            attrs = {"geometry_type": ((feat.get("geometry") or {}).get("type"))}
            if props.get("parent"):
                attrs["parent_name"] = props["parent"]
            regions.append(
                Region(
                    world_id=world_id, name=name, level=level, attributes=attrs, provenance=_prov()
                )
            )
            centroids.append(geojson_centroid(feat.get("geometry") or {}))

        # normalize centroids across the collection -> region.position
        for region, pos in zip(regions, normalize_positions(centroids), strict=True):
            region.position = pos
        return IngestionResult(world_id=world_id, region_hints=regions, errors=errors)
