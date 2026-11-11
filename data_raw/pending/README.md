# 待核原始材料

这里保存尚未进入正式分析语料的候选方言点文件。`scripts/clean_wenzhou.py` 只读取
`data_raw/points/`，因此本目录内容不会影响当前 84 点结果。

顾山已采用 `GS01_GUSHAN.csv` 版本并以 `GS01_江阴顾山镇_GUSHAN.csv` 移入正式点表；另一份
重复版本已删除。`同音字表 常州武进修改.csv` 是武进整理前的来源表，标准化后的点表已写入
`data_raw/points/CZ02_常州武进.csv`，来源表留在此目录供追溯。运行
`python scripts/generate_raw_data_checklist.py` 后，可在 `data_raw/raw_data_checklist.html`
中查看正式点表的完整性与重复点号提示。

常熟虞山原表已移至 `data_raw/reference/` 留档；当前正式点表用常熟梅李镇（CS03）暂代，
不把虞山原表与梅李重复计入分析。江阴顾山镇（GS01）、常州武进（CZ02）、常熟梅李镇（CS03）
的坐标已同步写入 `data_dict/point_coords_master.csv` 与各自点表。
