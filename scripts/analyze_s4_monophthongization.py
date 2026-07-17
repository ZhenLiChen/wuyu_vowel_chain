from __future__ import annotations

import ssl
import unicodedata
from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import pandas as pd


try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = PROJECT_ROOT / "data_clean"
VALUE_DIR = DATA_CLEAN / "value_type"
DATA_DICT = PROJECT_ROOT / "data_dict"
FIGS_DIR = PROJECT_ROOT / "figs"

INPUT_PATH = DATA_CLEAN / "wuyu_lexeme.csv"
COORDS_PATH = DATA_DICT / "point_coords_master.csv"

CORE_INVENTORY_OUTPUT = VALUE_DIR / "point_s0_s3_monophthong_inventory_for_s4.csv"
RELATION_OUTPUT = VALUE_DIR / "point_s4_hou_monophthong_relation.csv"
SUMMARY_OUTPUT = VALUE_DIR / "s4_hou_monophthong_relation_summary.csv"
VALUE_SUMMARY_OUTPUT = VALUE_DIR / "s4_hou_value_summary.csv"
SUBBRANCH_OUTPUT = VALUE_DIR / "s4_hou_monophthong_by_subbranch.csv"
CLUSTER_OUTPUT = VALUE_DIR / "s4_hou_geographic_cluster_summary.csv"
TYPOLOGY_OUTPUT = VALUE_DIR / "s4_hou_typology_with_s5_s0s1.csv"
TYPOLOGY_SUMMARY_OUTPUT = VALUE_DIR / "s4_hou_typology_summary.csv"
HAO_RELATION_PATH = VALUE_DIR / "point_hao_monophthong_relation.csv"
MERGE_RATES_PATH = DATA_CLEAN / "merge_analysis" / "point_onset_merge_rates.csv"

MAP_OUTPUT = FIGS_DIR / "s4_hou_monophthong_geography_map.png"
SUBBRANCH_FIG_OUTPUT = FIGS_DIR / "s4_hou_monophthong_subbranch_summary.png"

CORE_SLOTS = ["S0", "S1", "S2", "S3"]
TARGET_SLOT = "S4"
TARGET_RHYME = "侯"
EXCLUDED_CHARS = {"靴", "茄"}
S4_EXCLUDED_ONSET_CLASSES_NO_MP = {"M", "P"}

VOWEL_CHARS = set("aeiouyæøœɐɑɒɔəɛɜɞɤɯɪʊʌʏɵʉɷᴀᴇ")
GLIDE_CHARS = set("wɥj")
BACK_NUCLEI = {"u", "o", "ɔ", "ɒ", "ɑ", "ɤ", "ɯ", "ʊ", "ʌ", "ɷ"}
FRONT_ROUNDED_NUCLEI = {"ø", "ɵ", "y", "ʏ", "œ", "ʉ"}
E_CLASS_NUCLEI = {"e", "ᴇ", "ɛ", "æ", "ɪ", "i"}
UO_CLASS_NUCLEI = {"u", "o", "ɔ", "ɷ", "ʊ"}
CENTRAL_NUCLEI = {"ə", "ɐ", "ʌ"}


def set_chinese_font() -> None:
    available_fonts = [font.name for font in fm.fontManager.ttflist]
    preferred_fonts = [
        "PingFang SC",
        "Heiti SC",
        "SimHei",
        "Microsoft YaHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["font.sans-serif"] = [
        font_name for font_name in preferred_fonts if font_name in available_fonts
    ]
    plt.rcParams["axes.unicode_minus"] = False


def split_phonetic(value) -> list[str]:
    if pd.isna(value):
        return []
    value = str(value).replace("\u00a0", " ").strip()
    if not value or value.lower() == "nan":
        return []
    if value == "o（uo）":
        return ["u", "uo"]
    return [part.strip() for part in value.split("/") if part.strip()]


def decomposed_chars(value: str) -> list[str]:
    return [
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    ]


def vowel_sequence(value: str) -> list[str]:
    return [char for char in decomposed_chars(value) if char in VOWEL_CHARS]


def has_glide(value: str) -> bool:
    return any(char in GLIDE_CHARS for char in decomposed_chars(value))


def classify_value(value: str) -> str:
    if "ʔ" in value:
        return "checked_or_coda"
    vowels = vowel_sequence(value)
    if len(vowels) == 1 and not has_glide(value):
        return "monophthong"
    if len(vowels) > 1 or (len(vowels) == 1 and has_glide(value)):
        return "diphthong_or_glide"
    return "other"


def monophthong_nucleus(value: str) -> str:
    if classify_value(value) != "monophthong":
        return ""
    vowels = vowel_sequence(value)
    return vowels[0] if vowels else ""


def format_values(values) -> str:
    return ", ".join(sorted(value for value in values if value))


def format_counts(counts: pd.Series) -> str:
    return ", ".join(f"{value}({int(count)})" for value, count in counts.items())


