"""Structured map ingestion: Locus Map JSON + GeoJSON (US-1.3).

Pure parsing (no LLM). Invalid items are rejected into ``warnings`` while valid
ones continue (BR-U2-7, graceful).
"""

from __future__ import annotations

from locus.shared.models import (
    BuildWarning,
    Coord,
    IngestionResult,
    Provenance,
    Region,
    RegionLevel,
    SourceKind,
)
from locus.shared.models.util import clamp01
from locus.world.ingestion.mapping import ingest_warning

_GENERATED_BY = "structured-map"


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT, generated_by=_GENERATED_BY)


def _explicit_position(raw: dict) -> Coord | None:
    """Read an explicit x/y or position {x,y} from a Locus Map region. Pure."""
    pos = raw.get("position")
    if isinstance(pos, dict) and "x" in pos and "y" in pos:
        return Coord(x=clamp01(float(pos["x"])), y=clamp01(float(pos["y"])))
    if raw.get("x") is not None and raw.get("y") is not None:
        return Coord(x=clamp01(float(raw["x"])), y=clamp01(float(raw["y"])))
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
            out.append(Coord(x=clamp01((p[0] - minx) / rx), y=clamp01(1.0 - (p[1] - miny) / ry)))
    return out


def infer_missing_levels(raw_regions: list[dict], warnings: list[BuildWarning]) -> dict[str, str]:
    """Regions without an explicit ``level`` get one from their place in the ``parent``
    chain — leaf -> town, parent of towns -> province, above that -> continent — so a
    level-less map still forms a hierarchy (parents must be broader, BR-U2-8)."""
    by_name: dict[str, dict] = {str(r["name"]): r for r in raw_regions if r.get("name")}
    children: dict[str, list[str]] = {}
    for r in raw_regions:
        if r.get("name") and r.get("parent"):
            children.setdefault(str(r["parent"]), []).append(str(r["name"]))

    def height(name: str, seen: frozenset = frozenset()) -> int:
        if name in seen:
            return 0
        kids = children.get(name, [])
        return 0 if not kids else 1 + max(height(k, seen | {name}) for k in kids)

    ladder = [RegionLevel.TOWN.value, RegionLevel.PROVINCE.value, RegionLevel.CONTINENT.value]
    out: dict[str, str] = {}
    for name, r in by_name.items():
        if r.get("level"):
            continue
        level = ladder[min(height(name), 2)]
        out[name] = level
        warnings.append(ingest_warning(f"region {name!r}: no level given; inferred {level!r}"))
    return out


def _coerce_level(value: object, where: str, warnings: list[BuildWarning]) -> RegionLevel | None:
    if value is None:
        return RegionLevel.TOWN
    try:
        return RegionLevel(str(value))
    except ValueError:
        warnings.append(ingest_warning(f"{where}: invalid level {value!r}"))
        return None


class StructuredMapIngestor:
    def parse(self, doc: dict, *, world_id: str) -> IngestionResult:
        if not isinstance(doc, dict):
            return IngestionResult(
                world_id=world_id,
                warnings=[ingest_warning("structured map must be a JSON object", severity="error")],
            )
        if doc.get("type") == "FeatureCollection":
            return self._parse_geojson(doc, world_id)
        return self._parse_locus_map(doc, world_id)

    # -- Locus Map JSON --------------------------------------------------- #
    def _parse_locus_map(self, doc: dict, world_id: str) -> IngestionResult:
        warnings: list[BuildWarning] = []
        regions: list[Region] = []
        name_set: set[str] = set()
        raw_regions = [r for r in (doc.get("regions", []) or []) if isinstance(r, dict)]
        inferred = infer_missing_levels(raw_regions, warnings)

        for i, raw in enumerate(raw_regions):
            where = f"regions[{i}]"
            name = raw.get("name")
            if not name:
                warnings.append(ingest_warning(f"{where}: missing 'name'"))
                continue
            level = _coerce_level(raw.get("level") or inferred.get(name), where, warnings)
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
        for j, conn in enumerate(doc.get("connections", []) or []):
            where = f"connections[{j}]"
            if not isinstance(conn, dict):
                warnings.append(ingest_warning(f"{where}: expected an object"))
                continue
            frm, to = conn.get("from"), conn.get("to")
            if not frm or not to:
                warnings.append(ingest_warning(f"{where}: missing 'from'/'to'"))
                continue
            hints.append({"from": frm, "to": to, "kind": conn.get("kind", "adjacent")})
        if hints and regions:
            regions[0].attributes.setdefault("connection_hints", hints)

        return IngestionResult(world_id=world_id, region_hints=regions, warnings=warnings)

    # -- GeoJSON ---------------------------------------------------------- #
    def _parse_geojson(self, doc: dict, world_id: str) -> IngestionResult:
        warnings: list[BuildWarning] = []
        regions: list[Region] = []
        centroids: list[tuple[float, float] | None] = []
        features = [f for f in (doc.get("features", []) or []) if isinstance(f, dict)]
        inferred = infer_missing_levels(
            [dict(f.get("properties") or {}) for f in features], warnings
        )
        for i, feat in enumerate(features):
            where = f"features[{i}]"
            props = feat.get("properties") or {}
            name = props.get("name")
            if not name:
                warnings.append(ingest_warning(f"{where}: missing properties.name"))
                continue
            level = _coerce_level(props.get("level") or inferred.get(name), where, warnings)
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
        return IngestionResult(world_id=world_id, region_hints=regions, warnings=warnings)
