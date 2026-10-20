from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from .normalize import ANSWER_NORMALIZATION_VERSION, normalize_answer
from .wikidata_client import WDQS_ENDPOINT, WIKIDATA_API_ENDPOINT, WikidataClient

SOVEREIGN_STATE_QID = "Q3624078"
EUROPE_QID = "Q46"

# We intentionally inspect P30 statements instead of wdt:P30 so historical
# continent statements carrying an end-time qualifier can be excluded.
EUROPE_SOVEREIGN_STATES_QUERY = f"""
SELECT DISTINCT ?country WHERE {{
  ?country wdt:P31 wd:{SOVEREIGN_STATE_QID} .
  ?country p:P30 ?continentStatement .
  ?continentStatement ps:P30 wd:{EUROPE_QID} .
  ?continentStatement wikibase:rank ?continentRank .
  FILTER(?continentRank != wikibase:DeprecatedRank)
  FILTER NOT EXISTS {{ ?continentStatement pq:P582 ?continentEnd . }}
  OPTIONAL {{ ?continentStatement pq:P580 ?continentStart . }}
  FILTER(!BOUND(?continentStart) || ?continentStart <= NOW())
}}
ORDER BY ?country
""".strip()


@dataclass(frozen=True)
class NameCandidate:
    value: str
    kind: str


