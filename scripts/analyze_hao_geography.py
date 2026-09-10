from pathlib import Path
import ssl

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
VALUE_DIR = PROJECT_ROOT / "data_clean" / "value_type"
DATA_DICT = PROJECT_ROOT / "data_dict"
FIGS_DIR = PROJECT_ROOT / "figs" / "monophthongization"

RELATION_PATH = VALUE_DIR / "point_hao_monophthong_relation.csv"
COORDS_PATH = DATA_DICT / "point_coords_master.csv"

SUBBRANCH_OUTPUT = VALUE_DIR / "hao_monophthong_by_subbranch.csv"
CLUSTER_OUTPUT = VALUE_DIR / "hao_geographic_cluster_summary.csv"
MAP_OUTPUT = FIGS_DIR / "hao_monophthong_geography_map.png"
SUBBRANCH_FIG_OUTPUT = FIGS_DIR / "hao_monophthong_subbranch_summary.png"


def set_chinese_font() -> None:
    available_fonts = [font.name for font in fm.fontManager.ttflist]
    preferred_fonts = [
        "PingFang SC",
        "Heiti SC",
        "SimHei",
        "Microsoft YaHei",
        "Arial Unicode MS",
    ]
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def classify_map_category(row: pd.Series) -> str:
    if row["hao_status"] == "diphthong_or_glide_only":
        return "未单音化"
    if row["hao_status"] == "mixed_mono_and_diphthong":
        return "混合"
    dominant = str(row["hao_dominant_value"])
    if dominant == "ɔ":
        return "ɔ单音化"
    if dominant == "ɒ":
        return "ɒ单音化"
    return "其他单音化"


def format_point_list(group: pd.DataFrame) -> str:
    return " | ".join(
        f"{row.point_id}:{row.point_name}" for row in group.itertuples(index=False)
    )


def format_counts(series: pd.Series) -> str:
    counts = series.value_counts()
    return " | ".join(f"{key}({int(value)})" for key, value in counts.items())


def load_data() -> pd.DataFrame:
    relation = pd.read_csv(RELATION_PATH)
    coords = pd.read_csv(COORDS_PATH)
    coords.columns = coords.columns.str.strip()
    for frame in [relation, coords]:
        for column in frame.columns:
            if frame[column].dtype == "object":
                frame[column] = frame[column].astype("string").str.strip()

    coords["lat"] = pd.to_numeric(coords["lat"], errors="coerce")
    coords["lon"] = pd.to_numeric(coords["lon"], errors="coerce")
    data = relation.merge(
        coords[["point_name", "lat", "lon"]],
        on="point_name",
        how="left",
    )
    data = data.dropna(subset=["lat", "lon"]).copy()
    data["map_category"] = data.apply(classify_map_category, axis=1)
    return data


