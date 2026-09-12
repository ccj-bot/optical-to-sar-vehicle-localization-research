# Cross-scene mapping comparison

| Layer | GM_RM011 | GM_RM017 | GM_RM019 | Cross-scene decision |
|---|---|---|---|---|
| Time FPS/index semantics | 24/50, nominal only | 24/50, nominal only | 24/50, nominal only | SHARED operational assumption; exact sync UNKNOWN |
| SAR native/display geometry | 2308×1334, fan origin (1154,1330.6) | same | same | SHARED display transform; upstream imaging chain unresolved |
| 0.03 m/px | display grid approximation | display grid approximation | display grid approximation | SHARED semantics; not true resolution |
| Optical→SAR azimuth | no eligible scene-specific anchors | 20 development + 45 held-out; linear open-book fit | no eligible scene-specific anchors | SCENE_SPECIFIC / UNRESOLVED; no global promotion |

The only shared claim supported by current evidence is the deterministic display/fan relation and the operational FPS convention. Exact synchronization, optical-to-azimuth calibration, and uncertainty remain scene-specific or unresolved. GM017's fit is GT/manual-reference derived and is not runtime permission.