# 吴语太湖片元音链演变分析

> Wuyu Taihu Vowel Chain Shift Analysis

本仓库是一套面向吴语太湖片元音链研究的可复现分析流程。项目从方言点原始
CSV 出发，统一清洗读音与文白层次，构建 `S0–S5` 链位，计算声组条件下的合并率，
并进一步完成主体层聚类、音值库藏、裂化/单音化、地理分布和 ACO 模拟。

当前正式语料包含 **82 个方言点**；核心清洗母表约 **5 万行**。仓库同时保留脚本、
派生表、说明文档和一套按研究主题整理的静态图，便于复核现有结论或重跑单个模块。

## 研究对象与链位

| 链位 | 韵部 | 主要用途 |
|:---:|---|---|
| S0 | 佳、皆 | 低位链起点 |
| S1 | 麻 | 低位链中段 |
| S2 | 歌、戈 | 后移/高化过渡 |
| S3 | 模 | 主链高位端 |
| S4 | 侯 | 单音化扩展分析 |
| S5 | 豪 | 单音化与吸引子分析 |

核心声组为 `K / M / P / TS / Ø`。`L` 在清洗后并入 `N`，`Ts / TS* / Ts*`
统一为 `TS`；`N / T` 在合并率中按独立高位链口径处理。完整定义和公式见
[merge rate 方法说明](docs/merge_rate_methodology.md)。

## 分析流程

```text
data_raw/points/*.csv
        │
        ▼  clean_wenzhou.py
data_clean/wuyu_lexeme.csv
        │
        ├── analyze_rhyme_phonetics.py ──► 主体层音值链
        │                                  │
        │                                  ▼  update_mainlayer_tables.py
        │                         mainlayer_merge / evolution profiles
        │                                  │
        │                                  ├── 主体层聚类与交互图
        │                                  └── Sankey / Sunburst
        │
        ├── calculate_merge_rate.py ─────► 合并率、排序与聚类
        ├── analyze_*inventory*.py ──────► 音值库藏与复杂度
        ├── analyze_s0_s3_*.py ──────────► 裂化分析
        ├── analyze_*monophthong*.py ────► 侯/豪单音化
        └── run_vowel_aco_*.py ─────────► ACO 模拟
```

## 仓库结构

```text
.
├── data_raw/
│   ├── points/                 # 正式纳入主流程的 82 点原始表
│   ├── pending/                # 尚待核定、不会被主流程读取的候选材料
│   └── raw_data_checklist.*    # 原始材料核查页及其生成数据
├── data_clean/
│   ├── wuyu_lexeme.csv         # 全项目核心清洗母表
│   ├── merge_analysis/         # 合并率、强度和聚类结果
│   └── value_type/             # 主体层、音值类型、裂化、单音化和 ACO 表
├── data_dict/                  # 链位、声组、权重和方言点坐标映射
├── scripts/                    # 数据处理、分析和制图脚本
├── docs/                       # 方法、专题结果与数据口径说明
├── figs/                       # 按研究主题归档的图像、PDF 和交互 HTML
├── output/                     # 面向人工阅读的 Excel/PDF 成品
└── web/                        # 轻量前端浏览页面
```

各目录的细节分别见 [原始数据说明](data_raw/README.md)、
[清洗数据说明](data_clean/README.md)、[映射表说明](data_dict/README.md)、
[脚本索引](scripts/README.md) 和 [图片索引](figs/README.md)。

## 环境安装

推荐 Python 3.12。不要把虚拟环境或 `node_modules` 提交到仓库。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

交互网页使用 D3 与 Papa Parse；只有修改 `web/` 时才需要 Node.js 18+：

```bash
npm install
```

地图脚本通过 Contextily 获取在线底图，首次运行需要网络。中文与 IPA 字体会优先使用
macOS 自带字体；在 Linux/Windows 上运行时，字形和排版可能略有差异。

## 推荐重跑顺序

所有命令均在仓库根目录执行。

### 1. 核查与清洗原始材料

```bash
python scripts/generate_raw_data_checklist.py
python scripts/clean_wenzhou.py
```

核查脚本生成 `data_raw/raw_data_checklist_data.js`。直接打开
[`raw_data_checklist.html`](data_raw/raw_data_checklist.html) 可以检查字段、读音覆盖、
新增韵部数量和重复点号。

### 2. 重建主体层基础表

```bash
python scripts/analyze_rhyme_phonetics.py
python scripts/update_mainlayer_tables.py
```

主要依赖链为：

```text
wuyu_lexeme.csv
  → point_slot_onset_distribution.csv
  → type_phonetic_chains.csv
  → data_raw/mainlayer_merge.csv
  → data_raw/dialect_evolution_profiles_full.csv
```

### 3. 计算合并率

