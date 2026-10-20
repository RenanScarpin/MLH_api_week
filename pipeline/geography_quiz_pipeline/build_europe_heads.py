from __future__ import annotations

import argparse
import json
from pathlib import Path

from .demo_overlay import apply_leader_data_to_quiz
from .europe_leaders import build_europe_leader_dataset
from .io_utils import write_json_atomic
from .wikidata_client import WikidataClient

PIPELINE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = PIPELINE_DIR.parent
DEFAULT_OUTPUT = PIPELINE_DIR / "build" / "europe-leader-states.json"
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
            "Fetch current European sovereign states and their current Wikidata "
            "P35 head(s) of state."
        )
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--apply-demo",
        action="store_true",
        help=(
            "Atomically update names/answers and real head-of-state prompts for "
            "matching demo subjects. Images remain null fixtures for this stage."
        ),
    )
    parser.add_argument("--demo-quiz", type=Path, default=DEFAULT_DEMO_QUIZ)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    client = WikidataClient()
    dataset = build_europe_leader_dataset(client)
    write_json_atomic(args.output, dataset)

    print(
        f"Wrote {dataset['eligibleStateCount']} leader-quiz-eligible European "
        f"sovereign states to {args.output}"
    )
    print(
        f"Excluded {dataset['excludedStateCount']} state(s) with no current P35; "
        f"{len(dataset['diagnostics']['multipleCurrentHeads'])} state(s) have "
        "multiple current P35 values."
    )
    if dataset["collisions"]:
        print(f"Detected {len(dataset['collisions'])} normalized answer collision(s).")

    if args.apply_demo:
        with args.demo_quiz.open("r", encoding="utf-8") as file:
            quiz = json.load(file)
        updated_quiz, updated, removed = apply_leader_data_to_quiz(quiz, dataset)
        write_json_atomic(args.demo_quiz, updated_quiz)
        print(f"Updated {len(updated)} demo subject(s) in {args.demo_quiz}")
        if removed:
            print(
                "Removed demo subject(s) without a current P35: "
                + ", ".join(removed)
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
