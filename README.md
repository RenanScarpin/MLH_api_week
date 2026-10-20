# Geography Quiz MVP

This repository implements the first vertical slice of the geography quiz website plus the first real Wikidata ingestion stage.

## Frontend vertical slice

Implemented:

- React + TypeScript + Vite frontend skeleton.
- Immutable snapshot contracts.
- Hand-written `demo-v1` snapshot fixture.
- Five European sovereign-state leader questions.
- Single-head, multiple-head (Andorra), and non-human collective-head (Switzerland) prompt shapes.
- Missing-image placeholder path (`Swiss Federal Council` deliberately has `imageId: null` in the fixture).
- Permissive answer normalization.
- Pure sequential quiz-session engine.
- Derived map highlighting from solved subjects.
- Simplified SVG Europe fixture map loaded from GeoJSON.
- Node tests for answer normalization, fixture integrity, and quiz-engine behavior.

The local SVG portraits and simplified polygons are development fixtures, not source data and not intended to represent the eventual Commons/Natural Earth ingestion output.

## Wikidata pipeline — stage 1

`pipeline/` now contains the first live-data stage. It:

- queries Wikidata for current sovereign states in Europe;
- fetches English labels and aliases;
- includes current `P1813` short names and `P1448` official names;
- includes ISO alpha-2 and alpha-3 codes;
- uses the same answer normalization rules as the TypeScript frontend;
- emits normalized-answer collision diagnostics instead of dropping ambiguous aliases;
- can atomically overlay only real names/accepted answers onto the five-country demo while preserving fixture leaders and map IDs.

See `pipeline/README.md` for commands and details.

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

## Frontend tests

```bash
cd frontend
npm test
```

## Pipeline tests

```bash
cd pipeline
python -m unittest discover -s tests -v
```

## Fetch the first real Wikidata artifact

```bash
cd pipeline
python -m geography_quiz_pipeline.build_europe_names
```

To apply the fetched names to the existing demo fixture:

```bash
python -m geography_quiz_pipeline.build_europe_names --apply-demo
```

## Snapshot boundary

The frontend starts at `public/latest.json`, follows it to one immutable snapshot manifest, then loads:

- `quizzes/europe-leader.json`
- `maps/europe.geojson`
- `assets/images.json`
- portrait files lazily as needed

The Python pipeline will eventually produce this entire immutable contract. The React app should never need to understand Wikidata properties/qualifiers, Natural Earth hierarchy fields, or Commons API responses.

`latest.json` is intentionally not touched by the current ingestion stage. Full snapshot publication will only move that pointer after every required component has been built successfully.

### Wikidata batch robustness

The Wikidata Action API client retries transient JSON-level API errors (for example `maxlag`) and partial `wbgetentities` responses. If a batch returns only some requested QIDs, only the missing QIDs are retried.

