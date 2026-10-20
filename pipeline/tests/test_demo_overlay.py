import unittest

from geography_quiz_pipeline.demo_overlay import apply_state_names_to_quiz


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


if __name__ == "__main__":
    unittest.main()