```bash
python scripts/calculate_merge_rate.py
python scripts/analyze_merge_strength_clusters.py
python scripts/plot_merge_clustering_comparison.py
```

当前总体指标只使用 `S1–S2` 与 `S2–S3` 两段：先在声组层面分别求均值，
再按 `1/2` 等权合成。`S0–S1` 保留在明细中但不进入总体排序；直接计算的
`S1–S3` 只作跨级参照。数值榜单见 [当前结果](docs/merge_rate_results.md)。

### 4. 生成总览图

```bash
python scripts/generate_sankey.py
python scripts/generate_sunburst.py
python scripts/plot_dialect_map.py
```

输出位于 `figs/overview/`。

### 5. 按需运行专题模块

| 主题 | 主要脚本 | 图目录 |
|---|---|---|
| 主体层链与 IPA | `analyze_mainlayer_ipa_positions.py`、`cluster_mainlayer_chains.py`、`plot_mainlayer_chain_*.py` | `figs/mainlayer/` |
| 声组分化矩阵 | `analyze_mainlayer_by_onset.py`、`plot_dialect_onset_merge_pattern_matrix.py` | `figs/merge_analysis/` |
| 音值库藏与复杂度 | `analyze_*inventory*.py`、`analyze_vowel_*map.py` | `figs/vowel_inventory/` |
| S0–S3 裂化 | `analyze_s0_s3_diphthongization.py` | `figs/diphthongization/` |
| 侯/豪单音化 | `analyze_s4_monophthongization.py`、`analyze_hao_*.py` | `figs/monophthongization/` |
| ACO 模拟 | `run_vowel_aco_*.py`、`visualize_vowel_ant_colony.py` | `figs/aco/` |
| 结构类型 | `analyze_point_structure_types.py` | `figs/structure_type_analysis/` |

## 建议优先查看的结果

- 核心母表：[`data_clean/wuyu_lexeme.csv`](data_clean/wuyu_lexeme.csv)
- 主体层分类：[`data_raw/mainlayer_merge.csv`](data_raw/mainlayer_merge.csv)
- 点 × 声组合并率：[`point_onset_merge_rates.csv`](data_clean/merge_analysis/point_onset_merge_rates.csv)
- 声组总体排序：[`onset_merge_rate_summary.csv`](data_clean/merge_analysis/onset_merge_rate_summary.csv)
- 主体层三类聚类：[`mainlayer_chain_clusters.html`](figs/mainlayer/mainlayer_chain_clusters.html)
- 方言点地形总览：[`wuyu_topography_map.png`](figs/overview/wuyu_topography_map.png)
- 主体层 k=3 地理图：[`mainlayer_chain_k3_map.png`](figs/mainlayer/mainlayer_chain_k3_map.png)
- 点级 IPA 图册：[`mainlayer_ipa_point_atlas.pdf`](output/pdf/mainlayer_ipa_point_atlas.pdf)
- 声母分化工作簿：[`mainlayer_onset_differentiation.xlsx`](output/mainlayer_onset_differentiation.xlsx)

静态图是与当前提交配套的结果快照。当前脚本会覆盖同名文件；历史图统一放在
`figs/archive/`，不应和当前分析结果混用。

## 数据与复现约定

- 原始点表文件名采用 `POINTID_地点名.csv`；详细规则见
  [方言点命名说明](docs/point_naming.md)。
- 正式分析入口只扫描 `data_raw/points/*.csv`，不会自动读取 `data_raw/pending/`。
- 派生表默认以 `UTF-8 with BOM` 写出，便于在 Excel 中打开中文字段。
- 多个 `/` 分隔读音按等概率拆分；当前 merge rate 保留 `weight_type`，但统一使用
  权重 `1.0`。
- `scripts/build_mainlayer_onset_workbook.mjs` 依赖支持 `@oai/artifact-tool` 的制表环境；
  普通 Node 环境可直接使用仓库内已导出的工作簿。
- 仓库目前未声明开源许可证；复用语料或图表前请先联系维护者确认授权与引用方式。

## 文档导航

- [当前 82 点清单](docs/current_82_point_inventory.md)
- [merge rate 方法与字段](docs/merge_rate_methodology.md)
- [merge rate 当前结果](docs/merge_rate_results.md)
- [主体层链聚类](docs/mainlayer_chain_clustering.md)
- [声组库藏与合并率的区别](docs/onset_inventory_and_merge_interpretation.md)
- [S0–S3 裂化分析](docs/s0_s3_diphthongization_analysis.md)
- [侯韵单音化分析](docs/s4_hou_monophthong_analysis.md)
- [豪韵模型](docs/hao_monophthong_models.md)
- [结构类型与 k-means](docs/structure_type_and_kmeans_explainer.md)
- [ACO 小模型结果](docs/vowel_aco_small_results.md)
