# Demo world (Aldermoor)

A tiny fictional world for end-to-end validation (SC-1/2/4). Same content is
available via `locus.demo.load_demo_world()`.

- `memo.txt` — designer notes (regions, people, customs, a rumor, a global fact).
- `map.json` — Locus Map JSON (hierarchy + a mountain-blocked connection).
- `map.png` — a stylized map image (Sea · Greenvale + Aldwen River · Spine Mountains · Frostreach · Riverton/Highcrag) used to exercise the **VLM** ingestion path. Regenerate with `python examples/demo_world/generate_map.py` (needs Pillow).

`load_demo_world()` includes `map.png` when present, so `locus build-world --demo` runs the VLM
on the image (live, needs `OPENAI_API_KEY`) in addition to the structured map + memo.

Build and query it:

```bash
locus build-world --world aldermoor --demo   # also distills this world's own commonsense priors
# then query via the serving API:
#   GET /api/query/regions/<region_id>/knowledge?world_id=aldermoor
locus export --world aldermoor --out aldermoor.json
```

Expectation: Riverton's market knowledge reaches Highcrag only weakly (mountain
→ low weight) — as a rumor or unknown — while the "sun rises in the east" fact is
global to every region.
