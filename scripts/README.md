# 脚本索引

脚本均假定从仓库根目录运行，并通过脚本文件位置解析项目根路径。大多数脚本会覆盖
同名 CSV、图片或 HTML；提交前应检查 `git diff`，确认数据口径变化符合预期。

## 主流程

| 脚本 | 作用 |
|---|---|
| `generate_raw_data_checklist.py` | 扫描正式/待核材料并更新原始数据核查页 |
| `clean_wenzhou.py` | 清洗 `data_raw/points/`，生成核心母表 |
| `analyze_rhyme_phonetics.py` | 统计音值分布并提取主体层链 |
| `update_mainlayer_tables.py` | 生成主体层分类表和演变画像表 |
| `calculate_merge_rate.py` | 计算点 × 声组合并率、总体声组排序和结果文档 |

## 主体层与合并分析

| 脚本 | 主要输出 |
|---|---|
| `analyze_merge_strength_clusters.py` | `data_clean/merge_analysis/` 中的点级强度聚类 |
| `plot_merge_clustering_comparison.py` | `figs/merge_analysis/` 中的强度/模式聚类比较 |
| `plot_continuous_merge_strength_cluster_map.py` | 连续合并强度地图 |
| `analyze_mainlayer_ipa_positions.py` | 主体层 IPA 表、总览图和点级 PDF 图册 |
| `analyze_mainlayer_by_onset.py` | 声组条件下的主体层结构与音值链表 |
| `cluster_mainlayer_chains.py` | 点级代表链和 `k=2…8` 聚类数据 |
| `plot_mainlayer_chain_k3_map.py` | 推荐 `k=3` 类型地理图 |
| `plot_mainlayer_chain_main_only.py` | 三类代表主链 HTML 与独立 PNG |
| `plot_dialect_onset_merge_pattern_matrix.py` | 82 点 × 声组模式矩阵（PNG/PDF） |
| `plot_mainlayer_stats_tree.py`、`plot_s1_s3_type_tree.py` | 主体层结构树 |

## 音值、裂化与单音化

- `analyze_point_phonetic_inventory.py`、`analyze_rhyme_phonetics.py`、
  `analyze_slot_onset_phonetic_counts.py`：音值库藏与格位分布。
- `analyze_onset_inventory_ratio.py`：声组音值覆盖率与不均衡。
- `analyze_vowel_inventory.py`、`analyze_vowel_entropy_map.py`、
  `analyze_vowel_complexity_with_i.py`：点级复杂度与地理图。
- `analyze_s0_s3_diphthongization.py`、
  `analyze_s0_s3_mainlayer_vowel_complexity.py`：S0–S3 裂化和主体层复杂度。
- `analyze_s4_monophthongization.py`：侯韵单音化。
- `analyze_hao_monophthong_relation.py`、`analyze_hao_implications.py`、
  `analyze_hao_models.py`、`analyze_hao_geography.py`：豪韵关系、模型与地理分布。
- `analyze_point_structure_types.py`：链位关系、结构类型与 k-means 对照。

## 可视化与模拟

- `generate_sankey.py`、`generate_sunburst.py`：总体演变画像。
- `plot_dialect_map.py`、`plot_dialect_map_large_legend.py`：采样点地形图。
- `analyze_byrhyme.py`：分韵细图。
- `run_vowel_aco_small.py`、`run_vowel_aco_conditioned.py`、
  `visualize_vowel_ant_colony.py`：ACO 路径模拟与机制图。

## 辅助导出

- `extract_point_template.py`：从原始材料提取坐标模板。
- `build_mainlayer_onset_workbook.mjs`：导出声母分化工作簿；依赖支持
  `@oai/artifact-tool` 的制表运行环境。

