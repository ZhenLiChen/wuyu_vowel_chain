# 吴语太湖片元音链演变自动化分析处理系统

### (Wuyu Vowel Chain Shift Analysis System)

本项目是一套围绕吴语太湖片元音链演变的自动化分析脚本集合，核心关注 `佳/皆/麻/歌/戈/模` 所对应的 `S0-S3` 链位，以及后续扩展到 `侯`、`豪` 等韵的单音化、裂化与类型学分布问题。

它现在已经不只是数据可视化的pipeline，而是一条从原始方言点 CSV 出发，经过清洗、加权合并率计算、音值库藏统计、地理投影、类型学归纳，再到 ACO（蚁群）模拟的完整工作流。

一句话版本：

> 这个仓库是在用可复现脚本，把吴语元音链变从“印象派观察”推到“可统计、可制图、可建模”的状态。

---

## 1. 项目目录结构 (Project Structure)

```text
.
├── README.md                          # 本说明文档
├── data_raw/                          # 【输入】原始方言点材料与中间汇总表
│   ├── points/                        # 各方言点原始 CSV
│   ├── mainlayer_merge.csv            # 主层合并分类表（旭日图/部分统计使用）
│   ├── dialect_evolution_profiles_full.csv
│   └── 导入模版Template.csv
├── data_clean/                        # 【中间】清洗后总表与派生分析结果
│   ├── wuyu_lexeme.csv                # 核心清洗总表
│   ├── merge_analysis/                # 合并率、聚类、层级报告
│   └── value_type/                    # 音值库藏、裂化、单音化、ACO 等派生表
├── data_dict/                         # 【词典】映射表、坐标表、权重表
│   ├── onset_mapping.csv              # 声组归并规则（如 L -> N, TS* -> TS）
│   ├── rhyme_slot_mapping.csv         # 韵部与链位映射
│   ├── weight_mapping.csv             # 离群字/层次字权重表
│   └── point_coords_master.csv        # 方言点经纬度与小片信息
├── scripts/                           # 【核心】分析脚本
│   ├── clean_wenzhou.py               # 原始 CSV 清洗、拆分读音、文白标注
│   ├── calculate_merge_rate.py        # 加权合并率与推力序列
│   ├── generate_sankey.py             # 演变画像桑基图
│   ├── generate_sunburst.py           # 合并模式旭日图
│   ├── plot_dialect_map.py            # 方言点地理分布图
│   ├── analyze_*.py                   # 音值库藏 / 裂化 / 单音化 / 类型学分析
│   └── run_vowel_aco_*.py             # ACO 元音演化模拟
├── docs/                              # 【说明】专题分析文档与结果解释
├── figs/                              # 【输出】地图、统计图、HTML 交互图
├── notebooks/                         # 试验性笔记
└── web/                               # 前端可视化相关文件
```

---

## 2. 项目现在在做什么 (What This Repo Actually Does)

目前仓库里的工作大致分成 5 组：

1. `数据清洗`
   从 `data_raw/points/*.csv` 批量读入，拆开斜杠音值，识别 `文/白`，统一 `onset_class` 与链位信息，最终生成 `data_clean/wuyu_lexeme.csv`。

2. `链位合并分析`
   以 `S0-S1`、`S1-S2`、`S2-S3` 为核心，按声母类别计算加权分布重叠度（merge rate），输出声组推力序列、点级合并率、聚类结果和解释报告。

3. `音值库藏与类型学分析`
   统计各点总音值库藏、分韵库藏、声母覆盖率、`S0-S3` 裂化模式，以及 `侯/豪` 韵单音化与其地理分布、蕴涵关系和简化模型。

4. `地理可视化`
   把方言点投到自然地貌底图上，做复杂度图、分布图、分韵细图和若干专题地图。

5. `ACO / 元音演化模拟`
   把 `a > ɑ > ɔ > o > ɷ > u > əu` 这类链条转成小型元音拓扑图，用蚁群算法做受控路径模拟。

---

## 3. 环境配置 (Setup)

本项目主要运行于 `Python 3.12+`。

```bash
# 1. 激活虚拟环境
source env/bin/activate

# 2. 如需补装依赖
pip install pandas numpy matplotlib geopandas contextily shapely plotly kaleido
```

如果你还要动 `web/` 里的前端小部件，仓库里也带了一个很轻量的 Node 依赖：

```bash
npm install
```

---

## 4. 推荐运行流程 (Recommended Workflow)

不是所有脚本都要每次全跑。通常按下面顺序就够了。

### Step 1. 清洗原始数据

```bash
python scripts/clean_wenzhou.py
```

这一步会：

- 汇总 `data_raw/points/*.csv`
- 拆开 `读音` 中的斜杠形式
- 根据 `note` 自动标注文白层次
- 合并韵位与声组映射
- 输出核心总表 `data_clean/wuyu_lexeme.csv`

### Step 2. 计算链位合并率

```bash
python scripts/calculate_merge_rate.py
```

这一步会：

- 引入 `data_dict/weight_mapping.csv`
- 保留 `weight_type` 标注，但本轮 merge rate 统一按等权处理
- 若同一字有多个 `/` 分隔读音，则仍按等概率均分
- 计算各点各声组的 `S0-S1 / S1-S2 / S2-S3` 合并率
- 补充计算 `S1-S3` 跨级参照值
- 输出 `data_clean/merge_analysis/` 下的一组汇总表与文字报告

### Step 3. 生成基础可视化

```bash
python scripts/generate_sankey.py
python scripts/generate_sunburst.py
python scripts/plot_dialect_map.py
```

主要输出：

- `figs/sankey_evolution_profiles.html`
- `figs/vowel_chain_sunburst_stats.html`
- `figs/wuyu_topography_map.png`

