from __future__ import annotations

import math
import re
import ssl
from pathlib import Path
from typing import Iterable

import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager as fm
from matplotlib import patheffects as pe


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
MERGE_DIR = PROJECT_ROOT / "data_clean" / "merge_analysis"
OUTPUT_DIR = MERGE_DIR / "structure_type_analysis"
FIGS_DIR = PROJECT_ROOT / "figs" / "structure_type_analysis"

# ===== Config =====
# Input tables
PROFILE_PATH = DATA_RAW / "dialect_evolution_profiles_full.csv"
KMEANS_PATH = MERGE_DIR / "point_merge_strength_clusters.csv"
KMEANS_REPORT_PATH = MERGE_DIR / "merge_strength_cluster_report.txt"

# Point / metadata columns
POINT_ID_COL = "point_id"
POINT_NAME_COL = "point_name"
GEO_COL = "subbranch"
SUBBRANCH_COL = "subbranch"
LAT_COL = "lat"
LON_COL = "lon"
KMEANS_COL = "nbclust_cluster"
KMEANS_LABEL_COL = "nbclust_display_label"
KMEANS_METHOD_COL = "nbclust_method"
KMEANS_K_COL = "nbclust_k"

# Two special onset-condition columns: only observe S2=S3
N_COL = "N_Status"
T_COL = "T_Status"

# Five value-pattern onset columns. Edit here if the source table changes.
VALUE_PATTERN_COLS = {
    "K": "K_L3",
    "M": "M_L3",
    "P": "P_L3",
    "TS": "TS_L3",
    "Ø": "Ø_L3",
}

SPECIAL_ONSET_COLS = {
    "N": N_COL,
    "T": T_COL,
}

# Existing k-means strength variables to check, not to overwrite.
KMEANS_STRENGTH_COLS = ["avg_S0_S1", "avg_S1_S2", "avg_S2_S3"]

RELATION_SPECS = {
    "A_rel": "S2=S3",
    "B_rel": "S1=S2",
    "C_rel": "S0=S1",
    "D_rel": "S1=S3",
}

STRUCTURE_LABELS = {
    "A_dominant": "S2=S3主导型",
    "B_dominant": "S1=S2主导型",
    "C_dominant": "S0=S1主导型",
    "AB_chain": "S1=S2=S3连锁型",
    "AC_dual": "S0=S1 与 S2=S3双段型",
    "ABC_chainwide": "S0=S1=S2=S3全链趋同型",
    "D_explicit_cross": "S1=S3显性跨链位型",
    "ABD_cross_chain": "S1=S2=S3连锁并伴随S1=S3型",
    "conservative_split": "保守分立型",
    "mixed_transition": "混合过渡型",
}

# Output files
RELATION_LONG_OUTPUT = OUTPUT_DIR / "relation_long.csv"
POINT_SUMMARY_OUTPUT = OUTPUT_DIR / "point_relation_summary.csv"
POINT_SUMMARY_STRUCT_OUTPUT = OUTPUT_DIR / "point_relation_summary_with_structure_type.csv"
KMEANS_CHECK_OUTPUT = OUTPUT_DIR / "kmeans_cluster_check.csv"
CROSSTAB_KMEANS_BY_STRUCTURE_OUTPUT = OUTPUT_DIR / "crosstab_kmeans_by_structure.csv"
CROSSTAB_KMEANS_BY_GEO_OUTPUT = OUTPUT_DIR / "crosstab_kmeans_by_geo.csv"
CROSSTAB_STRUCTURE_BY_GEO_OUTPUT = OUTPUT_DIR / "crosstab_structure_by_geo.csv"
CROSSTAB_RELATION_BY_ONSET_OUTPUT = OUTPUT_DIR / "crosstab_relation_by_onset.csv"
CHI_SQUARE_RESULTS_OUTPUT = OUTPUT_DIR / "chi_square_test_results.csv"

CLUSTER_CENTER_HEATMAP = FIGS_DIR / "cluster_center_heatmap.png"
STRUCTURE_COUNT_BAR = FIGS_DIR / "structure_type_count_barplot.png"
KMEANS_STRUCTURE_HEATMAP = FIGS_DIR / "kmeans_by_structure_heatmap.png"
GEO_STRUCTURE_HEATMAP = FIGS_DIR / "geo_by_structure_heatmap.png"
ONSET_RELATION_HEATMAP = FIGS_DIR / "onset_by_relation_heatmap.png"
KMEANS_MAP = FIGS_DIR / "map_kmeans_cluster.png"
STRUCTURE_MAP = FIGS_DIR / "map_structure_type.png"


try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass


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
    plt.rcParams["font.sans-serif"] = [name for name in preferred_fonts if name in available_fonts]
    plt.rcParams["axes.unicode_minus"] = False


