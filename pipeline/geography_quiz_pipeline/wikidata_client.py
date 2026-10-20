from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable
from typing import Any

WDQS_ENDPOINT = "https://query.wikidata.org/sparql"
WIKIDATA_API_ENDPOINT = "https://www.wikidata.org/w/api.php"

DEFAULT_USER_AGENT = (
    "GeographyQuizMVP/0.1 "
    "(development snapshot builder; set GEOGRAPHY_QUIZ_USER_AGENT with contact information)"
)


class WikidataRequestError(RuntimeError):
    pass


class WikidataClient:
    def __init__(
        self,
        *,
        user_agent: str | None = None,
        timeout_seconds: float = 45.0,
        max_attempts: int = 3,
    ) -> None:
        self.user_agent = user_agent or os.getenv("GEOGRAPHY_QUIZ_USER_AGENT", DEFAULT_USER_AGENT)
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts

    def _get_json(self, base_url: str, params: dict[str, str], accept: str = "application/json") -> Any:
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": accept,
            },
        )

        last_error: BaseException | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                last_error = error
                if error.code not in {429, 500, 502, 503, 504} or attempt == self.max_attempts:
                    break
                retry_after = error.headers.get("Retry-After")
                delay = float(retry_after) if retry_after and retry_after.isdigit() else float(2 ** (attempt - 1))
                time.sleep(delay)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
                last_error = error
                if attempt == self.max_attempts:
                    break
                time.sleep(float(2 ** (attempt - 1)))

        raise WikidataRequestError(f"Wikidata request failed after {self.max_attempts} attempts: {last_error}")

    def query_sparql(self, query: str) -> dict[str, Any]:
        return self._get_json(
            WDQS_ENDPOINT,
            {"query": query, "format": "json"},
            accept="application/sparql-results+json",
        )

    def get_entities(self, qids: Iterable[str], *, batch_size: int = 50) -> dict[str, dict[str, Any]]:
        ordered = list(dict.fromkeys(qids))
        entities: dict[str, dict[str, Any]] = {}

        for start in range(0, len(ordered), batch_size):
            batch = ordered[start : start + batch_size]
            pending = list(batch)
            last_api_error: str | None = None

            # The Action API can occasionally return an application-level error
            # (for example maxlag/ratelimited) with HTTP 200, or a partial entity
            # set. Retry only the still-missing QIDs instead of failing the entire
            # snapshot build.
            for attempt in range(1, self.max_attempts + 1):
                payload = self._get_json(
                    WIKIDATA_API_ENDPOINT,
                    {
                        "action": "wbgetentities",
                        "ids": "|".join(pending),
                        "props": "labels|aliases|claims",
                        "languages": "en",
                        "languagefallback": "1",
                        "format": "json",
                        "formatversion": "2",
                        "maxlag": "5",
                    },
                )

                if not isinstance(payload, dict):
                    raise WikidataRequestError(
                        "wbgetentities returned a non-object top-level payload "
                        f"of type {type(payload).__name__}"
                    )

                api_error = payload.get("error")
                if isinstance(api_error, dict):
                    code = api_error.get("code", "unknown")
                    info = api_error.get("info", "no details")
                    last_api_error = f"{code}: {info}"
                    if attempt < self.max_attempts:
                        time.sleep(float(2 ** (attempt - 1)))
                        continue
                    raise WikidataRequestError(
                        f"wbgetentities failed after {self.max_attempts} attempts: {last_api_error}"
                    )

                raw_entities = payload.get("entities", {})
                if isinstance(raw_entities, dict):
                    batch_entities = raw_entities.values()
                elif isinstance(raw_entities, list):
                    # Kept for compatibility with fixtures or alternate serializers.
                    batch_entities = raw_entities
                else:
                    raise WikidataRequestError(
                        "wbgetentities returned an unexpected 'entities' payload "
                        f"of type {type(raw_entities).__name__}"
                    )

                for entity in batch_entities:
                    if not isinstance(entity, dict):
                        raise WikidataRequestError(
                            "wbgetentities returned a non-object entity payload "
                            f"of type {type(entity).__name__}"
                        )
                    entity_id = entity.get("id")
                    if entity_id:
                        entities[entity_id] = entity

                pending = [qid for qid in pending if qid not in entities]
                if not pending:
                    break

                if attempt < self.max_attempts:
                    time.sleep(float(2 ** (attempt - 1)))

            if pending:
                detail = f"; last API error: {last_api_error}" if last_api_error else ""
                raise WikidataRequestError(
                    "wbgetentities returned no entity after retries for: "
                    f"{', '.join(pending)}{detail}"
                )

        return entities
