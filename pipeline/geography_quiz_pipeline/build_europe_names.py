from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo_overlay import apply_state_names_to_quiz
from .europe_states import build_europe_states_dataset
from .io_utils import write_json_atomic
from .wikidata_client import WikidataClient

PIPELINE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = PIPELINE_DIR.parent
DEFAULT_OUTPUT = PIPELINE_DIR / "build" / "europe-sovereign-states.json"
DEFAULT_DEMO_QUIZ = (
    PROJECT_DIR
    / "frontend"
    / "public"
    / "snapshots"
    / "demo-v1"
    / "quizzes"
    / "europe-leader.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch current European sovereign states from Wikidata and compile "
            "their permissive English answer names."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--apply-demo",
        action="store_true",
        help="Atomically update acceptedAnswers/displayName for matching subjects in the demo quiz.",
    )
    parser.add_argument("--demo-quiz", type=Path, default=DEFAULT_DEMO_QUIZ)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    client = WikidataClient()
    dataset = build_europe_states_dataset(client)
    write_json_atomic(args.output, dataset)

    print(f"Wrote {dataset['stateCount']} European sovereign states to {args.output}")
    if dataset["collisions"]:
        print(f"Detected {len(dataset['collisions'])} normalized answer collision(s).")

    if args.apply_demo:
        with args.demo_quiz.open("r", encoding="utf-8") as file:
            quiz = json.load(file)
        updated_quiz, updated = apply_state_names_to_quiz(quiz, dataset)
        write_json_atomic(args.demo_quiz, updated_quiz)
        print(f"Updated {len(updated)} demo subject(s) in {args.demo_quiz}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
