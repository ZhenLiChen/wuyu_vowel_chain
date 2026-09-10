import pandas as pd
import numpy as np
from pathlib import Path

# === 1. 路径与权重设置 ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = PROJECT_ROOT / "data_clean"
DATA_DICT = PROJECT_ROOT / "data_dict"
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_DIR = DATA_CLEAN / "merge_analysis"
ONSET_SUMMARY_OUTPUT = OUTPUT_DIR / "onset_merge_rate_summary.csv"
RESULTS_DOC_OUTPUT = DOCS_DIR / "merge_rate_results.md"

UNIFORM_WEIGHT = 1.0
RHYME_TO_SLOT = {
    "佳": "S0", "皆": "S0",
    "麻": "S1",
    "歌": "S2", "戈": "S2",
    "模": "S3"
}
CORE_PAIRS = [("S0", "S1"), ("S1", "S2"), ("S2", "S3")]
SUPPLEMENTARY_PAIRS = [("S1", "S3")]
CORE_ONSETS = ["K", "M", "P", "TS", "Ø"]
RESTRICTED_ONSETS = ["N", "T"]
OVERALL_MERGE_COLS = ["merge_S1_S2", "merge_S2_S3"]

# === 2. 加载与清洗 ===
df = pd.read_csv(DATA_CLEAN / "wuyu_lexeme.csv")
weight_dict_df = pd.read_csv(DATA_DICT / "weight_mapping.csv")

# 预处理：剔除不讨论字，清理声母类别并归并同类项
df = df[~df["char"].isin(["靴", "茄"])]
df["onset_class"] = (
    df["onset_class"]
    .astype("string")
    .str.strip()
    .replace({"L": "N", "Ts": "TS", "Ts*": "TS", "TS*": "TS"})
)

# 保留 weight_type 标注，但本轮 merge rate 采用等权重
df = df.merge(weight_dict_df, on="char", how="left")
df["weight_type"] = df["weight_type"].fillna("S")
df["W_i"] = UNIFORM_WEIGHT
df["slot"] = df["rhyme_modern"].map(RHYME_TO_SLOT)
df = df[df["slot"].notna()]

# 计算加权概率分布 P_k
df["n_pron"] = df.groupby(["point_id", "onset_class", "slot", "char"])["phonetic"].transform("count")
df["weighted_val"] = df["W_i"] / df["n_pron"]

denom = df.drop_duplicates(["point_id", "onset_class", "slot", "char"]).groupby(
    ["point_id", "point_name", "onset_class", "slot"]
)["W_i"].sum().reset_index(name="sum_W")

num = df.groupby(["point_id", "onset_class", "slot", "phonetic"])["weighted_val"].sum().reset_index(name="sum_weighted_val")
dist_df = num.merge(denom, on=["point_id", "onset_class", "slot"])
dist_df["P_k"] = dist_df["sum_weighted_val"] / dist_df["sum_W"]

# === 3. 计算合并率 (Merge Rate) ===
def calculate_overlap(group_a, group_b):
    merged = pd.merge(group_a, group_b, on="phonetic", how="outer", suffixes=('_A', '_B')).fillna(0)
    return np.sum(np.minimum(merged["P_k_A"], merged["P_k_B"]))

results = []
for (pid, pname, onset), group in dist_df.groupby(["point_id", "point_name", "onset_class"]):
    slots = group["slot"].unique()
    row_res = {"point_id": pid, "point_name": pname, "onset_class": onset}

    for s_a, s_b in CORE_PAIRS + SUPPLEMENTARY_PAIRS:
        # N/T 按独立高位链处理：T 无低位格；N 虽有部分 S1 数据，也按统一口径排除。
        if onset in ["N", "T"] and (s_a, s_b) in [("S0", "S1"), ("S1", "S2"), ("S1", "S3")]:
            row_res[f"merge_{s_a}_{s_b}"] = np.nan
        elif s_a in slots and s_b in slots:
            dist_a = group[group["slot"] == s_a][["phonetic", "P_k"]]
            dist_b = group[group["slot"] == s_b][["phonetic", "P_k"]]
            row_res[f"merge_{s_a}_{s_b}"] = round(calculate_overlap(dist_a, dist_b), 4)
        else:
            row_res[f"merge_{s_a}_{s_b}"] = np.nan
    results.append(row_res)

merge_df = pd.DataFrame(results)

