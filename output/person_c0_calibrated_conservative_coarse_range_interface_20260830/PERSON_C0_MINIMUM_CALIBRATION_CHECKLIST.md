# PERSON-C0 minimum calibration checklist

## Outcome target

Collect only the quantities needed to propagate a visible ground-contact interval into a conservative radar-relative range interval. Do not tune any quantity with PERSON SAR reference.

## 1. Camera intrinsics and distortion at the acquisition mode

- Measure: `fx, fy, cx, cy` and distortion coefficients for the optical camera used by R01ZF/R02ZF/R03ZF at native `3840x2160`.
- Tool: a printed rigid Charuco board is preferred; a checkerboard is acceptable.
- Procedure: capture at least 20-30 sharp views spanning image center, edges, different tilts, and working focus/zoom. Keep exposure and focus in the deployed mode.
- Initial quality order: target sub-pixel reprojection residuals, preferably median below about 0.5 px and no systematic edge residual; this is a collection QA target, not a guaranteed range-accuracy claim.
- Save: `person_camera_intrinsics_3840x2160.yaml` with camera serial/model, date, focus/zoom, image size, K, distortion model/coefficients, per-view residuals, and board specification. Preserve raw calibration images.
- Verify: undistort held-out board views and inspect straight lines/residual vectors across the full image.

## 2. Camera optical-center height and local attitude

- Measure: camera optical-center height above the local ground reference plus camera pitch and roll in the deployed mounting state.
- Tool: tape/steel rule or caliper for height; digital inclinometer or a surveyed level/board for attitude.
- Initial quality order: record height to about 5-10 mm and pitch/roll repeatability around 0.1-0.2 degrees. These are starting measurement targets; the interval propagation must later show whether they support +/-2 m.
- Save: `person_camera_ground_mount.yaml` with at least three repeated measurements, the adopted envelope, photos showing reference points, sign conventions, and the local ground definition.
- Verify: repeat after remounting and compare the envelope; do not keep a single reading without repeatability evidence.

## 3. Camera-to-radar rigid transform

- Measure: translation from camera optical center to radar origin and rotation between the camera and SAR fan coordinate conventions.
- Tool: direct physical measurement for translation plus surveyed common directions/targets for rotation. A calibration target visible in both modalities may be used if its physical correspondence is independently established.
- Initial quality order: translation around 1 cm and angular repeatability around 0.1-0.2 degrees are sensible first targets, subject to later sensitivity analysis.
- Save: `person_camera_to_radar_extrinsic.yaml` containing frame names, axis drawings, units, quaternion or rotation matrix, translation, uncertainty envelope, measurement method, and photographs.
- Verify: project several independent known ground directions/ranges; check left/right sign, origin, and range convention before PERSON use.

## 4. Local ground-plane envelope

- Measure: local plane normal and camera/radar origin offset, or a bounded slope envelope for the actual acquisition patch.
- Tool: level/inclinometer and measured ground points; a flat-ground assumption is allowed only when its spatial extent and slope envelope are recorded.
- Save: `person_local_ground_plane.yaml` with frame, normal convention, offset, valid spatial region, slope/roughness envelope, and date.
- Verify: measure multiple points across the PERSON working area and retain the worst credible envelope rather than only the best-fit plane.

## 5. Runtime footpoint observation interface

- Measure: not a single bbox-bottom pixel, but an interval `u in [u-,u+]`, `v in [v-,v+]` with one of `FOOTPOINT_OBSERVABLE`, `FOOTPOINT_PARTIAL`, `FOOTPOINT_CENSORED`, `FOOTPOINT_AMBIGUOUS`, or `FOOTPOINT_UNAVAILABLE`.
- Tool: the existing optical boxes plus a small manual protocol first; no new pose network is required for the initial calibration study.
- Save: CSV/Parquet columns for run/frame/hypothesis, state, interval bounds, boundary/occlusion reason, and reviewer provenance.
- Verify: double-review a stratified set containing clean, overlapping, doorway, image-boundary, and far-small PERSON cases. Never force an interval when ground contact is not visible.

## 6. Optional synchronization for temporal geometry

- Single-frame note: global platform pose is not required when camera-ground-radar geometry is fixed and range is expressed in the current radar frame.
- Temporal note: if range is propagated across frames or registered to the world, measure optical/SAR clock offset and drift and record platform pose/IMU/odometry with timestamps.
- Verify: use an observable common event or hardware trigger; frame-index/FPS zero-offset pairing is not a synchronization calibration.

## Integration gate

After files 1-5 exist, run deterministic corner/envelope propagation first. Report realized interval widths and ill-conditioned/unavailable rows before opening SAR PERSON reference. Only then compute post-reference radial-support retention and candidate contraction. A missing or censored range must always fall back to angle-only support and must never reject PERSON.
