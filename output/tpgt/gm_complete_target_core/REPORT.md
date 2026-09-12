# TPGT-GM-B1.1 Complete-Target Core Panel Construction and Cross-Scene Azimuth Validation

## Stop point

This run performs optical-only candidate construction and an optical-only PERSON scout. Human review is required before any candidate becomes frozen core. Because no review decision file was supplied, SAR manual reference was not opened and mapping validation remains blocked by design.

## Direct answers

### Q1. Complete-CAR identities

Optical-only AUTO_CANDIDATE counts are GM011=1, GM017=4, GM019=1. They are not human-confirmed core yet.

### Q2. Coverage and continuity

Each candidate row reports optical support range, full-visible frame count, interior-bbox count, and maximum contiguous complete run. Same-vehicle frames are not treated as independent vehicles.

### Q3–Q4. Frozen and scene-specific mapping

GM17 frozen mapping was not applied because there is no HUMAN_CONFIRMED_COMPLETE freeze. GM11/GM19 are therefore not assigned borrowed mapping values. Scene-specific and shared models are NOT_RUN; evidence is insufficient until review is completed.

### Q5–Q8. Cross-scene and corridor decision

No global/shared-slope/scene-specific model is promoted in this run. Vehicle-level holdout and corridor precision are NOT_ESTABLISHED. Continue mapping optimization only after a human-frozen panel exists; until then, STOP.

### Q9. PERSON scout

No clear continuous complete PERSON candidate was found. Existing caches provided only singleton detections (GM011/GM017); GM019 had no usable person detection in the scoped mature caches. Final PERSON core is NONE_FOUND; PERSON motion remains UNKNOWN.

### Q10. A-line recommendations

No events are recommended yet. Review the small optical contact-sheet panel first; after explicit ACCEPT CORE decisions, rerun with a frozen review file, then open SAR manual reference for B1.1 mapping validation. Do not modify A-line records.

## Deferred complexity

Deferred non-core optical vehicle identities: 16. They remain outside core because full-visible/interior temporal evidence was insufficient; no truncation correction or hard-case analysis was performed.

## Provenance

Optical identity registry: `D:\profile\research\optical-sar-visual-diagnosis-data-foundation\manifests\oty2\oty2_p1e_canonical_optical_vehicle_registry.csv`
Optical frame states: `D:\profile\research\optical-sar-visual-diagnosis-data-foundation\manifests\oty2\oty2_p1e_canonical_vehicle_frame_states.csv`
Existing detector caches were used only for PERSON discovery; detector confidence was not treated as human truth.

## Validation

Mapping validation status: `BLOCKED_NO_HUMAN_FROZEN_CORE_PANEL`
No SAR GT, SAR brightness, residual, IoU, or SAR response was used during candidate selection.

## Outputs

See `00_source_audit`, `01_complete_car_candidates`, `02_complete_car_core`, `03_mapping_validation`, `04_person_scout`, `05_contact_sheets`, `06_handoff`, and `07_validation`.