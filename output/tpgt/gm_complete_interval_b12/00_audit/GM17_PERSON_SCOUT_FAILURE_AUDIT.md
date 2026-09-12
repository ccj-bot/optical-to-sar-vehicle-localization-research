# GM17 PERSON Scout Failure Audit

The B1.1 scout did not scan the 368-frame stream. It consumed pre-existing detector tables, each containing only a sparse subset of frames. GM17 YOLOv8n and YOLO11n had zero person rows; YOLO12n had one person row (frame 184); YOLO26n had one (frame 164); YOLOv8s had two rows at frame 164. The scout then emitted each surviving detection as a singleton and applied no temporal linking. Therefore the prior NONE_FOUND result is a cache coverage and linking failure, not evidence of no PERSON.

## Cache audit

- `D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_220148\detector_tables\ultralytics_yolov8n_downloaded\GM_RM017\oty0_yolo_detection_table.csv`: rows=223, person_rows=0, person_frames=[]
- `D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_221415\detector_tables\ultralytics_yolo11n_downloaded\GM_RM017\oty0_yolo_detection_table.csv`: rows=205, person_rows=0, person_frames=[]
- `D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_221415\detector_tables\ultralytics_yolo12n_downloaded\GM_RM017\oty0_yolo_detection_table.csv`: rows=228, person_rows=1, person_frames=[184]
- `D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_221415\detector_tables\ultralytics_yolo26n_downloaded\GM_RM017\oty0_yolo_detection_table.csv`: rows=223, person_rows=1, person_frames=[164]
- `D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_221415\detector_tables\ultralytics_yolov8n_downloaded\GM_RM017\oty0_yolo_detection_table.csv`: rows=223, person_rows=0, person_frames=[]
- `D:\profile\research\optical-sar-visual-diagnosis\outputs\oty2\detector_swap_timeline_stability_probe_20260705_221415\detector_tables\ultralytics_yolov8s_downloaded\GM_RM017\oty0_yolo_detection_table.csv`: rows=257, person_rows=2, person_frames=[164]