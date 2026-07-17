import os
from collections import Counter
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl-cache")

import contextily as ctx
import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
MERGE_DIR = PROJECT_ROOT / "data_clean" / "merge_analysis"
DATA_DICT = PROJECT_ROOT / "data_dict"
FIGS_DIR = PROJECT_ROOT / "figs"

STRENGTH_PATH = MERGE_DIR / "point_merge_strength_clusters.csv"
MAINLAYER_PATH = DATA_RAW / "mainlayer_merge.csv"
COORD_PATH = DATA_DICT / "point_coords_master.csv"

PATTERN_CLUSTER_OUTPUT = MERGE_DIR / "point_merge_pattern_clusters.csv"
COMPARISON_REPORT_OUTPUT = MERGE_DIR / "merge_clustering_comparison_report.txt"

STRENGTH_MAP_OUTPUT = FIGS_DIR / "merge_strength_nbclust_plain_map.png"
STRENGTH_TILE_MAP_OUTPUT = FIGS_DIR / "merge_strength_nbclust_tile_map.png"
STRENGTH_SCATTER_OUTPUT = FIGS_DIR / "merge_strength_stage_scatter.png"
PATTERN_MAP_OUTPUT = FIGS_DIR / "merge_pattern_k4_map.png"
PATTERN_MDS_OUTPUT = FIGS_DIR / "merge_pattern_hamming_mds.png"

ONSET_ORDER = ["K", "M", "P", "Ø", "TS"]
FEATURE_COLS = ["avg_S0_S1", "avg_S1_S2", "avg_S2_S3"]

PALETTE = [
    "#4C78A8",
    "#F58518",
    "#54A24B",
    "#E45756",
    "#72B7B2",
    "#B279A2",
    "#FF9DA6",
]

TILE_SOURCES = [
    ("Esri.WorldTopoMap", ctx.providers.Esri.WorldTopoMap),
    ("OpenStreetMap.Mapnik", ctx.providers.OpenStreetMap.Mapnik),
    ("CartoDB.Positron", ctx.providers.CartoDB.Positron),
]


def set_chinese_font() -> None:
    available = {f.name for f in fm.fontManager.ttflist}
    for name in ["PingFang SC", "Heiti SC", "SimHei", "Microsoft YaHei", "Arial Unicode MS"]:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [col.strip().lstrip("\ufeff") for col in df.columns]
    return df


def hamming_distance_matrix(x: np.ndarray) -> np.ndarray:
    n = len(x)
    dist = np.zeros((n, n), dtype=float)
    for i in range(n):
        dist[i] = (x[i] != x).mean(axis=1)
    return dist


def initialize_modes(x: np.ndarray, k: int) -> np.ndarray:
    first_idx = int(np.argmin([(row == x).mean() for row in x]))
    modes = [x[first_idx]]
    while len(modes) < k:
        existing = np.vstack(modes)
        distances = np.array([(row != existing).mean(axis=1).min() for row in x])
        modes.append(x[int(np.argmax(distances))])
    return np.vstack(modes)


def kmodes(x: np.ndarray, k: int, max_iter: int = 100) -> np.ndarray:
    modes = initialize_modes(x, k)
    labels = np.zeros(len(x), dtype=int)
    for _ in range(max_iter):
        distances = np.array([(row != modes).mean(axis=1) for row in x])
        new_labels = distances.argmin(axis=1)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels
        for cluster_id in range(k):
            mask = labels == cluster_id
            if not mask.any():
                continue
            for col_idx in range(x.shape[1]):
                modes[cluster_id, col_idx] = Counter(x[mask, col_idx]).most_common(1)[0][0]
    return labels


def classical_mds(dist: np.ndarray, dims: int = 2) -> np.ndarray:
    n = dist.shape[0]
    squared = dist ** 2
    centering = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centering @ squared @ centering
    values, vectors = np.linalg.eigh(gram)
    order = np.argsort(values)[::-1]
    values = values[order]
    vectors = vectors[:, order]
    values = np.maximum(values[:dims], 0)
    return vectors[:, :dims] * np.sqrt(values)


