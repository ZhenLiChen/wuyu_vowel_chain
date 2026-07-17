import pandas as pd
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALUE_DIR = PROJECT_ROOT / "data_clean" / "value_type"
DATA_RAW = PROJECT_ROOT / "data_raw"

CHAIN_CANDIDATES = [
    VALUE_DIR / "type_phonetic_chains.csv",
    VALUE_DIR / "phonetic_evolution_chains.csv",
]
MAINLAYER_OUTPUT = DATA_RAW / "mainlayer_merge.csv"
PROFILE_OUTPUT = DATA_RAW / "dialect_evolution_profiles_full.csv"

CORE_ONSETS = ["K", "M", "P", "Ø", "TS"]
PROFILE_ONSETS = ["K", "M", "P", "Ø", "TS"]
ALL_SLOTS = ["S0", "S1", "S2", "S3"]


def load_chain_table() -> pd.DataFrame:
    for path in CHAIN_CANDIDATES:
        if path.exists():
            df = pd.read_csv(path)
            break
    else:
        raise FileNotFoundError("未找到主体层链表，请先运行 scripts/analyze_rhyme_phonetics.py")

    for col in ["point_id", "point_name", "onset_class", *ALL_SLOTS]:
        if col not in df.columns:
            raise ValueError(f"链表缺少必要列：{col}")

    for col in ["point_id", "point_name", "onset_class", *ALL_SLOTS]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    return df


def first_non_empty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def build_ts_row(point_df: pd.DataFrame) -> dict | None:
    ts = point_df[point_df["onset_class"].eq("TS")]
    ts_star = point_df[point_df["onset_class"].eq("TS*")]

    if ts.empty and ts_star.empty:
        return None

    base = (ts.iloc[0] if not ts.empty else ts_star.iloc[0]).to_dict()
    row = {
        "point_id": base["point_id"],
        "point_name": base["point_name"],
        "onset_class": "TS",
    }
    ts_vals = ts.iloc[0].to_dict() if not ts.empty else {}
    ts_star_vals = ts_star.iloc[0].to_dict() if not ts_star.empty else {}

    row["S0"] = first_non_empty(ts_vals.get("S0", ""), ts_star_vals.get("S0", ""))
    row["S1"] = first_non_empty(ts_vals.get("S1", ""), ts_star_vals.get("S1", ""))
    row["S2"] = first_non_empty(ts_vals.get("S2", ""), ts_star_vals.get("S2", ""))
    row["S3"] = first_non_empty(ts_vals.get("S3", ""), ts_star_vals.get("S3", ""))
    return row


def build_core_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, point_df in df.groupby(["point_id", "point_name"], sort=True):
        for onset in ["K", "M", "P", "Ø"]:
            hit = point_df[point_df["onset_class"].eq(onset)]
            if hit.empty:
                continue
            rows.append(hit.iloc[0][["point_id", "point_name", "onset_class", *ALL_SLOTS]].to_dict())

        ts_row = build_ts_row(point_df)
        if ts_row is not None:
            rows.append(ts_row)

    core = pd.DataFrame(rows)
    return core.sort_values(["point_id", "onset_class"]).reset_index(drop=True)


def non_empty_slot_values(row: pd.Series) -> list[str]:
    return [str(row[slot]).strip() for slot in ALL_SLOTS if str(row[slot]).strip()]


def any_merge(values: list[str]) -> bool:
    return len(values) != len(set(values))


