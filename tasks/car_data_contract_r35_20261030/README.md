# CAR R35 data contract and normalization — 2026-10-30

This task normalizes the R35 optical/SAR material before another localization
method is considered. It creates an auditable, layer-separated package under
`output/car_data_contract_r35_20261030`.

The package keeps four evidence layers distinct:

1. raw optical and SAR image/frame indexes;
2. image-derived SAR response fragments and the public image-domain transform;
3. optical detector candidates, which are search priors;
4. current user-confirmed native-SAR annotations, with DRAFT records preserved.

It also records unavailable, unannotated, unknown-visibility, and proposal-only
states separately. The package does not change source annotations, old results,
the CAR model, or the PERSON baseline.

Runtime: `python -X utf8 -B`.

The independent validator checks source values, JSON pointers, rotation-sign
regression, coordinate inverses for every extracted fragment, missing SAR495,
unknown versus negative labels, and real observation/review reader behavior.

Use the completed package's START_HERE.md. Default observation access provides
raw frame evidence; historical extraction, background and public motion are named
opt-in representations. User references require review or manual_initialized.

Rebuild into a NEW dedicated output folder:

```powershell
& python -X utf8 -B tasks/car_data_contract_r35_20261030/build.py --output output/car_data_contract_r35_rebuild
```

The current package is a workspace data release with source image/video paths;
source media remains external and hash-bound. It is not a portable all-media copy.
