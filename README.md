# Geography Quiz MVP — frontend vertical slice

This repository implements the first vertical slice of the planned geography quiz website.

## Implemented

- React + TypeScript + Vite frontend skeleton.
- Immutable snapshot contracts.
- Hand-written `demo-v1` snapshot fixture.
- Five European sovereign-state questions.
- Single-head, multiple-head (Andorra), and non-human collective-head (Switzerland) prompt shapes.
- Missing-image placeholder path (`Swiss Federal Council` deliberately has `imageId: null` in the fixture).
- Permissive answer normalization.
- Pure sequential quiz-session engine.
- Derived map highlighting from solved subjects.
- Simplified SVG Europe fixture map loaded from GeoJSON.
- Node tests for answer normalization and quiz engine behavior.
- Empty `pipeline/` boundary for the future real ingestion process.

The local SVG portraits and simplified polygons are **development fixtures**, not source data and not intended to represent the eventual Wikidata/Commons/Natural Earth ingestion output.

## Run

```bash
cd frontend
npm install
npm run dev
```

Then open the Vite URL printed in the terminal.

## Tests

The pure TypeScript quiz/normalization tests do not depend on React or Vite:

```bash
cd frontend
npm test
```

## Build

After dependencies are installed:

```bash
npm run build
```

## Snapshot boundary

The frontend starts at `public/latest.json`, follows it to one immutable snapshot manifest, then loads:

- `quizzes/europe-leader.json`
- `maps/europe.geojson`
- `assets/images.json`
- portrait files lazily as needed

The eventual Python pipeline must produce this contract; the React app should never need to understand Wikidata properties, qualifiers, Natural Earth hierarchy fields, or Commons API responses.
