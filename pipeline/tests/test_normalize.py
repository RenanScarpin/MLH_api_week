import unittest

from geography_quiz_pipeline.normalize import normalize_answer


class NormalizeAnswerTests(unittest.TestCase):
    def test_matches_frontend_case_and_whitespace(self) -> None:
        self.assertEqual(normalize_answer("  THE   NETHERLANDS  "), "the netherlands")

    def test_matches_frontend_period_handling(self) -> None:
        self.assertEqual(normalize_answer("U.S.A."), "usa")

    def test_matches_frontend_diacritics_and_apostrophes(self) -> None:
        self.assertEqual(normalize_answer("Côte d’Ivoire"), "cote divoire")

    def test_matches_frontend_separators(self) -> None:
        self.assertEqual(normalize_answer("Bosnia-Herzegovina"), "bosnia herzegovina")


if __name__ == "__main__":
    unittest.main()
