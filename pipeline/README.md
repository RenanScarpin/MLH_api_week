# Geography quiz data pipeline — stages 1–3

The pipeline now replaces country names, current heads of state, and the Europe map geometry with external source data while intentionally leaving Commons portraits for the next stage.

## Stage 1 — European sovereign states + accepted answers

`build_europe_names`:

1. Queries the current Wikidata set of sovereign states (`P31 = sovereign state`) whose current continent statements include Europe (`P30 = Europe`, ignoring ended/future/deprecated continent statements).
2. Fetches each entity through `wbgetentities` and compiles permissive English accepted answers from label, aliases, current short names (`P1813`), current official names (`P1448`), ISO alpha-2 (`P297`), and ISO alpha-3 (`P298`).

```bash
python -m geography_quiz_pipeline.build_europe_names
```

Output: `build/europe-sovereign-states.json`.

## Stage 2 — current heads of state

`build_europe_heads` resolves current `P35` values.

A `P35` statement is eligible when it:

- is not deprecated;
- has no `P582` end-time qualifier;
- is not future-starting when a `P580` start time is present;
- survives Wikidata rank selection (preferred current statements win over normal current statements).

All simultaneous surviving heads are preserved. No human-instance filter is applied. A state with zero surviving current heads is excluded from the leader quiz.

```bash
python -m geography_quiz_pipeline.build_europe_heads
```

Output: `build/europe-leader-states.json`.

The command now prints explicit diagnostic lists, for example:

```text
States with no current P35 (2):
  - Example State (Q...)

States with multiple current P35 values (1):
  - Andorra (Q228): Head A (Q...), Head B (Q...)
```

## Stage 3 — real Natural Earth Europe geometry

Natural Earth is intentionally pinned to **Admin 0 version 5.1.1** for this stage. The code never checks for or adopts a newer release automatically.

The builder downloads exact-tag GeoJSON from the Natural Earth GitHub repository and caches it under:

```text
cache/natural-earth/5.1.1/
```

It uses:

- `ne_10m_admin_0_sovereignty.geojson`
- `ne_10m_admin_0_map_units.geojson`

Run:

```bash
python -m geography_quiz_pipeline.build_europe_geometry
```

Output: `build/europe-geometry.json`.

### Geometry resolution rules

For every leader-quiz-eligible Wikidata sovereign state:

1. Resolve its Natural Earth `SOV_A3` directly by `WIKIDATAID` in Admin 0 Sovereignty.
2. If Wikidata models the sovereign at a higher level than Natural Earth (for example a sovereign realm), use the state's ISO alpha-3 code to find its home Map Unit and climb to `SOV_A3`.
3. Prefer all Map Units for that sovereignty whose Natural Earth `CONTINENT` is `Europe`.
4. If Natural Earth classifies the transcontinental state elsewhere, use its primary Map Unit as a fallback.
5. The frontend map has an explicit Europe viewport, so non-European portions of fallback geometries are simply outside the board rather than forcing a custom polygon source.

The command prints exactly which states needed hierarchy resolution and which needed the primary-map-unit regional fallback.

### Publish the full playable snapshot

After stages 1–2 have generated `build/europe-leader-states.json`, run:

```bash
python -m geography_quiz_pipeline.build_europe_geometry --publish
```

This compiles **all eligible European leader subjects** with real Natural Earth geometry and publishes a brand-new immutable snapshot under `frontend/public/snapshots/`.

Publication is intentionally two-phase:

1. quiz, map, image manifest, and snapshot manifest are written into an unpublished temporary directory;
2. the complete directory is atomically renamed;
3. `frontend/public/latest.json` is updated **last**.

A failed build therefore never activates a half-built snapshot.

Commons portraits are still intentionally absent in this stage, so all real heads render through the neutral named placeholder.

### Intentionally adopting another Natural Earth release

The default is pinned to `5.1.1`. A different release is only used when explicitly supplied:

```bash
python -m geography_quiz_pipeline.build_europe_geometry \
  --natural-earth-version 5.x.y
```

That is an intentional adoption decision; there is no `latest` lookup.

To force a re-download of the already pinned version:

```bash
python -m geography_quiz_pipeline.build_europe_geometry --refresh-natural-earth
```

## User-Agent

Wikimedia asks automated clients to identify themselves. Before real/production use, set an informative User-Agent with contact information, for example:

```bash
export GEOGRAPHY_QUIZ_USER_AGENT='GeographyQuiz/0.1 (https://example.com/contact)'
```

On Windows PowerShell:

```powershell
$env:GEOGRAPHY_QUIZ_USER_AGENT='GeographyQuiz/0.1 (https://example.com/contact)'
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests are offline and cover normalization, permissive names/codes, current-P35 selection, Wikidata retry behavior, Natural Earth sovereignty resolution, Europe-only map-unit selection, transcontinental fallback behavior, complete quiz compilation, and safe snapshot publication.