def normalize_original_value(value) -> str | pd.NA:
    if pd.isna(value):
        return pd.NA
    text = str(value).strip()
    if not text:
        return pd.NA
    text = text.replace("，", ",")
    text = re.sub(r"\s+", "", text)
    text = text.replace("[越级]", "")
    if text in {"合流", "合并"}:
        return "merge"
    if text in {"分立", "不合并"}:
        return "split"
    mapping = {
        "S2=S3": "pattern_A",
        "S1=S2": "pattern_B",
        "S0=S1": "pattern_C",
        "S1=S3": "pattern_D",
        "S1=S2=S3": "pattern_E",
        "S0=S1,S2=S3": "pattern_F",
        "全对立": "pattern_NONE",
        "全不等": "pattern_NONE",
    }
    return mapping.get(text, text)


def encode_special_merge_onset(value) -> dict[str, dict[str, object]]:
    normalized = normalize_original_value(value)
    if pd.isna(normalized):
        return {
            "A_rel": {"observable": False, "is_equal": pd.NA},
            "B_rel": {"observable": False, "is_equal": pd.NA},
            "C_rel": {"observable": False, "is_equal": pd.NA},
            "D_rel": {"observable": False, "is_equal": pd.NA},
        }

    is_merge = 1 if normalized == "merge" else 0
    return {
        "A_rel": {"observable": True, "is_equal": is_merge},
        "B_rel": {"observable": False, "is_equal": pd.NA},
        "C_rel": {"observable": False, "is_equal": pd.NA},
        "D_rel": {"observable": False, "is_equal": pd.NA},
    }


def encode_pattern_to_relations(value) -> dict[str, dict[str, object]]:
    normalized = normalize_original_value(value)
    base = {
        "A_rel": {"observable": False, "is_equal": pd.NA},
        "B_rel": {"observable": False, "is_equal": pd.NA},
        "C_rel": {"observable": False, "is_equal": pd.NA},
        "D_rel": {"observable": False, "is_equal": pd.NA},
    }
    if pd.isna(normalized):
        return base

    relation_flags = {
        "pattern_A": {"A_rel": 1, "B_rel": 0, "C_rel": 0, "D_rel": 0},
        "pattern_B": {"A_rel": 0, "B_rel": 1, "C_rel": 0, "D_rel": 0},
        "pattern_C": {"A_rel": 0, "B_rel": 0, "C_rel": 1, "D_rel": 0},
        "pattern_D": {"A_rel": 0, "B_rel": 0, "C_rel": 0, "D_rel": 1},
        "pattern_E": {"A_rel": 1, "B_rel": 1, "C_rel": 0, "D_rel": 0},
        "pattern_F": {"A_rel": 1, "B_rel": 0, "C_rel": 1, "D_rel": 0},
        "pattern_NONE": {"A_rel": 0, "B_rel": 0, "C_rel": 0, "D_rel": 0},
    }
    flags = relation_flags.get(normalized)
    if flags is None:
        raise ValueError(f"未识别的 pattern 值：{value} -> {normalized}")

    return {
        relation_type: {"observable": True, "is_equal": flags[relation_type]}
        for relation_type in RELATION_SPECS
    }


def load_input_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(f"未找到输入表：{PROFILE_PATH}")
    if not KMEANS_PATH.exists():
        raise FileNotFoundError(f"未找到 kmeans 结果表：{KMEANS_PATH}")

    profile_df = pd.read_csv(PROFILE_PATH)
    kmeans_df = pd.read_csv(KMEANS_PATH)
    return profile_df, kmeans_df


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def validate_required_columns(df: pd.DataFrame, required_cols: Iterable[str], table_name: str) -> None:
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"{table_name} 缺少必要列：{missing}")


def build_long_relation_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    required_cols = [POINT_ID_COL, POINT_NAME_COL, *SPECIAL_ONSET_COLS.values(), *VALUE_PATTERN_COLS.values()]
    validate_required_columns(df, required_cols, "profile_df")

    rows: list[dict[str, object]] = []
    for row in df.to_dict("records"):
        point_id = row[POINT_ID_COL]
        point_name = row.get(POINT_NAME_COL, "")

        for onset_class, column in SPECIAL_ONSET_COLS.items():
            original_value = row.get(column, pd.NA)
            normalized_value = normalize_original_value(original_value)
            encoded = encode_special_merge_onset(original_value)
            for relation_type, relation_label in RELATION_SPECS.items():
                rows.append(
                    {
                        POINT_ID_COL: point_id,
                        POINT_NAME_COL: point_name,
                        "onset_class": onset_class,
                        "slot_type": "special_merge_onset",
                        "source_column": column,
                        "original_value": original_value,
                        "normalized_value": normalized_value,
                        "relation_type": relation_type,
                        "relation_label": relation_label,
                        "observable": encoded[relation_type]["observable"],
                        "is_equal": encoded[relation_type]["is_equal"],
                    }
                )

        for onset_class, column in VALUE_PATTERN_COLS.items():
            original_value = row.get(column, pd.NA)
            normalized_value = normalize_original_value(original_value)
            encoded = encode_pattern_to_relations(original_value)
            for relation_type, relation_label in RELATION_SPECS.items():
                rows.append(
                    {
                        POINT_ID_COL: point_id,
                        POINT_NAME_COL: point_name,
                        "onset_class": onset_class,
                        "slot_type": "value_pattern_onset",
                        "source_column": column,
                        "original_value": original_value,
                        "normalized_value": normalized_value,
                        "relation_type": relation_type,
                        "relation_label": relation_label,
                        "observable": encoded[relation_type]["observable"],
                        "is_equal": encoded[relation_type]["is_equal"],
                    }
                )

    long_df = pd.DataFrame(rows)
    long_df["observable"] = long_df["observable"].astype(bool)
    long_df["is_equal"] = long_df["is_equal"].astype("Int64")
    return long_df


