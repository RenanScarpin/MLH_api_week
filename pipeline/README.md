# Wikidata pipeline — stages 1–2

The pipeline now replaces two pieces of hand-written quiz data with live Wikidata data while intentionally leaving Natural Earth geometry and Commons images as fixtures.

## Stage 1 — European sovereign states + accepted answers

`build_europe_names`:

1. Queries the current Wikidata set of sovereign states (`P31 = sovereign state`) whose current continent statements include Europe (`P30 = Europe`, ignoring ended/future/deprecated continent statements).
2. Fetches each entity through `wbgetentities` and compiles permissive English accepted answers from label, aliases, current short names (`P1813`), current official names (`P1448`), ISO alpha-2 (`P297`), and ISO alpha-3 (`P298`).

```bash
python -m geography_quiz_pipeline.build_europe_names
```

Output: `build/europe-sovereign-states.json`.

To overlay only names/accepted answers onto the five-country demo:

```bash
python -m geography_quiz_pipeline.build_europe_names --apply-demo
```

## Stage 2 — current heads of state

`build_europe_heads` repeats the European-state materialization and additionally resolves current `P35` values.

A `P35` statement is eligible when it:

- is not deprecated;
- has no `P582` end-time qualifier;
- is not future-starting when a `P580` start time is present;
- survives Wikidata rank selection (preferred current statements win over normal current statements).

All simultaneous surviving heads are preserved. No human-instance filter is applied, so collective heads such as the Swiss Federal Council work without special cases. A state with zero surviving current heads is excluded from the leader quiz.

```bash
python -m geography_quiz_pipeline.build_europe_heads
```

Output: `build/europe-leader-states.json`.

The artifact contains:

- `stateCount`: all European sovereign states from the scope query;
- `eligibleStateCount`: states that have at least one current `P35`;
- `excludedStateCount`;
- `states`: eligible states with permissive accepted answers and `heads[]`;
- `diagnostics.excludedNoCurrentHead`;
- `diagnostics.multipleCurrentHeads`;
- normalized answer collision diagnostics.

To apply real names and real head identities to the existing five-country demo:

```bash
python -m geography_quiz_pipeline.build_europe_heads --apply-demo
```

This preserves the fixture `mapTargetIds`. Every real head gets `imageId: null` for now, deliberately exercising the neutral placeholder UI. Commons image ingestion is the next separate stage.

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

Tests are offline and cover normalization, permissive names/codes, current-claim filtering, current-P35 rank/start/end behavior, simultaneous heads, non-human heads, collision reporting, Wikidata partial-response retries, and safe demo overlays.

## Snapshot safety

Writes use a temporary file followed by an atomic replace. These stages do **not** update `frontend/public/latest.json`; full snapshot publication remains a later pipeline stage, where `latest.json` will only move after every required component has been built successfully.