def expand_phonetics(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["phonetic"] = work["phonetic"].apply(split_phonetic)
    work = work.explode("phonetic")
    work = work[work["phonetic"].notna() & (work["phonetic"] != "")].copy()
    work["value_class"] = work["phonetic"].apply(classify_value)
    work["nucleus"] = work["phonetic"].apply(monophthong_nucleus)
    work["is_back_nucleus"] = work["nucleus"].isin(BACK_NUCLEI)
    return work


def summarize_core_inventory(core: pd.DataFrame) -> pd.DataFrame:
    mono = core[core["value_class"] == "monophthong"].copy()

    rows = []
    for keys, group in mono.groupby(["point_id", "point_name", "subbranch"], dropna=False):
        point_id, point_name, subbranch = keys
        values = set(group["phonetic"])
        nuclei = set(group["nucleus"])
        back_values = set(group.loc[group["is_back_nucleus"], "phonetic"])
        back_nuclei = set(group.loc[group["is_back_nucleus"], "nucleus"])
        nucleus_counts = group["nucleus"].value_counts().sort_values(ascending=False)
        back_nucleus_counts = (
            group.loc[group["is_back_nucleus"], "nucleus"]
            .value_counts()
            .sort_values(ascending=False)
        )
        rows.append(
            {
                "point_id": point_id,
                "point_name": point_name,
                "subbranch": subbranch,
                "core_slots": "+".join(CORE_SLOTS),
                "monophthong_values": format_values(values),
                "monophthong_value_size": len(values),
                "monophthong_token_count": len(group),
                "monophthong_nuclei": format_values(nuclei),
                "monophthong_nucleus_size": len(nuclei),
                "monophthong_nucleus_counts": format_counts(nucleus_counts),
                "back_monophthong_values": format_values(back_values),
                "back_monophthong_value_size": len(back_values),
                "back_monophthong_token_count": int(group["is_back_nucleus"].sum()),
                "back_monophthong_nuclei": format_values(back_nuclei),
                "back_monophthong_nucleus_size": len(back_nuclei),
                "back_monophthong_nucleus_counts": format_counts(back_nucleus_counts),
            }
        )
    return pd.DataFrame(rows)


def s4_status(group: pd.DataFrame) -> str:
    classes = set(group["value_class"])
    has_mono = "monophthong" in classes
    has_complex = "diphthong_or_glide" in classes
    has_other = bool(classes - {"monophthong", "diphthong_or_glide"})
    if not classes:
        return "missing"
    if has_mono and not has_complex and not has_other:
        return "monophthong_only"
    if has_complex and not has_mono and not has_other:
        return "diphthong_or_glide_only"
    if has_mono and has_complex and not has_other:
        return "mixed_mono_and_diphthong"
    if has_other and not has_mono and not has_complex:
        return "other_only"
    return "mixed_with_other"


def nucleus_category(nucleus: str) -> str:
    if nucleus in FRONT_ROUNDED_NUCLEI:
        return "front_rounded"
    if nucleus in {"ɤ", "ɯ"}:
        return "back_unrounded"
    if nucleus in E_CLASS_NUCLEI:
        return "e_like"
    if nucleus in UO_CLASS_NUCLEI:
        return "u_o_like"
    if nucleus in CENTRAL_NUCLEI:
        return "central"
    if nucleus:
        return "other_mono"
    return ""


def summarize_s4(s4: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in s4.groupby(["point_id", "point_name", "subbranch"], dropna=False):
        point_id, point_name, subbranch = keys
        counts = group["phonetic"].value_counts().sort_values(ascending=False)
        mono = group[group["value_class"] == "monophthong"]
        complex_values = group[group["value_class"] == "diphthong_or_glide"]
        other = group[
            ~group["value_class"].isin(["monophthong", "diphthong_or_glide"])
        ]
        dominant_value = counts.index[0] if len(counts) else ""
        dominant_count = int(counts.iloc[0]) if len(counts) else 0
        dominant_class = classify_value(dominant_value) if dominant_value else ""
        dominant_nucleus = monophthong_nucleus(dominant_value) if dominant_value else ""
        total_count = len(group)
        mono_count = len(mono)
        rows.append(
            {
                "point_id": point_id,
                "point_name": point_name,
                "subbranch": subbranch,
                "s4_slot_in_data": format_values(set(group["chain_slot"])),
                "s4_rhyme_in_data": format_values(set(group["rhyme_modern"])),
                "s4_initial": format_values(set(group["slot_type_initial"])),
                "s4_value_counts": format_counts(counts),
                "s4_total_token_count": total_count,
                "s4_monophthong_token_count": mono_count,
                "s4_monophthong_token_share": mono_count / total_count
                if total_count
                else 0,
                "s4_dominant_value": dominant_value,
                "s4_dominant_value_class": dominant_class,
                "s4_dominant_nucleus": dominant_nucleus,
                "s4_dominant_nucleus_category": nucleus_category(dominant_nucleus),
                "s4_dominant_token_count": dominant_count,
                "s4_dominant_token_share": dominant_count / total_count
                if total_count
                else 0,
                "s4_status": s4_status(group),
                "s4_monophthong_values": format_values(set(mono["phonetic"])),
                "s4_monophthong_nuclei": format_values(set(mono["nucleus"])),
                "s4_back_monophthong_nuclei": format_values(
                    set(mono.loc[mono["is_back_nucleus"], "nucleus"])
                ),
                "s4_diphthong_or_glide_values": format_values(
                    set(complex_values["phonetic"])
                ),
                "s4_other_values": format_values(set(other["phonetic"])),
            }
        )
    return pd.DataFrame(rows)


def split_set(value: str) -> set[str]:
    if pd.isna(value) or not str(value).strip():
        return set()
    return {part.strip() for part in str(value).split(",") if part.strip()}


def relation_label(s4_nuclei: set[str], core_nuclei: set[str], core_back: set[str]) -> str:
    if not s4_nuclei:
        return "no_s4_monophthong"
    if s4_nuclei <= core_back:
        return "all_s4_mono_in_core_back_inventory"
    if s4_nuclei <= core_nuclei:
        return "all_s4_mono_in_core_inventory"
    if s4_nuclei & core_nuclei:
        return "partial_s4_mono_in_core_inventory"
    return "s4_mono_outside_core_inventory"


def build_relation(
    core_summary: pd.DataFrame, s4_summary: pd.DataFrame, points: pd.DataFrame
) -> pd.DataFrame:
    relation = points.merge(
        core_summary,
        on=["point_id", "point_name", "subbranch"],
        how="left",
    ).merge(
        s4_summary,
        on=["point_id", "point_name", "subbranch"],
        how="left",
    )

    fill_empty = [
        "monophthong_values",
        "monophthong_nuclei",
        "monophthong_nucleus_counts",
        "back_monophthong_values",
        "back_monophthong_nuclei",
        "back_monophthong_nucleus_counts",
        "s4_slot_in_data",
        "s4_rhyme_in_data",
        "s4_initial",
        "s4_value_counts",
        "s4_status",
        "s4_dominant_value",
        "s4_dominant_value_class",
        "s4_dominant_nucleus",
        "s4_dominant_nucleus_category",
        "s4_monophthong_values",
        "s4_monophthong_nuclei",
        "s4_back_monophthong_nuclei",
        "s4_diphthong_or_glide_values",
        "s4_other_values",
    ]
    for column in fill_empty:
        if column in relation.columns:
            relation[column] = relation[column].fillna("")

    for column in [
        "monophthong_value_size",
        "monophthong_token_count",
        "monophthong_nucleus_size",
        "back_monophthong_value_size",
        "back_monophthong_token_count",
        "back_monophthong_nucleus_size",
        "s4_total_token_count",
        "s4_monophthong_token_count",
        "s4_dominant_token_count",
    ]:
        if column in relation.columns:
            relation[column] = relation[column].fillna(0).astype(int)

    for column in ["s4_monophthong_token_share", "s4_dominant_token_share"]:
        if column in relation.columns:
            relation[column] = relation[column].fillna(0.0)

    relation["core_slots"] = relation["core_slots"].fillna("+".join(CORE_SLOTS))
    relation["s4_monophthong_nuclei_in_core"] = ""
    relation["s4_monophthong_nuclei_in_core_back"] = ""
    relation["s4_monophthong_nuclei_not_in_core"] = ""
    relation["s4_core_relation"] = ""

    for idx, row in relation.iterrows():
        s4_nuclei = split_set(row["s4_monophthong_nuclei"])
        core_nuclei = split_set(row["monophthong_nuclei"])
        core_back = split_set(row["back_monophthong_nuclei"])
        relation.at[idx, "s4_monophthong_nuclei_in_core"] = format_values(
            s4_nuclei & core_nuclei
        )
        relation.at[idx, "s4_monophthong_nuclei_in_core_back"] = format_values(
            s4_nuclei & core_back
        )
        relation.at[idx, "s4_monophthong_nuclei_not_in_core"] = format_values(
            s4_nuclei - core_nuclei
        )
        relation.at[idx, "s4_core_relation"] = relation_label(
            s4_nuclei, core_nuclei, core_back
        )

    return relation.sort_values(["point_id", "point_name"]).reset_index(drop=True)


def build_value_summary(s4: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for value, group in s4.groupby("phonetic"):
        point_pairs = group[["point_id", "point_name"]].drop_duplicates()
        examples = [
            f"{row.point_id}:{row.point_name}"
            for row in point_pairs.head(12).itertuples(index=False)
        ]
        nucleus = monophthong_nucleus(value)
        rows.append(
            {
                "s4_value": value,
                "value_class": classify_value(value),
                "nucleus": nucleus,
                "nucleus_category": nucleus_category(nucleus),
                "point_count": len(point_pairs),
                "token_count": len(group),
                "example_points": " | ".join(examples),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["value_class", "point_count", "token_count", "s4_value"],
        ascending=[True, False, False, True],
    )


def map_category(row: pd.Series) -> str:
    status = row["s4_status"]
    if status == "diphthong_or_glide_only":
        return "未单音化"
    if status in {"mixed_mono_and_diphthong", "mixed_with_other", "other_only"}:
        return "混合"
    category = row["s4_dominant_nucleus_category"]
    if category == "back_unrounded":
        return "ɤ/ɯ类单音化"
    if category == "front_rounded":
        return "ø/ɵ/y类单音化"
    if category == "e_like":
        return "e类单音化"
    if category == "u_o_like":
        return "u/o类单音化"
    if category == "central":
        return "ə/ʌ类单音化"
    return "其他单音化"


def format_point_list(group: pd.DataFrame) -> str:
    return " | ".join(
        f"{row.point_id}:{row.point_name}" for row in group.itertuples(index=False)
    )


def category_counts(series: pd.Series) -> str:
    counts = series.value_counts()
    return " | ".join(f"{key}({int(value)})" for key, value in counts.items())


def map_label_text(value: str) -> str:
    return str(value).replace("ᴇ", "E")


def top_counts_label(value: str, limit: int = 2) -> str:
    parts = [part.strip() for part in str(value).split(",") if part.strip()]
    return ", ".join(parts[:limit])


def strip_object_columns(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].astype("string").str.strip()
    return df


def load_map_data(relation: pd.DataFrame) -> pd.DataFrame:
    coords = pd.read_csv(COORDS_PATH)
    coords.columns = coords.columns.str.strip()
    for frame in [relation, coords]:
        strip_object_columns(frame)
    coords["lat"] = pd.to_numeric(coords["lat"], errors="coerce")
    coords["lon"] = pd.to_numeric(coords["lon"], errors="coerce")
    data = relation.merge(coords[["point_name", "lat", "lon"]], on="point_name", how="left")
    data = data.dropna(subset=["lat", "lon"]).copy()
    data["map_category"] = data.apply(map_category, axis=1)
    return data


def build_subbranch_summary(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subbranch, group in data.groupby("subbranch"):
        total_tokens = int(group["s4_total_token_count"].sum())
        mono_tokens = int(group["s4_monophthong_token_count"].sum())
        rows.append(
            {
                "subbranch": subbranch,
                "point_count": len(group),
                "s4_total_token_count": total_tokens,
                "s4_monophthong_token_count": mono_tokens,
                "weighted_monophthong_share": mono_tokens / total_tokens
                if total_tokens
                else 0,
                "monophthong_only_point_count": int(
                    (group["s4_status"] == "monophthong_only").sum()
                ),
                "mixed_point_count": int(
                    group["s4_status"]
                    .isin(["mixed_mono_and_diphthong", "mixed_with_other", "other_only"])
                    .sum()
                ),
                "diphthong_only_point_count": int(
                    (group["s4_status"] == "diphthong_or_glide_only").sum()
                ),
                "dominant_category_counts": category_counts(group["map_category"]),
                "dominant_value_counts": category_counts(group["s4_dominant_value"]),
                "points": format_point_list(group.sort_values("point_id")),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["weighted_monophthong_share", "point_count"],
        ascending=[False, False],
    )


def build_cluster_summary(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for category, group in data.groupby("map_category"):
        total_tokens = int(group["s4_total_token_count"].sum())
        mono_tokens = int(group["s4_monophthong_token_count"].sum())
        rows.append(
            {
                "map_category": category,
                "point_count": len(group),
                "s4_total_token_count": total_tokens,
                "s4_monophthong_token_count": mono_tokens,
                "weighted_monophthong_share": mono_tokens / total_tokens
                if total_tokens
                else 0,
                "mean_lat": group["lat"].mean(),
                "mean_lon": group["lon"].mean(),
                "lat_min": group["lat"].min(),
                "lat_max": group["lat"].max(),
                "lon_min": group["lon"].min(),
                "lon_max": group["lon"].max(),
                "subbranch_counts": category_counts(group["subbranch"]),
                "dominant_value_counts": category_counts(group["s4_dominant_value"]),
                "points": format_point_list(group.sort_values("point_id")),
            }
        )
    return pd.DataFrame(rows).sort_values(["point_count", "map_category"], ascending=[False, True])


def append_group_summary(
    rows: list[dict],
    summary_type: str,
    group: str,
    subgroup: str,
    data: pd.DataFrame,
) -> None:
    s4_share = pd.to_numeric(
        data["s4_monophthong_token_share"], errors="coerce"
    ).dropna()
    s0s1_merge = pd.to_numeric(data["s0s1_merge_mean"], errors="coerce").dropna()
    rows.append(
        {
            "summary_type": summary_type,
            "group": group,
            "subgroup": subgroup,
            "point_count": len(data),
            "mean_s4_monophthong_share": s4_share.mean() if len(s4_share) else pd.NA,
            "median_s4_monophthong_share": s4_share.median()
            if len(s4_share)
            else pd.NA,
            "mean_s0s1_merge": s0s1_merge.mean() if len(s0s1_merge) else pd.NA,
            "median_s0s1_merge": s0s1_merge.median()
            if len(s0s1_merge)
            else pd.NA,
            "s5_monophthong_only_point_count": int(
                data["s5_monophthong_only"].eq(True).sum()
            ),
            "s5_has_monophthong_point_count": int(
                data["s5_has_monophthong"].eq(True).sum()
            ),
        }
    )


def build_typology_outputs(relation: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    typology = relation.copy()
    typology["s4_map_category"] = typology.apply(map_category, axis=1)
    typology["s4_has_monophthong"] = typology["s4_monophthong_token_count"] > 0
    typology["s4_monophthong_only"] = typology["s4_status"] == "monophthong_only"
    typology["s4_half_or_more_monophthong"] = (
        typology["s4_monophthong_token_share"] >= 0.5
    )

    if HAO_RELATION_PATH.exists():
        hao = pd.read_csv(HAO_RELATION_PATH)
        strip_object_columns(hao)
        hao_columns = [
            "point_name",
            "hao_status",
            "hao_monophthong_token_share",
            "hao_dominant_value",
            "hao_core_relation",
        ]
        hao = hao[hao_columns].copy()
        hao["s5_has_monophthong"] = hao["hao_monophthong_token_share"] > 0
        hao["s5_monophthong_only"] = hao["hao_status"] == "monophthong_only"
        typology = typology.merge(hao, on="point_name", how="left")
    else:
        typology["hao_status"] = ""
        typology["hao_monophthong_token_share"] = pd.NA
        typology["hao_dominant_value"] = ""
        typology["hao_core_relation"] = ""
        typology["s5_has_monophthong"] = pd.NA
        typology["s5_monophthong_only"] = pd.NA

    if MERGE_RATES_PATH.exists():
        merge = pd.read_csv(MERGE_RATES_PATH)
        strip_object_columns(merge)
        for column in ["merge_S0_S1", "merge_S1_S2", "merge_S2_S3"]:
            merge[column] = pd.to_numeric(merge[column], errors="coerce")
        merge_summary = (
            merge.groupby("point_name", as_index=False)
            .agg(
                s0s1_merge_mean=("merge_S0_S1", "mean"),
                s0s1_merge_median=("merge_S0_S1", "median"),
                s1s2_merge_mean=("merge_S1_S2", "mean"),
                s2s3_merge_mean=("merge_S2_S3", "mean"),
                onset_condition_count=("onset_class", "nunique"),
            )
        )
        typology = typology.merge(merge_summary, on="point_name", how="left")
    else:
        typology["s0s1_merge_mean"] = pd.NA
        typology["s0s1_merge_median"] = pd.NA
        typology["s1s2_merge_mean"] = pd.NA
        typology["s2s3_merge_mean"] = pd.NA
        typology["onset_condition_count"] = pd.NA

    rows: list[dict] = []
    append_group_summary(rows, "overall", "all", "all", typology)

    for category, group in typology.groupby("s4_map_category", dropna=False):
        append_group_summary(rows, "s4_map_category", category, "all", group)

    for status, group in typology.groupby("s4_status", dropna=False):
        append_group_summary(rows, "s4_status", status, "all", group)

    for hao_status, group in typology.groupby("hao_status", dropna=False):
        append_group_summary(rows, "s5_status", hao_status, "all", group)

    for keys, group in typology.groupby(
        ["s4_map_category", "hao_status"], dropna=False
    ):
        category, hao_status = keys
        append_group_summary(
            rows, "s4_map_category_x_s5_status", category, hao_status, group
        )

    for keys, group in typology.groupby(["s4_status", "hao_status"], dropna=False):
        s4_status_value, hao_status = keys
        append_group_summary(
            rows, "s4_status_x_s5_status", s4_status_value, hao_status, group
        )

    summary = pd.DataFrame(rows)
    numeric_columns = [
        "mean_s4_monophthong_share",
        "median_s4_monophthong_share",
        "mean_s0s1_merge",
        "median_s0s1_merge",
    ]
    for column in numeric_columns:
        summary[column] = pd.to_numeric(summary[column], errors="coerce").round(4)

    return typology.sort_values(["point_id", "point_name"]), summary


def plot_map(data: pd.DataFrame) -> None:
    set_chinese_font()
    gdf = gpd.GeoDataFrame(
        data,
        geometry=gpd.points_from_xy(data["lon"], data["lat"]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)

    palette = {
        "ɤ/ɯ类单音化": "#2F80ED",
        "ø/ɵ/y类单音化": "#8E44AD",
        "e类单音化": "#27AE60",
        "u/o类单音化": "#00796B",
        "ə/ʌ类单音化": "#6F8F3A",
        "其他单音化": "#9B51E0",
        "混合": "#F2994A",
        "未单音化": "#EB5757",
    }
    marker_map = {
        "ɤ/ɯ类单音化": "o",
        "ø/ɵ/y类单音化": "s",
        "e类单音化": "^",
        "u/o类单音化": "P",
        "ə/ʌ类单音化": "v",
        "其他单音化": "*",
        "混合": "D",
        "未单音化": "X",
    }
    label_offsets = [
        (1200, 1200),
        (-1200, 1200),
        (1200, -1200),
        (-1200, -1200),
        (1800, 0),
        (-1800, 0),
        (0, 1800),
        (0, -1800),
    ]

    fig, ax = plt.subplots(figsize=(14, 11))
    ordered_categories = [
        "ɤ/ɯ类单音化",
        "ø/ɵ/y类单音化",
        "e类单音化",
        "u/o类单音化",
        "ə/ʌ类单音化",
        "其他单音化",
        "混合",
        "未单音化",
    ]
    for category in ordered_categories:
        group = gdf[gdf["map_category"] == category]
        if group.empty:
            continue
        sizes = 42 + group["s4_total_token_count"].clip(upper=120) * 1.7
        group.plot(
            ax=ax,
            marker=marker_map[category],
            color=palette[category],
            edgecolor="black",
            linewidth=0.75,
            markersize=sizes,
            alpha=0.9,
            label=category,
            zorder=3,
        )

    basemap_sources = [
        ("CartoDB.Voyager", ctx.providers.CartoDB.Voyager),
        ("OpenStreetMap.Mapnik", ctx.providers.OpenStreetMap.Mapnik),
        ("CartoDB.Positron", ctx.providers.CartoDB.Positron),
        ("Esri.WorldPhysical", ctx.providers.Esri.WorldPhysical),
    ]
    for source_name, source in basemap_sources:
        try:
            ctx.add_basemap(ax, source=source, alpha=0.68, zorder=1)
            print(f"已加载底图：{source_name}")
            break
        except Exception as exc:
            print(f"底图 {source_name} 下载失败：{exc}")
    else:
        print("所有底图下载失败，使用空白底图")

    for idx, row in enumerate(gdf.sort_values(["lat", "lon"]).itertuples(index=False)):
        dx, dy = label_offsets[idx % len(label_offsets)]
        label = map_label_text(str(row.point_name))
        ax.text(
            row.geometry.x + dx,
            row.geometry.y + dy,
            label,
            fontsize=7,
            fontweight="bold",
            color="black",
            ha="left" if dx >= 0 else "right",
            va="bottom" if dy >= 0 else "top",
            path_effects=[
                path_effects.withStroke(
                    linewidth=3,
                    foreground="white",
                    alpha=0.88,
                )
            ],
            zorder=4,
        )

    ax.set_title("S4 侯韵（*əu）单音化的地理分布", fontsize=18, pad=20)
    ax.legend(title="S4 侯韵状态", loc="lower left", frameon=True)
    ax.set_axis_off()
    fig.savefig(MAP_OUTPUT, dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_subbranch_summary(summary: pd.DataFrame) -> None:
    set_chinese_font()
    plot_df = summary.sort_values("weighted_monophthong_share", ascending=True)
    y = range(len(plot_df))

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(y, plot_df["weighted_monophthong_share"], color="#4C78A8")
    ax.set_yticks(list(y))
    ax.set_yticklabels(plot_df["subbranch"])
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("S4 侯韵单音化 token 占比")
    ax.set_title("各小片 S4 侯韵单音化程度，按 token 加权")

    for pos, row in zip(y, plot_df.itertuples(index=False)):
        label = (
            f"{row.weighted_monophthong_share:.2f}  "
            f"点={row.point_count}, 未单音化={row.diphthong_only_point_count}, 混合={row.mixed_point_count}"
        )
        ax.text(
            row.weighted_monophthong_share + 0.015,
            pos,
            label,
            va="center",
            fontsize=9,
        )

    fig.tight_layout()
    fig.savefig(SUBBRANCH_FIG_OUTPUT, dpi=220, bbox_inches="tight")
    plt.close(fig)


def outputs_for_suffix(suffix: str) -> dict[str, Path]:
    return {
        "core_inventory": VALUE_DIR / f"point_s0_s3_monophthong_inventory_for_s4{suffix}.csv",
        "relation": VALUE_DIR / f"point_s4_hou_monophthong_relation{suffix}.csv",
        "summary": VALUE_DIR / f"s4_hou_monophthong_relation_summary{suffix}.csv",
        "value_summary": VALUE_DIR / f"s4_hou_value_summary{suffix}.csv",
        "subbranch": VALUE_DIR / f"s4_hou_monophthong_by_subbranch{suffix}.csv",
        "cluster": VALUE_DIR / f"s4_hou_geographic_cluster_summary{suffix}.csv",
        "typology": VALUE_DIR / f"s4_hou_typology_with_s5_s0s1{suffix}.csv",
        "typology_summary": VALUE_DIR / f"s4_hou_typology_summary{suffix}.csv",
        "map": FIGS_DIR / f"s4_hou_monophthong_geography_map{suffix}.png",
        "subbranch_fig": FIGS_DIR / f"s4_hou_monophthong_subbranch_summary{suffix}.png",
    }


def plot_map_to_path(data: pd.DataFrame, output_path: Path, title: str) -> None:
    global MAP_OUTPUT
    original_map_output = MAP_OUTPUT
    MAP_OUTPUT = output_path
    try:
        set_chinese_font()
        gdf = gpd.GeoDataFrame(
            data,
            geometry=gpd.points_from_xy(data["lon"], data["lat"]),
            crs="EPSG:4326",
        ).to_crs(epsg=3857)

        palette = {
            "ɤ/ɯ类单音化": "#2F80ED",
            "ø/ɵ/y类单音化": "#8E44AD",
            "e类单音化": "#27AE60",
            "u/o类单音化": "#00796B",
            "ə/ʌ类单音化": "#6F8F3A",
            "其他单音化": "#9B51E0",
            "混合": "#F2994A",
            "未单音化": "#EB5757",
        }
        marker_map = {
            "ɤ/ɯ类单音化": "o",
            "ø/ɵ/y类单音化": "s",
            "e类单音化": "^",
            "u/o类单音化": "P",
            "ə/ʌ类单音化": "v",
            "其他单音化": "*",
            "混合": "D",
            "未单音化": "X",
        }
        label_offsets = [
            (1200, 1200),
            (-1200, 1200),
            (1200, -1200),
            (-1200, -1200),
            (1800, 0),
            (-1800, 0),
            (0, 1800),
            (0, -1800),
        ]

        fig, ax = plt.subplots(figsize=(14, 11))
        ordered_categories = [
            "ɤ/ɯ类单音化",
            "ø/ɵ/y类单音化",
            "e类单音化",
            "u/o类单音化",
            "ə/ʌ类单音化",
            "其他单音化",
            "混合",
            "未单音化",
        ]
        for category in ordered_categories:
            group = gdf[gdf["map_category"] == category]
            if group.empty:
                continue
            sizes = 42 + group["s4_total_token_count"].clip(upper=120) * 1.7
            group.plot(
                ax=ax,
                marker=marker_map[category],
                color=palette[category],
                edgecolor="black",
                linewidth=0.75,
                markersize=sizes,
                alpha=0.9,
                label=category,
                zorder=3,
            )

        basemap_sources = [
            ("CartoDB.Voyager", ctx.providers.CartoDB.Voyager),
            ("OpenStreetMap.Mapnik", ctx.providers.OpenStreetMap.Mapnik),
            ("CartoDB.Positron", ctx.providers.CartoDB.Positron),
            ("Esri.WorldPhysical", ctx.providers.Esri.WorldPhysical),
        ]
        for source_name, source in basemap_sources:
            try:
                ctx.add_basemap(ax, source=source, alpha=0.68, zorder=1)
                print(f"已加载底图：{source_name}")
                break
            except Exception as exc:
                print(f"底图 {source_name} 下载失败：{exc}")
        else:
            print("所有底图下载失败，使用空白底图")

        label_categories = {"混合", "ɤ/ɯ类单音化"}
        for idx, row in enumerate(gdf.sort_values(["lat", "lon"]).itertuples(index=False)):
            if row.map_category not in label_categories:
                continue
            dx, dy = label_offsets[idx % len(label_offsets)]
            label = (
                row.point_name
                if row.map_category != "混合"
                else f"{row.point_name}\n{top_counts_label(row.s4_value_counts)}"
            )
            label = map_label_text(label)
            ax.text(
                row.geometry.x + dx,
                row.geometry.y + dy,
                label,
                fontsize=8,
                fontweight="bold",
                color="black",
                ha="left" if dx >= 0 else "right",
                va="bottom" if dy >= 0 else "top",
                path_effects=[
                    path_effects.withStroke(
                        linewidth=3,
                        foreground="white",
                        alpha=0.88,
                    )
                ],
                zorder=4,
            )

        ax.set_title(title, fontsize=18, pad=20)
        ax.legend(title="S4 侯韵状态", loc="lower left", frameon=True)
        ax.set_axis_off()
        fig.savefig(output_path, dpi=240, bbox_inches="tight")
        plt.close(fig)
    finally:
        MAP_OUTPUT = original_map_output


def plot_subbranch_summary_to_path(
    summary: pd.DataFrame, output_path: Path, title: str
) -> None:
    global SUBBRANCH_FIG_OUTPUT
    original_subbranch_output = SUBBRANCH_FIG_OUTPUT
    SUBBRANCH_FIG_OUTPUT = output_path
    try:
        set_chinese_font()
        plot_df = summary.sort_values("weighted_monophthong_share", ascending=True)
        y = range(len(plot_df))

        fig, ax = plt.subplots(figsize=(11, 6))
        ax.barh(y, plot_df["weighted_monophthong_share"], color="#4C78A8")
        ax.set_yticks(list(y))
        ax.set_yticklabels(plot_df["subbranch"])
        ax.set_xlim(0, 1.05)
        ax.set_xlabel("S4 侯韵单音化 token 占比")
        ax.set_title(title)

        for pos, row in zip(y, plot_df.itertuples(index=False)):
            label = (
                f"{row.weighted_monophthong_share:.2f}  "
                f"点={row.point_count}, 未单音化={row.diphthong_only_point_count}, 混合={row.mixed_point_count}"
            )
            ax.text(
                row.weighted_monophthong_share + 0.015,
                pos,
                label,
                va="center",
                fontsize=9,
            )

        fig.tight_layout()
        fig.savefig(output_path, dpi=220, bbox_inches="tight")
        plt.close(fig)
    finally:
        SUBBRANCH_FIG_OUTPUT = original_subbranch_output


def run_analysis_variant(
    output_suffix: str = "",
    excluded_s4_onset_classes: set[str] | None = None,
    title_suffix: str = "",
) -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"未找到输入文件：{INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)
    required = [
        "point_id",
        "point_name",
        "subbranch",
        "rhyme_modern",
        "chain_slot",
        "slot_type_initial",
        "onset_class",
        "char",
        "phonetic",
    ]
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"输入文件缺少必要列：{sorted(missing)}")

    work = df[required].copy()
    for column in required:
        work[column] = work[column].astype("string").str.strip()
    work = work[
        work["point_name"].notna()
        & (work["point_name"] != "")
    ].copy()
    missing_point_id = work["point_id"].isna() | (work["point_id"] == "")
    work.loc[missing_point_id, "point_id"] = "NO_ID_" + work.loc[
        missing_point_id, "point_name"
    ].astype(str)

    points = work[["point_id", "point_name", "subbranch"]].drop_duplicates()
    expanded = expand_phonetics(work)
    core = expanded[
        expanded["chain_slot"].isin(CORE_SLOTS)
        & ~expanded["char"].isin(EXCLUDED_CHARS)
    ].copy()
    s4 = expanded[
        (expanded["chain_slot"] == TARGET_SLOT)
        & (expanded["rhyme_modern"] == TARGET_RHYME)
    ].copy()
    if excluded_s4_onset_classes:
        s4 = s4[~s4["onset_class"].isin(excluded_s4_onset_classes)].copy()

    core_summary = summarize_core_inventory(core)
    s4_summary = summarize_s4(s4)
    relation = build_relation(core_summary, s4_summary, points)
    status_summary = (
        relation.groupby(["s4_status", "s4_core_relation"], dropna=False)
        .size()
        .reset_index(name="point_count")
        .sort_values(["s4_status", "s4_core_relation"])
    )
    value_summary = build_value_summary(s4)
    relation["s4_map_category"] = relation.apply(map_category, axis=1)
    typology, typology_summary = build_typology_outputs(relation)
    map_data = load_map_data(relation)
    subbranch_summary = build_subbranch_summary(map_data)
    cluster_summary = build_cluster_summary(map_data)
    outputs = outputs_for_suffix(output_suffix)

    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    core_summary.to_csv(outputs["core_inventory"], index=False, encoding="utf-8-sig")
    relation.to_csv(outputs["relation"], index=False, encoding="utf-8-sig")
    status_summary.to_csv(outputs["summary"], index=False, encoding="utf-8-sig")
    value_summary.to_csv(outputs["value_summary"], index=False, encoding="utf-8-sig")
    subbranch_summary.to_csv(outputs["subbranch"], index=False, encoding="utf-8-sig")
    cluster_summary.to_csv(outputs["cluster"], index=False, encoding="utf-8-sig")
    typology.to_csv(outputs["typology"], index=False, encoding="utf-8-sig")
    typology_summary.to_csv(outputs["typology_summary"], index=False, encoding="utf-8-sig")
    plot_map_to_path(
        map_data,
        outputs["map"],
        f"S4 侯韵（*əu）单音化的地理分布{title_suffix}",
    )
    plot_subbranch_summary_to_path(
        subbranch_summary,
        outputs["subbranch_fig"],
        f"各小片 S4 侯韵单音化程度，按 token 加权{title_suffix}",
    )

    print(f"已生成 S0-S3 单元音库藏表：{outputs['core_inventory']}")
    print(f"已生成 S4 侯韵单音化关系表：{outputs['relation']}")
    print(f"已生成 S4 关系汇总表：{outputs['summary']}")
    print(f"已生成 S4 音值汇总表：{outputs['value_summary']}")
    print(f"已生成 S4 小片汇总：{outputs['subbranch']}")
    print(f"已生成 S4 地理聚集汇总：{outputs['cluster']}")
    print(f"已生成 S4-S5-S0/S1 类型学联表：{outputs['typology']}")
    print(f"已生成 S4 类型学汇总表：{outputs['typology_summary']}")
    print(f"已生成 S4 地图：{outputs['map']}")
    print(f"已生成 S4 小片图：{outputs['subbranch_fig']}")
    print(f"方言点记录数：{len(relation)}")


if __name__ == "__main__":
    run_analysis_variant()
    run_analysis_variant(
        output_suffix="_no_mp",
        excluded_s4_onset_classes=S4_EXCLUDED_ONSET_CLASSES_NO_MP,
        title_suffix="（排除侯韵 M/P 组）",
    )
