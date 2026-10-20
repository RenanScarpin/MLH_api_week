import tempfile
import unittest
from pathlib import Path

from geography_quiz_pipeline.europe_geometry import (
    build_europe_geometry,
    compile_full_europe_leader_quiz,
    resolve_state_geometry,
)
from geography_quiz_pipeline.natural_earth_client import NaturalEarthClient
from geography_quiz_pipeline.snapshot_publish import publish_europe_snapshot


def feature(*, qid=None, sov_a3, continent, ne_id, adm0_a3=None, name="X"):
    props = {
        "SOV_A3": sov_a3,
        "CONTINENT": continent,
        "NE_ID": ne_id,
        "NAME": name,
    }
    if qid is not None:
        props["WIKIDATAID"] = qid
    if adm0_a3 is not None:
        props["ADM0_A3"] = adm0_a3
    return {
        "type": "Feature",
        "properties": props,
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
        },
    }


class EuropeGeometryTests(unittest.TestCase):
    def setUp(self):
        self.sovereignty = [
            feature(qid="Q142", sov_a3="FR1", continent="Europe", ne_id=1, name="France sovereignty"),
            feature(qid="Q43", sov_a3="TUR", continent="Asia", ne_id=2, name="Turkey sovereignty"),
        ]
        self.map_units = [
            feature(qid="Q142", sov_a3="FR1", continent="Europe", ne_id=10, adm0_a3="FRA", name="France"),
            feature(qid="Q3769", sov_a3="FR1", continent="South America", ne_id=11, adm0_a3="GUF", name="French Guiana"),
            feature(qid="Q55", sov_a3="NL1", continent="Europe", ne_id=12, adm0_a3="NLD", name="Netherlands"),
            feature(qid="Q43", sov_a3="TUR", continent="Asia", ne_id=13, adm0_a3="TUR", name="Turkey"),
            feature(qid="Q999", sov_a3="ZZZ", continent="Europe", ne_id=14, adm0_a3="ZZZ", name="Background Europe"),
        ]

    def test_prefers_european_map_units_for_overseas_sovereign(self):
        state = {"qid": "Q142", "displayName": "France", "isoAlpha3": "FRA"}
        result = resolve_state_geometry(state, self.sovereignty, self.map_units)
        self.assertEqual(result.sov_a3, "FR1")
        self.assertEqual(result.regional_resolution, "europe_map_units")
        self.assertEqual([f["properties"]["NE_ID"] for f in result.map_unit_features], [10])

    def test_resolves_higher_level_kingdom_through_iso_map_unit(self):
        state = {"qid": "Q29999", "displayName": "Kingdom of the Netherlands", "isoAlpha3": "NLD"}
        result = resolve_state_geometry(state, self.sovereignty, self.map_units)
        self.assertEqual(result.sov_a3, "NL1")
        self.assertEqual(result.sovereignty_resolution, "map_unit_iso_to_sovereignty")
        self.assertEqual([f["properties"]["NE_ID"] for f in result.map_unit_features], [12])

    def test_resolves_kingdom_of_denmark_through_constituent_qids_without_iso(self):
        map_units = self.map_units + [
            feature(qid="Q35", sov_a3="DN1", continent="Europe", ne_id=20, adm0_a3="DNK", name="Denmark"),
            feature(qid="Q223", sov_a3="DN1", continent="North America", ne_id=21, adm0_a3="GRL", name="Greenland"),
            feature(qid="Q4628", sov_a3="DN1", continent="Europe", ne_id=22, adm0_a3="FRO", name="Faroe Islands"),
        ]
        state = {
            "qid": "Q756617",
            "displayName": "Kingdom of Denmark",
            "isoAlpha3": None,
            "geometryConstituentQids": ["Q35", "Q223", "Q4628"],
        }
        result = resolve_state_geometry(state, self.sovereignty, map_units)
        self.assertEqual(result.sov_a3, "DN1")
        self.assertEqual(
            result.sovereignty_resolution,
            "map_unit_constituents_to_sovereignty",
        )
        self.assertEqual(
            [f["properties"]["NE_ID"] for f in result.map_unit_features],
            [20, 22],
        )

    def test_transcontinental_state_falls_back_to_primary_unit(self):
        state = {"qid": "Q43", "displayName": "Turkey", "isoAlpha3": "TUR"}
        result = resolve_state_geometry(state, self.sovereignty, self.map_units)
        self.assertEqual(result.regional_resolution, "primary_map_unit_fallback")
        self.assertEqual([f["properties"]["NE_ID"] for f in result.map_unit_features], [13])

    def test_build_map_keeps_europe_background_and_subject_targets(self):
        leaders = {
            "states": [
                {"qid": "Q142", "displayName": "France", "isoAlpha3": "FRA", "acceptedAnswers": ["france"], "heads": [{"entityQid": "Q1", "displayName": "Head"}]},
                {"qid": "Q43", "displayName": "Turkey", "isoAlpha3": "TUR", "acceptedAnswers": ["turkey"], "heads": [{"entityQid": "Q2", "displayName": "Head 2"}]},
            ]
        }
        result = build_europe_geometry(
            leaders,
            {"type": "FeatureCollection", "features": self.sovereignty},
            {"type": "FeatureCollection", "features": self.map_units},
            natural_earth_version="5.1.1",
        )
        ids = {feature["properties"]["targetId"] for feature in result["map"]["features"]}
        self.assertIn("ne-map-unit-10", ids)
        self.assertIn("ne-map-unit-12", ids)  # Europe background even without quiz subject
        self.assertIn("ne-map-unit-13", ids)  # Turkey fallback despite NE continent=Asia
        self.assertIn("ne-map-unit-14", ids)
        self.assertNotIn("ne-map-unit-11", ids)  # French Guiana is not on Europe board
        self.assertEqual(result["map"]["bbox"], [-32.0, 33.0, 61.0, 72.0])

        quiz = compile_full_europe_leader_quiz(leaders, result)
        france = next(subject for subject in quiz["subjects"] if subject["id"] == "Q142")
        turkey = next(subject for subject in quiz["subjects"] if subject["id"] == "Q43")
        self.assertEqual(france["mapTargetIds"], ["ne-map-unit-10"])
        self.assertEqual(turkey["mapTargetIds"], ["ne-map-unit-13"])
        self.assertIsNone(france["prompt"]["heads"][0]["imageId"])

    def test_publisher_moves_latest_only_after_complete_snapshot(self):
        leaders = {
            "generatedAt": "2026-10-20T12:34:56Z",
            "normalizationVersion": 1,
        }
        quiz = {"id": "europe-leader", "subjects": []}
        map_geojson = {"type": "FeatureCollection", "bbox": [-1, -1, 1, 1], "features": []}
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory)
            result = publish_europe_snapshot(
                frontend_public_dir=public,
                leader_dataset=leaders,
                quiz=quiz,
                map_geojson=map_geojson,
                natural_earth_version="5.1.1",
            )
            self.assertTrue((result / "manifest.json").exists())
            self.assertTrue((result / "quizzes" / "europe-leader.json").exists())
            self.assertTrue((result / "maps" / "europe.geojson").exists())
            self.assertTrue((public / "latest.json").exists())

    def test_natural_earth_url_is_pinned_to_requested_tag(self):
        client = NaturalEarthClient(version="5.1.1")
        self.assertEqual(
            client.source_url("map_units"),
            "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.1/geojson/ne_10m_admin_0_map_units.geojson",
        )


if __name__ == "__main__":
    unittest.main()
