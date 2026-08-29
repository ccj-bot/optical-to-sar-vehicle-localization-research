# TERG-D0 multimodal visual review ledger

Status: `DIRECT_MULTIMODAL_REVIEW_COMPLETE`

Scope: development runs `R01ZF/R02ZF/R03ZF` only. `R04ZF` and any new
confirmation data were not accessed. Optical overlays are runtime-visible raw
fragment observations/corridors. Magenta SAR contours are offline
reference-supported regions and are post-reference only. Red graph nodes/edges
and yellow q95 contours identify the selected explanation component; they are
not a tracker path or a PERSON assignment.

## Direct observations

| Pack | Review conclusion |
|---|---|
| 01 long single-object persistence | A raw optical fragment can remain observable for 107 SAR frames while the corridor contains many SAR alternatives. Several long P0-supported components coexist; persistence is observable, uniqueness is not. |
| 02 stable two-object order | Disjoint optical angular intervals preserve a stable left/right relation over a long segment. This is visually more stable than frame-to-frame magnitude descriptors. |
| 03 optical approach tendency | The endpoint gap decreases, but the SAR graph simultaneously contains persistence, deformation, split/merge-like and isolated alternatives. `approach` is therefore a descriptor, not a hard cross-modal event. |
| 04 optical separation tendency | Optical separation is visible, but no unique or same-name SAR event follows. The case supports a non-isomorphic compatibility relation only. |
| 05 optical order change | Category not observed in the development atlas. It is not promoted into TERG-v0. |
| 06 optical overlap uncertainty | Overlapping optical angular intervals make relative order genuinely set-valued. The correct representation is an uncertainty state, not a forced crossing or occlusion label. |
| 07 SAR split-like | The selected red component contains a frozen P0 one-to-many topology and a visible q95 structural change. It is an image-domain split-like hypothesis, not a PERSON split and not an identity decision. |
| 08 SAR merge-like | The selected component contains frozen P0 many-to-one topology. The morphology is observable, but it does not establish that optical objects merged or that multiple people share one physical scatterer. |
| 09 complete P0 continuity | `TERGXC_1FD4CF2856175478AA05` covers F0-F15 with 16 nodes and 15 supported edges. Red/yellow highlights show complete temporal continuity inside the optical corridor. |
| 10 partial/unavailable P0 continuity | `TERGXC_A97D2FC78FCD287ADEEE` covers only F0-F4, then terminates while other alternatives remain. This visibly separates partial continuity from complete continuity without deleting the partial hypothesis. |
| 11 likely grounded potential disambiguation | The same complete component is supported on all four available reference frames and is `LIKELY_SUPPORTED_EXPLORATORY`; the partial component has zero reference-supported frames. This is potential explanation-set contraction, not confirmation. |
| 12 multiple-valid/ambiguous grounding | Category not observed. Absence is retained; it is not converted to evidence for uniqueness. |
| 13 boundary/censoring | A boundary-touching optical observation remains interpretable as censored support. It must not be treated as invalid or as a physical entry/exit event. |
| 14 birth/death | The shown endpoints are component boundaries within a dense graph. They visually demonstrate why raw response birth/death is highly sensitive to q95 component fragmentation and cannot be treated as physical appearance/disappearance. |
| 15 shared-response grounding | The same reference-supported component lies inside overlapping optical corridors and supports both optical hypotheses at shared frames. SAR order is therefore undefined even though optical order is stable. |
| 16 counterexample | Stable optical order coexists with shared SAR response structure. This directly refutes the assumption that optical order must always yield determinate SAR order. |

## Visual decisions

1. Freeze optical presence/lifecycle interval, stable/set-valued relative order,
   optical corridor support, P0-supported SAR persistence, shared-response/order
   undefined state, and SAR split/merge/deformation structural hypotheses.
2. Keep approach/separation/stable gap as descriptors only.
3. Downgrade raw SAR component birth/death to component-boundary hypotheses.
4. Reject direct same-name optical-event to SAR-event mapping.
5. Keep all selected components as members of an explanation set. No visual
   review authorizes a unique path, identity assignment, final center, or box.

## Renderer verification

The rerendered component packs visibly distinguish complete and partial
components using red graph highlights and yellow q95 contours while preserving
magenta offline-reference overlays. The pre-reference manifest SHA256 remains
`F2B54B38E7516C547784A2F1320C3F63C9859E75E54BA77E66262D6DC124E8AC`.
