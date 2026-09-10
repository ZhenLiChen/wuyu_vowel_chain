"""绘制连续合并强度聚类图副本（无底图、放大标记和图例）。"""

from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    PROJECT_ROOT
    / "data_clean"
    / "merge_analysis"
    / "point_merge_strength_clusters.csv"
)
OUTPUT_PATH = PROJECT_ROOT / "figs" / "merge_analysis" / "continuous_merge_strength_cluster_map.png"

# 原始 C3 是 S2–S3（歌模）主导，原始 C2 是 S1–S2（歌麻）主导。
# 为使新图的 C2/C3 名称与聚类中心一致，只在显示层重新编号，不修改源数据。
DISPLAY_CLUSTERS = [
    {
        "source_cluster": 1,
        "display_cluster": "C1",
        "name": "分立型",
        "color": "#4C78A8",
    },
    {
        "source_cluster": 3,
        "display_cluster": "C2",
        "name": "歌模合并主导型",
        "color": "#F58518",
    },
    {
        "source_cluster": 2,
        "display_cluster": "C3",
        "name": "歌麻合并主导型",
        "color": "#54A24B",
    },
]


def set_chinese_font() -> None:
    font_paths = [
        Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for font_path in font_paths:
        if font_path.exists():
            fm.fontManager.addfont(font_path)
            family = fm.FontProperties(fname=font_path).get_name()
            plt.rcParams["font.sans-serif"] = [family]
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_data() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"未找到聚类数据：{INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
    df.columns = [column.strip().lstrip("\ufeff") for column in df.columns]
    required = {"point_name", "lat", "lon", "nbclust_cluster"}
    missing_columns = sorted(required.difference(df.columns))
    if missing_columns:
        raise ValueError(f"聚类数据缺少字段：{', '.join(missing_columns)}")

    df = df.dropna(subset=["lat", "lon", "nbclust_cluster"]).copy()
    df["point_name"] = df["point_name"].astype(str).str.strip()
    df["nbclust_cluster"] = df["nbclust_cluster"].astype(int)
    expected = {item["source_cluster"] for item in DISPLAY_CLUSTERS}
    actual = set(df["nbclust_cluster"].unique())
    if actual != expected:
        raise ValueError(f"聚类编号不符合预期：实际 {sorted(actual)}，预期 {sorted(expected)}")
    return df


def plot_map(df: pd.DataFrame) -> None:
    set_chinese_font()
    fig, ax = plt.subplots(figsize=(13.2, 10.2), facecolor="white")
    ax.set_facecolor("white")

    for item in DISPLAY_CLUSTERS:
        group = df[df["nbclust_cluster"].eq(item["source_cluster"])]
        ax.scatter(
            group["lon"],
            group["lat"],
            s=165,
            color=item["color"],
            edgecolor="white",
            linewidth=1.35,
            alpha=0.94,
            label=(
                f"{item['display_cluster']} {item['name']}"
                f"（{len(group)}点）"
            ),
            zorder=3,
        )

    for row in df.itertuples():
        ax.text(
            row.lon + 0.015,
            row.lat + 0.01,
            row.point_name,
            fontsize=7.5,
            color="#202124",
            alpha=0.84,
            zorder=4,
        )

    ax.set_title("连续合并强度聚类图", fontsize=23, pad=18, fontweight="medium")
    ax.set_xlabel("经度", fontsize=18, labelpad=9)
    ax.set_ylabel("纬度", fontsize=18, labelpad=9)
    ax.tick_params(axis="both", which="major", labelsize=15, length=6, width=1.1)
    ax.grid(alpha=0.25, linewidth=0.75, zorder=0)

    legend = ax.legend(
        loc="lower left",
        fontsize=14.5,
        markerscale=1.25,
        frameon=True,
        framealpha=0.72,
        facecolor="white",
        edgecolor="#9CA3AF",
        borderpad=0.9,
        labelspacing=0.75,
        handletextpad=0.8,
    )
    legend.get_frame().set_linewidth(1.0)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    df = load_data()
    plot_map(df)
    counts = df["nbclust_cluster"].value_counts().sort_index().to_dict()
    print(f"地图副本：{OUTPUT_PATH}")
    print(f"点数：{len(df)}；原始聚类计数：{counts}")


if __name__ == "__main__":
    main()
