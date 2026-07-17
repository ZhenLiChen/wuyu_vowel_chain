import pandas as pd
import numpy as np
from pathlib import Path

# === 1. 路径与权重设置 ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = PROJECT_ROOT / "data_clean"
DATA_DICT = PROJECT_ROOT / "data_dict"
OUTPUT_DIR = DATA_CLEAN / "merge_analysis"

UNIFORM_WEIGHT = 1.0
RHYME_TO_SLOT = {
    "佳": "S0", "皆": "S0",
    "麻": "S1",
    "歌": "S2", "戈": "S2",
    "模": "S3"
}
CORE_PAIRS = [("S0", "S1"), ("S1", "S2"), ("S2", "S3")]
SUPPLEMENTARY_PAIRS = [("S1", "S3")]

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
        # 低位链与跨级 S1-S3 的比较都不纳入 T/N
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

# === 4. 核心：生成总结式序列 (Summary Hierarchy) ===
def get_ranked_list(col_name):
    # 只计算非NaN的声组平均值
    avg_series = merge_df.groupby("onset_class")[col_name].mean().dropna().sort_values(ascending=False)
    return [f"{idx}({val:.3f})" for idx, val in avg_series.items()]

# 提取各阶段序列
rank_s0_s1 = get_ranked_list("merge_S0_S1")
rank_s1_s2 = get_ranked_list("merge_S1_S2")
rank_s2_s3 = get_ranked_list("merge_S2_S3")
rank_s1_s3 = get_ranked_list("merge_S1_S3")

# 组织总结文档内容
summary_text = [
    "==================================================",
    " 吴语元音后高化链变：声组推力总结式序列报告",
    "==================================================",
    "\n【实验说明】",
    "1. 采用等权期望分布模型；保留 weight_type 标注，但不再对文读/离群字降权。",
    "2. 若同一字有多个 / 分隔读音，则按等概率均分；两读音各记 0.5，三读音各记 1/3。",
    "3. 针对低位链环节(S0-S1, S1-S2)与跨级参照(S1-S3)已排除T组与N组的无效数据。",
    "4. 数值代表合并率均值，数值越高代表推力越强，演化越激进。",
    "5. 主分析仍以相邻链位(S0-S1 / S1-S2 / S2-S3)为核心，S1-S3只作补充参照。\n",
    "【各阶段声组推力序列 (Onset Hierarchy)】",
    "--------------------------------------------------",
    f"阶段 A (S0 佳皆 -> S1 麻):",
    f"   {' > '.join(rank_s0_s1)}",
    "\n阶段 B (S1 麻 -> S2 歌戈):",
    f"   {' > '.join(rank_s1_s2)}",
    "\n阶段 C (S2 歌戈 -> S3 模):",
    f"   {' > '.join(rank_s2_s3)}",
    "\n补充阶段 X (S1 麻 -> S3 模，跨级参照):",
    f"   {' > '.join(rank_s1_s3)}",
    "--------------------------------------------------",
    "\n【综合演化趋势观察】"
]

# 简单的自动化观察逻辑
if rank_s0_s1 and rank_s2_s3:
    top_early = rank_s0_s1[0].split('(')[0]
    top_late = rank_s2_s3[0].split('(')[0]
    summary_text.append(f"※ 演化初期(S0-S1)最强推力为: {top_early}")
    summary_text.append(f"※ 演化后期(S2-S3)最强推力为: {top_late}")

# === 5. 导出结果 ===
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
merge_df.to_csv(OUTPUT_DIR / "point_onset_merge_rates.csv", index=False, encoding="utf-8-sig")

with open(OUTPUT_DIR / "summary_hierarchy_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(summary_text))

onset_report_text = [
    "=== 吴语元音后高化链变：声组合并率推力序列报告 ===",
    "",
    "【实验说明】",
    "1. 采用等权期望分布模型；保留 weight_type 标注，但不再对文读/离群字降权。",
    "2. 若同一字有多个 / 分隔读音，则按等概率均分；两读音各记 0.5，三读音各记 1/3。",
    "3. 声母类别已统一清理：L 并入 N，TS* 并入 TS。",
    "4. 针对低位链环节(S0-S1, S1-S2)与跨级参照(S1-S3)，排除 T 组与 N 组的无效格位。",
    "5. 数值为各方言点合并率均值，数值越高代表相关链位越趋于合并。",
    "6. 主分析使用相邻链位；S1-S3 只作补充观察。",
    "",
    "【第一部分】",
    "1. S0 (佳皆) 与 S1 (麻) 合并序列:",
    f"   {' > '.join(rank_s0_s1)}",
    "2. S1 (麻) 与 S2 (歌戈) 合并序列:",
    f"   {' > '.join(rank_s1_s2)}",
    "",
    "【第二部分】",
    "3. S2 (歌戈) 与 S3 (模) 合并序列:",
    f"   {' > '.join(rank_s2_s3)}",
    "",
    "【补充部分】",
    "4. S1 (麻) 与 S3 (模) 跨级合并序列:",
    f"   {' > '.join(rank_s1_s3)}",
]
with open(OUTPUT_DIR / "onset_hierarchy_report.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(onset_report_text))

print(f"✅ 总结式序列报告已生成至: {OUTPUT_DIR / 'summary_hierarchy_report.txt'}")
print("\n" + "\n".join(summary_text))