def pattern_label(row: pd.Series) -> str:
    values = [str(row[col]) for col in ONSET_ORDER]
    n_full = sum(value == "全对立" for value in values)
    n_s23 = sum(value == "S2=S3" for value in values)
    n_s12 = sum(value == "S1=S2" for value in values)
    n_multi = sum(("S1=S2=S3" in value) or ("S0=S1，S2=S3" in value) or ("全合流" in value) for value in values)
    n_leap = sum("越级" in value for value in values)
    if n_leap:
        return "越级/断裂型"
    if n_full >= 4:
        return "保守分立型"
    if n_s12 >= 3:
        return "中段合并型"
    if n_s23 >= 4 and n_multi == 0:
        return "后段合并型"
    if n_s23 >= 3 and n_multi >= 1:
        return "扩展合流型"
    if n_multi >= 2:
        return "多元压缩型"
    return "混合过渡型"


def cluster_labels_by_profile(df: pd.DataFrame, cluster_col: str) -> dict[int, str]:
    labels = {}
    for cluster_id, group in df.groupby(cluster_col):
        labels[int(cluster_id)] = group["rule_macro_type"].value_counts().idxmax()
    return labels


def plot_map(df: pd.DataFrame, color_col: str, label_col: str, output: Path, title: str) -> None:
    plot_df = df.dropna(subset=["lat", "lon"]).copy()
    color_keys = list(dict.fromkeys(plot_df[color_col].astype(str)))
    color_map = {key: PALETTE[idx % len(PALETTE)] for idx, key in enumerate(color_keys)}

    fig, ax = plt.subplots(figsize=(10.5, 8))
    for color_key, group in plot_df.groupby(color_col, sort=False):
        label = str(group[label_col].iloc[0])
        ax.scatter(
            group["lon"],
            group["lat"],
            s=74,
            color=color_map[str(color_key)],
            edgecolor="white",
            linewidth=0.8,
            label=f"{label} ({len(group)})",
            alpha=0.92,
        )
    for _, row in plot_df.iterrows():
        ax.text(row["lon"] + 0.015, row["lat"] + 0.01, str(row["point_name"]), fontsize=6.4, alpha=0.82)
    ax.set_title(title, fontsize=15)
    ax.set_xlabel("经度")
    ax.set_ylabel("纬度")
    ax.grid(alpha=0.25, linewidth=0.6)
    ax.legend(loc="best", fontsize=8, frameon=True)
    fig.tight_layout()
    fig.savefig(output, dpi=240)
    plt.close(fig)


