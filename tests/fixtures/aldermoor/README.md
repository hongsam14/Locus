# Aldermoor (test fixture)

Aldermoor was the packaged demo until U8. It now lives here as test input only;
the packaged demo is Emberleaf Isle (`locus/world/demo/worlds/`, listed in its
`manifest.json`).

- `aldermoor.world.json` — the hand-authored World File (5 regions, one blocked pass).
- `memo.txt`, `map.json` — its raw sources.
- `map.png` — a stylized map image for the VLM ingestion path. Regenerate with
  `python tests/fixtures/aldermoor/generate_map.py` (needs Pillow).

Tests read these files directly (`tests/fixtures/aldermoor/…`); a test that needs a
manifest builds one in a temporary folder.
