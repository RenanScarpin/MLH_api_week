from __future__ import annotations

import copy
from typing import Any


def apply_state_names_to_quiz(
    quiz: dict[str, Any],
    europe_states_dataset: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Overlay real names on fixture subjects without changing prompts or geometry."""
    states = {state["qid"]: state for state in europe_states_dataset["states"]}
    result = copy.deepcopy(quiz)
    updated: list[str] = []

    for subject in result.get("subjects", []):
        state = states.get(subject.get("entityQid"))
        if not state:
            continue
        subject["displayName"] = state["displayName"]
        subject["acceptedAnswers"] = state["acceptedAnswers"]
        updated.append(state["qid"])

    return result, updated
