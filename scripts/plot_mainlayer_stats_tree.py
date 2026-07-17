import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
FIGS_DIR = PROJECT_ROOT / "figs"
FIGS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_PATH = DATA_RAW / "mainlayer_merge.csv"
OUTPUT_PATH = FIGS_DIR / "mainlayer_stats_tree.png"


def set_chinese_font():
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    preferred_fonts = ["PingFang SC", "Heiti SC", "SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def format_label(name: str, count: int, total: int) -> str:
    return f"{name}\n{count} | {count / total * 100:.1f}%"


def build_tree(df: pd.DataFrame):
    total = len(df)

    l1_counts = df["一级分类"].value_counts()
    l2_counts = df["二级分类"].value_counts()
    l3_counts = df["三级分类(详细模式)"].value_counts()

    return {
        "label": f"主体层合并模式\n{total} | 100%",
        "x": 0.08,
        "y": 0.5,
        "color": "#111827",
        "children": [
            {
                "label": format_label("分立型 / 全对立", int(l1_counts.get("分立型", 0)), total),
                "x": 0.34,
                "y": 0.78,
                "color": "#5b8c85",
                "children": [],
            },
            {
                "label": format_label("合流型", int(l1_counts.get("合流型", 0)), total),
                "x": 0.34,
                "y": 0.34,
                "color": "#b45309",
                "children": [
                    {
                        "label": format_label("单一合并", int(l2_counts.get("单一合并", 0)), total),
                        "x": 0.58,
                        "y": 0.54,
                        "color": "#d97706",
                        "children": [
                            {
                                "label": format_label("S2=S3", int(l3_counts.get("S2=S3", 0)), total),
                                "x": 0.82,
                                "y": 0.70,
                                "color": "#e6a23c",
                                "children": [],
                            },
                            {
                                "label": format_label("S1=S2", int(l3_counts.get("S1=S2", 0)), total),
                                "x": 0.82,
                                "y": 0.56,
                                "color": "#e6a23c",
                                "children": [],
                            },
                            {
                                "label": format_label("S0=S1", int(l3_counts.get("S0=S1", 0)), total),
                                "x": 0.82,
                                "y": 0.42,
                                "color": "#e6a23c",
                                "children": [],
                            },
                            {
                                "label": format_label("S1=S3 [越级]", int(l3_counts.get("S1=S3 [越级]", 0)), total),
                                "x": 0.82,
                                "y": 0.28,
                                "color": "#9f1239",
                                "children": [],
                            },
                        ],
                    },
                    {
                        "label": format_label("多元合并", int(l2_counts.get("多元合并", 0)), total),
                        "x": 0.58,
                        "y": 0.14,
                        "color": "#92400e",
                        "children": [
                            {
                                "label": format_label("S0=S1，S2=S3", int(l3_counts.get("S0=S1，S2=S3", 0)), total),
                                "x": 0.82,
                                "y": 0.18,
                                "color": "#c2410c",
                                "children": [],
                            },
                            {
                                "label": format_label("S1=S2=S3", int(l3_counts.get("S1=S2=S3", 0)), total),
                                "x": 0.82,
                                "y": 0.06,
                                "color": "#c2410c",
                                "children": [],
                            },
                        ],
                    },
                ],
            },
        ],
    }


def draw_node(ax, node, parent=None):
    x = node["x"]
    y = node["y"]

    if parent is not None:
        px = parent["x"]
        py = parent["y"]
        mid_x = (px + x) / 2
        ax.plot([px, mid_x], [py, py], color=node["color"], lw=2.4, alpha=0.95)
        ax.plot([mid_x, mid_x], [py, y], color=node["color"], lw=2.4, alpha=0.95)
        ax.plot([mid_x, x], [y, y], color=node["color"], lw=2.4, alpha=0.95)

    ax.text(
        x,
        y,
        node["label"],
        ha="left",
        va="center",
        fontsize=15 if parent is None else 12,
        fontweight="bold" if parent is None else "normal",
        color=node["color"],
        bbox=dict(
            boxstyle="round,pad=0.35",
            facecolor=(1, 1, 1, 0.0),
            edgecolor=node["color"],
            linewidth=1.4,
        ),
    )

    for child in node["children"]:
        draw_node(ax, child, parent=node)


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"未找到输入文件：{INPUT_PATH}")

    set_chinese_font()
    df = pd.read_csv(INPUT_PATH, encoding="utf-8")
    for col in ["一级分类", "二级分类", "三级分类(详细模式)"]:
        df[col] = df[col].astype(str).str.strip()

    tree = build_tree(df)

    fig, ax = plt.subplots(figsize=(16, 9), facecolor=(1, 1, 1, 0))
    ax.set_facecolor((1, 1, 1, 0))
    draw_node(ax, tree)

    ax.set_xlim(0.02, 1.02)
    ax.set_ylim(-0.04, 0.96)
    ax.axis("off")

    plt.savefig(OUTPUT_PATH, dpi=320, bbox_inches="tight", transparent=True)
    plt.close(fig)
    print(f"✅ 主体层树状统计图已保存：{OUTPUT_PATH}")


if __name__ == "__main__":
    main()