def build_subbranch_summary(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subbranch, group in data.groupby("subbranch"):
        total_tokens = int(group["hao_total_token_count"].sum())
        mono_tokens = int(group["hao_monophthong_token_count"].sum())
        rows.append(
            {
                "subbranch": subbranch,
                "point_count": len(group),
                "hao_total_token_count": total_tokens,
                "hao_monophthong_token_count": mono_tokens,
                "weighted_monophthong_share": mono_tokens / total_tokens
                if total_tokens
                else 0,
                "monophthong_only_point_count": int(
                    (group["hao_status"] == "monophthong_only").sum()
                ),
                "mixed_point_count": int(
                    (group["hao_status"] == "mixed_mono_and_diphthong").sum()
                ),
                "diphthong_only_point_count": int(
                    (group["hao_status"] == "diphthong_or_glide_only").sum()
                ),
                "dominant_category_counts": format_counts(group["map_category"]),
                "dominant_value_counts": format_counts(group["hao_dominant_value"]),
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
        total_tokens = int(group["hao_total_token_count"].sum())
        mono_tokens = int(group["hao_monophthong_token_count"].sum())
        rows.append(
            {
                "map_category": category,
                "point_count": len(group),
                "hao_total_token_count": total_tokens,
                "hao_monophthong_token_count": mono_tokens,
                "weighted_monophthong_share": mono_tokens / total_tokens
                if total_tokens
                else 0,
                "mean_lat": group["lat"].mean(),
                "mean_lon": group["lon"].mean(),
                "lat_min": group["lat"].min(),
                "lat_max": group["lat"].max(),
                "lon_min": group["lon"].min(),
                "lon_max": group["lon"].max(),
                "subbranch_counts": format_counts(group["subbranch"]),
                "points": format_point_list(group.sort_values("point_id")),
            }
        )
    return pd.DataFrame(rows).sort_values(["point_count", "map_category"], ascending=[False, True])


def plot_map(data: pd.DataFrame) -> None:
    set_chinese_font()
    gdf = gpd.GeoDataFrame(
        data,
        geometry=gpd.points_from_xy(data["lon"], data["lat"]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)

    palette = {
        "ɔ单音化": "#2F80ED",
        "ɒ单音化": "#8E44AD",
        "其他单音化": "#27AE60",
        "混合": "#F2994A",
        "未单音化": "#EB5757",
    }
    marker_map = {
        "ɔ单音化": "o",
        "ɒ单音化": "s",
        "其他单音化": "^",
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
    for category, group in gdf.groupby("map_category"):
        sizes = 40 + group["hao_total_token_count"].clip(upper=120) * 1.9
        group.plot(
            ax=ax,
            marker=marker_map[category],
            color=palette[category],
            edgecolor="black",
            linewidth=0.8,
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

    emphasis_categories = {"未单音化", "混合", "ɒ单音化", "其他单音化"}
    for idx, row in enumerate(gdf.sort_values(["lat", "lon"]).itertuples(index=False)):
        dx, dy = label_offsets[idx % len(label_offsets)]
        is_emphasis = row.map_category in emphasis_categories
        label = row.point_name if not is_emphasis else f"{row.point_name}\n{row.hao_value_counts}"
        ax.text(
            row.geometry.x + dx,
            row.geometry.y + dy,
            label,
            fontsize=7 if not is_emphasis else 8,
            fontweight="normal" if not is_emphasis else "bold",
            color="#222222" if not is_emphasis else "black",
            ha="left" if dx >= 0 else "right",
            va="bottom" if dy >= 0 else "top",
            path_effects=[
                path_effects.withStroke(
                    linewidth=2.2 if not is_emphasis else 3,
                    foreground="white",
                    alpha=0.85,
                )
            ],
            zorder=4,
        )

    ax.set_title("豪韵单音化的地理分布：目标元音与未单音化点", fontsize=18, pad=20)
    ax.legend(title="豪韵状态", loc="lower left", frameon=True)
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
    ax.set_xlabel("豪韵单音化 token 占比")
    ax.set_title("各小片豪韵单音化程度，按 token 加权")

    for pos, row in zip(y, plot_df.itertuples(index=False)):
        label = (
            f"{row.weighted_monophthong_share:.2f}  "
            f"点={row.point_count}, 未单音化={row.diphthong_only_point_count}"
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


def run_analysis() -> None:
    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    data = load_data()
    subbranch_summary = build_subbranch_summary(data)
    cluster_summary = build_cluster_summary(data)

    subbranch_summary.to_csv(SUBBRANCH_OUTPUT, index=False, encoding="utf-8-sig")
    cluster_summary.to_csv(CLUSTER_OUTPUT, index=False, encoding="utf-8-sig")
    plot_map(data)
    plot_subbranch_summary(subbranch_summary)

    print(f"已生成小片汇总：{SUBBRANCH_OUTPUT}")
    print(f"已生成地理聚集汇总：{CLUSTER_OUTPUT}")
    print(f"已生成地图：{MAP_OUTPUT}")
    print(f"已生成小片图：{SUBBRANCH_FIG_OUTPUT}")


if __name__ == "__main__":
    run_analysis()
