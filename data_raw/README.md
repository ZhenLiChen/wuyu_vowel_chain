# 原始数据目录

`data_raw/` 保存输入材料和由主体层链表生成的上游汇总表。正式分析默认只读取
`points/*.csv`；顶层的外片、材料不全文件和 `pending/` 不会自动进入 82 点主语料。

## 目录约定

| 路径 | 状态 | 说明 |
|---|---|---|
| `points/` | 正式输入 | 当前主流程使用的 82 个太湖片方言点 |
| `pending/` | 待核 | 点号、版本或完整性尚未确认的候选材料 |
| `*_材料不全.csv` | 参考 | 未进入正式 82 点统计的残缺材料 |
| `point_template.csv`、`导入模版Template.csv` | 模板 | 新点录入用字段模板 |
| `新增韵部列表.csv` | 模板 | 咍、泰、灰、肴等扩展韵部清单 |
| `mainlayer_merge.csv` | 派生表 | `update_mainlayer_tables.py` 生成的主体层分合分类 |
| `dialect_evolution_profiles_full.csv` | 派生表 | Sankey 图使用的点级演变画像 |
| `raw_data_checklist.html` | 核查工具 | 原始文件完整性浏览页 |

正式点表命名为 `POINTID_地点名.csv`，必需字段至少包括 `point_id`、
`point_name`、`subbranch`、`lat`、`lon`、`韵`、`声组`、`汉字` 和读音列。
命名细则见 [`docs/point_naming.md`](../docs/point_naming.md)。

运行以下命令可更新核查页的数据：

```bash
python scripts/generate_raw_data_checklist.py
```

核查页会同时扫描正式点、待核点和部分顶层候选表，但这不等于它们都会进入清洗流程。

