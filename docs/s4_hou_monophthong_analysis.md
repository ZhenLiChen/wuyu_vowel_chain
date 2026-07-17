# S4 侯韵单音化分析

本文档记录 S4 侯韵的单音化分析。数据中的 S4 对应：

```text
chain_slot = S4
rhyme_modern = 侯
slot_type_initial = *əu
```

分析思路仿照之前的豪韵单音化：先判断每个现代读音是否为单元音，再按方言点汇总单音化程度、主导音值、与 S0-S3 单元音库藏的关系，最后投射到地图上观察地理聚集。

## 1. 口径

单元音判定：

```text
一个读音只有一个元音核，且不含 j/w/ɥ 介音或滑音，判为 monophthong
含两个以上元音核，或含 j/w/ɥ，判为 diphthong_or_glide
含 ʔ，判为 checked_or_coda，不计作单元音
没有元音核的 m/ŋ/v 等，判为 other
```

斜杠读音继续拆开计算，例如 `u/o` 计为 `u` 和 `o` 两个值。`o（uo）` 仍拆成 `u` 和 `uo`。

派生处理：

```text
启东吕四原表缺 point_id，派生表中记为 NO_ID_启东吕四
临平五杭坐标已补入 data_dict/point_coords_master.csv
```

这些处理不写回原始方言点数据。

## 2. 总体结果

本轮得到 82 条方言点记录，S4 有效读音 token 为 4737，其中单元音 token 为 2566：

```text
S4 侯韵单音化 token 占比 = 2566 / 4737 = 0.5417
```

按方言点状态看：

```text
monophthong_only: 31 点
mixed_mono_and_diphthong: 36 点
mixed_with_other: 11 点
diphthong_or_glide_only: 4 点
```

也就是说，S4 侯韵仍然不是像豪韵那样高度单音化，而是一个明显的过渡型格局：纯单音化点已经不少，但混合型仍然最多，未单音化点集中在少数区域。

## 3. 主要音值

S4 的单元音结果非常分散，但 token 最多的单元音是：

```text
ɤ: 762 tokens, 17 点
ø: 401 tokens, 12 点
e: 349 tokens, 11 点
ɯ: 296 tokens, 8 点
ɵ: 151 tokens, 3 点
u: 126 tokens, 58 点
o: 112 tokens, 21 点
ʏ: 86 tokens, 2 点
ᴇ: 79 tokens, 3 点
ə: 69 tokens, 3 点
```

复杂读音中，token 最多的是：

```text
ei: 658 tokens, 14 点
iəu: 157 tokens, 3 点
əu: 150 tokens, 7 点
ɤɯ: 139 tokens, 4 点
øy: 112 tokens, 2 点
œʏ: 104 tokens, 2 点
ou: 60 tokens, 5 点
```

这说明 S4 侯韵的单音化方向不是单一的“后元音化”或“高化”，而是至少分成几种类型：

```text
ɤ/ɯ 类：后不圆唇化或央后化
ø/ɵ/y/ʏ 类：前圆唇化
e/ᴇ/ɛ 类：前化/展唇化
u/o/ɔ 类：后圆唇保留或收缩
```

## 4. 小片差异

按 token 加权的小片单音化比例：

```text
太湖片-苕溪小片: 0.6975
太湖片-苏沪嘉小片: 0.6404
太湖片-临绍小片: 0.5933
太湖片-杭州小片: 0.3762
太湖片-毗陵小片: 0.3758
太湖片-甬江小片: 0.0327
```

苕溪、苏沪嘉、临绍的 S4 单音化程度明显较高；甬江最低。杭州和毗陵都比之前版本更高，说明新增点以后，S4 的单音化分布比原来看到的更广。

地理上看，苏沪嘉小片内部很值得注意：它既有大量 `ɤ/ɯ` 类单音化点，也有不少混合型点。这说明苏沪嘉不是简单地“全部单音化”，而是单音化方向比较分化。

## 5. 地图读法

地图文件：

```text
figs/s4_hou_monophthong_geography_map.png
```

图例含义：

