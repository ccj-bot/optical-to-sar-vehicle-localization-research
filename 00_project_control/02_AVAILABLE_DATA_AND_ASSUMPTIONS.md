# Available Data and Assumptions

## Available Data

The project has:

- complete optical frame sequences for three scenes;
- SAR gray frame sequences;
- SAR pseudo-color frame sequences;
- DepthPro outputs;
- track context where available;
- SAR candidate pools;
- empirical optical-to-SAR azimuth mapping;
- 231 GT-reviewed car samples with manually reviewed SAR boxes;
- prior ROI, range, candidate, and SAR evidence experiments.

## Missing Calibration

The project does not have:

- calibrated camera intrinsics;
- calibrated camera-to-radar extrinsics;
- strict metric 3D camera-to-SAR projection.

Camera and radar are physically close and roughly similar in height, which supports empirical directional constraints but not exact metric projection.

## Optical Information That Can Transfer

Optical information may provide bounded constraints and state cues:

1. vehicle center direction;
2. approximate heading or heading uncertainty;
3. visible vehicle support;
4. vehicle size range;
5. field-of-view position;
6. bottom truncation;
7. side truncation;
8. edge contact;
9. occlusion state;
10. nearby-object ambiguity;
11. track stability;
12. possible identity drift;
13. short-window temporal consistency;
14. weak relative depth or near/middle/far cues from DepthPro.

## Optical Information That Cannot Transfer Directly

Optical information cannot directly provide:

1. final SAR box;
2. SAR pseudo-color intensity;
3. radar return strength;
4. exact SAR range;
5. exact vehicle boundary in SAR;
6. optical texture, color, or shadow as SAR evidence.

## SAR Evidence Must Confirm

SAR evidence should confirm:

- compact vehicle-sized body support;
- side evidence;
- corner evidence;
- end-cap evidence;
- near-side response;
- local contrast;
- consistency with expected vehicle footprint;
- temporal consistency where available.

SAR evidence should reject:

- isolated peaks;
- road-edge-like long structures;
- static background clutter;
- diffuse support;
- support leakage outside vehicle-sized footprint;
- cap-only rescue;
- nearby wrong vehicle-like structures.
