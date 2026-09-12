# GM019 PV003 Contact-Sheet Audit

## Finding

Frame 136 is not on the silver MPV. The source box `[735.261,327.552,777.576,350.071]` is a tiny background box over the storefront, while the neighboring frames 118–123 contain large vehicle boxes. This is a source-box/detector anomaly (finding C), not a valid vehicle observation.

## Evidence

- frame 118: source=existing_yolo11l_detection; bbox=(118.919,273.509,657.958,594.558); visibility=full_visible
- frame 119: source=existing_yolo11l_detection; bbox=(148.546,262.290,699.273,594.518); visibility=full_visible
- frame 120: source=existing_yolo11l_detection; bbox=(221.502,263.755,750.016,594.070); visibility=full_visible
- frame 121: source=existing_yolo11l_detection; bbox=(228.579,261.679,795.545,594.230); visibility=full_visible
- frame 123: source=existing_yolo26l_detection; bbox=(80.800,263.911,679.091,595.885); visibility=full_visible
- frame 136: source=existing_yolo26l_detection; bbox=(735.261,327.552,777.576,350.071); visibility=full_visible

## Minimal repair

Exclude frame 136 from PV003 interval evidence and retain the provenance/error record. The valid maximal contiguous complete candidate remains frames 118–123; do not repair the box by interpolation in this task.