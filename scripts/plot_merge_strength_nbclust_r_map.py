"""Compare the current merge-strength map with the actual R/NbClust Ward.D2 map."""

from pathlib import Path
import math

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data_clean" / "merge_analysis" / "point_merge_strength_nbclust_r.csv"
OUTPUT_PATH = PROJECT_ROOT / "figs" / "merge_analysis" / "merge_strength_nbclust_r_comparison_map.png"

CLUSTER_ORDER = ["C1 低强度型", "C2 歌模合并主导型", "C3 歌麻合并主导型"]
COLORS = {
    "C1 低强度型": "#4C78A8",
    "C2 歌模合并主导型": "#F58518",
    "C3 歌麻合并主导型": "#54A24A",
}
CURRENT_LABELS = {
    1: "C1 低强度型",
    3: "C2 歌模合并主导型",
    2: "C3 歌麻合并主导型",
}


def set_chinese_font() -> None:
    font_paths = [
        Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for font_path in font_paths:
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))
            plt.rcParams["font.sans-serif"] = [fm.FontProperties(fname=str(font_path)).get_name()]
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_data() -> pd.DataFrame:
    data = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
    data.columns = [column.strip().lstrip("\ufeff") for column in data.columns]
    required = {
        "point_id", "point_name", "lat", "lon", "nbclust_cluster",
        "r_wardd2_cluster_label",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing required clustering fields: {sorted(missing)}")
    data = data.dropna(subset=["lat", "lon", "r_wardd2_cluster_label"]).copy()
    data["nbclust_cluster"] = pd.to_numeric(data["nbclust_cluster"], errors="raise").astype(int)
    data["current_label"] = data["nbclust_cluster"].map(CURRENT_LABELS)
    data["r_label"] = data["r_wardd2_cluster_label"].astype(str).str.strip()
    if data["current_label"].isna().any():
        raise ValueError("Current cluster IDs do not match the established display mapping.")
    if not set(data["r_label"]).issubset(set(CLUSTER_ORDER)):
        raise ValueError("Ward.D2 cluster labels differ from the expected 3-group map legend.")
    if data["point_id"].astype(str).str.strip().eq("SJ02").any():
        raise ValueError("SJ02 must remain excluded from this map.")
    return data


def draw_panel(ax: plt.Axes, data: pd.DataFrame, label_column: str, title: str) -> None:
    for label in CLUSTER_ORDER:
        group = data[data[label_column].eq(label)]
        ax.scatter(
            group["lon"], group["lat"], s=66, color=COLORS[label],
            edgecolor="white", linewidth=0.75, alpha=0.95,
            label=f"{label}（{len(group)}点）", zorder=3,
        )
    for row in data.itertuples():
        ax.annotate(
            row.point_name, (row.lon, row.lat), xytext=(4, 3),
            textcoords="offset points", fontsize=6.5, color="#202124", alpha=0.88,
        )
    ax.set_xlim(data["lon"].min() - 0.14, data["lon"].max() + 0.17)
    ax.set_ylim(data["lat"].min() - 0.12, data["lat"].max() + 0.10)
    ax.set_title(title, fontsize=15, pad=12)
    ax.set_xlabel("经度", fontsize=11)
    ax.set_ylabel("纬度", fontsize=11)
    ax.tick_params(labelsize=9)
    ax.grid(alpha=0.22, linewidth=0.6, zorder=0)
    ax.legend(loc="lower left", fontsize=9, framealpha=0.78, facecolor="white",
              edgecolor="#9CA3AF", borderpad=0.65, labelspacing=0.5)
    ax.set_aspect(1 / max(0.55, math.cos(math.radians(data["lat"].mean()))))


def main() -> None:
    set_chinese_font()
    data = load_data()
    fig, axes = plt.subplots(1, 2, figsize=(17, 9.5), facecolor="white")
    draw_panel(axes[0], data, "current_label", "当前结果：手工多指标比较 / k-means, k=3")
    draw_panel(axes[1], data, "r_label", "R NbClust：Ward.D2 / 多数投票, k=3")
    fig.suptitle("方言强度聚类对照（84 个点；不含泗泾）", fontsize=19, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PATH, dpi=260, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Comparison map: {OUTPUT_PATH}")
    print("Current groups:", data["current_label"].value_counts().to_dict())
    print("R Ward.D2 groups:", data["r_label"].value_counts().to_dict())


if __name__ == "__main__":
    main()
