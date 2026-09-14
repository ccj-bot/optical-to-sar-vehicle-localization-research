"""Exact text frozen before native execution, packaged as code for this round."""
import json

FROZEN_TEXT = '''{
  "scope": "Native nested aperture freeze, before corrected probe execution; not blind location choice",
  "native_image": "GM_RM017/GM_RM017_SARframes_gray/000344.png",
  "native_windows": {"W1": [1050, 965, 1230, 1055], "W2": [1020, 935, 1260, 1070], "W3": [990, 900, 1290, 1080]},
  "sampling": "native pixel slices only, half-open; no rotation/resizing/bilinear sampling",
  "context_policy": "Each window computed independently; no outside halo supplied; boundary-incomplete support explicit",
  "visual_regions_native_only_posthoc": {"main": [1060, 1022, 1215, 1047], "weak": [1105, 975, 1200, 998], "gap": [1110, 998, 1190, 1022]},
  "visual_regions_chart_only_posthoc": {"main": [12, 3, 150, 23], "weak": [22, 46, 110, 69]},
  "local_rank": {"window": 13, "percentile": 78, "strict_comparison": true},
  "oriented": {"directions": [[1,0],[0,1],[1,1],[1,-1]], "transverse_offsets": [2,4], "proposal_sigma": 1, "gaussian_radius_factor": 3, "minimum_run_pixels": 3, "numeric_epsilon": 1e-9},
  "scale_audit": [0,1,2,4],
  "group": {"anchor_center_radius_px": 24, "lateral_tolerance_px": 3, "endpoint_gap_px": 12, "union_extent_px": 48, "transitive_closure": false},
  "budgets": {"fragments": 5000, "pair_hypotheses": 5000},
  "stop_policy": "No window change, parameter sweep, ranking or score after outcomes. Dense/coincident groups remain unresolved."
}
'''
CONFIG = json.loads(FROZEN_TEXT)
