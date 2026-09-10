"""Plot the geographical distribution of the k=3 main-layer chain clusters."""

from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLUSTER_FILE = PROJECT_ROOT / "data_clean" / "value_type" / "mainlayer_chain_clusters.csv"
SUMMARY_FILE = PROJECT_ROOT / "data_clean" / "value_type" / "mainlayer_chain_cluster_summary.csv"
COORD_FILE = PROJECT_ROOT / "data_dict" / "point_coords_master.csv"
JOINED_FILE = PROJECT_ROOT / "data_clean" / "value_type" / "mainlayer_chain_k3_geography.csv"
OUTPUT_FILE = PROJECT_ROOT / "figs" / "mainlayer" / "mainlayer_chain_k3_map.png"

CLUSTER_STYLE = {
    1: {
        "label": "o-o-u",
        "color": "#2878B5",
        "marker": "o",
    },
    2: {
        "label": "o-əu-u",
        "color": "#E45756",
        "marker": "^",
    },
    3: {
        "label": "o-u-u",
        "color": "#43A047",
        "marker": "s",
    },
}

# Only move labels that otherwise collide badly in the Shanghai–Suzhou core.
# Offsets are in screen points so they remain stable when the figure is resized.
LABEL_OFFSETS = {
    "宝山": (-22, 8),
    "嘉定城厢": (-42, -2),
    "金山朱泾": (-48, -8),
    "闵行": (-30, 5),
    "青浦商榻": (-48, 8),
    "上海市区": (7, -11),
    "松江镇": (-39, -9),
    "奉贤": (7, -10),
    "川沙浦东": (7, 8),
    "南汇惠南镇": (7, -10),
    "苏州城区": (-45, 8),
    "吴县光福镇": (-49, -9),
    "吴江芦墟": (-43, -10),
    "嘉善魏塘镇": (-53, -8),
    "枫泾镇": (7, 8),
    "嘉兴城区": (-42, -10),
    "萧山城厢": (-44, -10),
    "杭州城区": (-43, 8),
    "彭埠镇": (7, 7),
    "宁波市区": (-44, 7),
    "鄞县中区": (-44, -10),
}


def set_chinese_font() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    # Arial Unicode MS covers both Chinese and the IPA symbols used in the
    # representative chains; use Chinese-only fonts only as fallbacks.
    for name in ["Arial Unicode MS", "PingFang HK", "Heiti TC", "Songti SC", "SimHei"]:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_data() -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    clusters = pd.read_csv(CLUSTER_FILE)
    summary = pd.read_csv(SUMMARY_FILE)
    coords = pd.read_csv(COORD_FILE)

    for frame in (clusters, coords):
        frame["point_name"] = frame["point_name"].astype(str).str.strip()

    keep = [
        "point_id",
        "point_name",
        "cluster_k3",
        "representative_chain",
        "representative_chain_collapsed",
        "ordered_diphthong_pattern",
    ]
    joined = clusters[keep].merge(coords, on="point_name", how="left", validate="one_to_one")
    missing = joined.loc[joined[["lat", "lon"]].isna().any(axis=1), "point_name"].tolist()
    if missing:
        raise ValueError(f"这些方言点缺少坐标：{'、'.join(missing)}")
    if len(joined) != len(clusters):
        raise ValueError("聚类结果和坐标表的方言点数不一致")

    label_lookup = summary.set_index("cluster")["type_label"].to_dict()
    joined["cluster_label"] = joined["cluster_k3"].map(label_lookup)
    joined.sort_values(["cluster_k3", "point_id"]).to_csv(JOINED_FILE, index=False, encoding="utf-8-sig")

    gdf = gpd.GeoDataFrame(
        joined,
        geometry=gpd.points_from_xy(joined["lon"], joined["lat"]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)
    return gdf, summary


def add_basemap(ax: plt.Axes) -> str:
    providers = [
        ("Esri WorldPhysical", ctx.providers.Esri.WorldPhysical),
        ("CartoDB Voyager", ctx.providers.CartoDB.Voyager),
        ("OpenStreetMap", ctx.providers.OpenStreetMap.Mapnik),
    ]
    request_headers = {
        "user-agent": "wuyu-vowel-chain-research-map/1.0",
        "referer": "https://github.com/",
    }
    errors = []
    for name, provider in providers:
        try:
            # Zoom 7 is sufficient for this regional figure and greatly reduces
            # the number of remote tile requests, making rendering more robust.
            ctx.add_basemap(
                ax,
                source=provider,
                zoom=7,
                headers=request_headers,
                alpha=0.68,
                zorder=0,
            )
            return name
        except Exception as exc:  # pragma: no cover - depends on tile service availability
            errors.append(f"{name}: {exc}")
    raise RuntimeError("底图下载失败；" + " | ".join(errors))


def plot_map() -> None:
    set_chinese_font()
    gdf, summary = load_data()

    fig, ax = plt.subplots(figsize=(14.2, 13.4), facecolor="white")
    xpad, ypad = 42_000, 36_000
    ax.set_xlim(gdf.geometry.x.min() - xpad, gdf.geometry.x.max() + xpad)
    ax.set_ylim(gdf.geometry.y.min() - ypad, gdf.geometry.y.max() + ypad)
    add_basemap(ax)

    counts = gdf["cluster_k3"].value_counts().sort_index().to_dict()
    for cluster, style in CLUSTER_STYLE.items():
        subset = gdf[gdf["cluster_k3"] == cluster]
        ax.scatter(
            subset.geometry.x,
            subset.geometry.y,
            s=168,
            c=style["color"],
            marker=style["marker"],
            edgecolors="white",
            linewidths=1.55,
            alpha=0.96,
            zorder=3,
        )

    for row in gdf.itertuples():
        dx, dy = LABEL_OFFSETS.get(row.point_name, (6, 6))
        ha = "right" if dx < 0 else "left"
        va = "top" if dy < 0 else "bottom"
        label = ax.annotate(
            row.point_name,
            xy=(row.geometry.x, row.geometry.y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va=va,
            fontsize=7.4,
            color="#202124",
            zorder=4,
        )
        label.set_path_effects(
            [path_effects.withStroke(linewidth=2.2, foreground="white", alpha=0.9)]
        )

    handles = []
    for cluster, style in CLUSTER_STYLE.items():
        handles.append(
            Line2D(
                [0],
                [0],
                linestyle="none",
                marker=style["marker"],
                markersize=14,
                markerfacecolor=style["color"],
                markeredgecolor="white",
                markeredgewidth=1.4,
                label=style["label"],
            )
        )
    legend = ax.legend(
        handles=handles,
        title="k=3 主链类型",
        loc="lower left",
        bbox_to_anchor=(0.018, 0.018),
        frameon=True,
        framealpha=0.62,
        facecolor="white",
        borderpad=1.0,
        labelspacing=0.8,
        handletextpad=0.9,
        fontsize=14.2,
        title_fontsize=15.5,
    )
    legend.get_frame().set_edgecolor("#c8c8c8")

    ax.set_title("S0–S3 主链条 k=3 聚类的地理分布", fontsize=20, pad=19, weight="medium")
    ax.set_axis_off()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=250, bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)
    print(f"地图：{OUTPUT_FILE}")
    print(f"地理分类表：{JOINED_FILE}")
    print(f"点数：{len(gdf)}；分类：{counts}")


if __name__ == "__main__":
    plot_map()
