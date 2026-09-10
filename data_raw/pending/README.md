# 待核原始材料

这里保存尚未进入正式分析语料的候选方言点文件。`scripts/clean_wenzhou.py` 只读取
`data_raw/points/`，因此本目录内容不会影响当前 82 点结果。

目前 `GS01` 有两个内容不同的版本：

- `GS01_GUSHAN.csv`：837 行，约 402 条已填读音；
- `GS01_顾山.csv`：837 行，约 116 条已填读音。

在确认权威版本、补入坐标并重新生成全部派生结果前，请勿把两者同时移入
`data_raw/points/`。运行 `python scripts/generate_raw_data_checklist.py` 后，可在
`data_raw/raw_data_checklist.html` 中继续查看完整性与重复点号提示。