```text
ɤ/ɯ类单音化：主导音值为 ɤ 或 ɯ
ø/ɵ/y类单音化：主导音值为 ø/ɵ/y/ʏ/œ/ʉ 类
e类单音化：主导音值为 e/ᴇ/ɛ/æ/i 类
u/o类单音化：主导音值为 u/o/ɔ/ɷ 类
混合：同一点中既有单元音，也有复元音/滑音，或还含 m/ŋ/v/ʔ 等其他类
未单音化：只有复元音/滑音，没有单元音
```

当前地图已经直接标出所有方言点名，方便对照具体点位。完整读音分布仍保留在 `point_s4_hou_monophthong_relation.csv`。

合并图例以后，地图类别计数是：

```text
混合: 47 点
ɤ/ɯ类单音化: 18 点
e类单音化: 8 点
ø/ɵ/y类单音化: 4 点
未单音化: 4 点
u/o类单音化: 1 点
```

地图上比较清楚的聚集是：

```text
1. 上海、金山、松江、闵行、奉贤、嘉善、南汇一带集中出现 ɤ/ɯ 类单音化。
2. 苕溪小片整体单音化比例高，但点数少，内部有 e 类、ø 类和混合型。
3. 临绍小片以混合型为主，说明 S4 正处在多方向竞争中。
4. 甬江小片未单音化和混合型较多，整体单音化比例最低。
```

## 6. 与 S0-S3 单元音库藏的关系

按每个方言点 S0-S3 的单元音库藏来比较，S4 单元音多数不是完全孤立的新值：

```text
partial_s4_mono_in_core_inventory: 43 点
all_s4_mono_in_core_back_inventory: 21 点
all_s4_mono_in_core_inventory: 7 点
s4_mono_outside_core_inventory: 6 点
no_s4_monophthong: 5 点
```

这可以解释为：S4 单音化常常会落到本方言点已经存在的单元音系统中，但不一定只落到后元音库藏。相较豪韵主要讨论后元音吸引，侯韵 S4 更需要同时讨论前化、圆唇化、央后化和复元音保留。

## 7. 类型学补充：S4、S5 与 S0-S1

S5 豪韵对应 `*au`，S4 侯韵对应 `*əu`。把两者放在一起看，最清楚的关系不是“二者同步单音化”，而是一个不对称蕴涵：

```text
S4 纯单音化 => S5 豪韵纯单音化
S5 豪韵纯单音化 ≠> S4 纯单音化
```

现在有 31 个 S4 纯单音化点，而 S5 豪韵纯单音化有 74 点。关键是这 31 个 S4 纯单音化点全部同时是 S5 豪韵纯单音化点：

```text
S4 ɤ/ɯ 类单音化 18 点：S5 全部为 monophthong_only
S4 e 类单音化 8 点：S5 全部为 monophthong_only
S4 ø/ɵ/y 类单音化 4 点：S5 全部为 monophthong_only
S4 u/o 类单音化 1 点：S5 也为 monophthong_only
```

反过来不成立：74 个 S5 豪韵纯单音化点中，S4 仍有 40 点是混合型，3 点是未单音化。这说明豪韵 `*au` 的单音化更普遍、更容易完成；侯韵 `*əu` 的单音化门槛更高，并且要在不同地区选择不同目标音：`ɤ/ɯ`、`e/ᴇ`、`ø/ɵ/y` 等。

和 S0-S1 的关系可以用“链位压缩倾向”来理解。这里的 S0-S1 合流率是各声母条件下 S0 与 S1 读音接近或合并的平均值；它不是因果解释，只是一个系统内部结构指标。结果显示：

```text
S4 纯单音化点的平均 S0-S1 合流率: 0.1793
S4 混合点的平均 S0-S1 合流率: 0.1385
S4 未单音化点的平均 S0-S1 合流率: 0.1063

e 类单音化: 0.1734
ɤ/ɯ 类单音化: 0.1803
ø/ɵ/y 类单音化: 0.1784
```

这个结果可以保守地解释为：S4 纯单音化更常见于元音链内部已经有一定压缩或重组倾向的方言点。也就是说，S4 单音化不是单独发生的孤立事件，而更像是某些点整体元音系统重排的一部分。S0-S1 合流率越高，说明链位边界越不稳定；在这种系统中，`*əu` 更容易从复合读音中收缩出来，落入一个现成的单元音位置。

