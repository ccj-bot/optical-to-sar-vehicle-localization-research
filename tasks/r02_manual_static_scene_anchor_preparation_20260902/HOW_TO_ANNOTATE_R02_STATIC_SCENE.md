# R02 静态场景标注：最简操作

1. 双击 `START_R02_STATIC_ANNOTATION.bat`，浏览器会自动打开。
2. 默认只做四步：光学近边 → 光学远边 → SAR 近边 → SAR 远边。
3. 在当前大图上左键点 3–8 个点，按 `Enter` 完成；工具会自动进入下一项。
4. 鼠标滚轮缩放；按住空格拖动画面；已有节点可以直接拖动微调。
5. 点“撤销一点”或按 `Backspace` 撤回最后一点；点“清空重画”或按 `Delete` 删除当前项。
6. 看不清就点“无法判断”或“不可见”，不用勉强选择。
7. 树不是必做项；需要时展开“可选：树 / 杆”。不知道 SAR 对应点就点 `TREE_UNKNOWN`。
8. 左右方向键切换帧，`S` 跳过整对。自动提示默认关闭，可按 `H` 临时打开。
9. 每次点击和节点拖动都会立即自动保存。结束时点“保存并退出”。

标注仍保存在：

`D:\profile\research\workspace\output\r02_manual_static_scene_anchor_preparation_20260902\user_annotations`

之前 OpenCV 版本产生的人工 JSONL 会原样保留并自动显示。旧界面备用入口是 `START_R02_STATIC_ANNOTATION_LEGACY.bat`。