def get_series(df: pd.DataFrame, column: str) -> pd.Series:
    obj = df[column]
    if isinstance(obj, pd.DataFrame):
        return obj.iloc[:, 0]
    return obj


def summarize_point_relations(long_df: pd.DataFrame) -> pd.DataFrame:
    point_keys = [POINT_ID_COL, POINT_NAME_COL]
    base = long_df[point_keys].drop_duplicates().copy()
    summary = base.copy()

    observable_df = long_df[long_df["observable"]].copy()

    for relation_type in RELATION_SPECS:
        key = relation_type[0]
        relation_sub = observable_df[observable_df["relation_type"] == relation_type].copy()
        grouped = relation_sub.groupby(point_keys, dropna=False).agg(
            observable_n=("observable", "sum"),
            count=("is_equal", lambda s: int(pd.Series(s).fillna(0).sum())),
        )
        grouped = grouped.rename(
            columns={
                "count": f"{key}_count",
                "observable_n": f"{key}_observable_n",
            }
        ).reset_index()
        summary = summary.merge(grouped, on=point_keys, how="left")
        summary[f"{key}_count"] = summary[f"{key}_count"].fillna(0).astype(int)
        summary[f"{key}_observable_n"] = summary[f"{key}_observable_n"].fillna(0).astype(int)
        summary[f"{key}_strength"] = np.where(
            summary[f"{key}_observable_n"] > 0,
            summary[f"{key}_count"] / summary[f"{key}_observable_n"],
            np.nan,
        )

    return summary


