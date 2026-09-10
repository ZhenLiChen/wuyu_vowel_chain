from __future__ import annotations

import math
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VALUE_DIR = PROJECT_ROOT / "data_clean" / "value_type"
FIGS_DIR = PROJECT_ROOT / "figs" / "aco"

VALUE_CLASSIFICATION = VALUE_DIR / "s0_s3_split_value_classification.csv"
SUPPORT_OUTPUT = VALUE_DIR / "ant_colony_core_split_support.csv"

TOPOLOGY_FIG = FIGS_DIR / "ant_colony_vowel_topology.png"
PHEROMONE_FIG = FIGS_DIR / "ant_colony_split_pheromone_support.png"
MECHANISM_FIG = FIGS_DIR / "ant_colony_chain_mechanism.png"

CORE_SPLIT_VALUES = ["əu", "əɯ", "ou", "ɤɯ", "ʌɯ", "ʌɤ"]
SPLIT_SOURCE = {
    "əu": "u",
    "əɯ": "ə",
    "ou": "o",
    "ɤɯ": "ɤ",
    "ʌɯ": "ʌ",
    "ʌɤ": "ʌ",
}

NODE_POS = {
    "a": (0.6, 0.8),
    "ɑ": (1.7, 0.9),
    "ʌ": (2.45, 1.9),
    "ɔ": (2.9, 2.25),
    "o": (3.12, 3.1),
    "ɷ": (3.18, 3.48),
    "u": (3.22, 3.9),
    "ɤ": (2.45, 3.1),
    "ɯ": (2.5, 3.9),
    "ə": (1.8, 2.55),
    "ou": (4.15, 3.12),
    "əu": (4.45, 3.9),
    "əɯ": (3.85, 2.55),
    "ɤɯ": (3.72, 3.55),
    "ʌɯ": (3.72, 2.15),
    "ʌɤ": (3.62, 1.75),
}


def set_chinese_font() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    preferred = [
        "Arial Unicode MS",
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Songti SC",
        "SimHei",
        "Microsoft YaHei",
        "DejaVu Sans",
    ]
    plt.rcParams["font.sans-serif"] = [font for font in preferred if font in available]
    plt.rcParams["axes.unicode_minus"] = False


def load_support() -> pd.DataFrame:
    if not VALUE_CLASSIFICATION.exists():
        raise FileNotFoundError(f"缺少输入文件：{VALUE_CLASSIFICATION}")
    df = pd.read_csv(VALUE_CLASSIFICATION)
    support = (
        df[df["phonetic"].isin(CORE_SPLIT_VALUES)]
        .loc[:, ["phonetic", "split_category", "token_count", "point_count", "slot_counts"]]
        .copy()
    )
    support["source_node"] = support["phonetic"].map(SPLIT_SOURCE)
    support["support_rank"] = support["token_count"].rank(ascending=False, method="first")
    support = support.sort_values("token_count", ascending=False).reset_index(drop=True)
    return support


def token_lookup(support: pd.DataFrame) -> dict[str, int]:
    return dict(zip(support["phonetic"], support["token_count"]))


def width_from_tokens(tokens: int, max_tokens: int) -> float:
    if max_tokens <= 0:
        return 1.0
    return 1.1 + 6.2 * math.sqrt(tokens / max_tokens)


def draw_arrow(
    ax,
    start: str,
    end: str,
    color: str,
    linewidth: float,
    alpha: float = 1.0,
    style: str = "-|>",
    rad: float = 0.0,
    zorder: int = 2,
) -> None:
    x1, y1 = NODE_POS[start]
    x2, y2 = NODE_POS[end]
    arrow = patches.FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=14,
        linewidth=linewidth,
        color=color,
        alpha=alpha,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=20,
        shrinkB=22,
        zorder=zorder,
    )
    ax.add_patch(arrow)


