from __future__ import annotations

import hashlib
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve()
WORKSPACE = SCRIPT.parents[2]
OUTPUT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "m0b1_v2_cross_modal_direction_discrimination"
)
MANIFEST = OUTPUT / "final_output_manifest.json"
QA = OUTPUT / "VISUAL_QA_AND_CLOSEOUT.md"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def main() -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_path = {item["path"]: item for item in payload["files"]}
    for path in (QA, SCRIPT):
        relative = str(path.relative_to(WORKSPACE))
        by_path[relative] = {
            "path": relative,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
    payload["files"] = list(by_path.values())
    payload["visual_qa_completed"] = True
    payload["visual_qa_aggregate_conflict_observed"] = False
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
