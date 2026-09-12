# TPGT-GM-B1: GM Spatiotemporal Coordinate and Azimuth Mapping Reconciliation

## Scope and stop condition

This is a read-only reconciliation of time, native SAR pixels, display/fan coordinates, and optical-to-SAR azimuth support for GM_RM011/017/019. It does not define a target mechanism, alter the TPGT Observation Workbench, or produce final SAR boxes.

## Direct answers

### Q1. Optical/SAR time correspondence

All three scenes have 24 FPS optical and 50 FPS SAR stored frame indices. The available historical table supports `t_o=i/24`, `t_s=j/50` and `j≈round(i·50/24)` only as a nominal common-start operational hypothesis. Exact synchronization remains UNKNOWN; nearby SAR windows must retain local drift.

### Q2. Where does fixed 24→50 common-start hold?

It is internally consistent with the generated 368-row operational tables, but those rows are not independent sync truth. It is therefore usable for coarse frame-window construction across the stored domain, not for an exact synchronized frame claim.

### Q3. Offset, drift, piecewise correction

The historical fixed-offset reliability flag is false for all three scenes. T2 affine fits are descriptive; T3 piecewise/local models are not justified without independent anchors showing systematic drift.

### Q4. SAR pixel→display/fan/range/azimuth chain

Decoded SAR PNG pixel → display pixel is treated as identity at 2308×1334; display pixel → fan coordinates uses `r=hypot(x-1154,y-1330.6)` and `theta=atan2(x-1154,1330.6-y)`; inverse is deterministic for this display relation. The upstream sensor/imaging coordinate chain remains unresolved.

### Q5. Meaning of 0.03 m/px

It is a project/display physical-scale approximation for grid quantities. It is not true spatial resolution, PSF width, independent range measurement, or a universal scale for new65/PERSON.

### Q6. Historical optical→SAR azimuth formulas and GT use

The traceable global diagnostic proxy is `theta=0.0875154·u-40.413555`. It is GT/manual-reference derived, broad-azimuth-only, and runtime-incompatible. GM017 has a separate development linear refit in its contract; GM011/GM019 have no eligible scene-specific fit.

### Q7. Can the scenes share one mapping?

No evidence supports promoting one shared optical→azimuth calibration. The display/fan transform is shared; optical→azimuth calibration is scene-specific or unresolved.

### Q8. What is shared?

Stored image dimensions, display fan origin/formulas, and nominal FPS assumptions are shared operational layers. Scene-specific calibration, uncertainty, and exact synchronization are not shared.

### Q9. Mapping uncertainty

GM017 open-book development/held-out diagnostics report uncertainty in the azimuth contract (including held-out MAE/RMSE/p95). GM011/GM019 are UNKNOWN rather than assigned a borrowed value.

### Q10–Q11. Future A-line use

A future caller may explicitly load native pixel/display fan contracts and nominal time corridors. GT-calibrated optical→azimuth fits remain open-book/development only unless a separately authorized runtime calibration is established. A-line schemas and records are untouched.

### Q12. New GM optical target capability

Current answer: bounded azimuth corridor only for GM017 under explicit open-book use and within its observed u-domain; GM011/GM019 are currently unidentifiable at scene-specific mapping level. No scene supports a precise SAR azimuth point or final target box from optical alone.

## Scene summary

- **GM_RM011**: time=UNKNOWN; native/display=verified display contract; optical→azimuth=UNRESOLVED_NO_MAPPING_ELIGIBLE_ANCHORS; runtime corridor=False
- **GM_RM017**: time=UNKNOWN; native/display=verified display contract; optical→azimuth=DEVELOPMENT_CALIBRATED_OPEN_BOOK_ONLY; runtime corridor=False
- **GM_RM019**: time=UNKNOWN; native/display=verified display contract; optical→azimuth=UNRESOLVED_NO_MAPPING_ELIGIBLE_ANCHORS; runtime corridor=False

## Validation

- Coordinate round-trip: `PASS`; max error 0 px.
- Lineage: source and producer paths are recorded in `GM_MAPPING_LINEAGE.csv`; external producer paths are intentionally marked rather than copied into A-line.
- Time split: insufficient independent sync anchors; no fabricated train/holdout claim.
- Leakage: each mapping contract explicitly records GT/manual-reference/SAR-response usage.

## Outputs

See `00_audit`, `01_time`, `02_sar_coordinates`, `03_optical_to_azimuth`, `04_contracts`, `05_figures`, and `06_validation` under this output directory.
