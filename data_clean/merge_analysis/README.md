merge_analysis 目录说明
======================

这个目录主要保存吴语 S0-S3 链位相邻合并率及其点级聚类结果。

一、核心入口
------------

1. point_onset_merge_rates.csv
   来源脚本：scripts/calculate_merge_rate.py
   用途：最基础的合并率结果表。
   粒度：point_id × onset_class
   关键列：
   - merge_S0_S1
   - merge_S1_S2
   - merge_S2_S3
   - merge_S1_S3（跨级补充参照列，不属于主链段）
   - comparison_scope（S1-S2 + S2-S3 两链段总体 / N-T 高位链的可比范围）
   - merge_S1_S3_two_link_mean（仅 K/M/P/TS/Ø；S1-S2 与 S2-S3 等权平均）
   - merge_NT_S2_S3_only（仅 N/T；S2-S3 独立值）

2. onset_merge_rate_summary.csv
   来源脚本：scripts/calculate_merge_rate.py
   用途：声组层面的总体合并率与排序。
   计算口径：
   - K/M/P/TS/Ø：先分别求 S1-S2、S2-S3 的声组均值，再按 1/2 等权平均并排名。
   - S0-S1：保留明细，但不参与当前总体值和总体排序。
   - N/T：仅按 S2-S3 均值在 N/T 内部单独排名。
   - S1-S3：只作跨级参照，不进入总体值。

详细说明已统一放到 docs：
- docs/merge_rate_methodology.md：完整公式、统计层级、字段说明与手算例子。
- docs/merge_rate_results.md：由脚本自动生成的当前数值榜单，代替原有两个重复 TXT 报告。

补充口径说明：
- 当前 merge rate 计算保留 `weight_type` 标注，但实际一律按等权 `1.0` 处理。
- 同一字若有多个 `/` 分隔读音，则仍按等概率均分到各读音。
- 当前总体指标只使用相邻链位 `S1-S2 / S2-S3`。
- `S0-S1` 暂不参与总体指标；直接 `S1-S3` 仅作跨级补充观察。

二、点级强度与聚类
----------------

3. point_merge_strength_summary.csv
   来源脚本：scripts/analyze_merge_strength_clusters.py
   用途：把点级三阶段合并率进一步压缩成强度摘要。

4. point_merge_strength_clusters.csv
   来源脚本：scripts/analyze_merge_strength_clusters.py
   用途：给每个方言点分配“合并强度簇”。

5. merge_strength_cluster_report.txt
   来源脚本：scripts/analyze_merge_strength_clusters.py
   用途：文字版聚类解释。

三、模式聚类比较
--------------

6. point_merge_pattern_clusters.csv
   来源脚本：scripts/plot_merge_clustering_comparison.py
   用途：另一套按模式而非强度得到的聚类结果。

7. merge_clustering_comparison_report.txt
   来源脚本：scripts/plot_merge_clustering_comparison.py
   用途：比较“强度聚类”和“模式聚类”的差异。

四、建议使用顺序
--------------

1. 先看 point_onset_merge_rates.csv
2. 看 onset_merge_rate_summary.csv 获取总体声组排序
3. 看 docs/merge_rate_methodology.md 理解完整公式
4. 看 docs/merge_rate_results.md 获取自动更新的文字结果
5. 再看 point_merge_strength_summary.csv
6. 最后看 point_merge_pattern_clusters.csv 与 comparison_report
