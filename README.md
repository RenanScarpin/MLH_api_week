# Geography Quiz MVP

This repository implements the first vertical slice of the geography quiz website plus three live-data ingestion stages.

## Current playable MVP

The frontend is React + TypeScript + Vite and implements:

- immutable snapshot loading;
- sequential “guess sovereign state by head of state” gameplay;
- permissive normalized text answers;
- multiple simultaneous heads of state;
- neutral named placeholders for missing portraits;
- derived SVG map highlighting;
- an explicit Europe viewport so transcontinental states do not stretch the board across Asia.

The initial `demo-v1` fixture remains in the repository, but Stage 3 can now publish a new complete snapshot containing the **full real European leader set and real Natural Earth geometry**.

## Data pipeline

### 1. European sovereign states + permissive names

```bash
cd pipeline
python -m geography_quiz_pipeline.build_europe_names
```

### 2. Current Wikidata heads of state

```bash
python -m geography_quiz_pipeline.build_europe_heads
```

The command prints the actual states with no current `P35` and the actual states with multiple current `P35` values, including their head names/QIDs.

### 3. Natural Earth geometry

```bash
python -m geography_quiz_pipeline.build_europe_geometry
```

Natural Earth Admin 0 is pinned to version **5.1.1** and cached locally. No newer Natural Earth release is adopted automatically.

To make the real dataset playable in the frontend:

```bash
python -m geography_quiz_pipeline.build_europe_geometry --publish
```

This publishes a new immutable snapshot and moves `public/latest.json` only after the full snapshot succeeds.

At this point leader portraits are intentionally still placeholders; Commons/P18 ingestion is the next stage.

See `pipeline/README.md` for the exact geometry resolution rules and diagnostics.

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

## Tests

Frontend:

```bash
cd frontend
npm test
```

Pipeline:

```bash
cd pipeline
python -m unittest discover -s tests -v
```

## Snapshot boundary

The frontend starts at `public/latest.json`, follows it to one immutable snapshot manifest, then loads:

- `quizzes/europe-leader.json`
- `maps/europe.geojson`
- `assets/images.json`

The React app does not understand `P31`, `P30`, `P35`, statement qualifiers/ranks, `SOV_A3`, or other upstream semantics. Those are fully compiled by Python into the runtime contract.


## Natural Earth hierarchy note

The geometry stage resolves higher-level Wikidata sovereign realms through current
Wikidata constituent/part QIDs before falling back to ISO identifiers. This is
required for the Kingdom of Denmark (`Q756617`), whose sovereign-state item does
not expose a usable current ISO alpha-3 identifier.

After updating from a version created before this support was added, regenerate
the intermediate leader dataset before building geometry:

```bash
cd pipeline
python -m geography_quiz_pipeline.build_europe_heads
python -m geography_quiz_pipeline.build_europe_geometry
```

To publish the complete immutable snapshot after inspecting diagnostics:

```bash
python -m geography_quiz_pipeline.build_europe_geometry --publish
```
