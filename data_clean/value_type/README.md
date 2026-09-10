value_type 目录说明
==================

这个目录是项目里最杂、但也最重要的结果仓库。
这里混合保存了：
- 音值分布
- 主体层链值表
- 裂化分析
- 豪/侯 单音化分析
- ACO 模拟输入输出
- 若干人工检查辅助表

一、主体层与链值相关
------------------

1. point_slot_onset_distribution.csv
   来源脚本：scripts/analyze_rhyme_phonetics.py
   用途：按 point_id × onset_class × chain_slot 汇总读音频次分布。
   说明：如果你的主体层逻辑是“取出现次数最多的元音”，这张表就是最直接的依据。

2. type_phonetic_chains.csv
   来源脚本：scripts/analyze_rhyme_phonetics.py
   用途：从 point_slot_onset_distribution.csv 中提取每格频次最高的音值，透视成 S0/S1/S2/S3 链表。
   说明：这是目前更像“主体层链表”的标准来源文件。

3. phonetic_evolution_chains.csv
   兼容旧文件名的链表文件。
   说明：当前由 scripts/analyze_rhyme_phonetics.py 同步写出，与 type_phonetic_chains.csv 保持一致。

4. mainlayer_manual_adjudication_candidates.csv
   人工检查辅助表。
   说明：这是排查旧口径或异常格位时用的辅助表，不是项目原生主流程文件。

5. outlier_char_frequency.csv
   来源脚本：scripts/analyze_rhyme_phonetics.py
   用途：统计低频或分布特殊的例字。

6. 相关主流程脚本
   - scripts/clean_wenzhou.py
     负责清洗原始点表，并抽取 vowel_symbol。
   - scripts/analyze_rhyme_phonetics.py
     负责生成 point_slot_onset_distribution.csv 和主体层链表。
   - scripts/update_mainlayer_tables.py
     负责从主体层链表生成 data_raw/mainlayer_merge.csv 与 data_raw/dialect_evolution_profiles_full.csv。

6a. mainlayer_chain_clusters.csv
   来源脚本：scripts/cluster_mainlayer_chains.py
   用途：82 个方言点的 S0-S3 点级代表链、各 slot 的声母内部离散度，以及 k=2..8 的聚类标签。

6b. mainlayer_chain_cluster_summary.csv
   来源脚本：scripts/cluster_mainlayer_chains.py
   用途：自动推荐 k=3 的类型结论、主模式、代表方言点、成员表与各类 S3 复元音点数。
   选类规则：先要求每类至少 5 点，再在合格解中选择 silhouette 最高者。

6c. mainlayer_chain_clusters.json
   来源脚本：scripts/cluster_mainlayer_chains.py
   用途：保存 IPA 节点、复元音起止顺序、各 k 解和 S3 复元音诊断，供交互图使用。

6d. mainlayer_chain_all_k_summary.csv
   来源脚本：scripts/cluster_mainlayer_chains.py
   用途：汇总 k=2..8 的全部类别规模、代表链与成员；用于检查较细解中出现的 uo 等小型模式。

6e. mainlayer_chain_k3_geography.csv
   来源脚本：scripts/plot_mainlayer_chain_k3_map.py
   用途：将推荐的 k=3 类别与 82 个方言点的经纬度、吴语小片及代表链合并，供地理制图和逐点核查。
   对应地图：figs/mainlayer_chain_k3_map.png

   详细算法与当前结果见：docs/mainlayer_chain_clustering.md

二、音值库藏与分布
----------------

6. point_phonetic_inventory.csv
   来源脚本：scripts/analyze_point_phonetic_inventory.py
   用途：各点总体音值库藏。

7. rhyme_phonetic_distribution.csv
   来源脚本：scripts/analyze_rhyme_phonetics.py
   用途：分韵详细音值分布。

8. point_rhyme_inventory.csv
   来源脚本：scripts/analyze_rhyme_phonetics.py
   用途：各点分韵音值集合。

9. point_total_inventory.csv
   来源脚本：scripts/analyze_rhyme_phonetics.py
   用途：各点全局音值集合及数量。

