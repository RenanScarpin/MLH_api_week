import unittest
from unittest.mock import patch

from geography_quiz_pipeline.wikidata_client import WikidataClient, WikidataRequestError


class StubWikidataClient(WikidataClient):
    def __init__(self, payload):
        super().__init__(max_attempts=1)
        self.payload = payload

    def _get_json(self, base_url, params, accept="application/json"):
        return self.payload


class SequenceWikidataClient(WikidataClient):
    def __init__(self, payloads):
        super().__init__(max_attempts=len(payloads))
        self.payloads = list(payloads)
        self.calls = []

    def _get_json(self, base_url, params, accept="application/json"):
        self.calls.append(dict(params))
        if not self.payloads:
            raise AssertionError("Unexpected extra request")
        return self.payloads.pop(0)


class WikidataClientTests(unittest.TestCase):
    def test_get_entities_accepts_real_wikidata_dict_shape(self) -> None:
        client = StubWikidataClient(
            {
                "entities": {
                    "Q142": {"id": "Q142", "labels": {}},
                    "Q183": {"id": "Q183", "labels": {}},
                }
            }
        )

        result = client.get_entities(["Q142", "Q183"])

        self.assertEqual(set(result), {"Q142", "Q183"})
        self.assertEqual(result["Q142"]["id"], "Q142")

    def test_get_entities_still_accepts_list_shape_for_test_fixtures(self) -> None:
        client = StubWikidataClient(
            {
                "entities": [
                    {"id": "Q142", "labels": {}},
                    {"id": "Q183", "labels": {}},
                ]
            }
        )

        result = client.get_entities(["Q142", "Q183"])

        self.assertEqual(set(result), {"Q142", "Q183"})

    def test_get_entities_rejects_unexpected_entity_container(self) -> None:
        client = StubWikidataClient({"entities": "Q142"})

        with self.assertRaises(WikidataRequestError):
            client.get_entities(["Q142"])

    @patch("geography_quiz_pipeline.wikidata_client.time.sleep", return_value=None)
    def test_get_entities_retries_only_missing_qids_from_partial_batch(self, _sleep) -> None:
        client = SequenceWikidataClient(
            [
                {
                    "entities": {
                        "Q142": {"id": "Q142", "labels": {}},
                    }
                },
                {
                    "entities": {
                        "Q183": {"id": "Q183", "labels": {}},
                    }
                },
            ]
        )

        result = client.get_entities(["Q142", "Q183"], batch_size=50)

        self.assertEqual(set(result), {"Q142", "Q183"})
        self.assertEqual(client.calls[0]["ids"], "Q142|Q183")
        self.assertEqual(client.calls[1]["ids"], "Q183")

    @patch("geography_quiz_pipeline.wikidata_client.time.sleep", return_value=None)
    def test_get_entities_retries_json_level_api_error(self, _sleep) -> None:
        client = SequenceWikidataClient(
            [
                {"error": {"code": "maxlag", "info": "Waiting for replication lag"}},
                {"entities": {"Q142": {"id": "Q142", "labels": {}}}},
            ]
        )

        result = client.get_entities(["Q142"])

        self.assertEqual(set(result), {"Q142"})
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[0]["maxlag"], "5")


if __name__ == "__main__":
    unittest.main()
