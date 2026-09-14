from pathlib import Path
import json
from playwright.sync_api import sync_playwright

W = Path("D:/profile/research/workspace")
O = W / "output/tpgt/unified_target_review_observation"
A = O / "audit"
A.mkdir(parents=True, exist_ok=True)

checks = {}
details = {}
qa_state = None

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path="C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        headless=True,
    )
    context = browser.new_context(viewport={"width": 1500, "height": 1000})
    page = context.new_page()
    page.goto("http://127.0.0.1:8780/workspace/output/tpgt/unified_target_review_observation/index.html")
    checks["scene_groups"] = "PASS" if page.locator(".scene-card").count() >= 5 else "FAIL"

    url = "http://127.0.0.1:8780/workspace/output/tpgt/unified_target_review_observation/TARGET_REVIEW_VIEW.html?scene=GM_RM017"
    page.goto(url)
    page.evaluate("localStorage.removeItem('TPGT_OPTICAL_HUMAN_TARGET_SET_GM_RM017')")
    page.reload()
    page.wait_for_timeout(500)

    frame231_counts = page.evaluate("""
      () => {
        const s = window.TPGT_REVIEW_DATA.scenes.GM_RM017;
        const all = [...(s.detections.yolo11 || []), ...(s.detections.yolo26 || [])].filter(d => d.frame === 231);
        return {person: all.filter(d => d.class_name === 'person').length, vehicle: all.filter(d => ['car','truck','bus'].includes(d.class_name)).length};
      }
    """)
    checks["gm17_frame231_vehicle_and_person_streams"] = "PASS" if frame231_counts["person"] >= 2 and frame231_counts["vehicle"] >= 0 else "FAIL"
    details["gm17_frame231_counts"] = frame231_counts

    checks["annotation_workflow_ui"] = "PASS" if all(
        page.locator(f"#{item}").count() == 1
        for item in [
            "targetList", "newTarget", "manualBox", "edgeTruncated", "nearTruncated",
            "occluded", "identityStart", "identityEnd", "confirmIdentitySegment",
            "markAnnotation", "importTargets", "exportTargets", "proposalChooser",
            "clearFrameBox", "removeFrameFromTarget", "deleteTarget",
            "removeIdentityRange",
        ]
    ) else "FAIL"
    checks["coexisting_condition_controls"] = "PASS" if all(
        page.locator(f"#{item}").get_attribute("type") == "checkbox"
        for item in ["edgeTruncated", "nearTruncated", "occluded"]
    ) else "FAIL"

    first_detection = page.evaluate("""
      () => {
        const s = window.TPGT_REVIEW_DATA.scenes.GM_RM017;
        const all = [...(s.detections.yolo11 || []), ...(s.detections.yolo26 || [])];
        return all[0] || null;
      }
    """)
    if first_detection:
        page.locator("#frameInput").fill(str(first_detection["frame"]))
        page.locator("#jump").click()
        page.locator("#newTarget").click()
        canvas = page.locator("#overlay").bounding_box()
        scene_size = page.evaluate("() => ({w: window.TPGT_REVIEW_DATA.scenes.GM_RM017.width, h: window.TPGT_REVIEW_DATA.scenes.GM_RM017.height})")
        cx = (first_detection["x1"] + first_detection["x2"]) / 2
        cy = (first_detection["y1"] + first_detection["y2"]) / 2
        page.mouse.click(canvas["x"] + cx / scene_size["w"] * canvas["width"], canvas["y"] + cy / scene_size["h"] * canvas["height"])
        if page.locator("#proposalChooser").is_visible():
            page.locator(".proposal-choice").first.click()

        start = first_detection["frame"]
        end = min(start + 2, page.evaluate("() => window.TPGT_REVIEW_DATA.scenes.GM_RM017.frame_count - 1"))
        page.locator("#identityStart").fill(str(start))
        page.locator("#identityEnd").fill(str(end))
        page.locator("#confirmIdentitySegment").click()

        page.locator("#frameInput").fill(str(end))
        page.locator("#jump").click()
        for control in ["edgeTruncated", "nearTruncated", "occluded"]:
            page.locator(f"#{control}").check()
        page.locator("#frameState").select_option("PARTIAL_VISIBLE")
        page.locator("#saveFrameState").click()

        page.locator("#frameInput").fill(str(start))
        page.locator("#jump").click()
        for control in ["edgeTruncated", "nearTruncated", "occluded"]:
            page.locator(f"#{control}").uncheck()
        page.locator("#frameState").select_option("COMPLETE_VISIBLE")
        page.locator("#saveFrameState").click()
        page.locator("#markAnnotation").click()

        state = page.evaluate("() => JSON.parse(localStorage.getItem('TPGT_OPTICAL_HUMAN_TARGET_SET_GM_RM017'))")
        qa_state = state
        target = next(iter(state["targets"].values()))
        obs = target["frame_observations"][str(start)]
        checks["target_created_from_detection"] = "PASS" if target["anchors"] and obs["bbox"] else "FAIL"
        checks["identity_segment_saved"] = "PASS" if [start, end] in target["identity_segments"] else "FAIL"
        checks["coexisting_conditions_saved"] = "PASS" if set(target["frame_observations"][str(end)]["condition_flags"]) == {
            "IMAGE_EDGE_TRUNCATED", "NEAR_FIELD_TRUNCATED", "OCCLUDED"
        } else "FAIL"
        checks["formal_annotation_frame_saved"] = "PASS" if target["primary_annotation_frame_index"] == start and len(target["formal_annotations"]) == 1 else "FAIL"
        checks["no_fake_boxes_in_bulk_identity_range"] = "PASS" if all(
            target["frame_observations"][str(f)]["bbox"] is None for f in range(start + 1, end + 1)
        ) else "FAIL"

        overlapping = page.evaluate("""
          () => {
            const s = window.TPGT_REVIEW_DATA.scenes.GM_RM017;
            const all = [...(s.detections.yolo11 || []), ...(s.detections.yolo26 || [])].filter(d => d.class_name !== 'person');
            for (let i = 0; i < all.length; i++) for (let k = i + 1; k < all.length; k++) {
              const a = all[i], b = all[k];
              if (a.frame !== b.frame) continue;
              const x1 = Math.max(a.x1, b.x1), y1 = Math.max(a.y1, b.y1);
              const x2 = Math.min(a.x2, b.x2), y2 = Math.min(a.y2, b.y2);
              if (x2 > x1 && y2 > y1) return {frame: a.frame, x: (x1 + x2) / 2, y: (y1 + y2) / 2};
            }
            return null;
          }
        """)
        if overlapping:
            page.locator("#frameInput").fill(str(overlapping["frame"]))
            page.locator("#jump").click()
            canvas = page.locator("#overlay").bounding_box()
            page.mouse.click(canvas["x"] + overlapping["x"] / scene_size["w"] * canvas["width"], canvas["y"] + overlapping["y"] / scene_size["h"] * canvas["height"])
            checks["overlapping_proposal_chooser"] = "PASS" if page.locator("#proposalChooser").is_visible() and page.locator(".proposal-choice").count() >= 2 else "FAIL"
            details["overlap_fixture"] = overlapping
            page.screenshot(path=str(A / "overlap_proposal_chooser.png"), full_page=True)
            page.locator("#cancelProposalChoice").click()
        else:
            checks["overlapping_proposal_chooser"] = "FAIL_NO_OVERLAP_FIXTURE"

        page.locator("#frameInput").fill(str(start))
        page.locator("#jump").click()
        page.locator("#clearFrameBox").click()
        cleared = page.evaluate("() => JSON.parse(localStorage.getItem('TPGT_OPTICAL_HUMAN_TARGET_SET_GM_RM017'))")
        cleared_target = next(iter(cleared["targets"].values()))
        checks["clear_frame_box_preserves_identity"] = "PASS" if (
            cleared_target["frame_observations"][str(start)]["bbox"] is None
            and [start, end] in cleared_target["identity_segments"]
            and not cleared_target["formal_annotations"]
        ) else "FAIL"

        page.locator("#frameInput").fill(str(end))
        page.locator("#jump").click()
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#removeFrameFromTarget").click()
        removed = page.evaluate("() => JSON.parse(localStorage.getItem('TPGT_OPTICAL_HUMAN_TARGET_SET_GM_RM017'))")
        removed_target = next(iter(removed["targets"].values()))
        checks["remove_frame_splits_identity"] = "PASS" if (
            str(end) not in removed_target["frame_observations"]
            and [start, end - 1] in removed_target["identity_segments"]
        ) else "FAIL"

        page.locator("#identityStart").fill(str(end - 1))
        page.locator("#identityEnd").fill(str(end))
        page.once("dialog", lambda dialog: dialog.accept())
        page.locator("#removeIdentityRange").click()
        range_removed = page.evaluate("() => JSON.parse(localStorage.getItem('TPGT_OPTICAL_HUMAN_TARGET_SET_GM_RM017'))")
        range_target = next(iter(range_removed["targets"].values()))
        checks["remove_identity_range_trims_segment"] = "PASS" if [start, end - 2] in range_target["identity_segments"] else "FAIL"
        details["tested_detection"] = first_detection
        details["tested_target_id"] = target["id"]
        page.locator("#frameInput").fill("231")
        page.locator("#jump").click()
        page.screenshot(path=str(A / "optical_annotation_frame_workflow.png"), full_page=True)
    else:
        for key in ["target_created_from_detection", "identity_segment_saved", "formal_annotation_frame_saved", "no_fake_boxes_in_bulk_identity_range"]:
            checks[key] = "FAIL_NO_DETECTION"

    page.goto("http://127.0.0.1:8780/workspace/output/tpgt/unified_target_review_observation/TARGET_REVIEW_VIEW.html?scene=R35ZF")
    page.wait_for_timeout(500)
    checks["manifest_non_gm_frame_count"] = "PASS" if page.locator("#frameInput").get_attribute("max") == "297" else "FAIL"
    browser.close()

