from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

NATURAL_EARTH_VERSION = "5.1.1"
NATURAL_EARTH_SCALE = "10m"
NATURAL_EARTH_REPOSITORY = "nvkelso/natural-earth-vector"

_DATASET_FILES = {
    "sovereignty": "ne_10m_admin_0_sovereignty.geojson",
    "map_units": "ne_10m_admin_0_map_units.geojson",
}


class NaturalEarthRequestError(RuntimeError):
    pass


class NaturalEarthClient:
    """Fetch pinned Natural Earth GeoJSON files from an exact Git tag.

    Natural Earth is deliberately *not* auto-updated. Changing `version` is an
    explicit adoption decision; cached files live under a versioned directory.
    """

    def __init__(
        self,
        *,
        version: str = NATURAL_EARTH_VERSION,
        timeout_seconds: float = 60.0,
        max_attempts: int = 3,
        user_agent: str = "GeographyQuizMVP/0.1 (Natural Earth snapshot builder)",
    ) -> None:
        self.version = version
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.user_agent = user_agent

    def source_url(self, dataset: str) -> str:
        try:
            filename = _DATASET_FILES[dataset]
        except KeyError as error:
            raise ValueError(f"Unknown Natural Earth dataset: {dataset}") from error
        return (
            "https://raw.githubusercontent.com/"
            f"{NATURAL_EARTH_REPOSITORY}/v{self.version}/geojson/{filename}"
        )

    def get_geojson(
        self,
        dataset: str,
        *,
        cache_dir: Path,
        refresh: bool = False,
    ) -> dict[str, Any]:
        try:
            filename = _DATASET_FILES[dataset]
        except KeyError as error:
            raise ValueError(f"Unknown Natural Earth dataset: {dataset}") from error

        version_dir = cache_dir / self.version
        cache_path = version_dir / filename
        if cache_path.exists() and not refresh:
            with cache_path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            self._validate_feature_collection(payload, dataset)
            return payload

        request = urllib.request.Request(
            self.source_url(dataset),
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/geo+json, application/json",
            },
        )
        last_error: BaseException | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.load(response)
                self._validate_feature_collection(payload, dataset)
                version_dir.mkdir(parents=True, exist_ok=True)
                temporary = cache_path.with_suffix(cache_path.suffix + ".tmp")
                with temporary.open("w", encoding="utf-8") as file:
                    json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))
                temporary.replace(cache_path)
                return payload
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in {429, 500, 502, 503, 504} or attempt == self.max_attempts:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                last_error = error
                if attempt == self.max_attempts:
                    break
            time.sleep(float(2 ** (attempt - 1)))

        raise NaturalEarthRequestError(
            f"Natural Earth {dataset} v{self.version} request failed after "
            f"{self.max_attempts} attempts: {last_error}"
        )

    @staticmethod
    def _validate_feature_collection(payload: Any, dataset: str) -> None:
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise NaturalEarthRequestError(
                f"Natural Earth {dataset} returned a non-FeatureCollection payload"
            )
        if not isinstance(payload.get("features"), list):
            raise NaturalEarthRequestError(
                f"Natural Earth {dataset} returned no feature list"
            )
