# CAR数据读取器

读取外部R35规范数据包，不复制或修改源图。默认`observation`视图读取原图与帧信息；派生片段、背景模型与公共变换需显式请求；参考标注仅在`review`或`manual_initialized`视图可读。

```python
from pathlib import Path
from car_data_contract import CarDataset
data = CarDataset(Path("output/car_data_contract_r35_20261030"))
image = data.image("SAR", 358)
```

将仓库`tools/`加入PYTHONPATH。需numpy、pandas、pyarrow与Pillow，并提供规范Parquet/JSON及其中指向的原图。源图逐次读取可校验SHA256。包内路径依赖原环境，更换机器须建立显式映射或新发行版本；不静默改旧封存。

坐标为原生图像x向右/y向下、正SVG角；`native_corners`仅做几何表达，不解释物理车头。源SAR495缺失应明确报错，不能替换为494。详情见`docs/research/STATUS_20261102.md`。
