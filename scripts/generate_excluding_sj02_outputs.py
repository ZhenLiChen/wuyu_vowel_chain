"""Generate a parallel result bundle with SJ02 excluded.

This script writes a parallel bundle below ``data_clean/excluding_SJ02`` and
``figs/excluding_SJ02``. Canonical point inputs also exclude SJ02 when its raw
file is stored outside ``data_raw/points``.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mpl-cache")

import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from analyze_merge_strength_clusters import (
    FEATURE_COLS,
    K_RANGE,
    METHODS,
    evaluate_solution,
    generate_labels,
    pairwise_distances,
    rank_solutions,
    zscore_matrix,
)
import plot_s1_s3_type_tree as magemo_tree
from plot_dialect_map import draw_cached_terrain


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_POINT = "SJ02"
EXCLUDED_POINT_NAME = "泗泾"
DATA_OUT = PROJECT_ROOT / "data_clean" / "excluding_SJ02"
FIG_OUT = PROJECT_ROOT / "figs" / "excluding_SJ02"

RATES_INPUT = PROJECT_ROOT / "data_clean" / "merge_analysis" / "point_onset_merge_rates.csv"
COORD_INPUT = PROJECT_ROOT / "data_dict" / "point_coords_master.csv"
CHAIN_INPUT = PROJECT_ROOT / "data_clean" / "value_type" / "mainlayer_chain_clusters.csv"

CORE_ONSETS = ["K", "M", "P", "TS", "Ø"]
NT_ONSETS = ["N", "T"]
COLORS = {"C1": "#4C78A8", "C2": "#F58518", "C3": "#54A24B"}


def set_font() -> None:
    font_paths = [
        Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for font_path in font_paths:
        if font_path.exists():
            fm.fontManager.addfont(font_path)
            plt.rcParams["font.sans-serif"] = [fm.FontProperties(fname=font_path).get_name()]
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_coords() -> pd.DataFrame:
    coords = pd.read_csv(COORD_INPUT, encoding="utf-8-sig")
    coords.columns = [column.strip().lstrip("\ufeff") for column in coords.columns]
    coords = coords[coords["point_name"].astype(str).str.strip().ne(EXCLUDED_POINT_NAME)].copy()
    return coords.dropna(subset=["lat", "lon"])


def write_merge_rates() -> tuple[pd.DataFrame, pd.DataFrame]:
    rates = pd.read_csv(RATES_INPUT, encoding="utf-8-sig")
    rates.columns = [column.strip().lstrip("\ufeff") for column in rates.columns]
    for column in ["point_id", "point_name", "onset_class"]:
        rates[column] = rates[column].astype("string").str.strip()
    rates = rates[rates["point_id"].astype(str).str.strip().ne(EXCLUDED_POINT)].copy()

    summary = (
        rates.groupby("onset_class", dropna=False)
        .agg(
            mean_merge_S1_S2=("merge_S1_S2", "mean"),
            mean_merge_S2_S3=("merge_S2_S3", "mean"),
            valid_points_S1_S2=("merge_S1_S2", "count"),
            valid_points_S2_S3=("merge_S2_S3", "count"),
        )
        .reset_index()
    )
    summary["overall_S1_S3_two_link_mean"] = np.where(
        summary["onset_class"].isin(CORE_ONSETS),
        summary[["mean_merge_S1_S2", "mean_merge_S2_S3"]].mean(axis=1),
        np.nan,
    )
    summary["NT_S2_S3_mean"] = np.where(
        summary["onset_class"].isin(NT_ONSETS), summary["mean_merge_S2_S3"], np.nan
    )
    summary["comparison_scope"] = np.select(
        [summary["onset_class"].isin(CORE_ONSETS), summary["onset_class"].isin(NT_ONSETS)],
        ["S1-S3_two_link_mean", "S2-S3_only"],
        default="unclassified",
    )
    summary = summary.sort_values(
        "overall_S1_S3_two_link_mean", ascending=False, na_position="last"
    )

    rates.to_csv(DATA_OUT / "point_onset_merge_rates_excluding_SJ02.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(DATA_OUT / "onset_merge_rate_summary_excluding_SJ02.csv", index=False, encoding="utf-8-sig")

    core = summary[summary["onset_class"].isin(CORE_ONSETS)].sort_values(
        "overall_S1_S3_two_link_mean", ascending=False
    )
    nt = summary[summary["onset_class"].isin(NT_ONSETS)].sort_values(
        "NT_S2_S3_mean", ascending=False
    )
    core_rank = " > ".join(
        f"{row.onset_class}({row.overall_S1_S3_two_link_mean:.3f})" for row in core.itertuples()
    )
    nt_rank = " > ".join(f"{row.onset_class}({row.NT_S2_S3_mean:.3f})" for row in nt.itertuples())
    lines = [
        "# 排除 SJ02 后的 merge rate",
        "",
        f"- 方言点数：{rates['point_id'].nunique()}",
        "- 核心总体值：仅计算 S1–S2 与 S2–S3，并将两个链段的声组均值等权平均。",
        "- T / N：只计算 S2–S3，单独排序。",
        "",
        f"**核心声组：{core_rank}**",
        "",
        "| 声组 | S1–S2 | S2–S3 | 总体值 |",
        "|:---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row.onset_class} | {row.mean_merge_S1_S2:.6f} | {row.mean_merge_S2_S3:.6f} | {row.overall_S1_S3_two_link_mean:.6f} |"
        for row in core.itertuples()
    )
    lines.extend(["", f"**T / N：{nt_rank}**", "", "| 声组 | S2–S3 | 有效点数 |", "|:---:|---:|---:|"])
    lines.extend(
        f"| {row.onset_class} | {row.NT_S2_S3_mean:.6f} | {int(row.valid_points_S2_S3)} |"
        for row in nt.itertuples()
    )
    (DATA_OUT / "merge_rate_results_excluding_SJ02.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rates, summary


def draw_topography(coords: pd.DataFrame) -> None:
    gdf = gpd.GeoDataFrame(
        coords, geometry=gpd.points_from_xy(coords["lon"], coords["lat"]), crs="EPSG:4326"
    ).to_crs(epsg=3857)
    fig, ax = plt.subplots(figsize=(12, 12))
    cmap = plt.get_cmap("tab10")
    for idx, (subbranch, group) in enumerate(gdf.groupby("subbranch", sort=False)):
        group.plot(
            ax=ax, color=cmap(idx), label=subbranch, markersize=80, edgecolor="white",
            linewidth=1, alpha=0.9, zorder=3,
        )
    draw_cached_terrain(ax)
    for row in gdf.itertuples():
        label = ax.text(row.geometry.x + 1500, row.geometry.y + 1500, row.point_name,
                        fontsize=8.2, fontweight="bold", zorder=4)
        label.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white", alpha=0.75)])
    ax.legend(
        title="吴语小片分类", loc="lower left", bbox_to_anchor=(0.018, 0.018),
        fontsize=13.5, title_fontsize=16, markerscale=1.55, framealpha=0.58,
        facecolor="white", edgecolor="#4B5563", fancybox=True, borderpad=1.0,
        labelspacing=0.72, handletextpad=0.8,
    )
    ax.set_title("吴语太湖片方言采样点地形地貌图（排除 SJ02）", fontsize=18, pad=20)
    ax.set_axis_off()
    fig.savefig(FIG_OUT / "wuyu_topography_map_large_legend_excluding_SJ02.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def cluster_strength(rates: pd.DataFrame, coords: pd.DataFrame) -> pd.DataFrame:
    summary = (
        rates.groupby(["point_id", "point_name"], dropna=False)
        .agg(
            avg_S0_S1=("merge_S0_S1", "mean"),
            avg_S1_S2=("merge_S1_S2", "mean"),
            avg_S2_S3=("merge_S2_S3", "mean"),
        )
        .reset_index()
        .merge(coords[["point_name", "subbranch", "lat", "lon"]], on="point_name", how="left")
    )
    x = zscore_matrix(summary[FEATURE_COLS].to_numpy(dtype=float))
    dist = pairwise_distances(x)
    solutions, labels_by_solution = [], {}
    for method in METHODS:
        for k in K_RANGE:
            labels = generate_labels(x, method, k)
            solutions.append({"method": method, "k": k, **evaluate_solution(x, dist, labels)})
            labels_by_solution[(method, k)] = labels
    ranked = rank_solutions(pd.DataFrame(solutions))
    best = ranked.iloc[0]
    method, k = str(best["method"]), int(best["k"])
    if k != 3:
        method, k = "kmeans", 3
    summary["source_cluster"] = labels_by_solution[(method, k)] + 1

    centers = summary.groupby("source_cluster")[FEATURE_COLS].mean()
    low_cluster = int(centers.mean(axis=1).idxmin())
    remaining = centers.drop(index=low_cluster)
    ge_mo_cluster = int((remaining["avg_S2_S3"] - remaining["avg_S1_S2"]).idxmax())
    ge_ma_cluster = int(next(idx for idx in remaining.index if idx != ge_mo_cluster))
    remap = {low_cluster: "C1", ge_mo_cluster: "C2", ge_ma_cluster: "C3"}
    names = {"C1": "分立型", "C2": "歌模合并主导型", "C3": "歌麻合并主导型"}
    summary["cluster"] = summary["source_cluster"].map(remap)
    summary["cluster_label"] = summary["cluster"].map(names)
    summary["method"] = method
    summary["k"] = k
    summary.to_csv(DATA_OUT / "continuous_merge_strength_clusters_excluding_SJ02.csv", index=False, encoding="utf-8-sig")

    gdf = gpd.GeoDataFrame(
        summary.dropna(subset=["lat", "lon"]),
        geometry=gpd.points_from_xy(summary.dropna(subset=["lat", "lon"])["lon"], summary.dropna(subset=["lat", "lon"])["lat"]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)
    fig, ax = plt.subplots(figsize=(12.5, 10))
    for cluster in ["C1", "C2", "C3"]:
        group = gdf[gdf["cluster"].eq(cluster)]
        ax.scatter(group.geometry.x, group.geometry.y, s=105, color=COLORS[cluster],
                   edgecolor="white", linewidth=1.1, alpha=0.94,
                   label=f"{cluster} {names[cluster]}（{len(group)}点）", zorder=3)
    for row in gdf.itertuples():
        ax.text(row.geometry.x + 1700, row.geometry.y + 1100, row.point_name,
                fontsize=6.8, alpha=0.86, zorder=4)
    draw_cached_terrain(ax)
    ax.set_title(f"连续合并强度聚类图（排除 SJ02；{method}, k={k}）", fontsize=18, pad=16)
    ax.set_axis_off()
    ax.legend(loc="lower left", fontsize=12.5, markerscale=1.2, framealpha=0.72,
              facecolor="white", edgecolor="#9CA3AF", borderpad=0.9, labelspacing=0.75)
    fig.savefig(FIG_OUT / "continuous_merge_strength_tile_map_excluding_SJ02.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    return summary


def draw_t1_t3_tree() -> pd.DataFrame:
    chains = pd.read_csv(CHAIN_INPUT, encoding="utf-8-sig")
    chains = chains[chains["point_id"].astype(str).str.strip().ne(EXCLUDED_POINT)].copy()
    labels = {
        1: "歌麻并位型",
        2: "歌位复元音型",
        3: "歌模并位型",
    }
    counts = chains["cluster_k3"].value_counts().reindex([1, 2, 3], fill_value=0)
    result = pd.DataFrame({
        "type": ["T1", "T2", "T3"],
        "cluster_k3": [1, 2, 3],
        "label": [labels[1], labels[2], labels[3]],
        "count": [int(counts[1]), int(counts[2]), int(counts[3])],
    })
    result["percent"] = result["count"] / len(chains) * 100
    result.to_csv(DATA_OUT / "mainlayer_T1_T2_T3_summary_excluding_SJ02.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(13.5, 7.6), facecolor="white")
    root_x, root_y, branch_x = 0.08, 0.5, 0.42
    ys = [0.76, 0.50, 0.24]
    ax.plot([0.25, branch_x], [root_y, root_y], color="#374151", lw=2)
    ax.plot([branch_x, branch_x], [min(ys), max(ys)], color="#374151", lw=2)
    ax.text(root_x, root_y, f"主体层主链\n{len(chains)}点 | 100%", ha="left", va="center",
            fontsize=16, fontweight="bold", color="#111827")
    for row, y, color in zip(result.itertuples(), ys, ["#D97706", "#7C3AED", "#2563EB"]):
        ax.plot([branch_x, 0.55], [y, y], color="#374151", lw=2)
        ax.plot([0.57, 0.57], [y - 0.035, y + 0.035], color=color, lw=5, solid_capstyle="round")
        ax.text(0.60, y, f"{row.type}  {row.label}\n{row.count}点 | {row.percent:.1f}%",
                ha="left", va="center", fontsize=15, color=color, linespacing=1.35)
    ax.set_title("主体层主链 T1–T3 一般树形图（排除 SJ02）", fontsize=21, pad=18, fontweight="bold")
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0.08, 0.92)
    ax.axis("off")
    fig.savefig(FIG_OUT / "mainlayer_T1_T2_T3_tree_excluding_SJ02.png", dpi=320, bbox_inches="tight")
    plt.close(fig)
    return result


def draw_s1_s3_magemo_tree() -> pd.DataFrame:
    """Recreate the canonical S1–S3 麻歌模 five-type tree without SJ02."""
    source = pd.read_csv(magemo_tree.INPUT_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    required = {"point_id", "point_name", "onset_class", "S1", "S2", "S3"}
    for column in required:
        source[column] = source[column].str.strip()
    source = source[source["point_id"].ne(EXCLUDED_POINT)].copy()
    source["type"] = source.apply(magemo_tree.classify_type, axis=1)
    source["type_formula"] = source["type"].map(
        lambda value: magemo_tree.TYPE_META[value]["formula"]
    )
    source["一级分类_S1_S3"] = source["type"].map(
        lambda value: magemo_tree.TYPE_META[value]["一级分类"]
    )
    source["二级分类_S1_S3"] = source["type"].map(
        lambda value: magemo_tree.TYPE_META[value]["二级分类"]
    )
    summary = magemo_tree.build_summary(source)

    detail_columns = [
        "point_id", "point_name", "onset_class", "S1", "S2", "S3", "type",
        "type_formula", "一级分类_S1_S3", "二级分类_S1_S3",
    ]
    source[detail_columns].to_csv(
        DATA_OUT / "s1_s3_magemo_type_assignments_excluding_SJ02.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary.to_csv(
        DATA_OUT / "s1_s3_magemo_type_summary_excluding_SJ02.csv",
        index=False,
        encoding="utf-8-sig",
        float_format="%.6f",
    )

    original_png, original_svg = magemo_tree.PNG_OUTPUT, magemo_tree.SVG_OUTPUT
    try:
        magemo_tree.PNG_OUTPUT = FIG_OUT / "s1_s3_magemo_type_tree_excluding_SJ02.png"
        magemo_tree.SVG_OUTPUT = FIG_OUT / "s1_s3_magemo_type_tree_excluding_SJ02.svg"
        magemo_tree.draw_tree(summary)
    finally:
        magemo_tree.PNG_OUTPUT, magemo_tree.SVG_OUTPUT = original_png, original_svg
    return summary


def main() -> None:
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    FIG_OUT.mkdir(parents=True, exist_ok=True)
    set_font()
    coords = load_coords()
    rates, rate_summary = write_merge_rates()
    draw_topography(coords)
    clusters = cluster_strength(rates, coords)
    tree = draw_t1_t3_tree()
    magemo = draw_s1_s3_magemo_tree()
    print(f"outputs: {DATA_OUT.relative_to(PROJECT_ROOT)} ; {FIG_OUT.relative_to(PROJECT_ROOT)}")
    print(f"points: rates={rates['point_id'].nunique()}, map={coords['point_name'].nunique()}, clusters={len(clusters)}, tree={tree['count'].sum()}")
    print(f"S1-S3 magemo observations: {int(magemo['count'].sum())}")
    print(rate_summary[["onset_class", "overall_S1_S3_two_link_mean", "NT_S2_S3_mean"]].to_string(index=False))


if __name__ == "__main__":
    main()
