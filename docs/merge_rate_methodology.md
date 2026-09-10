# S1-S2、S2-S3 Merge Rate：计算公式、总体值与解释

本文是项目中 merge rate（合并率）的正式计算说明。对应实现为
`scripts/calculate_merge_rate.py`，当前数值结果见
`docs/merge_rate_results.md`。

## 1. 指标要回答什么问题

Merge rate 比较同一方言点、同一声母条件下，两个链位的音值概率分布有多大程度重叠。

- 数值接近 `1`：两个链位主要使用相同音值，表面合流程度较高。
- 数值接近 `0`：两个链位主要使用不同音值，表面区分程度较高。
- 它衡量的是分布重叠，不是单纯比较音值类型数，也不是直接测量元音之间的语音距离。
- 它本身不能证明变化方向、年代先后或声母条件的因果作用。

基础明细表保留三个相邻链段：

```text
S0（佳、皆）— S1（麻）— S2（歌、戈）— S3（模）
```

当前总体指标只使用 `S1-S2` 和 `S2-S3`。`S0-S1` 暂不参与总体值或总体排序，
仅保留在基础明细表中供旧分析兼容。

另外直接计算 `S1-S3` 作为跨级参照。这个直接重叠率与
`S1-S2`、`S2-S3` 两段的平均值不是同一个指标。

## 2. 输入数据与预处理

### 2.1 输入文件

- `data_clean/wuyu_lexeme.csv`：方言点、字项、韵位、声母组、音值等清洗结果。
- `data_dict/weight_mapping.csv`：保留 `weight_type` 标注；当前计算不使用差异权重。

### 2.2 韵位映射

| 今韵 | 链位 |
|:---:|:---:|
| 佳、皆 | S0 |
| 麻 | S1 |
| 歌、戈 | S2 |
| 模 | S3 |

映射不到 S0-S3 的记录不进入本项统计。

### 2.3 声母组归并

计算前统一声母标签：

```text
L → N
Ts / Ts* / TS* → TS
```

最终使用的声组为 `K / M / N / P / T / TS / Ø`。

### 2.4 特殊字项与权重

- 排除当前分析不讨论的 `靴`、`茄`。
- 每个字的基础权重统一设为 `W_i = 1`。
- `weight_type` 仍保留在处理流程中，但不改变本轮数值。
- 同一字若有多个 `/` 分隔读音，权重在这些读音之间等分。

例如某字有两个读音，则每个读音获得 `1/2`；三个读音则各获得 `1/3`。
这样一个多读音字的总贡献仍为 `1`，不会因为记录拆成多行而被重复加权。

## 3. 链位内音值概率分布

令：

- `p`：方言点；
- `c`：声母组；
- `s`：链位；
- `i`：字项；
- `m_i`：字项 `i` 在当前方言点、声组和链位下的读音数；
- `v_ij`：字项 `i` 的第 `j` 个音值；
- `W_i`：字项权重，当前恒为 `1`。

一个具体读音记录分得的权重为：

```math
w_{ij}=\frac{W_i}{m_i}
```

音值 `v` 在 `(p,c,s)` 条件下的加权频数为：

```math
C_{p,c,s}(v)=\sum_i\sum_{j=1}^{m_i}
\mathbf{1}(v_{ij}=v)\frac{W_i}{m_i}
```

其中 `1(·)` 是指示函数：条件成立取 `1`，否则取 `0`。

该条件下的总字项权重为：

```math
D_{p,c,s}=\sum_i W_i
```

于是音值概率分布为：

```math
P_{p,c,s}(v)=\frac{C_{p,c,s}(v)}{D_{p,c,s}}
```

在数据完整的情况下：

```math
\sum_v P_{p,c,s}(v)=1
```

## 4. 两个链位之间的 Merge Rate

对同一方言点 `p`、同一声母组 `c` 的两个链位 `a`、`b`，合并率定义为两个音值概率分布的重叠系数：

```math
MR_{p,c}^{a,b}=\sum_{v\in V_a\cup V_b}
\min\left(P_{p,c,a}(v),P_{p,c,b}(v)\right)
```

