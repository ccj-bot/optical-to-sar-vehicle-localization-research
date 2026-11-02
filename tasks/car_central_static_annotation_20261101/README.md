> HISTORICAL V1 — The user reported late-sequence drift on2026-11-02. This version retains fixed358 dimensions/angle and moves boxes using short-response midpoints; it is not a reliable full-sequence reference. See the separatev2 repair andv3 bright-band margin tasks.

# CAR central static vehicle annotation

Current user priority (2026-11-01): prioritize stationary vehicles that have a
temporally complete appearance inside the whole SAR image. Establish clear
annotations for central vehicles first, followed by temporal prediction for
complete vehicles. Edge and near-field cases are later mechanism work.

The previous three-question ambiguity queue is superseded. The user confirmed
that optical conflict panels1–4 show the same vehicle (003) and5–6 another (004).
No additional confirmation of that obvious optical correspondence is needed.

Scope: inventory the current CAR cohort; inspect full raw SAR sequences; build
the first central complete-vehicle temporal annotation segment. Use existing
manual SAR anchors with direct native-frame readings at additional keyframes.
Record keyframe drawing versus interpolation without making it a workflow gate.
Outputs: workspace/output/car_central_static_annotation_20261101.
Interpreter: python -X utf8 -B, CPU.
No old_work dependency. Source annotations remain available as originals.

Deliverable: clear labelled whole-frame sequence, per-vehicle temporal labels,
scene inventory and a short current entry. No new review-question portal.

## Executed

- `scout.py`: inventory50 existing candidate records across8 scenes and render raw scene overview. Raw scenes actually inspected.
- `annotate.py`:3 parked cars002/003/005, frames358–494,24 native keyframe readings,411 per-frame rows. Whole-body extent inherited from user358, per-car position adjusted by directly read local structure; intervening frames interpolated.
- Whole native SAR video plus optical/SAR paired video,137 decoded frames each; half-speed15fps playback of30fps source.
- Output `START_HERE.md`, `ANNOTATIONS.json`, `KEYFRAME_ANNOTATIONS.json`, `CENTRAL_STATIC_SAR.mp4`.

This is a concrete first temporal annotation version, not newly measured body
dimensions at every time. No public-motion score, optimizer or track-ID match
chooses the new keyframe locations. The selected raw frames and existing
manual358 extent are the annotation inputs. Sources were not overwritten.