需要注意，这不是绝对规则。S0-S1 合流率只是平均指标，具体还要看声母条件、小片和目标音类。特别是 `ɤ/ɯ` 类明显集中在苏沪嘉一带，说明地理扩散和小片传统仍然很重要。

## 8. 蕴涵关系

把 `S4`、`S5` 和 `S0-S1` 放在一起看，可以整理出几条比较稳定的蕴涵关系。

全量 `侯韵` 版本：

```text
S4 纯单音化 => S5 纯单音化      31 / 31 = 1.0000
S4 任意出现单音值 => S5 也有单音值 72 / 77 = 0.9351
S4 落入纯单音化类别 => S5 纯单音化 31 / 31 = 1.0000
```

这说明 `*əu` 的单音化完成度始终不高于 `*au`。换句话说，豪韵 `S5` 的单音化是更宽松、更先完成的一步；侯韵 `S4` 只有在系统已经允许豪韵稳定单音化的情况下，才会进一步收缩到 `ɤ/ɯ`、`e/ᴇ`、`ø/ɵ/y` 这些单元音目标。

和 `S0-S3` 库藏的关系也有一个偏强的方向：

```text
S4 纯单音化 => S4 单音值落在或部分落在 S0-S3 库藏中 30 / 31 = 0.9677
```

也就是说，全量版本里，侯韵一旦完成纯单音化，通常不是凭空冒出一个新目标，而是落进本方言已经存在的单元音格局里。这个方向和豪韵有点像，只是侯韵的目标音更分散，不只偏向后元音。

## 9. 补充：排除侯韵 M/P 组

为了回答“侯韵的单音化是不是主要靠 M/P 组撑出来”的问题，我额外重跑了一版补充分析：

```text
只在 S4 + 侯 的子集里排除 onset_class = M, P
S0-S3 库藏、S5 豪韵结果、merge rate 汇总口径都保持不变
```

补充版输出：

```text
data_clean/value_type/point_s4_hou_monophthong_relation_no_mp.csv
data_clean/value_type/s4_hou_monophthong_relation_summary_no_mp.csv
data_clean/value_type/s4_hou_value_summary_no_mp.csv
data_clean/value_type/s4_hou_monophthong_by_subbranch_no_mp.csv
data_clean/value_type/s4_hou_geographic_cluster_summary_no_mp.csv
data_clean/value_type/s4_hou_typology_with_s5_s0s1_no_mp.csv
data_clean/value_type/s4_hou_typology_summary_no_mp.csv
figs/s4_hou_monophthong_geography_map_no_mp.png
figs/s4_hou_monophthong_subbranch_summary_no_mp.png
```

排除 M/P 后，S4 token 从 `4737` 降到 `4086`，单音化 token 从 `2566` 降到 `2114`，总体占比从 `0.5417` 降到 `0.5174`。更关键的是，很多原来带少量单音值的“混合点”直接变成了“未单音化”：

```text
monophthong_only: 33 点
mixed_mono_and_diphthong: 20 点
diphthong_or_glide_only: 29 点
```

地图类别也明显重排：

```text
未单音化: 29 点
混合: 20 点
ɤ/ɯ类单音化: 18 点
e类单音化: 8 点
ø/ɵ/y类单音化: 6 点
u/o类单音化: 1 点
```

这说明 `M/P` 在侯韵里主要扮演的是“提供零星单音化痕迹”的角色，而不是决定主导演化方向的角色。真正稳定的主导结果仍然主要是 `ɤ/ɯ`、`e/ᴇ`、`ø/ɵ/y` 这几类纯单音化点。相反，那些一去掉 `M/P` 就从“混合”塌成“未单音化”的点，更适合解释成：

```text
该点的 S4 主体仍以复元音/滑音为主
单音值主要是局部声母条件下的次生产物
```

小片差异在补充版里也更清楚：

```text
太湖片-苕溪小片: 0.6529
太湖片-苏沪嘉小片: 0.6202
太湖片-临绍小片: 0.5695
太湖片-毗陵小片: 0.3555
太湖片-杭州小片: 0.3333
太湖片-甬江小片: 0.0000
```

最关键的一点是甬江小片：排除 `M/P` 以后，7 个点全部不再有 S4 单音值，整体占比直接降到 `0`。这说明甬江原先那一点点单音化痕迹，几乎完全依赖 `M/P` 条件，不构成一个稳定的全系统收缩方向。

