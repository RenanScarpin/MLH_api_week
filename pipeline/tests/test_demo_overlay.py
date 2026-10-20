import unittest

from geography_quiz_pipeline.demo_overlay import apply_leader_data_to_quiz, apply_state_names_to_quiz


class DemoOverlayTests(unittest.TestCase):
    def test_updates_names_without_touching_prompt_or_map(self) -> None:
        quiz = {
            "subjects": [
                {
                    "id": "Q142",
                    "entityQid": "Q142",
                    "displayName": "Fixture France",
                    "acceptedAnswers": ["fixture"],
                    "mapTargetIds": ["france"],
                    "prompt": {"kind": "head_of_state", "heads": [{"entityQid": "QX"}]},
                }
            ]
        }
        dataset = {
            "states": [
                {
                    "qid": "Q142",
                    "displayName": "France",
                    "acceptedAnswers": ["france", "french republic", "fra"],
                }
            ]
        }

        result, updated = apply_state_names_to_quiz(quiz, dataset)
        subject = result["subjects"][0]
        self.assertEqual(updated, ["Q142"])
        self.assertEqual(subject["displayName"], "France")
        self.assertEqual(subject["acceptedAnswers"], ["france", "french republic", "fra"])
        self.assertEqual(subject["mapTargetIds"], ["france"])
        self.assertEqual(subject["prompt"], quiz["subjects"][0]["prompt"])
        self.assertEqual(quiz["subjects"][0]["displayName"], "Fixture France")


    def test_leader_overlay_updates_prompt_preserves_map_and_removes_ineligible(self) -> None:
        quiz = {
            "subjects": [
                {
                    "id": "Q142",
                    "entityQid": "Q142",
                    "displayName": "Fixture France",
                    "acceptedAnswers": ["fixture"],
                    "mapTargetIds": ["france"],
                    "prompt": {
                        "kind": "head_of_state",
                        "heads": [{"entityQid": "QOLD", "displayName": "Old", "imageId": "fixture"}],
                    },
                },
                {
                    "id": "Q999",
                    "entityQid": "Q999",
                    "displayName": "No Head State",
                    "acceptedAnswers": ["no head"],
                    "mapTargetIds": ["no-head"],
                    "prompt": {"kind": "head_of_state", "heads": []},
                },
            ]
        }
        dataset = {
            "states": [
                {
                    "qid": "Q142",
                    "displayName": "France",
                    "acceptedAnswers": ["france", "fra"],
                    "heads": [
                        {"entityQid": "Q3052772", "displayName": "Emmanuel Macron"}
                    ],
                }
            ],
            "diagnostics": {
                "excludedNoCurrentHead": [
                    {"qid": "Q999", "displayName": "No Head State"}
                ]
            },
        }

        result, updated, removed = apply_leader_data_to_quiz(quiz, dataset)
        self.assertEqual(updated, ["Q142"])
        self.assertEqual(removed, ["Q999"])
        self.assertEqual(len(result["subjects"]), 1)
        subject = result["subjects"][0]
        self.assertEqual(subject["mapTargetIds"], ["france"])
        self.assertEqual(subject["displayName"], "France")
        self.assertEqual(subject["acceptedAnswers"], ["france", "fra"])
        self.assertEqual(
            subject["prompt"],
            {
                "kind": "head_of_state",
                "heads": [
                    {
                        "entityQid": "Q3052772",
                        "displayName": "Emmanuel Macron",
                        "imageId": None,
                    }
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
