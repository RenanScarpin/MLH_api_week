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



def apply_leader_data_to_quiz(
    quiz: dict[str, Any],
    europe_leader_dataset: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Overlay real state names and P35 prompts while preserving fixture geometry.

    Commons image ingestion is intentionally a later stage, so every real head
    gets imageId=None and exercises the frontend's neutral placeholder path.
    Demo subjects that are known European sovereign states but have no current
    P35 are removed, matching leader-quiz eligibility semantics.
    """
    states = {state["qid"]: state for state in europe_leader_dataset["states"]}
    excluded = {
        state["qid"]
        for state in europe_leader_dataset.get("diagnostics", {}).get(
            "excludedNoCurrentHead", []
        )
    }

    result = copy.deepcopy(quiz)
    updated: list[str] = []
    removed: list[str] = []
    subjects: list[dict[str, Any]] = []

    for subject in result.get("subjects", []):
        qid = subject.get("entityQid")
        if qid in excluded:
            removed.append(qid)
            continue

        state = states.get(qid)
        if state:
            subject["displayName"] = state["displayName"]
            subject["acceptedAnswers"] = state["acceptedAnswers"]
            subject["prompt"] = {
                "kind": "head_of_state",
                "heads": [
                    {
                        "entityQid": head["entityQid"],
                        "displayName": head["displayName"],
                        "imageId": None,
                    }
                    for head in state["heads"]
                ],
            }
            updated.append(qid)

        subjects.append(subject)

    result["subjects"] = subjects
    return result, updated, removed
