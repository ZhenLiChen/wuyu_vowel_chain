import pandas as pd
from pathlib import Path
import re

# === 路径设置 ===
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_CLEAN = PROJECT_ROOT / "data_clean"
OUTPUT_DIR = DATA_CLEAN / "value_type" 

# === 读取数据 ===
input_path = DATA_CLEAN / "wuyu_lexeme.csv"
if not input_path.exists():
    raise FileNotFoundError(f"未找到清洗后的数据文件：{input_path}")

df = pd.read_csv(input_path)

# === 1. 预处理 ===
# 剔除 “靴” 和 “茄”
df = df[~df["char"].isin(["靴", "茄"])]
df = df[df["phonetic"].notna()]

# 参数设置
target_rhymes = ["歌", "戈", "麻", "模", "佳", "皆"]
df_filtered = df[df["rhyme_modern"].isin(target_rhymes)].copy()

def split_phonetic(value):
    if pd.isna(value):
        return []
    value = str(value).replace("\u00a0", " ").strip()
    if not value or value.lower() == "nan":
        return []
    if value == "o（uo）":
        return ["u", "uo"]
    return [part.strip() for part in value.split("/") if part.strip()]

df_filtered["phonetic"] = df_filtered["phonetic"].apply(split_phonetic)
df_filtered = df_filtered.explode("phonetic")
df_filtered = df_filtered[df_filtered["phonetic"].notna() & (df_filtered["phonetic"] != "")]

# 定义 chain_slot 的逻辑顺序，用于后续排序
slot_order = {"S0": 0, "S1": 1, "S2": 2, "S3": 3}
df_filtered['slot_rank'] = df_filtered['chain_slot'].map(slot_order)

# === 2. 核心修改：改变输出模式的分布统计 ===
def get_phonetic_distribution(series):
    # 计算频率并自动降序排列
    counts = series.value_counts()
    # 格式化输出为：音值(频数), 音值(频数)
    return ", ".join([f"{val}({count})" for val, count in counts.items()])

# 分组统计
# 注意：这里加入了 slot_rank 以确保排序正确
slot_onset_dist = df_filtered.groupby(
    ['point_id', 'point_name', 'onset_class', 'chain_slot', 'slot_rank']
)['phonetic'].apply(get_phonetic_distribution).reset_index()

# 按照 [方言点 -> 声组 -> 链位顺序] 进行排序
slot_onset_dist = slot_onset_dist.sort_values(by=['point_id', 'onset_class', 'slot_rank'])

# 移除辅助排序的列
slot_onset_dist = slot_onset_dist.drop(columns=['slot_rank'])
slot_onset_dist.rename(columns={'phonetic': 'phonetic_frequency'}, inplace=True)

# === 3. 其他统计（保持原有逻辑） ===
# 分韵详细分布
summary = df_filtered.groupby(['point_id', 'point_name', 'rhyme_modern', 'phonetic']).agg(
    char_count=('char', 'nunique'),
    char_list=('char', lambda x: sorted(list(set(x.dropna()))))
).reset_index()

def format_char_info(row):
    if row['char_count'] <= 4:
        return " / ".join(row['char_list'])
    return f"共 {row['char_count']} 个例字"

summary['example_chars'] = summary.apply(format_char_info, axis=1)

# 分韵库藏
rhyme_inventory = df_filtered.groupby(['point_id', 'point_name', 'rhyme_modern'])['phonetic'].apply(
    lambda x: ", ".join(sorted(list(set(x.dropna()))))
).reset_index()
rhyme_inventory.rename(columns={'phonetic': 'rhyme_phonetic_set'}, inplace=True)

# 总库藏
point_inventory = df_filtered.groupby(['point_id', 'point_name'])['phonetic'].apply(
    lambda x: ", ".join(sorted(list(set(x.dropna()))))
).reset_index()
point_inventory['vowel_count'] = point_inventory['phonetic'].apply(lambda x: len(x.split(", ")) if x else 0)

# 离群汉字
outliers = summary[summary['char_count'] <= 4].copy()
all_outlier_chars = []
for chars in outliers['char_list']:
    all_outlier_chars.extend(chars)
char_frequency = pd.Series(all_outlier_chars).value_counts().reset_index()
char_frequency.columns = ['char', 'outlier_frequency']

# === 4. 导出结果 ===
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 导出修改后的分布表
slot_onset_dist.to_csv(OUTPUT_DIR / "point_slot_onset_distribution.csv", index=False, encoding="utf-8-sig")

# 导出其他辅助表
summary.drop(columns=['char_list']).to_csv(OUTPUT_DIR / "rhyme_phonetic_distribution.csv", index=False, encoding="utf-8-sig")
rhyme_inventory.to_csv(OUTPUT_DIR / "point_rhyme_inventory.csv", index=False, encoding="utf-8-sig")
point_inventory.to_csv(OUTPUT_DIR / "point_total_inventory.csv", index=False, encoding="utf-8-sig")
char_frequency.to_csv(OUTPUT_DIR / "outlier_char_frequency.csv", index=False, encoding="utf-8-sig")

print(f"✅ 统计分析完成！输出模式已调整：先声组，后链位顺序。")

# === 5. 新增功能：整理成演变链汇总表 (Pivoted Evolution Chains) ===
def extract_top_phonetic(freq_str):
    """从 'a(13), ia(4)' 格式中提取频数最高的读音 'a'"""
    if pd.isna(freq_str) or not isinstance(freq_str, str):
        return ""
    # 使用正则匹配音值，提取第一个括号前的部分（因为您的 get_phonetic_distribution 已按频数降序排列）
    match = re.search(r'([^,()\s]+)\s*\(', freq_str)
    return match.group(1) if match else ""

# 拷贝一份分布表进行处理
df_chains = slot_onset_dist.copy()
# 提取每个 Slot 频率最高的音值
df_chains['top_val'] = df_chains['phonetic_frequency'].apply(extract_top_phonetic)

# 使用透视表将 S0, S1, S2, S3 转为列
# 即使 T 和 N 声组下缺失 S0/S1，pivot_table 也会自动填充为 NaN（空）
pivoted_chains = df_chains.pivot_table(
    index=['point_id', 'point_name', 'onset_class'],
    columns='chain_slot',
    values='top_val',
    aggfunc='first'
).reset_index()

# 确保 S0, S1, S2, S3 列都存在（防止某些数据完全缺失导致列不存在）
for s in ['S0', 'S1', 'S2', 'S3']:
    if s not in pivoted_chains.columns:
        pivoted_chains[s] = ""

# 按照 [方言点代码 -> 声组顺序] 排序，并整理列顺序
# 满足：point_id, point_name, onset_class, S0, S1, S2, S3
final_cols = ['point_id', 'point_name', 'onset_class', 'S0', 'S1', 'S2', 'S3']
pivoted_chains = pivoted_chains.reindex(columns=final_cols).fillna("")

# 导出结果
type_chain_path = OUTPUT_DIR / "type_phonetic_chains.csv"
legacy_chain_path = OUTPUT_DIR / "phonetic_evolution_chains.csv"
pivoted_chains.to_csv(type_chain_path, index=False, encoding="utf-8-sig")
pivoted_chains.to_csv(legacy_chain_path, index=False, encoding="utf-8-sig")

print(f"✅ 演变链汇总表已生成：{type_chain_path}")
print(f"✅ 兼容旧文件名同步更新：{legacy_chain_path}")
print(f"   (注：T 和 N 声组的 S0/S1 若无数据已按要求留空)")
