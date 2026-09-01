# R02 静态场景标注：快速操作

1. 双击本目录中的 `START_R02_STATIC_ANNOTATION.bat`。
2. 左边是时间最近的 optical 帧，右边是 SAR 帧。顶部会显示两边帧号、时间戳和名义时间残差。
3. 选择标注类别：
   - `1/2`：Optical Near / Far boundary
   - `3/4/5`：Optical Tree A / B / C
   - `6/7`：SAR Near / Far boundary
   - `8/9/0`：SAR Tree A / B / C
4. 画 boundary：鼠标左键依次点 3–8 个点，`Enter` 完成；`Backspace` 撤销最后一点；`Delete` 删除当前类别标注。
5. 标树：选择 Tree A/B/C 后，在树干轴线或 SAR compact bright response 中心单击一次。
6. 置信状态：`C` CONFIDENT，`L` LIKELY，`U` UNCERTAIN，`V` NOT_VISIBLE。
7. 如果当前 SAR Tree A/B/C 不知道对应哪个亮点，按 `X` 记录 `TREE_UNKNOWN`，不要勉强选点。
8. 浏览：`D`/右方向键下一对，`A`/左方向键上一对，`S` 跳过当前对。
9. `H` 开关 `AUTOMATIC_HINT`。提示默认关闭，不代表真值。
10. 每次点击都会立即自动保存；按 `Q` 或 `Esc` 保存并退出。

标注保存在：

`D:\profile\research\workspace\output\r02_manual_static_scene_anchor_preparation_20260902\user_annotations`

主要文件是 `manual_static_scene_annotations.jsonl`；它是追加式人工记录。可以跳过、不确定或标记不可见，不需要二选一。