补充版里的蕴涵关系也更清楚了一层：

```text
S4 纯单音化（排除 M/P） => S5 纯单音化      33 / 33 = 1.0000
S4 任意出现单音值（排除 M/P） => S5 也有单音值 51 / 53 = 0.9623
甬江小片（排除 M/P） => S4 不再有单音值      7 / 7 = 1.0000
```

但和全量版本不同的是，排除 `M/P` 以后，纯单音化结果不再总是落在 `S0-S3` 旧库藏内部：

```text
S4 纯单音化（排除 M/P）且落在/部分落在 S0-S3 库藏中: 16 / 33
S4 纯单音化（排除 M/P）但落在 S0-S3 库藏之外:      17 / 33
```

这说明一旦把 `M/P` 组提供的零星条件单音值拿掉，剩下那些稳定的侯韵单音化点里，有相当一部分并不是简单“借用现成 S0-S3 音位”，而是把 `*əu` 推到了一个相对独立的新单元音目标上。换句话说：

```text
全量版本更像“系统内吸收”
去掉 M/P 后更能看到“侯韵自身的独立收缩方向”
```

## 10. 暂时结论

S4 侯韵的单音化不是一个整齐的单方向变化，而是一个高度分化的演化场：

```text
*əu > ɤ/ɯ
*əu > ø/ɵ/y/ʏ
*əu > e/ᴇ
*əu 保留为 ei/əu/iəu/øy/œʏ 等复杂读音
```

其中，单音化较强的小片是苕溪、苏沪嘉、临绍；甬江明显保留复元音/滑音型。补充版进一步说明：不少“混合型”其实是 `M/P` 组单独贡献了一点单音值，而真正稳定的系统性单音化，还是集中在 `ɤ/ɯ`、`e/ᴇ`、`ø/ɵ/y` 这几类主导结果上。苏沪嘉内部的 `ɤ/ɯ` 类聚集仍然最值得进一步分析，因为它可能代表一条与豪韵 `*au` 单音化不同的 S4 内部机制。

下一步可以继续做三件事：

```text
1. 仿照豪韵模型，把 S4 是否单音化作为因变量，考察 S0-S3 单元音库藏、后元音库藏、前圆唇库藏、S0-S1 合流率的解释力。
2. 把 S4 的目标单元音分成 ɤ/ɯ、ø/ɵ/y、e/ᴇ 三类，做多分类模型，观察不同小片是否选择不同“吸引子”。
3. 把 S4 与 S5 联合建模，检验“豪韵先完成单音化，侯韵在部分地区继续单音化”的蕴涵关系是否稳定。
```

## 11. 输出文件

```text
scripts/analyze_s4_monophthongization.py
data_clean/value_type/point_s0_s3_monophthong_inventory_for_s4.csv
data_clean/value_type/point_s4_hou_monophthong_relation.csv
data_clean/value_type/s4_hou_monophthong_relation_summary.csv
data_clean/value_type/s4_hou_value_summary.csv
data_clean/value_type/s4_hou_monophthong_by_subbranch.csv
data_clean/value_type/s4_hou_geographic_cluster_summary.csv
data_clean/value_type/s4_hou_typology_with_s5_s0s1.csv
data_clean/value_type/s4_hou_typology_summary.csv
figs/s4_hou_monophthong_geography_map.png
figs/s4_hou_monophthong_subbranch_summary.png
data_clean/value_type/point_s4_hou_monophthong_relation_no_mp.csv
data_clean/value_type/s4_hou_monophthong_relation_summary_no_mp.csv
data_clean/value_type/s4_hou_value_summary_no_mp.csv
data_clean/value_type/s4_hou_monophthong_by_subbranch_no_mp.csv
data_clean/value_type/s4_hou_geographic_cluster_summary_no_mp.csv
data_clean/value_type/s4_hou_typology_with_s5_s0s1_no_mp.csv
data_clean/value_type/s4_hou_typology_summary_no_mp.csv
figs/s4_hou_monophthong_geography_map_no_mp.png
figs/s4_hou_monophthong_subbranch_summary_no_mp.png
```
