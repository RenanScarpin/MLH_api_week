from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EUROPE_CONTINENT_NAME = "Europe"
# Explicit game-board viewport. Geometry is not modified; SVG rendering clips
# portions outside this rectangle. This keeps transcontinental states from
# stretching the board across Asia while still showing their European portion.
EUROPE_VIEW_BBOX = [-32.0, 33.0, 61.0, 72.0]


class GeometryResolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class StateGeometryResolution:
    qid: str
    display_name: str
    sov_a3: str
    sovereignty_resolution: str
    map_unit_features: tuple[dict[str, Any], ...]
    regional_resolution: str


def _properties(feature: dict[str, Any]) -> dict[str, Any]:
    props = feature.get("properties")
    return props if isinstance(props, dict) else {}


def _property(props: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in props:
            return props[name]
        lower = name.lower()
        if lower in props:
            return props[lower]
    return None


def _qid(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith("Q") and value[1:].isdigit():
        return value
    return None


def _feature_qid(feature: dict[str, Any]) -> str | None:
    return _qid(_property(_properties(feature), "WIKIDATAID"))


def _sov_a3(feature: dict[str, Any]) -> str | None:
    value = _property(_properties(feature), "SOV_A3")
    if isinstance(value, str) and value and value != "-99":
        return value
    return None


def _continent(feature: dict[str, Any]) -> str | None:
    value = _property(_properties(feature), "CONTINENT")
    return value if isinstance(value, str) else None


def _ne_id(feature: dict[str, Any]) -> str | None:
    value = _property(_properties(feature), "NE_ID")
    if isinstance(value, (str, int)):
        return str(value)
    return None


def _map_unit_matches_iso(feature: dict[str, Any], iso_alpha3: str | None) -> bool:
    if not iso_alpha3:
        return False
    props = _properties(feature)
    for field in ("ADM0_A3", "ISO_A3", "ISO_A3_EH", "GU_A3", "SU_A3"):
        if _property(props, field) == iso_alpha3:
            return True
    return False


def resolve_state_sov_a3(
    state: dict[str, Any],
    sovereignty_features: list[dict[str, Any]],
    map_unit_features: list[dict[str, Any]],
) -> tuple[str, str]:
    qid = state["qid"]
    direct = [feature for feature in sovereignty_features if _feature_qid(feature) == qid]
    direct_codes = {_sov_a3(feature) for feature in direct if _sov_a3(feature)}
    if len(direct_codes) == 1:
        return next(iter(direct_codes)), "sovereignty_qid"
    if len(direct_codes) > 1:
        raise GeometryResolutionError(
            f"{state['displayName']} ({qid}) maps to multiple Natural Earth sovereignty codes: "
            + ", ".join(sorted(direct_codes))
        )

    # Wikidata sometimes models the sovereign state one level above Natural
    # Earth's map-unit identities. Prefer current Wikidata constituent/part
    # QIDs and climb from those Natural Earth map units to their shared SOV_A3.
    # This is the important path for the Kingdom of Denmark, whose sovereign
    # Wikidata item intentionally has no usable current ISO alpha-3.
    constituent_qids = {
        value
        for value in state.get("geometryConstituentQids", [])
        if isinstance(value, str) and value.startswith("Q")
    }
    constituent_candidates = [
        feature for feature in map_unit_features if _feature_qid(feature) in constituent_qids
    ]
    constituent_codes = {
        _sov_a3(feature) for feature in constituent_candidates if _sov_a3(feature)
    }
    if len(constituent_codes) == 1:
        return next(iter(constituent_codes)), "map_unit_constituents_to_sovereignty"
    if len(constituent_codes) > 1:
        raise GeometryResolutionError(
            f"{state['displayName']} ({qid}) has constituent Natural Earth map units "
            "under multiple sovereignty codes: " + ", ".join(sorted(constituent_codes))
        )

    # ISO remains a useful secondary hierarchy hint when Wikidata gives the
    # higher-level sovereign item a current ISO code (e.g. Kingdom of the
    # Netherlands). It is deliberately not required.
    iso_alpha3 = state.get("isoAlpha3")
    candidates = [
        feature for feature in map_unit_features if _map_unit_matches_iso(feature, iso_alpha3)
    ]
    codes = {_sov_a3(feature) for feature in candidates if _sov_a3(feature)}
    if len(codes) == 1:
        return next(iter(codes)), "map_unit_iso_to_sovereignty"

    detail_parts = []
    if constituent_qids:
        detail_parts.append(
            "constituents " + ", ".join(sorted(constituent_qids, key=lambda value: int(value[1:])))
        )
    detail_parts.append(f"ISO {iso_alpha3}" if iso_alpha3 else "no ISO alpha-3")
    detail = "; ".join(detail_parts)
    raise GeometryResolutionError(
        f"Could not resolve Natural Earth sovereignty for {state['displayName']} "
        f"({qid}; {detail}). Candidate SOV_A3 values: {sorted(code for code in codes if code)}"
    )


def _primary_map_units(
    state: dict[str, Any],
    all_map_units: list[dict[str, Any]],
    sov_a3: str,
) -> list[dict[str, Any]]:
    qid = state["qid"]
    by_qid = [
        feature
        for feature in all_map_units
        if _sov_a3(feature) == sov_a3 and _feature_qid(feature) == qid
    ]
    if by_qid:
        return by_qid

    iso_alpha3 = state.get("isoAlpha3")
    by_iso = [
        feature
        for feature in all_map_units
        if _sov_a3(feature) == sov_a3 and _map_unit_matches_iso(feature, iso_alpha3)
    ]
    return by_iso


def resolve_state_geometry(
    state: dict[str, Any],
    sovereignty_features: list[dict[str, Any]],
    map_unit_features: list[dict[str, Any]],
) -> StateGeometryResolution:
    sov_a3, sovereignty_resolution = resolve_state_sov_a3(
        state, sovereignty_features, map_unit_features
    )

    european_units = [
        feature
        for feature in map_unit_features
        if _sov_a3(feature) == sov_a3 and _continent(feature) == EUROPE_CONTINENT_NAME
    ]
    if european_units:
        selected = european_units
        regional_resolution = "europe_map_units"
    else:
        selected = _primary_map_units(state, map_unit_features, sov_a3)
        regional_resolution = "primary_map_unit_fallback"

    if not selected:
        raise GeometryResolutionError(
            f"No Natural Earth map unit geometry found for {state['displayName']} "
            f"({state['qid']}, SOV_A3={sov_a3})"
        )

    return StateGeometryResolution(
        qid=state["qid"],
        display_name=state["displayName"],
        sov_a3=sov_a3,
        sovereignty_resolution=sovereignty_resolution,
        map_unit_features=tuple(selected),
        regional_resolution=regional_resolution,
    )


def _target_id(feature: dict[str, Any], index: int) -> str:
    ne_id = _ne_id(feature)
    if ne_id:
        return f"ne-map-unit-{ne_id}"
    props = _properties(feature)
    gu_a3 = _property(props, "GU_A3") or _property(props, "ADM0_A3") or "unknown"
    return f"ne-map-unit-{gu_a3}-{index}"


def build_europe_geometry(
    leader_dataset: dict[str, Any],
    sovereignty_geojson: dict[str, Any],
    map_units_geojson: dict[str, Any],
    *,
    natural_earth_version: str,
) -> dict[str, Any]:
    sovereignty_features = list(sovereignty_geojson.get("features", []))
    map_unit_features = list(map_units_geojson.get("features", []))

    states = leader_dataset["states"]
    resolutions = {
        state["qid"]: resolve_state_geometry(state, sovereignty_features, map_unit_features)
        for state in states
    }

    # Background: all Natural Earth map units classified as Europe, plus any
    # transcontinental fallback units required by a playable state.
    chosen_by_key: dict[str, dict[str, Any]] = {}
    for index, feature in enumerate(map_unit_features):
        if _continent(feature) == EUROPE_CONTINENT_NAME:
            chosen_by_key[_target_id(feature, index)] = feature

    feature_index = {id(feature): index for index, feature in enumerate(map_unit_features)}
    for resolution in resolutions.values():
        for feature in resolution.map_unit_features:
            index = feature_index[id(feature)]
            chosen_by_key[_target_id(feature, index)] = feature

    # Reverse map Natural Earth sovereignty codes to our Wikidata sovereigns.
    sovereign_qid_by_sov_a3 = {
        resolution.sov_a3: resolution.qid for resolution in resolutions.values()
    }

    runtime_features: list[dict[str, Any]] = []
    target_id_by_object_id: dict[int, str] = {}
    for target_id, feature in chosen_by_key.items():
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            continue
        props = _properties(feature)
        entity_qid = _feature_qid(feature)
        sovereign_qid = sovereign_qid_by_sov_a3.get(_sov_a3(feature) or "")
        runtime_features.append(
            {
                "type": "Feature",
                "id": target_id,
                "properties": {
                    "targetId": target_id,
                    "entityQid": entity_qid,
                    "sovereignQid": sovereign_qid,
                },
                "geometry": geometry,
            }
        )
        target_id_by_object_id[id(feature)] = target_id

    runtime_features.sort(key=lambda feature: feature["properties"]["targetId"])

    subject_map_targets: dict[str, list[str]] = {}
    for qid, resolution in resolutions.items():
        ids = [target_id_by_object_id[id(feature)] for feature in resolution.map_unit_features]
        subject_map_targets[qid] = sorted(set(ids))

    diagnostics = {
        "sovereigntyResolution": [
            {
                "qid": resolution.qid,
                "displayName": resolution.display_name,
                "sovA3": resolution.sov_a3,
                "method": resolution.sovereignty_resolution,
            }
            for resolution in sorted(resolutions.values(), key=lambda item: item.display_name.casefold())
        ],
        "regionalFallbacks": [
            {
                "qid": resolution.qid,
                "displayName": resolution.display_name,
                "sovA3": resolution.sov_a3,
                "method": resolution.regional_resolution,
            }
            for resolution in sorted(resolutions.values(), key=lambda item: item.display_name.casefold())
            if resolution.regional_resolution != "europe_map_units"
        ],
    }

    return {
        "naturalEarthVersion": natural_earth_version,
        "map": {
            "type": "FeatureCollection",
            "bbox": EUROPE_VIEW_BBOX,
            "features": runtime_features,
        },
        "subjectMapTargets": subject_map_targets,
        "diagnostics": diagnostics,
    }


def compile_full_europe_leader_quiz(
    leader_dataset: dict[str, Any],
    geometry_dataset: dict[str, Any],
) -> dict[str, Any]:
    targets = geometry_dataset["subjectMapTargets"]
    subjects: list[dict[str, Any]] = []
    missing: list[str] = []

    for state in leader_dataset["states"]:
        map_target_ids = targets.get(state["qid"], [])
        if not map_target_ids:
            missing.append(f"{state['displayName']} ({state['qid']})")
            continue
        subjects.append(
            {
                "id": state["qid"],
                "entityQid": state["qid"],
                "sovereignQid": state["qid"],
                "displayName": state["displayName"],
                "acceptedAnswers": state["acceptedAnswers"],
                "mapTargetIds": map_target_ids,
                "prompt": {
                    "kind": "head_of_state",
                    "heads": [
                        {
                            "entityQid": head["entityQid"],
                            "displayName": head["displayName"],
                            "imageId": None,
                        }
                        for head in state["heads"]
                    ],
                },
            }
        )

    if missing:
        raise GeometryResolutionError(
            "Refusing to compile a half-mapped quiz; missing geometry for: " + ", ".join(missing)
        )

    subjects.sort(key=lambda subject: subject["displayName"].casefold())
    return {
        "id": "europe-leader",
        "title": "Guess the sovereign state by its head of state",
        "scope": {"kind": "continent", "id": "europe", "mapId": "europe"},
        "subjectKind": "sovereign_state",
        "promptKind": "head_of_state",
        "interactionKind": "text",
        "progressionKind": "sequential",
        "completionRule": "all_subjects",
        "subjects": subjects,
    }
