import unittest
from datetime import datetime, timezone

from geography_quiz_pipeline.europe_leaders import (
    build_europe_leader_dataset,
    build_head_record,
    extract_current_head_qids,
)

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)


def item_statement(qid, *, rank="normal", start=None, end=None):
    qualifiers = {}
    if start is not None:
        qualifiers["P580"] = [
            {"datavalue": {"type": "time", "value": {"time": start}}}
        ]
    if end is not None:
        qualifiers["P582"] = [
            {"datavalue": {"type": "time", "value": {"time": end}}}
        ]
    return {
        "rank": rank,
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {
                "type": "wikibase-entityid",
                "value": {"entity-type": "item", "id": qid},
            },
        },
        "qualifiers": qualifiers,
    }




class StubClient:
    def __init__(self, country_entities, head_entities):
        self.country_entities = country_entities
        self.head_entities = head_entities
        self.entity_calls = []

    def query_sparql(self, _query):
        return {
            "results": {
                "bindings": [
                    {"country": {"value": f"http://www.wikidata.org/entity/{qid}"}}
                    for qid in self.country_entities
                ]
            }
        }

    def get_entities(self, qids):
        qids = list(qids)
        self.entity_calls.append(qids)
        source = self.country_entities if all(qid in self.country_entities for qid in qids) else self.head_entities
        return {qid: source[qid] for qid in qids}


class EuropeLeadersTests(unittest.TestCase):
    def test_current_p35_excludes_ended_future_and_deprecated(self) -> None:
        entity = {
            "claims": {
                "P35": [
                    item_statement("Q1"),
                    item_statement("Q2", end="+2026-10-19T00:00:00Z"),
                    item_statement("Q3", start="+2026-10-21T00:00:00Z"),
                    item_statement("Q4", rank="deprecated"),
                ]
            }
        }
        self.assertEqual(extract_current_head_qids(entity, now=NOW), ["Q1"])

    def test_preferred_rank_wins_over_normal_current_statement(self) -> None:
        entity = {
            "claims": {
                "P35": [
                    item_statement("Q1"),
                    item_statement("Q2", rank="preferred"),
                ]
            }
        }
        self.assertEqual(extract_current_head_qids(entity, now=NOW), ["Q2"])

    def test_multiple_preferred_heads_are_preserved(self) -> None:
        entity = {
            "claims": {
                "P35": [
                    item_statement("Q1", rank="preferred"),
                    item_statement("Q2", rank="preferred"),
                ]
            }
        }
        self.assertEqual(extract_current_head_qids(entity, now=NOW), ["Q1", "Q2"])

    def test_duplicate_head_qid_is_deduplicated(self) -> None:
        entity = {
            "claims": {
                "P35": [item_statement("Q1"), item_statement("Q1")]
            }
        }
        self.assertEqual(extract_current_head_qids(entity, now=NOW), ["Q1"])

    def test_nonhuman_head_needs_no_special_handling(self) -> None:
        entity = {
            "id": "Q30917",
            "labels": {"en": {"language": "en", "value": "Swiss Federal Council"}},
        }
        self.assertEqual(
            build_head_record(entity),
            {"entityQid": "Q30917", "displayName": "Swiss Federal Council"},
        )


    def test_full_dataset_excludes_missing_p35_and_reports_multiple_heads(self) -> None:
        country_entities = {
            "Q1": {
                "id": "Q1",
                "labels": {"en": {"value": "One"}},
                "aliases": {"en": []},
                "claims": {"P35": [item_statement("Q10", rank="preferred"), item_statement("Q11", rank="preferred")]},
            },
            "Q2": {
                "id": "Q2",
                "labels": {"en": {"value": "Two"}},
                "aliases": {"en": []},
                "claims": {},
            },
        }
        head_entities = {
            "Q10": {"id": "Q10", "labels": {"en": {"value": "Head A"}}},
            "Q11": {"id": "Q11", "labels": {"en": {"value": "Head B"}}},
        }
        client = StubClient(country_entities, head_entities)

        dataset = build_europe_leader_dataset(client, now=NOW)

        self.assertEqual(dataset["stateCount"], 2)
        self.assertEqual(dataset["eligibleStateCount"], 1)
        self.assertEqual(dataset["excludedStateCount"], 1)
        self.assertEqual(dataset["states"][0]["qid"], "Q1")
        self.assertEqual(
            [head["displayName"] for head in dataset["states"][0]["heads"]],
            ["Head A", "Head B"],
        )
        self.assertEqual(
            dataset["diagnostics"]["excludedNoCurrentHead"],
            [{"qid": "Q2", "displayName": "Two"}],
        )
        self.assertEqual(dataset["diagnostics"]["multipleCurrentHeads"][0]["qid"], "Q1")
        self.assertEqual(client.entity_calls, [["Q1", "Q2"], ["Q10", "Q11"]])


if __name__ == "__main__":
    unittest.main()