### Step 4. 跑扩展分析模块

按需要挑着跑即可：

```bash
python scripts/analyze_point_phonetic_inventory.py
python scripts/analyze_rhyme_phonetics.py
python scripts/analyze_onset_inventory_ratio.py
python scripts/analyze_s0_s3_diphthongization.py
python scripts/analyze_s4_monophthongization.py
python scripts/analyze_hao_monophthong_relation.py
python scripts/analyze_hao_implications.py
python scripts/analyze_hao_models.py
python scripts/analyze_hao_geography.py
python scripts/analyze_merge_strength_clusters.py
python scripts/plot_merge_clustering_comparison.py
```

### Step 5. 跑 ACO 模拟

```bash
python scripts/run_vowel_aco_small.py
python scripts/visualize_vowel_ant_colony.py
python scripts/run_vowel_aco_conditioned.py
```

---

## 5. 核心数据口径 (Core Analytical Assumptions)

这部分很重要，不然很容易把结果看歪。

### 5.1 链位对应

```text
S0 = 佳 / 皆
S1 = 麻
S2 = 歌 / 戈
S3 = 模
S4 = 侯
S5 = 豪
```

### 5.2 声组归并

- `L` 并入 `N`
- `Ts / TS* / Ts*` 并入 `TS`
- `T / N` 默认不参与低位链环节 (`S0/S1`) 的比较

### 5.3 权重分配

当前 `scripts/calculate_merge_rate.py` 的 merge rate 口径是：

- 保留 `data_dict/weight_mapping.csv` 中的 `weight_type`
- 但实际计算统一使用等权重 `1.0`
- 不再额外压低文读层或离群字
- 同一字若拆成多个 `/` 读音，仍按 `1/n` 分摊到各读音

这套规则写在：

- `scripts/calculate_merge_rate.py`
- `data_dict/weight_mapping.csv`

### 5.4 例外处理

项目里多次显式排除了 `靴`、`茄` 等特殊字项；一些介音、裂化与入声形式也会在专题脚本中单独分流，而不是强行并进主统计。

---

## 6. 主要输出文件 (Main Outputs)

如果你第一次看这个仓库，优先看这些：

### A. 核心总表

- `data_clean/wuyu_lexeme.csv`

### B. 合并率与层级报告

- `data_clean/merge_analysis/point_onset_merge_rates.csv`
- `data_clean/merge_analysis/summary_hierarchy_report.txt`
- `data_clean/merge_analysis/onset_hierarchy_report.txt`
- `data_clean/merge_analysis/point_merge_strength_summary.csv`
- `data_clean/merge_analysis/merge_clustering_comparison_report.txt`

### C. 音值库藏与类型学表

- `data_clean/value_type/point_phonetic_inventory.csv`
- `data_clean/value_type/point_rhyme_inventory.csv`
- `data_clean/value_type/point_onset_inventory_ratios.csv`
- `data_clean/value_type/global_onset_inventory_inequality.csv`
- `data_clean/value_type/s0_s3_split_implication_rules.csv`
- `data_clean/value_type/point_hao_monophthong_relation.csv`
- `data_clean/value_type/hao_typological_implication_rules.csv`

### D. 图像与交互图

- `figs/sankey_evolution_profiles.html`
- `figs/vowel_chain_sunburst_stats.html`
- `figs/wuyu_topography_map.png`
- `figs/vowel_complexity_gradient_map.png`
- `figs/s0_s3_split_onset_rates.png`
- `figs/hao_monophthong_geography_map.png`
- `figs/ant_colony_chain_mechanism.png`

---

## 7. 推荐阅读顺序 (If You Want To Read This Repo Properly)

建议按这个顺序看：

1. 先看 `data_clean/wuyu_lexeme.csv`
   这是所有后续脚本的母表。

2. 再看 `scripts/calculate_merge_rate.py`
   这里定义了项目最核心的一组量化逻辑。

3. 然后看 `docs/onset_inventory_and_merge_interpretation.md`
   这份文档最能说明“库藏覆盖率”和“链位合并率”不是一个东西。

4. 如果你关心裂化问题，再看：
   `docs/s0_s3_diphthongization_analysis.md`

5. 如果你关心 `侯/豪` 韵单音化，再看：
   `docs/s4_hou_monophthong_analysis.md`
   `docs/hao_monophthong_models.md`

6. 如果你关心建模尝试，再看：
   `docs/vowel_aco_small_results.md`
   `docs/vowel_ant_colony_internal_mechanism.md`

---

## 8. 常见注意事项 (Troubleshooting)

### 坐标图画不出来

先检查：

- `data_dict/point_coords_master.csv` 是否有合法 `lat/lon`
- 本机能否正常请求底图服务
- `geopandas / contextily / shapely` 是否安装完整

### 中文标注乱码

脚本里已经优先尝试：

- `PingFang SC`
- `Heiti SC`
- `SimHei`
- `Microsoft YaHei`

如果你的环境没有这些字体，地图仍能跑，但中文显示可能不稳定。

### 为什么结果和早期 README 不一样

因为项目已经扩展了很多，旧版 README 只覆盖了最早一批脚本。现在的分析输出主要以 `data_clean/merge_analysis/`、`data_clean/value_type/`、`docs/` 和 `figs/` 为准。

---

## 9. Support

If this repo helps your work, leave a star if you want.

Wuyu dataset in this project is self-constructed and still under continuous cleaning / expansion.  
Some modules are already stable enough for analysis, some are still in a very "working notebook turned script" phase, which is also why the repo looks slightly wild right now.

I will keep polishing the dataset, the documentation, and the ACO part after the thesis stage.

Maintainer: Zhenli Chen  
README update: 2026-04-25
