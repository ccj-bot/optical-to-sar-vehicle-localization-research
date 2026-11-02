# 复现与依赖

这是源码与研究记录的保存，不是完整数据集发布。大视频、权重、Parquet/NumPy缓存、人工标注快照和本地封存输出仍在Git外。没有这些依赖时，不声称可一键重现实验成绩。

## 可独立加载的组件

- `tools/person_localizer/`：rc9公共运行代码；20个Python文件与本地冻结基线相同。
- `tools/car_data_contract/`：规范帧表/观测/参考读取器和原生坐标几何函数。

在Python3.11环境中，从仓库根目录运行：

```text
python -X utf8 -B tools/person_localizer/cli.py --help
```

数值组件依赖numpy、scipy、pandas、opencv-python、Pillow和threadpoolctl。CAR表读取另需pyarrow。光学检测/跟踪另需ultralytics和用户本地权重；绘图需matplotlib，视频导出需ffmpeg或imageio-ffmpeg，网页检查脚本需playwright及可用浏览器。版本记录见`environment.observed.json`，它记录验证环境而非保证任意平台兼容的锁文件。

PERSON的`config.json`仅将本机权重路径改为`models/yolov8s.pt`；使用者须显式提供正确的本地权重位置或已有车辆检测证据CSV。其他算法参数保留。不要把R01开发拟合方位参数或R50场景尺度直接当新场景标定。

## 需要本地研究资产的脚本

|源码|主要外部依赖|运行角色|
|---|---|---|
|`tasks/person_multiscene_baseline_v1_20261029/`|先前rc9集成结果、场景配置、源数据、交付哈希|封存与核验；不会在本仓库凭空恢复六景输入|
|`tasks/car_data_contract_r35_20261030/`|原帧目录、工作台Parquet、原用户JSON、旧SAR片段缓存|创建新目录中的规范数据包|
|`tasks/car_central_static_annotation_20261101/`|规范数据包、原始手工框、早期候选清单|历史v1，用于追溯已知后段漂移|
|`tasks/car_central_static_repair_20261102/`|规范数据包、v1记录、已有来源索引|v2导航、视觉审阅和视频制作|
|`tasks/car_bright_band_margin_20261102/`|已审核v2及其来源清单|v3单端6px标注余量|

CAR规范包的源路径需在本地有效；更换机器时应建立新的路径映射/发行版本，不能静默修改旧封存。绘图脚本现使用Windows系统中文字体；其他系统需替换为可用中文字体。系统字体路径不是私有项目路径。

`deliver.py`/`finalize.py`中的审核状态记录必须在实际看图后执行；自动运行脚本不构成人工或助手视觉验收。运行前保留现有输出，新实验使用新版本目录。

## 本次候选核查

仅核查源码对应、语法/导入、CLI帮助、配置路径差异及文件边界。没有重复昂贵的九组SAR数值回归，也没有生成新的精度结果。完整冻结基线及既有验证回执继续保留在本地。