def draw_node(
    ax,
    name: str,
    face: str,
    edge: str,
    radius: float = 0.13,
    fontsize: int = 18,
    text_color: str = "#1f2933",
    zorder: int = 4,
) -> None:
    x, y = NODE_POS[name]
    circle = patches.Circle(
        (x, y),
        radius,
        facecolor=face,
        edgecolor=edge,
        linewidth=1.6,
        zorder=zorder,
    )
    ax.add_patch(circle)
    ax.text(
        x,
        y,
        name,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=text_color,
        zorder=zorder + 1,
    )


def plot_topology(support: pd.DataFrame) -> None:
    set_chinese_font()
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    support_tokens = token_lookup(support)
    max_tokens = max(support_tokens.values())

    fig, ax = plt.subplots(figsize=(12, 7.5), facecolor="#f7f7f2")
    ax.set_facecolor("#f7f7f2")
    ax.set_xlim(0.15, 4.9)
    ax.set_ylim(0.35, 4.35)
    ax.axis("off")

    ax.text(0.18, 4.22, "S0-S3 后元音链的蚁群拓扑", fontsize=24, weight="bold", color="#1f2933")
    ax.text(
        0.18,
        4.02,
        "节点是元音状态；箭头是可选音变边；粗线表示当前数据支持量更高的信息素路径。",
        fontsize=13,
        color="#4b5563",
    )

    # Vowel chart guide.
    ax.annotate("高", xy=(0.22, 4.0), xytext=(0.22, 4.0), fontsize=11, color="#6b7280")
    ax.annotate("低", xy=(0.22, 0.75), xytext=(0.22, 0.75), fontsize=11, color="#6b7280")
    ax.annotate("前", xy=(0.5, 0.42), xytext=(0.5, 0.42), fontsize=11, color="#6b7280")
    ax.annotate("后", xy=(3.18, 0.42), xytext=(3.18, 0.42), fontsize=11, color="#6b7280")
    ax.plot([0.35, 3.35], [0.6, 0.6], color="#d5d0c7", linewidth=1.0)
    ax.plot([0.35, 0.35], [0.6, 4.05], color="#d5d0c7", linewidth=1.0)

    # Main chain and parallel branches.
    for start, end in [("a", "ɑ"), ("ɑ", "ɔ"), ("ɔ", "o"), ("o", "ɷ"), ("ɷ", "u")]:
        draw_arrow(ax, start, end, "#00796b", 3.0, alpha=0.95)
    draw_arrow(ax, "ɔ", "ʌ", "#6f8f3a", 1.7, alpha=0.8, rad=-0.12)
    draw_arrow(ax, "o", "ɤ", "#6f8f3a", 1.7, alpha=0.8, rad=0.1)
    draw_arrow(ax, "ɤ", "ɯ", "#6f8f3a", 1.7, alpha=0.8)
    draw_arrow(ax, "ʌ", "ə", "#9aa0a6", 1.2, alpha=0.65, rad=0.18)

    # Split edges with pheromone-like widths.
    split_color = "#d55e00"
    edge_map = [("u", "əu"), ("ə", "əɯ"), ("o", "ou"), ("ɤ", "ɤɯ"), ("ʌ", "ʌɯ"), ("ʌ", "ʌɤ")]
    for start, end in edge_map:
        draw_arrow(
            ax,
            start,
            end,
            split_color,
            width_from_tokens(support_tokens.get(end, 1), max_tokens),
            alpha=0.82,
            rad=0.08 if end != "ʌɤ" else -0.15,
            zorder=1,
        )

    # Nodes.
    for node in ["a", "ɑ", "ɔ", "o", "ɷ", "u"]:
        draw_node(ax, node, "#e9f5ef", "#00796b")
    for node in ["ɤ", "ɯ", "ʌ"]:
        draw_node(ax, node, "#eef3df", "#6f8f3a")
    draw_node(ax, "ə", "#eeeeee", "#9aa0a6")
    for node in CORE_SPLIT_VALUES:
        draw_node(ax, node, "#fff0e7", "#d55e00", radius=0.15, fontsize=16)

    ax.text(0.7, 0.52, "单元音链移：a > ɑ > ɔ > o > ɷ > u", fontsize=12, color="#00796b")
    ax.text(3.1, 4.18, "裂化入口", fontsize=12, color="#d55e00")
    ax.text(1.05, 2.52, "ə：中央化节点", fontsize=11, color="#6b7280")
    ax.text(2.15, 3.78, "ɤ/ɯ：后不圆唇平行链", fontsize=11, color="#5c6f24")
    ax.text(2.58, 1.52, "ʌ：纳入后元音链", fontsize=11, color="#5c6f24")

    # Excluded panel.
    panel = patches.FancyBboxPatch(
        (0.43, 3.04),
        1.26,
        0.62,
        boxstyle="round,pad=0.03,rounding_size=0.05",
        facecolor="#f1f1ed",
        edgecolor="#c9c4bb",
        linewidth=1.0,
        zorder=0,
    )
    ax.add_patch(panel)
    ax.text(0.5, 3.48, "暂不入模", fontsize=11, weight="bold", color="#4b5563")
    ax.text(0.5, 3.31, "au / ao / aɤ", fontsize=10.5, color="#4b5563")
    ax.text(0.5, 3.15, "yo / yɑ / øy / uo / ua / uE", fontsize=10.5, color="#4b5563")

    fig.tight_layout()
    fig.savefig(TOPOLOGY_FIG, dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_pheromone_support(support: pd.DataFrame) -> None:
    set_chinese_font()
    plot_df = support.sort_values("token_count", ascending=True).copy()
    colors = ["#d55e00" if value == "əu" else "#009e73" for value in plot_df["phonetic"]]

    fig, ax = plt.subplots(figsize=(10.5, 6.4), facecolor="#f7f7f2")
    ax.set_facecolor("#f7f7f2")
    bars = ax.barh(plot_df["phonetic"], plot_df["token_count"], color=colors, height=0.58)
    fig.suptitle("核心裂化路径的信息素支持", fontsize=22, weight="bold", color="#1f2933", y=0.97)
    fig.text(
        0.12,
        0.91,
        "把 token 支持量当作 ACO 的初始信息素强度；əu 是主通道，əɯ/ɤɯ/ʌɯ/ʌɤ 是 əu 型邻近变体，ou 是 o 位链上裂化。",
        fontsize=11.5,
        color="#4b5563",
        ha="left",
        va="center",
    )
    ax.set_xlabel("当前数据中的 token 支持量", fontsize=12)
    ax.set_ylabel("裂化音值", fontsize=12)
    ax.grid(axis="x", color="#dedbd2", linewidth=1, alpha=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", length=0, labelsize=12)

    for bar, row in zip(bars, plot_df.itertuples(index=False)):
        label = f"{int(row.token_count)} tokens, {int(row.point_count)} 点"
        ax.text(
            bar.get_width() + 22,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            ha="left",
            fontsize=11,
            color="#374151",
        )

    ax.set_xlim(0, max(plot_df["token_count"]) * 1.2)
    fig.subplots_adjust(top=0.80, bottom=0.14, left=0.12, right=0.94)
    fig.savefig(PHEROMONE_FIG, dpi=240, bbox_inches="tight")
    plt.close(fig)


def rounded_label(ax, x: float, y: float, text: str, face: str, edge: str, width: float = 0.76) -> None:
    box = patches.FancyBboxPatch(
        (x - width / 2, y - 0.18),
        width,
        0.36,
        boxstyle="round,pad=0.03,rounding_size=0.06",
        facecolor=face,
        edgecolor=edge,
        linewidth=1.2,
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=18, color="#1f2933")


def plot_chain_mechanism(support: pd.DataFrame) -> None:
    set_chinese_font()
    support_tokens = token_lookup(support)
    fig, ax = plt.subplots(figsize=(12.5, 5.8), facecolor="#f7f7f2")
    ax.set_facecolor("#f7f7f2")
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.8)

    ax.text(0.3, 4.45, "蚁群模拟的结果展示方式", fontsize=23, weight="bold", color="#1f2933")
    ax.text(
        0.3,
        4.16,
        "第一层看单元音如何沿后元音链移动；第二层看哪些位置最容易进入 əu 型裂化。",
        fontsize=12.5,
        color="#4b5563",
    )

    chain = ["a", "ɑ", "ɔ", "o", "ɷ", "u"]
    x_positions = [0.8, 2.0, 3.2, 4.4, 5.3, 6.2]
    for x, value in zip(x_positions, chain):
        rounded_label(ax, x, 3.1, value, "#e9f5ef", "#00796b")
    for x1, x2 in zip(x_positions[:-1], x_positions[1:]):
        ax.annotate(
            "",
            xy=(x2 - 0.43, 3.1),
            xytext=(x1 + 0.43, 3.1),
            arrowprops=dict(arrowstyle="-|>", color="#00796b", linewidth=2.5),
        )
    ax.text(2.9, 3.62, "单元音链移", fontsize=13, color="#00796b", weight="bold")

    rounded_label(ax, 8.1, 3.1, "əu", "#fff0e7", "#d55e00")
    ax.annotate(
        "",
        xy=(7.68, 3.1),
        xytext=(6.62, 3.1),
        arrowprops=dict(arrowstyle="-|>", color="#d55e00", linewidth=5.5),
    )
    ax.text(6.9, 3.62, f"裂化入口：əu {support_tokens.get('əu', 0)} tokens", fontsize=13, color="#d55e00", weight="bold")

    neighbor_y = 1.95
    neighbors = [("ou", "o 位链上裂化"), ("əɯ", "中央化邻近"), ("ɤɯ", "后不圆唇邻近"), ("ʌɯ", "ʌ 邻近"), ("ʌɤ", "ʌ 邻近")]
    neighbor_x = [3.8, 5.05, 6.25, 7.45, 8.65]
    for (value, label), x in zip(neighbors, neighbor_x):
        rounded_label(ax, x, neighbor_y, value, "#fff0e7", "#d55e00", width=0.72)
        ax.text(x, neighbor_y - 0.45, f"{support_tokens.get(value, 0)}", ha="center", fontsize=12, color="#374151")
        ax.text(x, neighbor_y - 0.72, label, ha="center", fontsize=9.8, color="#6b7280")
    ax.text(0.78, 1.95, "邻近裂化变体", fontsize=13, color="#d55e00", weight="bold")
    ax.plot([2.15, 9.15], [2.45, 2.45], color="#d55e00", linewidth=1.1, alpha=0.35)

    excluded = patches.FancyBboxPatch(
        (0.55, 0.42),
        8.9,
        0.62,
        boxstyle="round,pad=0.04,rounding_size=0.07",
        facecolor="#eeeeea",
        edgecolor="#c9c4bb",
        linewidth=1.1,
    )
    ax.add_patch(excluded)
    ax.text(0.78, 0.78, "暂不进入第一版模拟：", fontsize=12, weight="bold", color="#4b5563")
    ax.text(
        2.4,
        0.78,
        "au / ao / aɤ     yo / yɑ / øy / uo / ua / uE     ai / ɛi / æi / ɔi",
        fontsize=12,
        color="#4b5563",
    )

    fig.tight_layout()
    fig.savefig(MECHANISM_FIG, dpi=240, bbox_inches="tight")
    plt.close(fig)


def run() -> None:
    FIGS_DIR.mkdir(parents=True, exist_ok=True)
    support = load_support()
    support.to_csv(SUPPORT_OUTPUT, index=False, encoding="utf-8-sig")
    plot_topology(support)
    plot_pheromone_support(support)
    plot_chain_mechanism(support)
    print(f"已生成核心裂化支持表：{SUPPORT_OUTPUT}")
    print(f"已生成拓扑图：{TOPOLOGY_FIG}")
    print(f"已生成信息素支持图：{PHEROMONE_FIG}")
    print(f"已生成链移-裂化机制图：{MECHANISM_FIG}")


if __name__ == "__main__":
    run()