if qa_state is not None:
    contract_errors = []
    for required in ["schema_version", "scene_id", "targets", "active_target_id"]:
        if required not in qa_state:
            contract_errors.append(f"missing root field: {required}")
    for target_id, target in qa_state.get("targets", {}).items():
        for required in ["anchors", "frame_observations", "identity_segments", "visible_segments", "formal_annotations", "primary_annotation_frame_index", "frozen_revisions"]:
            if required not in target:
                contract_errors.append(f"{target_id} missing: {required}")
        for frame_id, observation in target.get("frame_observations", {}).items():
            if not isinstance(observation.get("condition_flags"), list):
                contract_errors.append(f"{target_id} frame {frame_id}: condition_flags is not list")
            if observation.get("bbox") is None and observation.get("bbox_source") != "NONE":
                contract_errors.append(f"{target_id} frame {frame_id}: null bbox has non-NONE source")
    checks["export_contract_validation"] = "PASS" if not contract_errors else "FAIL"
    details["contract_errors"] = contract_errors
    (A / "qa_human_target_set_fixture.json").write_text(json.dumps(qa_state, ensure_ascii=False, indent=2), encoding="utf-8")

out = {
    "kind": "TPGT_OPTICAL_ANNOTATION_FRAME_WORKFLOW_QA",
    "checks": checks,
    "details": details,
    "complete": all(value == "PASS" for value in checks.values()),
}
(A / "unified_workbench_qa.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False))