def plot_tiled_map(df: pd.DataFrame, color_col: str, label_col: str, output: Path, title: str) -> str | None:
    plot_df = df.dropna(subset=["lat", "lon"]).copy()
    color_keys = list(dict.fromkeys(plot_df[color_col].astype(str)))
    color_map = {key: PALETTE[idx % len(PALETTE)] for idx, key in enumerate(color_keys)}

    gdf = gpd.GeoDataFrame(
        plot_df,
        geometry=gpd.points_from_xy(plot_df["lon"], plot_df["lat"]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(10.8, 8.6))
    for color_key, group in gdf.groupby(color_col, sort=False):
        label = str(group[label_col].iloc[0])
        ax.scatter(
            group.geometry.x,
            group.geometry.y,
            s=76,
            color=color_map[str(color_key)],
            edgecolor="white",
            linewidth=0.9,
            label=f"{label} ({len(group)})",
            alpha=0.94,
            zorder=3,
        )
    for _, row in gdf.iterrows():
        ax.text(row.geometry.x + 1800, row.geometry.y + 1200, str(row["point_name"]), fontsize=6.3, alpha=0.85, zorder=4)

    tile_errors = []
    tile_loaded = False
    for source_name, source in TILE_SOURCES:
        try:
            ctx.add_basemap(ax, source=source, alpha=0.78, zorder=1)
            tile_loaded = True
            break
        except Exception as exc:
            tile_errors.append(f"{source_name}: {type(exc).__name__}: {exc}")

    if not tile_loaded:
        plt.close(fig)
        return " ; ".join(tile_errors)

    ax.set_title(title, fontsize=15)
    ax.set_axis_off()
    ax.legend(loc="best", fontsize=8, frameon=True)
    fig.tight_layout()
    fig.savefig(output, dpi=240)
    plt.close(fig)
    return None


def plot_strength_scatter(df: pd.DataFrame) -> None:
    plot_df = df.copy()
    label_col = "nbclust_display_label"
    color_col = "nbclust_cluster"
    color_keys = list(dict.fromkeys(plot_df[color_col].astype(str)))
    color_map = {key: PALETTE[idx % len(PALETTE)] for idx, key in enumerate(color_keys)}

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    for color_key, group in plot_df.groupby(color_col, sort=False):
        label = str(group[label_col].iloc[0])
        axes[0].scatter(group["avg_S0_S1"], group["avg_S2_S3"], color=color_map[str(color_key)], label=label, s=66, alpha=0.9)
        axes[1].scatter(group["avg_S1_S2"], group["avg_S2_S3"], color=color_map[str(color_key)], label=label, s=66, alpha=0.9)
    axes[0].set_xlabel("平均 S0-S1 合并强度")
    axes[0].set_ylabel("平均 S2-S3 合并强度")
    axes[1].set_xlabel("平均 S1-S2 合并强度")
    axes[1].set_ylabel("平均 S2-S3 合并强度")
    axes[0].set_title("低位 vs 后段")
    axes[1].set_title("中段 vs 后段")
    for ax in axes:
        ax.grid(alpha=0.25)
    axes[1].legend(fontsize=8, loc="best")
    fig.suptitle("连续合并强度聚类散点图", fontsize=15)
    fig.tight_layout()
    fig.savefig(STRENGTH_SCATTER_OUTPUT, dpi=240)
    plt.close(fig)


def plot_mds(df: pd.DataFrame) -> None:
    label_col = "pattern_k4_label"
    labels = list(dict.fromkeys(df[label_col].astype(str)))
    color_map = {label: PALETTE[idx % len(PALETTE)] for idx, label in enumerate(labels)}

    fig, ax = plt.subplots(figsize=(8.5, 7))
    for label, group in df.groupby(label_col, sort=False):
        ax.scatter(group["mds_x"], group["mds_y"], s=72, color=color_map[str(label)], edgecolor="white", linewidth=0.8, label=f"{label} ({len(group)})")
    for _, row in df.iterrows():
        ax.text(row["mds_x"] + 0.006, row["mds_y"] + 0.006, str(row["point_name"]), fontsize=6.4, alpha=0.8)
    ax.set_title("类别合并模式聚类：Hamming-MDS 投影", fontsize=15)
    ax.set_xlabel("MDS 1")
    ax.set_ylabel("MDS 2")
    ax.grid(alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(PATTERN_MDS_OUTPUT, dpi=240)
    plt.close(fig)


def run() -> None:
    set_chinese_font()
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    strength = clean_columns(pd.read_csv(STRENGTH_PATH))
    for col in ["point_name", "subbranch", "nbclust_cluster_label", "nbclust_display_label", "nbclust_method"]:
        strength[col] = strength[col].astype("string").str.strip()
    best_method = strength["nbclust_method"].iloc[0]
    best_k = int(strength["nbclust_k"].iloc[0])

    plot_map(
        strength,
        color_col="nbclust_cluster",
        label_col="nbclust_display_label",
        output=STRENGTH_MAP_OUTPUT,
        title=f"连续合并强度聚类地图纯净版（{best_method}, k={best_k}）",
    )
    tile_error = plot_tiled_map(
        strength,
        color_col="nbclust_cluster",
        label_col="nbclust_display_label",
        output=STRENGTH_TILE_MAP_OUTPUT,
        title=f"连续合并强度聚类地图含瓦片底图（{best_method}, k={best_k}）",
    )
    plot_strength_scatter(strength)

    main = clean_columns(pd.read_csv(MAINLAYER_PATH))
    coords = clean_columns(pd.read_csv(COORD_PATH))
    for col in ["point_id", "point_name", "onset_class", "三级分类(详细模式)"]:
        if col in main:
            main[col] = main[col].astype("string").str.strip()
    coords["point_name"] = coords["point_name"].astype("string").str.strip()

    pattern = (
        main.pivot_table(
            index=["point_id", "point_name"],
            columns="onset_class",
            values="三级分类(详细模式)",
            aggfunc="first",
        )
        .reset_index()
    )
    for onset in ONSET_ORDER:
        if onset not in pattern:
            pattern[onset] = "缺"
        pattern[onset] = pattern[onset].fillna("缺").astype(str)
    pattern = pattern.merge(coords[["point_name", "subbranch", "lat", "lon"]], on="point_name", how="left")
    pattern["rule_macro_type"] = pattern.apply(pattern_label, axis=1)

    x = pattern[ONSET_ORDER].to_numpy(dtype=str)
    for k in [3, 4, 5]:
        col = f"pattern_k{k}"
        pattern[col] = kmodes(x, k) + 1
        label_map = cluster_labels_by_profile(pattern, col)
        pattern[f"{col}_label"] = pattern[col].map(label_map)

    dist = hamming_distance_matrix(x)
    coords_2d = classical_mds(dist)
    pattern["mds_x"] = coords_2d[:, 0]
    pattern["mds_y"] = coords_2d[:, 1]
    pattern.to_csv(PATTERN_CLUSTER_OUTPUT, index=False, encoding="utf-8-sig")

    plot_map(
        pattern,
        color_col="pattern_k4",
        label_col="pattern_k4_label",
        output=PATTERN_MAP_OUTPUT,
        title="类别合并模式聚类地图（Hamming/k-modes, k=4）",
    )
    plot_mds(pattern)

    report = [
        "合并模式两类聚类图输出",
        "=" * 40,
        "",
        "说明：",
        "当前最优方案与原始 kmeans_k3 方案在聚类分配上是同一套结果。",
        "也就是说，nbclust_cluster == kmeans_k3；最优方法最后仍然选中了 kmeans / k=3。",
        "如果两张 k=3 图看起来不一样，原因不在聚类本身，而在可视化口径：",
        "1. 原始图按原始 cluster id (1/2/3) 着色，所以 C1、C2、C3 各有独立颜色。",
        "2. 后来的 nbclust 图一度按宏观标签着色；由于 C1 和 C3 都被粗标成 S2_S3_dominant，视觉上会并成同类色。",
        "3. 中途还发生过文件覆盖：merge_strength_k3_map.png 曾被新输出误占用，现已恢复原图。",
        "",
        f"连续合并强度聚类：使用 avg_S0_S1, avg_S1_S2, avg_S2_S3 三个均值，采用 NbClust 风格自动选优，当前最优为 {best_method} / k={best_k}。",
        f"- 地图：{STRENGTH_MAP_OUTPUT}",
        f"- 散点：{STRENGTH_SCATTER_OUTPUT}",
        "类别合并模式聚类：使用 K/M/P/Ø/TS 的三级合并模式，Hamming 距离，k-modes 聚类，图中采用 k=4。",
        f"- 地图：{PATTERN_MAP_OUTPUT}",
        f"- MDS：{PATTERN_MDS_OUTPUT}",
        f"- 聚类表：{PATTERN_CLUSTER_OUTPUT}",
        "",
        f"连续聚类最优方案摘要（{best_method} / k={best_k}）：",
    ]
    if tile_error is None:
        report.insert(12, f"- 瓦片底图版：{STRENGTH_TILE_MAP_OUTPUT}")
    else:
        report.insert(12, f"- 瓦片底图版：当前环境抓取失败；原因：{tile_error}")
    for label, group in strength.groupby("nbclust_display_label", sort=False):
        subcounts = " | ".join(f"{idx}({val})" for idx, val in group["subbranch"].value_counts().items())
        report.append(f"- {label}: {len(group)} 点；{subcounts}")
    report.extend(["", "类别模式聚类 k=4 摘要："])
    for label, group in pattern.groupby("pattern_k4_label", sort=False):
        subcounts = " | ".join(f"{idx}({val})" for idx, val in group["subbranch"].value_counts().items())
        report.append(f"- {label}: {len(group)} 点；{subcounts}")
    COMPARISON_REPORT_OUTPUT.write_text("\n".join(report), encoding="utf-8")

    print(f"已输出连续强度聚类地图：{STRENGTH_MAP_OUTPUT}")
    if tile_error is None:
        print(f"已输出连续强度聚类瓦片地图：{STRENGTH_TILE_MAP_OUTPUT}")
    else:
        print(f"连续强度聚类瓦片地图未生成：{tile_error}")
    print(f"已输出连续强度聚类散点图：{STRENGTH_SCATTER_OUTPUT}")
    print(f"已输出类别模式聚类地图：{PATTERN_MAP_OUTPUT}")
    print(f"已输出类别模式 MDS 图：{PATTERN_MDS_OUTPUT}")
    print(f"已输出类别模式聚类表：{PATTERN_CLUSTER_OUTPUT}")
    print(f"已输出比较报告：{COMPARISON_REPORT_OUTPUT}")


if __name__ == "__main__":
    run()
