# 映射表与项目配置

这里保存跨脚本共享的规则表。修改这些文件会影响大部分派生结果，修改后应按
README 中的依赖顺序重新生成下游表和图。

| 文件 | 用途 |
|---|---|
| `rhyme_slot_mapping.csv` | 将韵部映射到 `S0–S5` 链位 |
| `onset_mapping.csv` | 统一声组标签，如 `L → N`、`TS* → TS` |
| `weight_mapping.csv` | 标注例字权重类型；当前 merge rate 实际统一按 `1.0` 计算 |
| `point_coords_master.csv` | 方言点名称、经纬度与小片信息的主表 |

`point_coords_master.csv` 是唯一坐标真源。新增点时请直接补入该表，不要另建
`new_*` 或 `copy_*` 版本；地图脚本要求 `lat/lon` 能转换为数值。