# 核心声组只按 S1-S2 与 S2-S3 两段等权合成总体值；S0-S1 不参与。
# N/T 只保留 S2-S3 的独立值，避免与两链段总体值放在同一榜单中比较。
core_mask = merge_df["onset_class"].isin(CORE_ONSETS)
restricted_mask = merge_df["onset_class"].isin(RESTRICTED_ONSETS)
merge_df["comparison_scope"] = np.select(
    [core_mask, restricted_mask],
    ["S1-S3_two_link_mean", "S2-S3_only"],
    default="unclassified",
)
merge_df["merge_S1_S3_two_link_mean"] = np.nan
merge_df.loc[core_mask, "merge_S1_S3_two_link_mean"] = merge_df.loc[
    core_mask, OVERALL_MERGE_COLS
].mean(axis=1, skipna=False).round(6)
merge_df["merge_NT_S2_S3_only"] = np.nan
merge_df.loc[restricted_mask, "merge_NT_S2_S3_only"] = merge_df.loc[
    restricted_mask, "merge_S2_S3"
]

# 声组层面的总体排序表：先分别汇总 S1-S2、S2-S3，再给两段相同权重。
# N/T 的名次只在 N/T 两组的 S2-S3 范围内计算。
onset_summary = (
    merge_df.groupby("onset_class", dropna=False)
    .agg(
        mean_merge_S1_S2=("merge_S1_S2", "mean"),
        mean_merge_S2_S3=("merge_S2_S3", "mean"),
        valid_points_S1_S2=("merge_S1_S2", "count"),
        valid_points_S2_S3=("merge_S2_S3", "count"),
    )
    .reset_index()
)
onset_summary["comparison_scope"] = np.select(
    [onset_summary["onset_class"].isin(CORE_ONSETS), onset_summary["onset_class"].isin(RESTRICTED_ONSETS)],
    ["S1-S3_two_link_mean", "S2-S3_only"],
    default="unclassified",
)
onset_summary["overall_S1_S3_two_link_mean"] = np.nan
core_summary_mask = onset_summary["onset_class"].isin(CORE_ONSETS)
onset_summary.loc[core_summary_mask, "overall_S1_S3_two_link_mean"] = onset_summary.loc[
    core_summary_mask,
    ["mean_merge_S1_S2", "mean_merge_S2_S3"],
].mean(axis=1, skipna=False)
onset_summary["overall_S1_S3_rank"] = pd.Series(pd.NA, index=onset_summary.index, dtype="Int64")
onset_summary.loc[core_summary_mask, "overall_S1_S3_rank"] = (
    onset_summary.loc[core_summary_mask, "overall_S1_S3_two_link_mean"]
    .rank(method="min", ascending=False)
    .astype("Int64")
)
onset_summary["NT_S2_S3_mean"] = np.nan
restricted_summary_mask = onset_summary["onset_class"].isin(RESTRICTED_ONSETS)
onset_summary.loc[restricted_summary_mask, "NT_S2_S3_mean"] = onset_summary.loc[
    restricted_summary_mask, "mean_merge_S2_S3"
]
onset_summary["NT_S2_S3_rank"] = pd.Series(pd.NA, index=onset_summary.index, dtype="Int64")
onset_summary.loc[restricted_summary_mask, "NT_S2_S3_rank"] = (
    onset_summary.loc[restricted_summary_mask, "NT_S2_S3_mean"]
    .rank(method="min", ascending=False)
    .astype("Int64")
)
onset_summary["aggregation_method"] = np.where(
    core_summary_mask,
    "S1-S2 与 S2-S3 两个声组层均值等权平均（每段 1/2；S0-S1 不参与）",
    "仅用 S2-S3 声组均值并在 N/T 两组内排名",
)
onset_summary["_scope_order"] = onset_summary["comparison_scope"].map(
    {"S1-S3_two_link_mean": 0, "S2-S3_only": 1}
).fillna(2)
onset_summary["_rank_order"] = onset_summary["overall_S1_S3_rank"].fillna(
    onset_summary["NT_S2_S3_rank"]
)
onset_summary = onset_summary.sort_values(
    ["_scope_order", "_rank_order", "onset_class"]
).drop(columns=["_scope_order", "_rank_order"])
summary_rate_cols = [
    "mean_merge_S1_S2",
    "mean_merge_S2_S3",
    "overall_S1_S3_two_link_mean",
    "NT_S2_S3_mean",
]
onset_summary[summary_rate_cols] = onset_summary[summary_rate_cols].round(6)

# === 4. 生成声组排序与结果文档 ===
def get_ranked_list(col_name):
    # 只计算非NaN的声组平均值
    avg_series = merge_df.groupby("onset_class")[col_name].mean().dropna().sort_values(ascending=False)
    return [f"{idx}({val:.3f})" for idx, val in avg_series.items()]

# 提取本次总体值涉及的两个阶段，以及 S1-S3 直接跨级参照
rank_s1_s2 = get_ranked_list("merge_S1_S2")
rank_s2_s3 = get_ranked_list("merge_S2_S3")
rank_s1_s3 = get_ranked_list("merge_S1_S3")