10. point_slot_onset_phonetic_counts.csv
    来源脚本：scripts/analyze_slot_onset_phonetic_counts.py
    用途：统计 point × slot × onset 的音值数量。

11. point_onset_inventory_ratios.csv
12. point_onset_inventory_inequalities.csv
13. global_onset_inventory_inequality.csv
    来源脚本：scripts/analyze_onset_inventory_ratio.py
    用途：观察各声组的音值库藏覆盖率及不均衡程度。

三、S0-S3 裂化分析
----------------

14. s0_s3_split_value_classification.csv
15. s0_s3_medial_pending.csv
16. s0_s3_i_offglide_excluded.csv
17. s0_s3_non_core_diphthong_excluded.csv
18. s0_s3_u_medial_pending.csv
19. s0_s3_split_onset_stats.csv
20. s0_s3_split_onset_sequences.csv
21. s0_s3_split_slot_stats.csv
22. s0_s3_split_slot_onset_stats.csv
23. s0_s3_split_point_onset_stats.csv
24. s0_s3_split_point_slot_stats.csv
25. s0_s3_split_implication_rules.csv
    来源脚本：scripts/analyze_s0_s3_diphthongization.py
    用途：围绕 S0-S3 裂化、介音化、排除项与蕴涵关系的整套结果。

四、豪/侯 单音化与类型学
----------------------

26. point_monophthong_inventory.csv
27. point_hao_monophthong_relation.csv
28. hao_monophthong_relation_summary.csv
29. hao_value_summary.csv
    来源脚本：scripts/analyze_hao_monophthong_relation.py

30. hao_implication_point_features.csv
31. hao_typological_implication_rules.csv
    来源脚本：scripts/analyze_hao_implications.py

32. hao_monophthong_logistic_coefficients.csv
33. hao_monophthong_logistic_predictions.csv
34. hao_attractor_softmax_coefficients.csv
35. hao_attractor_softmax_probabilities.csv
36. hao_attractor_softmax_summary.csv
    来源脚本：scripts/analyze_hao_models.py

37. hao_monophthong_by_subbranch.csv
38. hao_geographic_cluster_summary.csv
    来源脚本：scripts/analyze_hao_geography.py

39. point_s0_s3_monophthong_inventory_for_s4.csv
40. point_s4_hou_monophthong_relation.csv
41. s4_hou_monophthong_relation_summary.csv
42. s4_hou_value_summary.csv
43. s4_hou_monophthong_by_subbranch.csv
44. s4_hou_geographic_cluster_summary.csv
45. s4_hou_typology_with_s5_s0s1.csv
46. s4_hou_typology_summary.csv
    来源脚本：scripts/analyze_s4_monophthongization.py

五、ACO 模拟相关
---------------

47. aco_small_observation_tasks.csv
48. aco_small_edge_pheromones.csv
49. aco_small_slot_target_paths.csv
50. aco_small_sigma_comparison.csv
    来源脚本：scripts/run_vowel_aco_small.py

51. ant_colony_core_split_support.csv
    来源脚本：scripts/visualize_vowel_ant_colony.py

52. aco_conditioned_group_summary.csv
53. aco_conditioned_path_summary.csv
54. aco_conditioned_edge_pheromones.csv
55. aco_conditioned_linguistic_pressure.csv
    来源脚本：scripts/run_vowel_aco_conditioned.py

六、如果你现在只关心主体层和 sunburst/sankey
-------------------------------------------

建议优先看：

1. point_slot_onset_distribution.csv
   这里能直接看到每个格位的音值频次。

2. type_phonetic_chains.csv
   这里是按“最高频音值”透视出来的链表。

3. mainlayer_merge.csv
   这是在链表基础上加了分合分类的结果表。

4. dialect_evolution_profiles_full.csv
   这是桑基图直接使用的点级画像表。

当前判断：
- 你的主体层逻辑最接近 point_slot_onset_distribution.csv -> 取最高频 -> type_phonetic_chains.csv -> 分类成 mainlayer_merge.csv
- 当前更新链建议按这个顺序跑：
  clean_wenzhou.py -> analyze_rhyme_phonetics.py -> update_mainlayer_tables.py