其等价形式是：

```math
MR_{p,c}^{a,b}=1-\frac{1}{2}
\sum_v\left|P_{p,c,a}(v)-P_{p,c,b}(v)\right|
```

因此：

```math
0\le MR_{p,c}^{a,b}\le 1
```

- `MR = 1`：两个链位的音值概率分布完全相同。
- `MR = 0`：两个链位没有任何共同音值。
- 中间值表示部分音值及其概率质量重叠。

当前代码以清洗后的 `phonetic` 字符串完全相同作为音值匹配标准。例如两个仅在附加符号上不同的音值，不会自动按“语音相近”给予部分分数。

### 4.1 主链段

```text
merge_S0_S1 = MR^(S0,S1)
merge_S1_S2 = MR^(S1,S2)
merge_S2_S3 = MR^(S2,S3)
```

### 4.2 跨级参照

```text
merge_S1_S3 = MR^(S1,S3)
```

该列用于观察麻韵与模韵的跨级重叠，不属于相邻链位指标，不参与总体分数。

## 5. 手算例子

假设某方言点、某声组的两个相邻链位分布为：

| 音值 | 链位 A | 链位 B | 两者较小值 |
|:---:|---:|---:|---:|
| a | 0.75 | 0.25 | 0.25 |
| o | 0.25 | 0.50 | 0.25 |
| u | 0.00 | 0.25 | 0.00 |

则：

```math
MR^{A,B}=0.25+0.25+0=0.50
```

这表示两个链位有一半的概率质量落在共同音值上。

## 6. 方言点 × 声组的两链段总体值

只有在 S1、S2、S3 条件下具有可比数据的核心声组
`K / M / P / TS / Ø` 计算总体值。

对方言点 `p` 和核心声组 `c`：

```math
MR_{p,c}^{S1-S3\ two\ link}
=\frac{MR_{p,c}^{S1,S2}+MR_{p,c}^{S2,S3}}{2}
```

对应字段为：

```text
merge_S1_S3_two_link_mean
```

这里的 “two link” 指 `S1-S2` 与 `S2-S3` 两个相邻链段的总体平均，
不是直接计算 S1 与 S3 的分布重叠。两个链段各占 `1/2`，
`S0-S1` 不参与。

当前实现要求 `S1-S2`、`S2-S3` 都有有效值；若其中一段缺失，
总体值也保留为空，以避免单链段结果与双链段结果直接比较。

## 7. 声组层面的总体均值与排序

先对每个声组、每个相邻链段在所有有效方言点上求均值：

```math
\overline{MR}_{c}^{a,b}
=\frac{1}{n_{c,a,b}}\sum_{p\in\mathcal{P}_{c,a,b}}MR_{p,c}^{a,b}
```

其中：

- `P_(c,a,b)` 是声组 `c` 在链段 `a-b` 上有有效值的方言点集合；
- `n_(c,a,b)` 是该集合的方言点数；
- 当前总体表中记录为 `valid_points_S1_S2`、`valid_points_S2_S3`。

核心声组的两链段总体均值为：

```math
O_c=\frac{
\overline{MR}_{c}^{S1,S2}
+\overline{MR}_{c}^{S2,S3}
}{2},\qquad c\in\{K,M,P,TS,Ø\}
```

对应字段为：

```text
overall_S1_S3_two_link_mean
overall_S1_S3_rank
```

按 `O_c` 从高到低排序。并列时使用 `rank(method="min")`，即两个并列第一之后，下一名记为第三。

当前五个核心声组在 `S1-S2`、`S2-S3` 上都各有 82 个有效方言点，
因此“先按链段求声组均值再取两段平均”与“先求每个点的两段平均再跨点平均”
数值相同。保留分步公式是为了让将来出现缺失数据时，两个链段仍维持相同权重。

## 8. 为什么 N/T 单独计算

`N / T` 按独立高位链处理，不与核心声组的双链段总体值混排。
其中 T 没有 S1 数据；N 虽有部分 S1 数据，但为保持 N/T 的统一特殊声组口径，
本分析仍将 N 的低位链指标排除。因此代码对以下指标强制保留为空：

