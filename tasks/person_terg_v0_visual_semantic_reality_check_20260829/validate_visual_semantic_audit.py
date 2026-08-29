from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


SCRIPT = Path(__file__).resolve()
TASK = SCRIPT.parent
WORKSPACE = TASK.parents[1]
OUTPUT = WORKSPACE / "output" / "person_terg_v0_visual_semantic_reality_check_20260829"
TABLES = OUTPUT / "tables"
LOG = WORKSPACE / "logs" / "20260829_person_terg_v0_visual_semantic_reality_check.md"
MANIFEST = OUTPUT / "ARTIFACT_MANIFEST.sha256"
VALIDATION_REPORT = OUTPUT / "validation_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def owned_files() -> list[Path]:
    files = [path for path in TASK.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
    files.extend(
        path
        for path in OUTPUT.rglob("*")
        if path.is_file() and path not in {MANIFEST, VALIDATION_REPORT}
    )
    if LOG.exists():
        files.append(LOG)
    return sorted(set(files), key=lambda path: path.relative_to(WORKSPACE).as_posix())


def write_manifest() -> None:
    lines = [f"{sha256(path)}  {path.relative_to(WORKSPACE).as_posix()}" for path in owned_files()]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_manifest() -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        rows[relative] = digest
    return rows


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    if args.write_manifest:
        write_manifest()

    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object = "") -> None:
        checks.append({"name": name, "pass": bool(condition), "detail": detail})

    required = [
        OUTPUT / "TERG_V0_VISUAL_SEMANTIC_AUDIT.md",
        OUTPUT / "diagnostic_summary.json",
        TABLES / "independent_visual_review_ledger.csv",
        TABLES / "edge_evidence_descriptors.parquet",
        TABLES / "bridge_criticality.csv",
        TABLES / "possible_relation_set_audit.csv",
        TABLES / "temporal_stratification_contraction_audit.csv",
        TABLES / "exact_one_soft_overlap_edge_registry.csv",
        TABLES / "relation_set_case_registry.csv",
        MANIFEST,
        LOG,
    ]
    for path in required:
        check(f"required:{path.name}", path.is_file(), str(path))

    summary = json.loads((OUTPUT / "diagnostic_summary.json").read_text(encoding="utf-8"))
    check("phase_a_only", summary.get("phase") == "PHASE_A_READ_ONLY_DIAGNOSIS")
    check("mechanism_not_modified", summary.get("mechanism_modified") is False)
    check("confirmation_not_accessed", summary.get("confirmation_run_accessed") is False)
    check("supported_edges_3702", summary["edge_support_semantics"]["supported_edge_count"] == 3702)
    check("exact_one_edges_4", summary["edge_support_semantics"]["exact_one_soft_pixel_mass_edge_count"] == 4)
    check("conditioned_nodes_4328", summary["physical_node_semantics"]["conditioned_graph_node_rows"] == 4328)
    check("physical_regions_3056", summary["physical_node_semantics"]["unique_physical_sar_response_regions"] == 3056)
    check("shared_order_profiles_78", summary["relation_set"]["current_shared_order_undefined_profiles"] == 78)
    check("temporal_sets_88", summary["contraction_semantics"]["explanation_set_rows"] == 88)
    check("actual_pruned_nodes_zero", summary["contraction_semantics"]["actual_pruned_node_count"] == 0)
    check("timing_unverified", summary["timing_provenance"]["provenance_class"] == "UNVERIFIED_TIMING_MARGIN")

    edges = pd.read_parquet(TABLES / "edge_evidence_descriptors.parquet")
    relation = pd.read_csv(TABLES / "possible_relation_set_audit.csv")
    contraction = pd.read_csv(TABLES / "temporal_stratification_contraction_audit.csv")
    check("edge_table_rows_52460", len(edges) == 52460, len(edges))
    check("edge_table_supported_3702", int(edges["p0_supported_continuation"].sum()) == 3702)
    check("relation_profiles_85", len(relation) == 85, len(relation))
    check(
        "relation_shared_profiles_all_set_valued",
        int(
            relation["current_relative_order_compatibility"].eq("SHARED_RESPONSE_ORDER_UNDEFINED").sum()
        )
        == 78,
    )
    check("contraction_rows_88", len(contraction) == 88, len(contraction))
    check("exact_one_registry_4", csv_rows(TABLES / "exact_one_soft_overlap_edge_registry.csv") == 4)
    check("relation_case_registry_2", csv_rows(TABLES / "relation_set_case_registry.csv") == 2)
    check("visual_ledger_nonempty", csv_rows(TABLES / "independent_visual_review_ledger.csv") >= 18)

    figure_paths = [Path(path) for path in summary["output_figures"]]
    check("all_summary_figures_exist", all(path.is_file() for path in figure_paths), len(figure_paths))
    check("exact_one_figures_4", len(list((OUTPUT / "figures" / "exact_one_soft_overlap_edges").glob("*.png"))) == 4)
    check("relation_figures_2", len(list((OUTPUT / "figures" / "relation_set_cases").glob("*.png"))) == 2)

    manifest = load_manifest()
    current = {path.relative_to(WORKSPACE).as_posix(): sha256(path) for path in owned_files()}
    check("manifest_path_set_matches", set(manifest) == set(current), {"manifest": len(manifest), "current": len(current)})
    mismatches = sorted(path for path in set(manifest) & set(current) if manifest[path] != current[path])
    check("manifest_hashes_match", not mismatches, mismatches)
    check("no_old_work_paths", all("old_work" not in path.lower() for path in current))

    failed = [item for item in checks if not item["pass"]]
    report = {
        "schema": "PERSON_TERG_V0_VISUAL_SEMANTIC_AUDIT_VALIDATION_V1",
        "status": "PASS" if not failed else "FAIL",
        "check_count": len(checks),
        "failed_count": len(failed),
        "checks": checks,
        "note": "Integrity and schema validation only; not a scientific conclusion.",
    }
    VALIDATION_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
