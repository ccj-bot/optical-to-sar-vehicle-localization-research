#!/usr/bin/env python3
"""Frozen synthetic tests for the M0A source-to-destination soft mask warp."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


SCRIPT_PATH = Path(__file__).resolve()
TASK_DIR = SCRIPT_PATH.parent
RUNNER_PATH = TASK_DIR / "run_m0a_r02_lag1_q95_region_support_transport.py"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def weighted_centroid(mask: np.ndarray) -> tuple[float, float]:
    total = float(mask.sum())
    if total <= 0:
        raise AssertionError("warped support is empty")
    yy, xx = np.mgrid[0 : mask.shape[0], 0 : mask.shape[1]]
    return float((mask * xx).sum() / total), float((mask * yy).sum() / total)


def assert_close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise AssertionError(f"{label}: actual={actual} expected={expected} tol={tolerance}")


def run_tests() -> dict[str, Any]:
    runner = load_module("m0a_runner_for_warp_tests", RUNNER_PATH)
    freeze = runner.verify_protocol_freeze()
    tests: list[dict[str, Any]] = []

    identity = np.zeros((9, 11), np.float32)
    identity[2:6, 3:8] = 1.0
    identity_warp = runner.soft_affine_translation_warp(identity, 0.0, 0.0)
    identity_error = float(np.max(np.abs(identity_warp - identity)))
    assert_close(identity_error, 0.0, 0.0, "identity max error")
    tests.append({"name": "IDENTITY_TRANSLATION", "status": "PASS", "max_abs_error": identity_error})

    integer = np.zeros((10, 12), np.float32)
    integer[3:5, 4:7] = 1.0
    expected_integer = np.zeros_like(integer)
    expected_integer[5:7, 7:10] = 1.0
    integer_warp = runner.soft_affine_translation_warp(integer, 3.0, 2.0)
    integer_error = float(np.max(np.abs(integer_warp - expected_integer)))
    assert_close(integer_error, 0.0, 0.0, "integer translation max error")
    tests.append({"name": "INTEGER_TRANSLATION_DIRECTION", "status": "PASS", "dx": 3.0, "dy": 2.0, "max_abs_error": integer_error})

    subpixel = np.zeros((9, 9), np.float32)
    subpixel[4, 4] = 1.0
    subpixel_warp = runner.soft_affine_translation_warp(subpixel, 0.25, 0.5)
    expected_weights = {(4, 4): 0.375, (4, 5): 0.125, (5, 4): 0.375, (5, 5): 0.125}
    subpixel_error = max(
        abs(float(subpixel_warp[y, x]) - value) for (y, x), value in expected_weights.items()
    )
    assert_close(float(subpixel_warp.sum()), 1.0, 1e-7, "subpixel support sum")
    assert_close(subpixel_error, 0.0, 1e-7, "subpixel bilinear weights")
    tests.append({"name": "SUBPIXEL_BILINEAR_OCCUPANCY", "status": "PASS", "dx": 0.25, "dy": 0.5, "max_weight_error": subpixel_error})

    boundary = np.zeros((8, 8), np.float32)
    boundary[4, 7] = 1.0
    boundary_warp = runner.soft_affine_translation_warp(boundary, 0.5, 0.0)
    boundary_sum = float(boundary_warp.sum())
    assert_close(boundary_sum, 0.5, 1e-7, "boundary support sum")
    tests.append({"name": "BOUNDARY_LOSS_NO_RENORMALIZATION", "status": "PASS", "source_support_total": 1.0, "warped_support_before_valid_clip": boundary_sum, "lost_support": 1.0 - boundary_sum})

    p0 = load_module("p0_for_m0a_warp_tests", runner.P0_SCRIPT)
    inputs = runner.prepare_runtime_inputs()
    point_rows: list[dict[str, Any]] = []
    selected_pairs = [inputs["pairs"][0], inputs["pairs"][len(inputs["pairs"]) // 2], inputs["pairs"][-1]]
    for pair in selected_pairs:
        frame = inputs["frames"][pair["from_frame_uid"]]
        q95 = frame["labels"][runner.Q95]
        coords = np.argwhere(q95 > 0)
        if len(coords) < 3:
            raise AssertionError(f"insufficient q95 representative points for {pair['from_frame_uid']}")
        picks = coords[[len(coords) // 4, len(coords) // 2, (3 * len(coords)) // 4]]
        model = {"model": "M1", "parameters": {"translation_xy": [pair["dx_px"], pair["dy_px"]]}}
        for y, x in picks:
            source = np.zeros_like(q95, dtype=np.float32)
            source[int(y), int(x)] = 1.0
            warped = runner.soft_affine_translation_warp(source, pair["dx_px"], pair["dy_px"])
            cx, cy = weighted_centroid(warped)
            displacement = p0.predict_displacement(
                model, np.array([[float(x), float(y)]], np.float64), inputs["geometry"]
            )[0]
            expected_x = float(x) + float(displacement[0])
            expected_y = float(y) + float(displacement[1])
            error = math.hypot(cx - expected_x, cy - expected_y)
            if error > 0.05:
                raise AssertionError(
                    f"point-vs-mask mismatch {pair['from_frame']}->{pair['to_frame']} error={error}"
                )
            point_rows.append(
                {
                    "from_frame": pair["from_frame"],
                    "to_frame": pair["to_frame"],
                    "source_x_px": int(x),
                    "source_y_px": int(y),
                    "dx_px": pair["dx_px"],
                    "dy_px": pair["dy_px"],
                    "warped_centroid_x_px": cx,
                    "warped_centroid_y_px": cy,
                    "predicted_x_px": expected_x,
                    "predicted_y_px": expected_y,
                    "euclidean_error_px": error,
                }
            )
    tests.append(
        {
            "name": "P0_POINT_VS_MASK_CONSISTENCY",
            "status": "PASS",
            "representative_point_count": len(point_rows),
            "max_euclidean_error_px": max(row["euclidean_error_px"] for row in point_rows),
            "tolerance_px": 0.05,
            "points": point_rows,
        }
    )
    return {
        "schema": "PERSON_M0A_WARP_SYNTHETIC_TESTS_V1",
        "status": "PASS",
        "tests_passed": len(tests),
        "tests_expected": 5,
        "protocol_sha256": freeze["protocol_sha256"],
        "warp_semantics": "SOURCE_TO_DESTINATION_SOFT_OCCUPANCY_NOT_CONSERVED_MASS",
        "tests": tests,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the frozen JSON result")
    args = parser.parse_args()
    result = run_tests()
    if args.write:
        runner = sys.modules["m0a_runner_for_warp_tests"]
        runner.write_json(runner.SYNTHETIC_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
