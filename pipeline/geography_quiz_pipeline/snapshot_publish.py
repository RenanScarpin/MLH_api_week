from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .io_utils import write_json_atomic


def snapshot_id_for(*, wikidata_generated_at: str, natural_earth_version: str) -> str:
    compact_time = re.sub(r"[^0-9TZ]", "", wikidata_generated_at)
    return f"europe-leader-{compact_time}-ne{natural_earth_version}"


def publish_europe_snapshot(
    *,
    frontend_public_dir: Path,
    leader_dataset: dict[str, Any],
    quiz: dict[str, Any],
    map_geojson: dict[str, Any],
    natural_earth_version: str,
) -> Path:
    """Publish a complete immutable snapshot, then atomically move latest.json.

    The final snapshot directory does not exist until every component has been
    written successfully into a temporary sibling directory. `latest.json` is
    the final write, so a failed build never activates partial data.
    """
    snapshots_dir = frontend_public_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    snapshot_id = snapshot_id_for(
        wikidata_generated_at=leader_dataset["generatedAt"],
        natural_earth_version=natural_earth_version,
    )
    final_dir = snapshots_dir / snapshot_id
    if final_dir.exists():
        raise FileExistsError(
            f"Snapshot {snapshot_id} already exists. Re-run the Wikidata stage to create "
            "a new immutable source snapshot, or remove the unpublished directory explicitly."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix=f".{snapshot_id}.", dir=snapshots_dir))
    try:
        (temp_dir / "quizzes").mkdir()
        (temp_dir / "maps").mkdir()
        (temp_dir / "assets").mkdir()

        quiz_rel = f"/snapshots/{snapshot_id}/quizzes/europe-leader.json"
        map_rel = f"/snapshots/{snapshot_id}/maps/europe.geojson"
        images_rel = f"/snapshots/{snapshot_id}/assets/images.json"

        manifest = {
            "snapshotId": snapshot_id,
            "generatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sources": {
                "wikidataFetchedAt": leader_dataset["generatedAt"],
                "commonsFetchedAt": None,
                "naturalEarthVersion": natural_earth_version,
            },
            "answerNormalizationVersion": leader_dataset["normalizationVersion"],
            "quizzes": {"europe-leader": quiz_rel},
            "maps": {"europe": map_rel},
            "images": images_rel,
        }

        # Plain writes are safe inside the unpublished temporary directory.
        with (temp_dir / "quizzes" / "europe-leader.json").open("w", encoding="utf-8") as file:
            json.dump(quiz, file, ensure_ascii=False, indent=2)
            file.write("\n")
        with (temp_dir / "maps" / "europe.geojson").open("w", encoding="utf-8") as file:
            json.dump(map_geojson, file, ensure_ascii=False, separators=(",", ":"))
            file.write("\n")
        with (temp_dir / "assets" / "images.json").open("w", encoding="utf-8") as file:
            json.dump({}, file)
            file.write("\n")
        with (temp_dir / "manifest.json").open("w", encoding="utf-8") as file:
            json.dump(manifest, file, ensure_ascii=False, indent=2)
            file.write("\n")

        os.replace(temp_dir, final_dir)
        write_json_atomic(
            frontend_public_dir / "latest.json",
            {
                "snapshotId": snapshot_id,
                "manifest": f"/snapshots/{snapshot_id}/manifest.json",
            },
        )
        return final_dir
    except BaseException:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        raise
