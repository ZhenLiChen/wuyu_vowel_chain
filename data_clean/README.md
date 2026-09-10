data_clean 目录说明
==================

这个目录放的是清洗后的母表和各分析脚本导出的中间结果。

一、核心母表
------------

1. wuyu_lexeme.csv
   来源脚本：scripts/clean_wenzhou.py
   用途：全项目最核心的清洗总表。后续多数统计、类型学分析、链位分析都从这里出发。

2. wenzhou_lexeme.csv
   历史或局部清洗表。
   目前项目主线主要使用 wuyu_lexeme.csv。

二、子目录
----------

1. merge_analysis/
   主要放链位合并率、点级强度、聚类报告。
   主入口脚本通常是：
   - scripts/calculate_merge_rate.py
   - scripts/analyze_merge_strength_clusters.py
   - scripts/plot_merge_clustering_comparison.py

2. value_type/
   主要放音值库藏、主体层链表、裂化/单音化统计、ACO 模拟输入输出等。
   常见来源脚本包括：
   - scripts/analyze_rhyme_phonetics.py
   - scripts/analyze_point_phonetic_inventory.py
   - scripts/analyze_onset_inventory_ratio.py
   - scripts/analyze_s0_s3_diphthongization.py
   - scripts/analyze_s4_monophthongization.py
   - scripts/analyze_hao_monophthong_relation.py
   - scripts/analyze_hao_models.py
   - scripts/analyze_hao_implications.py
   - scripts/run_vowel_aco_small.py
   - scripts/run_vowel_aco_conditioned.py

三、目前建议阅读顺序
------------------

1. 先看 wuyu_lexeme.csv
2. 再看 merge_analysis/point_onset_merge_rates.csv
3. 然后看 value_type/point_slot_onset_distribution.csv
4. 若关心主体层链值，再看：
   - value_type/type_phonetic_chains.csv
   - value_type/phonetic_evolution_chains.csv

四、当前需要注意的命名遗留
------------------------

1. type_phonetic_chains.csv
   是 scripts/analyze_rhyme_phonetics.py 当前实际导出的链值表名。

2. phonetic_evolution_chains.csv
   也是一张链值表，但与 type_phonetic_chains.csv 目前并不完全一致。
   后续建议统一只保留一个标准文件名。
