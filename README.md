# 吴语太湖片元音链演变自动化分析处理系统

### (Wuyu Vowel Chain Shift Analysis System)

本项目是一套针对吴语太湖片（苏沪嘉、毗陵、甬江、苕溪、临绍、杭州各个小片）元音演变的量化分析工具集。通过对“歌、模、麻、佳皆”韵的词汇数据进行挖掘，直观展示元音高化链变（Vowel Chain Shift）的地理分布与层级包装逻辑。

---

## 1. 项目目录结构 (Project Structure)

```text
.
├── README.md                # 本说明文档
├── data_raw                 # 【输入】原始采样数据
│   ├── points/              # 各方言点原始 CSV (注意：JD01 嘉定表头需为 point_name)
│   └── mainlayer_merge.csv  # 汇总层级数据
├── data_clean               # 【中间】标准化后的清洗数据
│   └── wuyu_lexeme.csv      # 核心词汇数据库（含声组归并逻辑）
├── data_dict                # 【词典】映射关系与坐标
│   ├── onset_mapping.csv    # 声组归并逻辑 (L->N, TS*->TS)
│   ├── rhyme_slot_mapping.csv # 韵部与演变位点 (S0-S3) 对应表
│   └── point_coords_master.csv # 方言点经纬度映射（运行地图前需补全）
├── scripts                  # 【核心】执行脚本
│   ├── clean_wuyu.py        # 自动化清洗与文白异读标注
│   ├── calculate_merge_rates.py # 基于加权分布的合并率计算
│   ├── generate_sunburst.py # 生成层级嵌套旭日图 (交互式 HTML)
│   ├── generate_sankey.py   # 生成演变画像桑基图与描述性统计
│   └── plot_dialect_map.py  # 绘制自然地貌方言分布图
└── figs                     # 【输出】可视化成果
    ├── vowel_chain_sunburst.html
    ├── wuyu_topography_map.png
    └── sankey_evolution_profiles.html
2. 环境配置 (Setup)本项目运行于 Python 3.12+ 虚拟环境：Bash# 1. 激活环境
source env/bin/activate

## 2. 安装必要依赖包
pip install pandas matplotlib geopandas contextily plotly kaleido

## 3. 核心运行流程 (Workflow)
Step 1: 数据标准化运行清洗脚本。它会自动处理拼写错误兼容、声组归并，并根据 note 列自动标注文 (literary) / 白读。
python scripts/clean_wuyu.py

Step 2: 坐标补全打开 data_dict/point_coords_master.csv。在 Google Maps 上通过右键点击获取经纬度。将数值填入 lat 和 lon 列。

Step 3: 绘制地理分布图生成带有自然地貌底图（Esri World Physical）的分布图，透明度已优化为 0.85 以增强地形质感。
python scripts/plot_dialect_map.py

Step 4: 演变模式分析生成桑基图与旭日图，查看越级合并（Leap-frog Merger）的异常值占比。
python scripts/generate_sankey.py
python scripts/generate_sunburst.py

## 4. 关键算法逻辑说明权重分配：主体层 (Main Layer): 权重 1.0。文读层 (Literary): 权重 0.3（压低文读干扰，聚焦底层演化）。离群字 (Outlier): 权重 0.1。
聚类分析：通过 Combination (如 $K_{L3}|M_{L3}|...$) 对方言点进行“演变画像”聚合，识别核心演化模式。异常值监控：专门统计“越级合并率”（如 $S1=S3$），识别非线性演变路径。
## 5. 常见问题排查 (Troubleshooting)

## ☕️ Support
If my script hepls you to solve some problems, please leave me a star ⭐~
Wuyu Dataset は私自身が構築したものです (Self-constructed, lol). もし手伝ってくれる (help me out) なら, feel free to contact me!
I will public the full version of the dataset after attaining my master degree.
あとは Ant Colony Algorithm などの元音演化脚本のコンテンツ, so please stay tuned!

Maintainer: Zhenli Chen
Update: 2026-03-30
```
