# Real-world sample (Wiki bootstrap)

A tiny Earth-like reference used to bootstrap the Common-sense Wiki. The same
content is available programmatically via `locus.commonsense_wiki.load_bundled_realworld()`.

- `memo.txt` — real-world geography priors in prose.
- `map.json` — a small Locus Map JSON with terrain-tagged regions.

Build the wiki from these (or your own real-world materials):

```bash
locus build-wiki   # (wired in U9; uses the bundled sample by default)
```