def classify_pattern(row: pd.Series) -> dict:
    s0, s1, s2, s3 = [str(row[slot]).strip() for slot in ALL_SLOTS]
    values = [s0, s1, s2, s3]

    eq01 = bool(s0 and s1 and s0 == s1)
    eq12 = bool(s1 and s2 and s1 == s2)
    eq23 = bool(s2 and s3 and s2 == s3)
    eq02 = bool(s0 and s2 and s0 == s2)
    eq13 = bool(s1 and s3 and s1 == s3)
    eq03 = bool(s0 and s3 and s0 == s3)

    filled = [v for v in values if v]
    merged = any_merge(filled)
    leap = (eq02 and not eq01 and not eq12) or (eq13 and not eq12 and not eq23) or (eq03 and not eq01 and not eq12 and not eq23)

    if not merged:
        return {
            "一级分类": "分立型",
            "二级分类": "全不等",
            "三级分类(详细模式)": "全对立",
            "是否越级": False,
            "profile_L1": "分立型",
            "profile_L2": "全不等",
            "profile_L3": "全对立",
        }

    if s0 and s1 and s2 and s3 and len(set(values)) == 1:
        detail = "S0=S1=S2=S3"
        return {
            "一级分类": "合流型",
            "二级分类": "多元合并",
            "三级分类(详细模式)": detail,
            "是否越级": False,
            "profile_L1": "合流型",
            "profile_L2": "全合流",
            "profile_L3": detail,
        }

    if eq01 and eq12 and eq23:
        detail = "S0=S1=S2=S3"
        return {
            "一级分类": "合流型",
            "二级分类": "多元合并",
            "三级分类(详细模式)": detail,
            "是否越级": False,
            "profile_L1": "合流型",
            "profile_L2": "全合流",
            "profile_L3": detail,
        }

    if eq01 and eq12 and not eq23:
        detail = "S0=S1=S2"
        return {
            "一级分类": "合流型",
            "二级分类": "多元合并",
            "三级分类(详细模式)": detail,
            "是否越级": False,
            "profile_L1": "合流型",
            "profile_L2": "连续多元合并",
            "profile_L3": detail,
        }

    if eq12 and eq23 and not eq01:
        detail = "S1=S2=S3"
        return {
            "一级分类": "合流型",
            "二级分类": "多元合并",
            "三级分类(详细模式)": detail,
            "是否越级": False,
            "profile_L1": "合流型",
            "profile_L2": "连续多元合并",
            "profile_L3": detail,
        }

    if eq01 and eq23 and not eq12:
        detail = "S0=S1，S2=S3"
        return {
            "一级分类": "合流型",
            "二级分类": "多元合并",
            "三级分类(详细模式)": detail,
            "是否越级": False,
            "profile_L1": "合流型",
            "profile_L2": "断裂多元合并",
            "profile_L3": detail,
        }

    single_patterns = []
    if eq01:
        single_patterns.append("S0=S1")
    if eq12:
        single_patterns.append("S1=S2")
    if eq23:
        single_patterns.append("S2=S3")
    if eq02 and not eq01 and not eq12:
        single_patterns.append("S0=S2 [越级]")
    if eq13 and not eq12 and not eq23:
        single_patterns.append("S1=S3 [越级]")
    if eq03 and not eq01 and not eq12 and not eq23:
        single_patterns.append("S0=S3 [越级]")

    detail = "，".join(single_patterns) if single_patterns else "合流"
    return {
        "一级分类": "合流型",
        "二级分类": "单一合并",
        "三级分类(详细模式)": detail,
        "是否越级": leap,
        "profile_L1": "合流型",
        "profile_L2": "单一合并",
        "profile_L3": detail,
    }


def row_status(row: pd.Series) -> str:
    values = non_empty_slot_values(row)
    if not values:
        return "分立"
    return "合流" if any_merge(values) else "分立"


def build_mainlayer_merge(core: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    profile_rows = []

    for _, row in core.iterrows():
        info = classify_pattern(row)
        out_row = {
            "point_id": row["point_id"],
            "point_name": row["point_name"],
            "onset_class": row["onset_class"],
            "S0": row["S0"],
            "S1": row["S1"],
            "S2": row["S2"],
            "S3": row["S3"],
            "一级分类": info["一级分类"],
            "二级分类": info["二级分类"],
            "三级分类(详细模式)": info["三级分类(详细模式)"],
            "是否越级": info["是否越级"],
        }
        rows.append(out_row)

    main = pd.DataFrame(rows).sort_values(["point_id", "onset_class"]).reset_index(drop=True)

    chain = load_chain_table()
    for (point_id, point_name), point_df in chain.groupby(["point_id", "point_name"], sort=True):
        record = {"point_id": point_id, "point_name": point_name}

        for onset in PROFILE_ONSETS:
            onset_main = main[(main["point_id"].eq(point_id)) & (main["onset_class"].eq(onset))]
            if onset_main.empty:
                record[f"{onset}_L1"] = ""
                record[f"{onset}_L2"] = ""
                record[f"{onset}_L3"] = ""
            else:
                first = onset_main.iloc[0]
                info = classify_pattern(first)
                record[f"{onset}_L1"] = info["profile_L1"]
                record[f"{onset}_L2"] = info["profile_L2"]
                record[f"{onset}_L3"] = info["profile_L3"]

        n_row = point_df[point_df["onset_class"].eq("N")]
        t_row = point_df[point_df["onset_class"].eq("T")]
        record["N_Status"] = row_status(n_row.iloc[0]) if not n_row.empty else ""
        record["T_Status"] = row_status(t_row.iloc[0]) if not t_row.empty else ""

        combination_parts = []
        for onset in PROFILE_ONSETS:
            combination_parts.append(record[f"{onset}_L2"])
        combination_parts.extend([record["N_Status"], record["T_Status"]])
        record["Combination"] = " | ".join(combination_parts)
        profile_rows.append(record)

    profile = pd.DataFrame(profile_rows).sort_values(["point_id"]).reset_index(drop=True)
    return main, profile


def main():
    chain = load_chain_table()
    core = build_core_table(chain)
    mainlayer_merge, profile = build_mainlayer_merge(core)

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    mainlayer_merge.to_csv(MAINLAYER_OUTPUT, index=False, encoding="utf-8-sig")
    profile.to_csv(PROFILE_OUTPUT, index=False, encoding="utf-8-sig")

    print(f"✅ 已更新主体层分类表：{MAINLAYER_OUTPUT}")
    print(f"✅ 已更新桑基图画像表：{PROFILE_OUTPUT}")
    print(f"   核心声组行数：{len(mainlayer_merge)}")
    print(f"   方言点数：{mainlayer_merge['point_id'].nunique()}")


if __name__ == "__main__":
    main()