def _qid_from_uri(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def parse_europe_qids(sparql_payload: dict[str, Any]) -> list[str]:
    qids: list[str] = []
    for binding in sparql_payload.get("results", {}).get("bindings", []):
        country = binding.get("country", {}).get("value")
        if country:
            qids.append(_qid_from_uri(country))
    return sorted(set(qids), key=lambda value: int(value[1:]))


def _qualifier_times(statement: dict[str, Any], property_id: str) -> list[str]:
    values: list[str] = []
    for snak in statement.get("qualifiers", {}).get(property_id, []):
        datavalue = snak.get("datavalue")
        if datavalue and datavalue.get("type") == "time":
            value = datavalue.get("value", {}).get("time")
            if value:
                values.append(value)
    return values


def _wikidata_time_to_datetime(value: str) -> datetime | None:
    # We only need enough precision to reject obviously future starts. Values
    # can begin with '+' and can contain years outside Python's datetime range.
    raw = value.lstrip("+")
    try:
        date_part = raw.split("T", 1)[0]
        year_text, month_text, day_text = date_part.split("-", 2)
        year = int(year_text)
        if not (1 <= year <= 9999):
            return None
        month = max(1, int(month_text))
        day = max(1, int(day_text))
        return datetime(year, month, day, tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def current_statements(
    entity: dict[str, Any],
    property_id: str,
    *,
    now: datetime,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for statement in entity.get("claims", {}).get(property_id, []):
        if statement.get("rank") == "deprecated":
            continue
        mainsnak = statement.get("mainsnak", {})
        if mainsnak.get("snaktype") != "value" or "datavalue" not in mainsnak:
            continue
        if _qualifier_times(statement, "P582"):
            continue

        starts = [_wikidata_time_to_datetime(value) for value in _qualifier_times(statement, "P580")]
        starts = [value for value in starts if value is not None]
        if starts and min(starts) > now:
            continue
        candidates.append(statement)

    preferred = [statement for statement in candidates if statement.get("rank") == "preferred"]
    return preferred or candidates


def _statement_value(statement: dict[str, Any]) -> Any:
    return statement["mainsnak"]["datavalue"]["value"]


def _current_string_claims(entity: dict[str, Any], property_id: str, *, now: datetime) -> list[str]:
    values: list[str] = []
    for statement in current_statements(entity, property_id, now=now):
        value = _statement_value(statement)
        if isinstance(value, str):
            values.append(value)
    return values




def _current_entity_claims(entity: dict[str, Any], property_id: str, *, now: datetime) -> list[str]:
    qids: list[str] = []
    seen: set[str] = set()
    for statement in current_statements(entity, property_id, now=now):
        value = _statement_value(statement)
        if not isinstance(value, dict):
            continue
        qid = value.get("id")
        if not isinstance(qid, str):
            numeric_id = value.get("numeric-id")
            if isinstance(numeric_id, int):
                qid = f"Q{numeric_id}"
        if isinstance(qid, str) and qid.startswith("Q") and qid not in seen:
            seen.add(qid)
            qids.append(qid)
    return qids

def _current_english_monolingual_claims(
    entity: dict[str, Any], property_id: str, *, now: datetime
) -> list[str]:
    values: list[str] = []
    for statement in current_statements(entity, property_id, now=now):
        value = _statement_value(statement)
        if isinstance(value, dict) and value.get("language") == "en" and value.get("text"):
            values.append(value["text"])
    return values


def extract_name_candidates(entity: dict[str, Any], *, now: datetime) -> list[NameCandidate]:
    candidates: list[NameCandidate] = []

    label = entity.get("labels", {}).get("en", {}).get("value")
    if label:
        candidates.append(NameCandidate(label, "label"))

    for alias in entity.get("aliases", {}).get("en", []):
        value = alias.get("value")
        if value:
            candidates.append(NameCandidate(value, "alias"))

    for value in _current_english_monolingual_claims(entity, "P1813", now=now):
        candidates.append(NameCandidate(value, "short_name"))

    for value in _current_english_monolingual_claims(entity, "P1448", now=now):
        candidates.append(NameCandidate(value, "official_name"))

    for value in _current_string_claims(entity, "P297", now=now):
        candidates.append(NameCandidate(value, "iso_alpha2"))

    for value in _current_string_claims(entity, "P298", now=now):
        candidates.append(NameCandidate(value, "iso_alpha3"))

    return candidates


def normalize_name_candidates(candidates: Iterable[NameCandidate]) -> tuple[list[dict[str, Any]], list[str]]:
    merged: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        normalized = normalize_answer(candidate.value)
        if not normalized:
            continue
        entry = merged.setdefault(
            normalized,
            {
                "value": candidate.value,
                "normalized": normalized,
                "kinds": [],
            },
        )
        if candidate.kind not in entry["kinds"]:
            entry["kinds"].append(candidate.kind)

    names = sorted(merged.values(), key=lambda item: (item["normalized"], item["value"]))
    for item in names:
        item["kinds"].sort()
    accepted = [item["normalized"] for item in names]
    return names, accepted


def build_state_record(entity: dict[str, Any], *, now: datetime) -> dict[str, Any]:
    qid = entity["id"]
    candidates = extract_name_candidates(entity, now=now)
    names, accepted = normalize_name_candidates(candidates)
    label = entity.get("labels", {}).get("en", {}).get("value") or qid

    alpha2 = _current_string_claims(entity, "P297", now=now)
    alpha3 = _current_string_claims(entity, "P298", now=now)

    # Some Wikidata sovereign-state items sit above the country/map-unit level
    # used by Natural Earth. Keep current constituent/part QIDs as a geometry
    # hint so the Natural Earth stage can climb from those map units to one
    # shared SOV_A3 without relying on names or deprecated ISO identifiers.
    geometry_constituents: list[str] = []
    seen_geometry_constituents: set[str] = set()
    for property_id in ("P150", "P527"):
        for constituent_qid in _current_entity_claims(entity, property_id, now=now):
            if constituent_qid not in seen_geometry_constituents:
                seen_geometry_constituents.add(constituent_qid)
                geometry_constituents.append(constituent_qid)

    return {
        "qid": qid,
        "displayName": label,
        "isoAlpha2": alpha2[0] if alpha2 else None,
        "isoAlpha3": alpha3[0] if alpha3 else None,
        "geometryConstituentQids": geometry_constituents,
        "names": names,
        "acceptedAnswers": accepted,
    }


def find_collisions(states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_answer: dict[str, list[dict[str, str]]] = {}
    for state in states:
        for answer in state["acceptedAnswers"]:
            by_answer.setdefault(answer, []).append(
                {"qid": state["qid"], "displayName": state["displayName"]}
            )

    return [
        {"answer": answer, "states": matches}
        for answer, matches in sorted(by_answer.items())
        if len({match["qid"] for match in matches}) > 1
    ]


def build_europe_states_dataset(
    client: WikidataClient,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    query_payload = client.query_sparql(EUROPE_SOVEREIGN_STATES_QUERY)
    qids = parse_europe_qids(query_payload)
    entities = client.get_entities(qids)

    states = [build_state_record(entities[qid], now=now) for qid in qids]
    states.sort(key=lambda state: state["displayName"].casefold())

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
        "stateCount": len(states),
        "states": states,
        "collisions": find_collisions(states),
    }