core_overall_rank = [
    f"{row.onset_class}({row.overall_S1_S3_two_link_mean:.3f})"
    for row in onset_summary.loc[core_summary_mask].sort_values("overall_S1_S3_rank").itertuples()
]
nt_s2_s3_rank = [
    f"{row.onset_class}({row.NT_S2_S3_mean:.3f})"
    for row in onset_summary.loc[restricted_summary_mask].sort_values("NT_S2_S3_rank").itertuples()
]

def format_rate(value):
    return "—" if pd.isna(value) else f"{value:.3f}"


core_table_rows = []
for row in onset_summary.loc[core_summary_mask].sort_values("overall_S1_S3_rank").itertuples():
    core_table_rows.append(
        f"| {int(row.overall_S1_S3_rank)} | {row.onset_class} | "
        f"{format_rate(row.mean_merge_S1_S2)} | {format_rate(row.mean_merge_S2_S3)} | "
        f"{format_rate(row.overall_S1_S3_two_link_mean)} |"
    )

nt_table_rows = []
for row in onset_summary.loc[restricted_summary_mask].sort_values("NT_S2_S3_rank").itertuples():
    nt_table_rows.append(
        f"| {int(row.NT_S2_S3_rank)} | {row.onset_class} | "
        f"{format_rate(row.mean_merge_S2_S3)} | {int(row.valid_points_S2_S3)} |"
    )

n_points = merge_df["point_id"].nunique()
results_markdown = [
    "# Merge rate 当前计算结果",
    "",
    "> 本文件由 `scripts/calculate_merge_rate.py` 自动生成，请勿手工修改。",
    "> 详细定义、公式与手算例子见 `docs/merge_rate_methodology.md`。",
    "",
    "## 1. 本轮统计口径",
    "",
    f"- 方言点数：{n_points}",
    "- 核心声组：`K / M / P / TS / Ø`",
    "- 核心总体值：只使用 `S1-S2` 与 `S2-S3`，两个声组均值按 `1/2` 等权平均",
    "- `S0-S1`：保留明细列供旧分析兼容，不参与本次总体值和总体排序",
    "- `N / T`：只在 `S2-S3` 范围内单独比较，不进入核心总体榜单",
    "- `S1-S3`：仅作跨级参照，不计入总体值",
    "",
    "## 2. S1-S2、S2-S3 核心声组总体排序",
    "",
    f"**{' > '.join(core_overall_rank)}**",
    "",
    "| 名次 | 声组 | S1-S2 | S2-S3 | 总体值 |",
    "|---:|:---:|---:|---:|---:|",
    *core_table_rows,
    "",
    "## 3. N/T 独立排序",
    "",
    f"**{' > '.join(nt_s2_s3_rank)}**",
    "",
    "| 名次 | 声组 | S2-S3 | 有效方言点数 |",
    "|---:|:---:|---:|---:|",
    *nt_table_rows,
    "",
    "## 4. 本次纳入总体值的两个链段",
    "",
    f"- S1-S2（麻 → 歌戈）：{' > '.join(rank_s1_s2)}",
    f"- S2-S3（歌戈 → 模）：{' > '.join(rank_s2_s3)}",
    "",
    "## 5. 跨级参照",
    "",
    f"- S1-S3（麻 → 模）：{' > '.join(rank_s1_s3)}",
    "",
    "该项是 S1 与 S3 的直接分布重叠，不等于两个相邻链段的平均，也不进入总体值。",
    "",
    "## 6. 描述性观察",
    "",
    f"- S1-S2 合并率最高的声组：{rank_s1_s2[0].split('(')[0]}",
    f"- S2-S3 合并率最高的声组：{rank_s2_s3[0].split('(')[0]}",
    "- Merge rate 反映音值概率分布的表面重叠程度；单凭该数值不能直接证明变化方向、先后顺序或因果关系。",
    "",
]

# === 5. 导出结果 ===
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
merge_df.to_csv(OUTPUT_DIR / "point_onset_merge_rates.csv", index=False, encoding="utf-8-sig")
onset_summary.to_csv(ONSET_SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")
RESULTS_DOC_OUTPUT.write_text("\n".join(results_markdown), encoding="utf-8")

print(f"✅ 声组总体排序表已生成至: {ONSET_SUMMARY_OUTPUT}")
print(f"✅ 结果文档已生成至: {RESULTS_DOC_OUTPUT}")
print(f"\nS1-S2、S2-S3 两段总体排序: {' > '.join(core_overall_rank)}")
print(f"N/T 独立排序: {' > '.join(nt_s2_s3_rank)}")
