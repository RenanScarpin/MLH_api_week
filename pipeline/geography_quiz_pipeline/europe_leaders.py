from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .europe_states import (
    ANSWER_NORMALIZATION_VERSION,
    EUROPE_QID,
    EUROPE_SOVEREIGN_STATES_QUERY,
    SOVEREIGN_STATE_QID,
    build_state_record,
    current_statements,
    find_collisions,
    parse_europe_qids,
)
from .wikidata_client import WDQS_ENDPOINT, WIKIDATA_API_ENDPOINT, WikidataClient

HEAD_OF_STATE_PROPERTY = "P35"


def _statement_entity_qid(statement: dict[str, Any]) -> str | None:
    mainsnak = statement.get("mainsnak", {})
    datavalue = mainsnak.get("datavalue")
    if not isinstance(datavalue, dict):
        return None
    value = datavalue.get("value")
    if not isinstance(value, dict):
        return None

    entity_id = value.get("id")
    if isinstance(entity_id, str) and entity_id.startswith("Q"):
        return entity_id

    numeric_id = value.get("numeric-id")
    if isinstance(numeric_id, int):
        return f"Q{numeric_id}"

    return None


def extract_current_head_qids(
    country_entity: dict[str, Any],
    *,
    now: datetime,
) -> list[str]:
    """Return distinct current P35 targets, preserving Wikidata statement order."""
    qids: list[str] = []
    seen: set[str] = set()
    for statement in current_statements(country_entity, HEAD_OF_STATE_PROPERTY, now=now):
        qid = _statement_entity_qid(statement)
        if qid and qid not in seen:
            seen.add(qid)
            qids.append(qid)
    return qids


def build_head_record(entity: dict[str, Any]) -> dict[str, Any]:
    qid = entity["id"]
    label = entity.get("labels", {}).get("en", {}).get("value") or qid
    return {
        "entityQid": qid,
        "displayName": label,
    }


def build_europe_leader_dataset(
    client: WikidataClient,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compile the European sovereign states that currently have at least one P35."""
    now = now or datetime.now(timezone.utc)

    query_payload = client.query_sparql(EUROPE_SOVEREIGN_STATES_QUERY)
    qids = parse_europe_qids(query_payload)
    country_entities = client.get_entities(qids)

    states_by_qid = {
        qid: build_state_record(country_entities[qid], now=now)
        for qid in qids
    }
    head_qids_by_state = {
        qid: extract_current_head_qids(country_entities[qid], now=now)
        for qid in qids
    }

    all_head_qids = sorted(
        {head_qid for head_qids in head_qids_by_state.values() for head_qid in head_qids},
        key=lambda value: int(value[1:]),
    )
    head_entities = client.get_entities(all_head_qids) if all_head_qids else {}

    eligible_states: list[dict[str, Any]] = []
    excluded_no_current_head: list[dict[str, str]] = []
    multiple_current_heads: list[dict[str, Any]] = []

    for qid in qids:
        state = states_by_qid[qid]
        head_qids = head_qids_by_state[qid]
        if not head_qids:
            excluded_no_current_head.append(
                {"qid": qid, "displayName": state["displayName"]}
            )
            continue

        heads = [build_head_record(head_entities[head_qid]) for head_qid in head_qids]
        leader_state = {
            **state,
            "heads": heads,
        }
        eligible_states.append(leader_state)

        if len(heads) > 1:
            multiple_current_heads.append(
                {
                    "qid": qid,
                    "displayName": state["displayName"],
                    "heads": heads,
                }
            )

    eligible_states.sort(key=lambda state: state["displayName"].casefold())
    excluded_no_current_head.sort(key=lambda state: state["displayName"].casefold())
    multiple_current_heads.sort(key=lambda state: state["displayName"].casefold())

    return {
        "generatedAt": now.isoformat().replace("+00:00", "Z"),
        "normalizationVersion": ANSWER_NORMALIZATION_VERSION,
        "scope": {
            "kind": "continent",
            "continentQid": EUROPE_QID,
            "continentName": "Europe",
            "sovereignStateClassQid": SOVEREIGN_STATE_QID,
        },
        "sources": {
            "wikidataQueryService": WDQS_ENDPOINT,
            "wikidataActionApi": WIKIDATA_API_ENDPOINT,
        },
        "stateCount": len(qids),
        "eligibleStateCount": len(eligible_states),
        "excludedStateCount": len(excluded_no_current_head),
        "states": eligible_states,
        "collisions": find_collisions(eligible_states),
        "diagnostics": {
            "excludedNoCurrentHead": excluded_no_current_head,
            "multipleCurrentHeads": multiple_current_heads,
        },
    }