def build_profile_structure_features(profile_df: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [POINT_ID_COL, POINT_NAME_COL, *SPECIAL_ONSET_COLS.values(), *VALUE_PATTERN_COLS.values()]
    validate_required_columns(profile_df, keep_cols, "profile_df")

    feature_rows: list[dict[str, object]] = []
    for row in profile_df.to_dict("records"):
        pattern_values = [normalize_original_value(row[col]) for col in VALUE_PATTERN_COLS.values()]
        nt_values = [normalize_original_value(row[col]) for col in SPECIAL_ONSET_COLS.values()]
        pattern_merge_count = sum(value not in {pd.NA, "pattern_NONE"} for value in pattern_values)
        pattern_non_a_merge_count = sum(
            value not in {pd.NA, "pattern_NONE", "pattern_A"} for value in pattern_values
        )
        nt_merge_count = sum(value == "merge" for value in nt_values)
        feature_rows.append(
            {
                POINT_ID_COL: row[POINT_ID_COL],
                POINT_NAME_COL: row[POINT_NAME_COL],
                "pattern_merge_count": int(pattern_merge_count),
                "pattern_non_a_merge_count": int(pattern_non_a_merge_count),
                "pattern_none_count": int(sum(value == "pattern_NONE" for value in pattern_values)),
                "nt_merge_count": int(nt_merge_count),
                "nt_split_count": int(sum(value == "split" for value in nt_values)),
                "all_pattern_none": bool(all(value == "pattern_NONE" for value in pattern_values)),
            }
        )
    return pd.DataFrame(feature_rows)


def classify_structure_type(
    row: pd.Series,
    high_threshold: float = 0.5,
    dominance_margin: float = 0.2,
) -> str:
    strengths = {
        "A": float(row.get("A_strength", np.nan) if pd.notna(row.get("A_strength")) else 0.0),
        "B": float(row.get("B_strength", np.nan) if pd.notna(row.get("B_strength")) else 0.0),
        "C": float(row.get("C_strength", np.nan) if pd.notna(row.get("C_strength")) else 0.0),
        "D": float(row.get("D_strength", np.nan) if pd.notna(row.get("D_strength")) else 0.0),
    }
    sorted_strengths = sorted(strengths.items(), key=lambda item: item[1], reverse=True)
    top_key, top_value = sorted_strengths[0]
    second_value = sorted_strengths[1][1]

    high = {key for key, value in strengths.items() if value >= high_threshold}
    explicit_d = row.get("D_count", 0) > 0 and strengths["D"] >= high_threshold
    pattern_merge_count = int(row.get("pattern_merge_count", 0))
    pattern_non_a_merge_count = int(row.get("pattern_non_a_merge_count", 0))

    if (
        strengths["B"] == 0
        and strengths["C"] == 0
        and strengths["D"] == 0
        and strengths["A"] < high_threshold
        and pattern_non_a_merge_count == 0
        and pattern_merge_count <= 2
    ):
        return "conservative_split"

    if len(high) == 0 and top_value < max(0.3, high_threshold * 0.8):
        return "mixed_transition"
    if {"A", "B", "C"} <= high:
        return "ABC_chainwide"
    if explicit_d and {"A", "B"} <= high:
        return "ABD_cross_chain"
    if explicit_d and "D" in high and not {"A", "B"} <= high:
        return "D_explicit_cross"
    if {"A", "B"} <= high and "C" not in high:
        return "AB_chain"
    if {"A", "C"} <= high and "B" not in high:
        return "AC_dual"
    if top_key == "A" and top_value >= high_threshold and top_value - second_value >= dominance_margin:
        return "A_dominant"
    if top_key == "B" and top_value >= high_threshold and top_value - second_value >= dominance_margin:
        return "B_dominant"
    if top_key == "C" and top_value >= high_threshold and top_value - second_value >= dominance_margin:
        return "C_dominant"
    if top_key == "D" and top_value >= high_threshold and top_value - second_value >= dominance_margin:
        return "D_explicit_cross"
    return "mixed_transition"


def add_structure_types(
    summary_df: pd.DataFrame,
    high_threshold: float = 0.5,
    dominance_margin: float = 0.2,
) -> pd.DataFrame:
    result = summary_df.copy()
    result["structure_type"] = result.apply(
        classify_structure_type,
        axis=1,
        high_threshold=high_threshold,
        dominance_margin=dominance_margin,
    )
    result["structure_label"] = result["structure_type"].map(STRUCTURE_LABELS)
    return result


def pairwise_distances(x: np.ndarray) -> np.ndarray:
    diff = x[:, None, :] - x[None, :, :]
    return np.sqrt(np.sum(diff * diff, axis=2))


def silhouette_score_manual(x: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    if len(unique_labels) < 2 or len(unique_labels) >= len(x):
        return float("nan")
    dist = pairwise_distances(x)
    sil_values = []
    for idx in range(len(x)):
        same_mask = labels == labels[idx]
        same_mask[idx] = False
        a = dist[idx, same_mask].mean() if same_mask.any() else 0.0
        b_vals = []
        for label in unique_labels:
            if label == labels[idx]:
                continue
            other_mask = labels == label
            if other_mask.any():
                b_vals.append(dist[idx, other_mask].mean())
        b = min(b_vals) if b_vals else 0.0
        sil = 0.0 if max(a, b) == 0 else (b - a) / max(a, b)
        sil_values.append(sil)
    return float(np.mean(sil_values))


def cluster_centers(x: np.ndarray, labels: np.ndarray) -> dict[int, np.ndarray]:
    centers: dict[int, np.ndarray] = {}
    for cluster_id in sorted(np.unique(labels)):
        centers[int(cluster_id)] = x[labels == cluster_id].mean(axis=0)
    return centers


def zscore_array(x: np.ndarray) -> np.ndarray:
    mean = x.mean(axis=0)
    std = x.std(axis=0, ddof=0)
    std[std == 0] = 1.0
    return (x - mean) / std


def compute_wcss(x: np.ndarray, labels: np.ndarray) -> float:
    centers = cluster_centers(x, labels)
    total = 0.0
    for cluster_id, center in centers.items():
        members = x[labels == cluster_id]
        total += float(np.sum((members - center) ** 2))
    return total


def parse_saved_kmeans_metrics(report_path: Path, k_value: int) -> dict[str, object]:
    result = {
        "saved_silhouette": np.nan,
        "saved_ch": np.nan,
        "saved_db": np.nan,
        "saved_rank_score": np.nan,
        "saved_min_cluster_size": np.nan,
        "has_saved_metrics": False,
    }
    if not report_path.exists():
        return result
    pattern = re.compile(
        rf"- k={k_value}: silhouette=([0-9.]+), CH=([0-9.]+), DB=([0-9.]+), min_cluster=([0-9]+), rank_score=([0-9.]+)"
    )
    text = report_path.read_text(encoding="utf-8")
    match = pattern.search(text)
    if not match:
        return result
    result.update(
        {
            "saved_silhouette": float(match.group(1)),
            "saved_ch": float(match.group(2)),
            "saved_db": float(match.group(3)),
            "saved_min_cluster_size": int(match.group(4)),
            "saved_rank_score": float(match.group(5)),
            "has_saved_metrics": True,
        }
    )
    return result


def check_existing_kmeans(summary_df: pd.DataFrame, cluster_col: str, strength_cols: list[str]) -> pd.DataFrame:
    if cluster_col not in summary_df.columns:
        raise ValueError(f"summary_df 中未找到 cluster 列：{cluster_col}")
    usable = summary_df.dropna(subset=[cluster_col, *strength_cols]).copy()
    usable[cluster_col] = usable[cluster_col].astype(int)

    x_raw = usable[strength_cols].to_numpy(dtype=float)
    x = zscore_array(x_raw)
    labels = usable[cluster_col].to_numpy(dtype=int)
    cluster_sizes = usable[cluster_col].value_counts().sort_index()
    centers = usable.groupby(cluster_col)[strength_cols].mean().reset_index()

    silhouette = silhouette_score_manual(x, labels)
    wcss = compute_wcss(x, labels)
    saved_metrics = parse_saved_kmeans_metrics(KMEANS_REPORT_PATH, int(usable[KMEANS_K_COL].mode().iloc[0])) if KMEANS_K_COL in usable.columns else parse_saved_kmeans_metrics(KMEANS_REPORT_PATH, 3)

    rows = []
    for _, row in centers.iterrows():
        cluster_id = int(row[cluster_col])
        result = {
            "cluster_id": cluster_id,
            "cluster_size": int(cluster_sizes.loc[cluster_id]),
            "computed_silhouette": silhouette,
            "computed_wcss": wcss,
            "computed_on_zscore": True,
            **saved_metrics,
        }
        for col in strength_cols:
            result[col] = float(row[col])
        rows.append(result)
    return pd.DataFrame(rows)


def expected_frequencies(table: np.ndarray) -> np.ndarray:
    row_sums = table.sum(axis=1, keepdims=True)
    col_sums = table.sum(axis=0, keepdims=True)
    total = table.sum()
    if total == 0:
        return np.zeros_like(table, dtype=float)
    return row_sums @ col_sums / total


def log_choose(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact_two_sided(table: np.ndarray) -> tuple[float, float]:
    a, b = int(table[0, 0]), int(table[0, 1])
    c, d = int(table[1, 0]), int(table[1, 1])
    row1 = a + b
    row2 = c + d
    col1 = a + c
    total = row1 + row2

    def hypergeom_prob(x: int) -> float:
        log_p = log_choose(row1, x) + log_choose(row2, col1 - x) - log_choose(total, col1)
        return math.exp(log_p)

    min_x = max(0, col1 - row2)
    max_x = min(row1, col1)
    observed_p = hypergeom_prob(a)
    p_value = 0.0
    for x in range(min_x, max_x + 1):
        p = hypergeom_prob(x)
        if p <= observed_p + 1e-12:
            p_value += p

    odds_ratio = math.inf if b * c == 0 and a * d > 0 else ((a * d) / (b * c) if b * c != 0 else 0.0)
    return odds_ratio, min(p_value, 1.0)


def gammq(a: float, x: float) -> float:
    if x < 0 or a <= 0:
        return float("nan")
    if x == 0:
        return 1.0
    itmax = 100
    eps = 3e-7
    fpmin = 1e-30

    if x < a + 1.0:
        ap = a
        summ = 1.0 / a
        delta = summ
        for _ in range(itmax):
            ap += 1.0
            delta *= x / ap
            summ += delta
            if abs(delta) < abs(summ) * eps:
                gln = math.lgamma(a)
                gamser = summ * math.exp(-x + a * math.log(x) - gln)
                return 1.0 - gamser
    else:
        gln = math.lgamma(a)
        b = x + 1.0 - a
        c = 1.0 / fpmin
        d = 1.0 / b
        h = d
        for i in range(1, itmax + 1):
            an = -i * (i - a)
            b += 2.0
            d = an * d + b
            if abs(d) < fpmin:
                d = fpmin
            c = b + an / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < eps:
                gammcf = math.exp(-x + a * math.log(x) - gln) * h
                return gammcf
    return float("nan")


def chi_square_test(table: np.ndarray) -> tuple[float, int, float, np.ndarray]:
    expected = expected_frequencies(table)
    mask = expected > 0
    statistic = float(np.sum(((table - expected) ** 2)[mask] / expected[mask]))
    dof = int((table.shape[0] - 1) * (table.shape[1] - 1))
    p_value = gammq(dof / 2.0, statistic / 2.0) if dof > 0 else float("nan")
    return statistic, dof, p_value, expected


def make_crosstab_and_test(df: pd.DataFrame, row_var: str, col_var: str, test_name: str) -> tuple[pd.DataFrame, dict[str, object]]:
    row_series = get_series(df, row_var)
    col_series = get_series(df, col_var)
    work = pd.DataFrame({row_var: row_series, col_var: col_series}).dropna().copy()
    if work.empty:
        return pd.DataFrame(), {
            "test_name": test_name,
            "row_var": row_var,
            "col_var": col_var,
            "test_type": "not_run",
            "reason": "no valid rows",
        }

    crosstab = pd.crosstab(work[row_var], work[col_var], dropna=False)
    table = crosstab.to_numpy(dtype=float)
    if crosstab.shape[0] < 2 or crosstab.shape[1] < 2:
        return crosstab, {
            "test_name": test_name,
            "row_var": row_var,
            "col_var": col_var,
            "test_type": "not_run",
            "reason": "table is not at least 2x2",
        }

    result: dict[str, object]
    if crosstab.shape == (2, 2):
        odds_ratio, p_value = fisher_exact_two_sided(table)
        chi2, dof, chi_p, expected = chi_square_test(table)
        result = {
            "test_name": test_name,
            "row_var": row_var,
            "col_var": col_var,
            "test_type": "fisher_exact_2x2",
            "odds_ratio": odds_ratio,
            "p_value": p_value,
            "chi_square_statistic": chi2,
            "chi_square_p_value": chi_p,
            "dof": dof,
            "expected_min": float(expected.min()) if expected.size else np.nan,
            "warning": "expected frequencies too small; chi-square result should be interpreted cautiously."
            if (expected < 5).any()
            else "",
        }
    else:
        chi2, dof, p_value, expected = chi_square_test(table)
        result = {
            "test_name": test_name,
            "row_var": row_var,
            "col_var": col_var,
            "test_type": "chi_square",
            "chi_square_statistic": chi2,
            "dof": dof,
            "p_value": p_value,
            "expected_min": float(expected.min()) if expected.size else np.nan,
            "warning": "expected frequencies too small; chi-square result should be interpreted cautiously."
            if (expected < 5).any()
            else "",
        }
    return crosstab, result


def test_relation_by_onset(long_df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, object]], dict[str, pd.DataFrame]]:
    results: list[dict[str, object]] = []
    crosstabs: dict[str, pd.DataFrame] = {}

    equal_only = long_df[long_df["observable"] & long_df["is_equal"].eq(1)].copy()
    relation_ct, relation_res = make_crosstab_and_test(
        equal_only,
        "relation_type",
        "onset_class",
        "relation_type_by_onset_class_equal_only",
    )
    crosstabs["relation_by_onset"] = relation_ct
    results.append(relation_res)

    observable_df = long_df[long_df["observable"]].copy()
    observable_df["is_equal_str"] = observable_df["is_equal"].astype("Int64").astype(str)
    for relation_type in RELATION_SPECS:
        rel_df = observable_df[observable_df["relation_type"] == relation_type].copy()
        ct, res = make_crosstab_and_test(
            rel_df,
            "onset_class",
            "is_equal_str",
            f"onset_class_by_{relation_type}",
        )
        crosstabs[f"onset_by_{relation_type}"] = ct
        results.append(res)

    rel_equal_ct, rel_equal_res = make_crosstab_and_test(
        observable_df,
        "relation_type",
        "is_equal_str",
        "relation_type_by_is_equal",
    )
    crosstabs["relation_by_is_equal"] = rel_equal_ct
    results.append(rel_equal_res)

    return relation_ct, results, crosstabs


def plot_heatmap(df: pd.DataFrame, output_path: Path, title: str, cmap: str = "Blues", annotate: bool = True) -> None:
    if df.empty:
        return
    set_chinese_font()
    fig, ax = plt.subplots(figsize=(max(6, 1.2 * df.shape[1]), max(4, 0.8 * df.shape[0])))
    image = ax.imshow(df.to_numpy(dtype=float), cmap=cmap, aspect="auto")
    ax.set_xticks(range(df.shape[1]))
    ax.set_xticklabels(df.columns, rotation=45, ha="right")
    ax.set_yticks(range(df.shape[0]))
    ax.set_yticklabels(df.index)
    ax.set_title(title)
    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    if annotate:
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                ax.text(j, i, f"{df.iat[i, j]:.2f}" if isinstance(df.iat[i, j], float) else str(df.iat[i, j]), ha="center", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def rename_relation_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    rename_map = RELATION_SPECS.copy()
    result = df.copy()
    result.index = [rename_map.get(value, value) for value in result.index]
    return result


def plot_structure_count_barplot(summary_df: pd.DataFrame, output_path: Path) -> None:
    set_chinese_font()
    counts = summary_df["structure_label"].value_counts().sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(counts.index, counts.values, color="#4C78A8")
    ax.set_title("结构类型数量分布")
    ax.set_ylabel("方言点数")
    ax.set_xticks(range(len(counts.index)))
    ax.set_xticklabels(counts.index, rotation=30, ha="right")
    for idx, value in enumerate(counts.values):
        ax.text(idx, value + 0.3, str(value), ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_cluster_centers(df: pd.DataFrame, output_path: Path, cluster_col: str, feature_cols: list[str]) -> None:
    centers = df.groupby(cluster_col)[feature_cols].mean().sort_index()
    rename_map = {
        "avg_S0_S1": "S0-S1 平均合并强度",
        "avg_S1_S2": "S1-S2 平均合并强度",
        "avg_S2_S3": "S2-S3 平均合并强度",
        "A_strength": "S2=S3 强度",
        "B_strength": "S1=S2 强度",
        "C_strength": "S0=S1 强度",
        "D_strength": "S1=S3 强度",
    }
    centers = centers.rename(columns=rename_map)
    plot_heatmap(centers, output_path, "k-means cluster center heatmap", cmap="YlGnBu")


def plot_map_points(df: pd.DataFrame, color_col: str, label_col: str, output_path: Path, title: str) -> None:
    required = {LAT_COL, LON_COL, color_col}
    if not required <= set(df.columns):
        return
    set_chinese_font()
    plot_df = df.dropna(subset=[LAT_COL, LON_COL, color_col]).copy()
    if plot_df.empty:
        return
    categories = list(pd.Series(plot_df[color_col]).dropna().unique())
    cmap = plt.get_cmap("tab20", len(categories))
    color_map = {category: cmap(idx) for idx, category in enumerate(categories)}
    label_offsets = [
        (2200, 1800),
        (-2200, 1800),
        (2200, -1800),
        (-2200, -1800),
        (3000, 0),
        (-3000, 0),
        (0, 2500),
        (0, -2500),
        (3400, 1600),
        (-3400, 1600),
        (3400, -1600),
        (-3400, -1600),
    ]

    gdf = gpd.GeoDataFrame(
        plot_df,
        geometry=gpd.points_from_xy(plot_df[LON_COL], plot_df[LAT_COL]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(12, 10))
    for category in categories:
        group = gdf[gdf[color_col] == category]
        ax.scatter(
            group.geometry.x,
            group.geometry.y,
            label=str(category),
            s=45,
            color=color_map[category],
            alpha=0.85,
            edgecolors="black",
            linewidths=0.4,
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

    for idx, row in enumerate(gdf.sort_values([LAT_COL, LON_COL]).itertuples(index=False)):
        dx, dy = label_offsets[idx % len(label_offsets)]
        x0 = row.geometry.x
        y0 = row.geometry.y
        x1 = x0 + dx
        y1 = y0 + dy
        ax.plot([x0, x1], [y0, y1], color="#555555", linewidth=0.7, alpha=0.8, zorder=3.5)
        txt = ax.text(
            x1,
            y1,
            str(getattr(row, label_col)),
            fontsize=8.5,
            fontweight="bold",
            color="black",
            ha="left" if dx >= 0 else "right",
            va="bottom" if dy >= 0 else "top",
            bbox=dict(
                boxstyle="round,pad=0.22",
                facecolor="white",
                edgecolor="#666666",
                linewidth=0.6,
                alpha=0.92,
            ),
            zorder=4,
        )
        txt.set_path_effects([pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_title(title)
    ax.set_axis_off()
    ax.legend(loc="best", fontsize=9, framealpha=0.95)
    fig.tight_layout()
    fig.savefig(output_path, dpi=260, bbox_inches="tight")
    plt.close(fig)


def save_outputs(
    relation_long: pd.DataFrame,
    point_summary: pd.DataFrame,
    point_summary_with_structure: pd.DataFrame,
    kmeans_check: pd.DataFrame,
    crosstab_outputs: dict[str, pd.DataFrame],
    test_results: list[dict[str, object]],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    relation_long.to_csv(RELATION_LONG_OUTPUT, index=False, encoding="utf-8-sig")
    point_summary.to_csv(POINT_SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")
    point_summary_with_structure.to_csv(POINT_SUMMARY_STRUCT_OUTPUT, index=False, encoding="utf-8-sig")
    kmeans_check.to_csv(KMEANS_CHECK_OUTPUT, index=False, encoding="utf-8-sig")

    if "kmeans_by_structure" in crosstab_outputs:
        crosstab_outputs["kmeans_by_structure"].to_csv(CROSSTAB_KMEANS_BY_STRUCTURE_OUTPUT, encoding="utf-8-sig")
    if "kmeans_by_geo" in crosstab_outputs:
        crosstab_outputs["kmeans_by_geo"].to_csv(CROSSTAB_KMEANS_BY_GEO_OUTPUT, encoding="utf-8-sig")
    if "structure_by_geo" in crosstab_outputs:
        crosstab_outputs["structure_by_geo"].to_csv(CROSSTAB_STRUCTURE_BY_GEO_OUTPUT, encoding="utf-8-sig")
    if "relation_by_onset" in crosstab_outputs:
        crosstab_outputs["relation_by_onset"].to_csv(CROSSTAB_RELATION_BY_ONSET_OUTPUT, encoding="utf-8-sig")

    pd.DataFrame(test_results).to_csv(CHI_SQUARE_RESULTS_OUTPUT, index=False, encoding="utf-8-sig")


def main() -> None:
    profile_df, kmeans_df = load_input_tables()
    validate_required_columns(
        kmeans_df,
        [POINT_ID_COL, POINT_NAME_COL, GEO_COL, LAT_COL, LON_COL, KMEANS_COL, *KMEANS_STRENGTH_COLS],
        "kmeans_df",
    )

    relation_long = build_long_relation_dataframe(profile_df)
    point_summary = summarize_point_relations(relation_long)
    profile_features = build_profile_structure_features(profile_df)
    point_summary = point_summary.merge(profile_features, on=[POINT_ID_COL, POINT_NAME_COL], how="left")

    kmeans_keep_cols = [
        POINT_ID_COL,
        POINT_NAME_COL,
        GEO_COL,
        SUBBRANCH_COL,
        LAT_COL,
        LON_COL,
        KMEANS_COL,
        KMEANS_LABEL_COL,
        KMEANS_METHOD_COL,
        KMEANS_K_COL,
        *KMEANS_STRENGTH_COLS,
    ]
    kmeans_keep_cols = [col for col in dedupe_preserve_order(kmeans_keep_cols) if col in kmeans_df.columns]
    point_summary = point_summary.merge(
        kmeans_df[kmeans_keep_cols].drop_duplicates(subset=[POINT_ID_COL]),
        on=[POINT_ID_COL, POINT_NAME_COL],
        how="left",
    )
    point_summary["kmeans_cluster"] = point_summary[KMEANS_COL] if KMEANS_COL in point_summary.columns else pd.NA
    point_summary["kmeans_cluster_label"] = point_summary[KMEANS_LABEL_COL] if KMEANS_LABEL_COL in point_summary.columns else pd.NA

    point_summary_with_structure = add_structure_types(point_summary)

    relation_strength_centers = (
        point_summary_with_structure.groupby("kmeans_cluster")[["A_strength", "B_strength", "C_strength", "D_strength"]]
        .mean()
        .reset_index()
    )

    relation_long = relation_long.merge(
        point_summary_with_structure[
            [
                POINT_ID_COL,
                POINT_NAME_COL,
                "structure_type",
                "structure_label",
                "kmeans_cluster",
                "kmeans_cluster_label",
            ]
        ],
        on=[POINT_ID_COL, POINT_NAME_COL],
        how="left",
    )

    kmeans_check = check_existing_kmeans(point_summary_with_structure, "kmeans_cluster", KMEANS_STRENGTH_COLS)
    kmeans_check = kmeans_check.merge(relation_strength_centers, left_on="cluster_id", right_on="kmeans_cluster", how="left").drop(columns=["kmeans_cluster"])

    test_results: list[dict[str, object]] = []
    crosstab_outputs: dict[str, pd.DataFrame] = {}

    kmeans_geo_ct, kmeans_geo_res = make_crosstab_and_test(
        point_summary_with_structure,
        "kmeans_cluster",
        GEO_COL,
        "kmeans_cluster_by_geo_region",
    )
    crosstab_outputs["kmeans_by_geo"] = kmeans_geo_ct
    test_results.append(kmeans_geo_res)

    structure_geo_ct, structure_geo_res = make_crosstab_and_test(
        point_summary_with_structure,
        "structure_label",
        GEO_COL,
        "structure_type_by_geo_region",
    )
    crosstab_outputs["structure_by_geo"] = structure_geo_ct
    test_results.append(structure_geo_res)

    kmeans_structure_ct, kmeans_structure_res = make_crosstab_and_test(
        point_summary_with_structure,
        "kmeans_cluster",
        "structure_label",
        "kmeans_cluster_by_structure_type",
    )
    crosstab_outputs["kmeans_by_structure"] = kmeans_structure_ct
    test_results.append(kmeans_structure_res)

    relation_by_onset_ct, relation_test_results, extra_crosstabs = test_relation_by_onset(relation_long)
    relation_by_onset_ct = rename_relation_index(relation_by_onset_ct)
    crosstab_outputs["relation_by_onset"] = relation_by_onset_ct
    crosstab_outputs.update(extra_crosstabs)
    test_results.extend(relation_test_results)

    save_outputs(
        relation_long=relation_long,
        point_summary=point_summary,
        point_summary_with_structure=point_summary_with_structure,
        kmeans_check=kmeans_check,
        crosstab_outputs=crosstab_outputs,
        test_results=test_results,
    )

    plot_cluster_centers(
        point_summary_with_structure,
        CLUSTER_CENTER_HEATMAP,
        "kmeans_cluster",
        KMEANS_STRENGTH_COLS + ["A_strength", "B_strength", "C_strength", "D_strength"],
    )
    plot_structure_count_barplot(point_summary_with_structure, STRUCTURE_COUNT_BAR)
    plot_heatmap(
        kmeans_structure_ct,
        KMEANS_STRUCTURE_HEATMAP,
        "kmeans cluster × structure type",
        cmap="Oranges",
        annotate=True,
    )
    plot_heatmap(
        structure_geo_ct,
        GEO_STRUCTURE_HEATMAP,
        "geo region × structure type",
        cmap="Purples",
        annotate=True,
    )
    plot_heatmap(
        relation_by_onset_ct,
        ONSET_RELATION_HEATMAP,
        "onset class × relation type (is_equal=1)",
        cmap="Greens",
        annotate=True,
    )
    plot_map_points(
        point_summary_with_structure,
        "kmeans_cluster",
        POINT_NAME_COL,
        KMEANS_MAP,
        "方言点地图：按既有 k-means cluster 着色",
    )
    plot_map_points(
        point_summary_with_structure,
        "structure_label",
        POINT_NAME_COL,
        STRUCTURE_MAP,
        "方言点地图：按结构类型着色",
    )

    print(f"已生成长表：{RELATION_LONG_OUTPUT}")
    print(f"已生成方言点汇总：{POINT_SUMMARY_OUTPUT}")
    print(f"已生成结构类型汇总：{POINT_SUMMARY_STRUCT_OUTPUT}")
    print(f"已生成 kmeans 检查表：{KMEANS_CHECK_OUTPUT}")
    print(f"已生成列联检验结果：{CHI_SQUARE_RESULTS_OUTPUT}")
    print(f"已生成图目录：{FIGS_DIR}")


if __name__ == "__main__":
    main()
