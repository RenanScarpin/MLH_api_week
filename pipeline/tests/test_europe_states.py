import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

from geography_quiz_pipeline.europe_states import (
    build_state_record,
    find_collisions,
    parse_europe_qids,
)

FIXTURE = Path(__file__).parent / "fixtures" / "wbgetentities_sample.json"
NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


class EuropeStatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with FIXTURE.open("r", encoding="utf-8") as file:
            cls.entities = {entity["id"]: entity for entity in json.load(file)["entities"]}

    def test_parse_europe_qids_deduplicates_and_sorts(self) -> None:
        payload = {
            "results": {
                "bindings": [
                    {"country": {"value": "http://www.wikidata.org/entity/Q29999"}},
                    {"country": {"value": "http://www.wikidata.org/entity/Q30"}},
                    {"country": {"value": "http://www.wikidata.org/entity/Q30"}},
                ]
            }
        }
        self.assertEqual(parse_europe_qids(payload), ["Q30", "Q29999"])

    def test_united_states_permissive_answers(self) -> None:
        state = build_state_record(self.entities["Q30"], now=NOW)
        for answer in (
            "united states",
            "united states of america",
            "america",
            "usa",
            "us",
            "the us",
        ):
            self.assertIn(answer, state["acceptedAnswers"])
        self.assertNotIn("deprecated america", state["acceptedAnswers"])

    def test_kingdom_of_netherlands_accepts_short_form_and_codes(self) -> None:
        state = build_state_record(self.entities["Q29999"], now=NOW)
        self.assertIn("kingdom of the netherlands", state["acceptedAnswers"])
        self.assertIn("netherlands", state["acceptedAnswers"])
        self.assertIn("the netherlands", state["acceptedAnswers"])
        self.assertIn("nl", state["acceptedAnswers"])
        self.assertIn("nld", state["acceptedAnswers"])
        self.assertNotIn("old kingdom name", state["acceptedAnswers"])


    def test_state_record_keeps_current_geometry_constituent_qids(self) -> None:
        entity = {
            "id": "Q756617",
            "labels": {"en": {"value": "Kingdom of Denmark"}},
            "aliases": {"en": []},
            "claims": {
                "P150": [
                    {
                        "rank": "normal",
                        "mainsnak": {
                            "snaktype": "value",
                            "datavalue": {
                                "type": "wikibase-entityid",
                                "value": {"id": "Q35"},
                            },
                        },
                        "qualifiers": {},
                    },
                    {
                        "rank": "normal",
                        "mainsnak": {
                            "snaktype": "value",
                            "datavalue": {
                                "type": "wikibase-entityid",
                                "value": {"id": "Q223"},
                            },
                        },
                        "qualifiers": {},
                    },
                ],
                "P527": [
                    {
                        "rank": "normal",
                        "mainsnak": {
                            "snaktype": "value",
                            "datavalue": {
                                "type": "wikibase-entityid",
                                "value": {"id": "Q4628"},
                            },
                        },
                        "qualifiers": {},
                    },
                    {
                        "rank": "normal",
                        "mainsnak": {
                            "snaktype": "value",
                            "datavalue": {
                                "type": "wikibase-entityid",
                                "value": {"id": "Q999"},
                            },
                        },
                        "qualifiers": {
                            "P582": [
                                {
                                    "datavalue": {
                                        "type": "time",
                                        "value": {"time": "+2000-01-01T00:00:00Z"},
                                    }
                                }
                            ]
                        },
                    },
                ],
            },
        }
        state = build_state_record(entity, now=NOW)
        self.assertEqual(state["geometryConstituentQids"], ["Q35", "Q223", "Q4628"])

    def test_collision_report_keeps_both_states(self) -> None:
        states = [
            {"qid": "Q1", "displayName": "One", "acceptedAnswers": ["shared", "one"]},
            {"qid": "Q2", "displayName": "Two", "acceptedAnswers": ["shared", "two"]},
        ]
        self.assertEqual(
            find_collisions(states),
            [
                {
                    "answer": "shared",
                    "states": [
                        {"qid": "Q1", "displayName": "One"},
                        {"qid": "Q2", "displayName": "Two"},
                    ],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
