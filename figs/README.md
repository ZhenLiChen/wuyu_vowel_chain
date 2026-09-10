# 图表目录

图表按研究主题归档，不再把所有 PNG、HTML 和 PDF 堆在 `figs/` 根目录。
目录内文件是与当前提交配套的结果快照；重新运行对应脚本会覆盖同名输出。

| 目录 | 内容 | 主要生成脚本 |
|---|---|---|
| `overview/` | 地形总览、Sankey、Sunburst 与描述统计 | `plot_dialect_map.py`、`generate_sankey.py`、`generate_sunburst.py` |
| `merge_analysis/` | 合并强度、模式聚类和声组矩阵 | `plot_merge_clustering_comparison.py`、`plot_dialect_onset_merge_pattern_matrix.py` |
| `mainlayer/` | 主体层链聚类、IPA 总览、结构树 | `plot_mainlayer_chain_*.py`、`analyze_mainlayer_ipa_positions.py` |
| `vowel_inventory/` | 音值库藏、熵与复杂度地图 | `analyze_vowel_*.py`、`analyze_s0_s3_mainlayer_vowel_complexity.py` |
| `diphthongization/` | S0–S3 裂化统计图 | `analyze_s0_s3_diphthongization.py` |
| `monophthongization/` | 侯/豪单音化、模型与地理分布 | `analyze_s4_monophthongization.py`、`analyze_hao_*.py` |
| `aco/` | ACO 模拟和机制示意图 | `run_vowel_aco_*.py`、`visualize_vowel_ant_colony.py` |
| `rhyme_detail_maps/` | 佳皆、麻、歌戈、模的分韵地图 | `analyze_byrhyme.py` |
| `structure_type_analysis/` | 结构类型热图、柱图和地图 | `analyze_point_structure_types.py` |
| `archive/` | 无当前生成入口或已被新版替代的旧图 | 不作为当前结果引用 |

## 当前推荐入口

- `overview/wuyu_topography_map.png`：82 点地形与小片分布。
- `overview/sankey_evolution_profiles.html`：点级演变画像交互图。
- `mainlayer/mainlayer_chain_clusters.html`：主体层聚类交互图。
- `mainlayer/mainlayer_chain_k3_map.png`：推荐三类的地理分布。
- `merge_analysis/dialect_onset_merge_pattern_matrix.png`：点 × 声组模式矩阵。

`archive/` 中包含旧版聚类、复杂度和 Sunburst 文件，仅用于追溯。若确认不再需要，
可以在后续版本单独删除；当前文档与脚本均不应链接这些文件。

