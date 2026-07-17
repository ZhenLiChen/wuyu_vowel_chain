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

2. summary_hierarchy_report.txt
   来源脚本：scripts/calculate_merge_rate.py
   用途：按声组汇总三阶段推力序列，并附带 S1-S3 跨级参照的文字报告。

3. onset_hierarchy_report.txt
   来源脚本：scripts/calculate_merge_rate.py
   用途：更细版的声组合并率排序说明。

补充口径说明：
- 当前 merge rate 计算保留 `weight_type` 标注，但实际一律按等权 `1.0` 处理。
- 同一字若有多个 `/` 分隔读音，则仍按等概率均分到各读音。
- 主分析仍以相邻链位 `S0-S1 / S1-S2 / S2-S3` 为核心。
- `S1-S3` 仅作跨级合并的补充观察，不建议直接替代主链指标。

二、点级强度与聚类
----------------

4. point_merge_strength_summary.csv
   来源脚本：scripts/analyze_merge_strength_clusters.py
   用途：把点级三阶段合并率进一步压缩成强度摘要。

5. point_merge_strength_clusters.csv
   来源脚本：scripts/analyze_merge_strength_clusters.py
   用途：给每个方言点分配“合并强度簇”。

6. merge_strength_cluster_report.txt
   来源脚本：scripts/analyze_merge_strength_clusters.py
   用途：文字版聚类解释。

三、模式聚类比较
--------------

7. point_merge_pattern_clusters.csv
   来源脚本：scripts/plot_merge_clustering_comparison.py
   用途：另一套按模式而非强度得到的聚类结果。

8. merge_clustering_comparison_report.txt
   来源脚本：scripts/plot_merge_clustering_comparison.py
   用途：比较“强度聚类”和“模式聚类”的差异。

四、建议使用顺序
--------------

1. 先看 point_onset_merge_rates.csv
2. 再看 point_merge_strength_summary.csv
3. 然后结合两个 txt 报告读聚类解释
4. 最后看 point_merge_pattern_clusters.csv 与 comparison_report
