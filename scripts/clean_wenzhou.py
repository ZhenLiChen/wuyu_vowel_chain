import pandas as pd
from pathlib import Path

# === 路径设置 ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
DATA_CLEAN = PROJECT_ROOT / "data_clean"
DATA_DICT = PROJECT_ROOT / "data_dict"

# === 1. 读入原始数据 ===
raw_dir = DATA_RAW / "points"
raw_files = sorted(raw_dir.glob("*.csv"))
if raw_files:
    df_list = [pd.read_csv(p) for p in raw_files]
    df = pd.concat(df_list, ignore_index=True)
else:
    raw_path = DATA_RAW / "wuyu_raw.csv"
    df = pd.read_csv(raw_path)

# 基础清洗
df = df[df["韵"].notna() & df["声组"].notna()]
df = df[df["韵"] != "韵"]
df = df.rename(columns={"汉字": "char", "读音": "phonetic_raw"})

# 兼容个别原始文件把“读音”列表头误写成点名等非标准列名的情况。
# 规则：若 phonetic_raw 为空，则从非标准额外列中寻找第一个非空值回填。
known_raw_columns = {
    "point_id", "point_name", "subbranch", "lat", "lon",
    "韵", "声组", "char", "phonetic_raw", "note",
}
fallback_phonetic_columns = [col for col in df.columns if col not in known_raw_columns]

if fallback_phonetic_columns:
    phonetic_fallback = df[fallback_phonetic_columns].bfill(axis=1).iloc[:, 0]
    if "phonetic_raw" not in df.columns:
        df["phonetic_raw"] = phonetic_fallback
    else:
        missing_mask = df["phonetic_raw"].isna() | df["phonetic_raw"].astype(str).str.strip().isin(["", "nan"])
        df.loc[missing_mask, "phonetic_raw"] = phonetic_fallback[missing_mask]

# === 2. 读音切分与文白标注 ===
df['phonetic_list'] = df['phonetic_raw'].fillna('').astype(str).str.split('/')
df['note_list'] = df['note'].fillna('').astype(str).str.split('/')

def align_lists(row):
    p_len = len(row['phonetic_list'])
    n_list = row['note_list']
    if len(n_list) < p_len:
        return n_list + [''] * (p_len - len(n_list))
    return n_list[:p_len]

df['note_list'] = df.apply(align_lists, axis=1)
df = df.explode(['phonetic_list', 'note_list'])
df = df.rename(columns={"phonetic_list": "phonetic", "note_list": "note_split"})

df["reading_layer"] = df["note_split"].apply(lambda x: "literary" if "文" in str(x) else "main")
df["mainlayer_flag"] = df["reading_layer"].apply(lambda x: 0 if x == "literary" else 1)

# === 3. 映射逻辑 (核心修正部分) ===

# 3.1 韵部映射
rhyme_map = pd.read_csv(DATA_DICT / "rhyme_slot_mapping.csv")
rhyme_map.columns = rhyme_map.columns.str.strip() # 清除表头空格
df = df.merge(rhyme_map, left_on="韵", right_on="rhyme", how="left")

# 3.2 声组映射 (解决 L->N, TS*->TS)
# --- 注意：这里千万不要写 df["onset_class"] = df["声组"] ---
onset_map = pd.read_csv(DATA_DICT / "onset_mapping.csv")
onset_map.columns = onset_map.columns.str.strip() # 关键：去除映射表表头空格

# 通过 merge 引入正确的 onset_class
df = df.merge(onset_map, left_on="声组", right_on="raw_onset", how="left")

# 合并后处理：如果映射表中没查到(NaN)，则保留原始“声组”的值
if "onset_class" in df.columns:
    df["onset_class"] = df["onset_class"].fillna(df["声组"])
else:
    # 这种通常是因为 mapping 文件的列名写错了
    df["onset_class"] = df["声组"]

df["rhyme_modern"] = df["韵"]

# === 4. 提取元音与 vowel_class 判定 ===
# 这里显式扩充项目中常见的 IPA/音标字符，避免 ɷ、ɑ、ᴀ、ᴇ、ʮ、ɥ 等被漏掉。
IPA_VOWEL_CHARS = set("aeiouAEIOUɤɔøœəɯɐʌyɨɷɑᴀᴇʮɥæɒʊʏɵɘɚɝɜɞɪʉv")
IPA_VOWEL_MODIFIERS = set("̞̠̹̯̃ː")


def extract_vowel_sequence(phonetic: str):
    start = None
    end = None

    for idx, char in enumerate(phonetic):
        if char in IPA_VOWEL_CHARS:
            if start is None:
                start = idx
            end = idx + 1
            continue

        if start is not None and char in IPA_VOWEL_MODIFIERS:
            end = idx + 1
            continue

        if start is not None:
            break

    if start is None:
        return None
    return phonetic[start:end]

def extract_vowel_info(phonetic):
    p_str = str(phonetic).strip()
    if not p_str or p_str == 'nan':
        return None, None
    v_sym = extract_vowel_sequence(p_str)
    
    # 复元音判定逻辑
    v_class = v_sym
    vowel_char_count = sum(char in IPA_VOWEL_CHARS for char in v_sym) if v_sym else 0
    if v_sym and vowel_char_count >= 2:
        v_class = "diphthong"
    return v_sym, v_class

df[["vowel_symbol", "vowel_class"]] = df.apply(
    lambda r: pd.Series(extract_vowel_info(r["phonetic"])), axis=1
)

# === 5. 整理导出 ===
df["combo_validity"] = 1
df["zero_type"] = "none"
df["feature_change"] = None 

cols_order = [
    "point_id", "point_name", "subbranch", "lat", "lon",
    "rhyme_modern", "chain_slot", "slot_type_initial", "is_free",
    "onset_class", "char", "phonetic", "note_split",
    "vowel_symbol", "vowel_class", "reading_layer", "mainlayer_flag",
    "combo_validity", "zero_type", "feature_change"
]

cols_order = [c for c in cols_order if c in df.columns]
df_clean = df[cols_order].copy()

DATA_CLEAN.mkdir(exist_ok=True)
out_path = DATA_CLEAN / "wuyu_lexeme.csv"
df_clean.to_csv(out_path, index=False, encoding="utf-8")

print(f"✅ 清洗成功！已完成声组转换(L->N, TS*->TS)并标记复元音。")
