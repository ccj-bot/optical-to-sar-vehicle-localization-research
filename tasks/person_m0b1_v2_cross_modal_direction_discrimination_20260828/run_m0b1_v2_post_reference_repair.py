from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve()
TASK_DIR = SCRIPT.parent
WORKSPACE = TASK_DIR.parents[1]
RUNNER = TASK_DIR / "run_m0b1_v2_cross_modal_direction.py"
OUTPUT = (
    WORKSPACE
    / "output"
    / "person_physics_guided_image_domain_study_20260824"
    / "m0b1_v2_cross_modal_direction_discrimination"
)
AMENDMENT = OUTPUT / "AMENDMENT_01_POST_REFERENCE_SENTINEL_PAIR_INDEX.md"


def load_runner():
    spec = importlib.util.spec_from_file_location("m0b1_v2_frozen_runner", RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    module = load_runner()
    original = module.build_pairwise

    def repaired_build_pairwise(bank, matched):
        frame = original(bank, matched)
        metadata = (
            bank[["base_edge_id", "pair_index", "from_frame", "to_frame"]]
            .drop_duplicates("base_edge_id")
            .set_index("base_edge_id")
        )
        for column in ("pair_index", "from_frame", "to_frame"):
            missing = frame[column].isna() if column in frame.columns else None
            if column not in frame.columns:
                frame[column] = frame["primary_base_edge_id"].map(metadata[column])
            elif missing.any():
                frame.loc[missing, column] = frame.loc[missing, "primary_base_edge_id"].map(metadata[column])
        return frame

    module.build_pairwise = repaired_build_pairwise
    module.post_reference()

    manifest_path = OUTPUT / "final_output_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing = {item["path"] for item in manifest["files"]}
    for path in (SCRIPT, AMENDMENT):
        relative = str(path.relative_to(WORKSPACE))
        if relative not in existing:
            manifest["files"].append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": module.sha256_file(path),
                }
            )
    manifest["frozen_execution_amendment"] = {
        "name": "AMENDMENT_01_POST_REFERENCE_SENTINEL_PAIR_INDEX",
        "scientific_rule_changed": False,
        "pre_reference_outputs_changed": False,
    }
    module.write_json(manifest_path, manifest)

    ledger_path = OUTPUT / "execution_ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger["events"].append(
        {
            "stage": "FROZEN_EXECUTION_AMENDMENT_01_REPORTING_KEYS_ONLY",
            "completed_at": module.now_iso(),
        }
    )
    module.write_json(ledger_path, ledger)


if __name__ == "__main__":
    main()
