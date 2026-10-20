# Wikidata pipeline — stage 1

This stage replaces the first piece of hand-written geography data with live Wikidata data while intentionally leaving leader prompts and Natural Earth geometry as fixtures.

It does two things:

1. Queries the current Wikidata set of sovereign states (`P31 = sovereign state`) whose current continent statements include Europe (`P30 = Europe`, ignoring ended/future/deprecated continent statements).
2. Fetches each entity through `wbgetentities` and compiles permissive English accepted answers from:
   - label;
   - aliases;
   - current short names (`P1813`);
   - current official names (`P1448`);
   - ISO alpha-2 (`P297`);
   - ISO alpha-3 (`P298`).

The generated artifact is `build/europe-sovereign-states.json`. It also reports normalized answer collisions instead of deleting ambiguous names.

## Run

From `pipeline/`:

```bash
python -m geography_quiz_pipeline.build_europe_names
```

To also replace only `displayName` and `acceptedAnswers` for the matching five subjects in the current demo fixture:

```bash
python -m geography_quiz_pipeline.build_europe_names --apply-demo
```

The overlay deliberately preserves the fixture leader prompts and map target IDs.

No third-party Python packages are required.

### User-Agent

Wikimedia asks automated clients to identify themselves. Before real/production use, set an informative User-Agent with contact information, for example:

```bash
export GEOGRAPHY_QUIZ_USER_AGENT='GeographyQuiz/0.1 (https://example.com/contact)'
```

## Tests

```bash
python -m unittest discover -s tests -v
```

The tests are offline and include normalization parity with the TypeScript frontend, current-name filtering, permissive aliases/codes, collision reporting, and safe demo overlay behavior.

## Snapshot safety

Writes use a temporary file followed by an atomic replace. This stage does **not** update `frontend/public/latest.json`; full snapshot publication remains a later pipeline stage, where `latest.json` will only move after every required component has been built successfully.