```text
N/T 的 merge_S0_S1
N/T 的 merge_S1_S2
N/T 的 merge_S1_S3
```

`N / T` 只比较共同有效的 `S2-S3`：

```math
H_c=\overline{MR}_{c}^{S2,S3},\qquad c\in\{N,T\}
```

并且只在 N、T 两组内部排序。对应字段为：

```text
merge_NT_S2_S3_only
NT_S2_S3_mean
NT_S2_S3_rank
```

N/T 的数值不能直接插入五个核心声组的总体榜单，因为前者只概括
`S2-S3` 一个链段，后者概括 `S1-S2`、`S2-S3` 两个链段。

## 9. 输出表字段说明

### 9.1 `point_onset_merge_rates.csv`

粒度是一行一个 `方言点 × 声组`。

| 字段 | 含义 |
|---|---|
| `point_id` | 方言点编号 |
| `point_name` | 方言点名称 |
| `onset_class` | 归并后的声母组 |
| `merge_S0_S1` | S0 与 S1 的分布重叠率 |
| `merge_S1_S2` | S1 与 S2 的分布重叠率 |
| `merge_S2_S3` | S2 与 S3 的分布重叠率 |
| `merge_S1_S3` | S1 与 S3 的跨级参照值 |
| `comparison_scope` | `S1-S3_two_link_mean` 或 `S2-S3_only` |
| `merge_S1_S3_two_link_mean` | 核心声组的 S1-S2、S2-S3 两链段等权平均 |
| `merge_NT_S2_S3_only` | N/T 的 S2-S3 独立值 |

### 9.2 `onset_merge_rate_summary.csv`

粒度是一行一个声组。

| 字段 | 含义 |
|---|---|
| `mean_merge_S1_S2` | 声组跨方言点的 S1-S2 均值 |
| `mean_merge_S2_S3` | 声组跨方言点的 S2-S3 均值 |
| `valid_points_S1_S2` | S1-S2 的有效方言点数 |
| `valid_points_S2_S3` | S2-S3 的有效方言点数 |
| `comparison_scope` | 该声组参与的比较范围 |
| `overall_S1_S3_two_link_mean` | 核心声组的两链段总体值 |
| `overall_S1_S3_rank` | 核心声组内部名次 |
| `NT_S2_S3_mean` | N/T 的 S2-S3 均值 |
| `NT_S2_S3_rank` | N/T 两组内部名次 |
| `aggregation_method` | 人类可读的计算口径说明 |

CSV 中的空单元格表示该指标在设计上不适用或数据不足，不应按 `0` 解释。

## 10. 与其他表的关系

- `point_onset_merge_rates.csv`：最基础的点 × 声组合并率。
- `onset_merge_rate_summary.csv`：本文定义的声组总体排序。
- `point_merge_strength_summary.csv`：服务于方言点聚类的另一层摘要，不等同于声组总体排序。
- `docs/onset_inventory_and_merge_interpretation.md`：解释 merge rate 与音值库藏覆盖率为什么不能互相替代。
- `docs/merge_rate_results.md`：当前数据运行后自动生成的数值榜单。

特别注意：现有点级聚类表的 `avg_S2_S3` 是对该方言点所有有效声组求均值，
包含 N/T；本文的核心声组总体榜单只平均 `S1-S2`、`S2-S3` 并把 N/T 分开。
二者服务于不同分析问题，不应混作同一个指标。

## 11. 复现方式

在项目根目录运行：

```bash
env/bin/python scripts/calculate_merge_rate.py
```

脚本会更新：

```text
data_clean/merge_analysis/point_onset_merge_rates.csv
data_clean/merge_analysis/onset_merge_rate_summary.csv
docs/merge_rate_results.md
```

建议复核顺序：

1. 检查两个 CSV 的有效点数和空值范围；
2. 检查核心声组的 S1-S2、S2-S3 均值；
3. 按本文公式重算 `overall_S1_S3_two_link_mean`；
4. 确认 N/T 只在 `S2-S3` 内排序；
5. 最后阅读自动生成的结果文档。
