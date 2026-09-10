"""绘制只基于 S1–S3（麻、歌、模）的五类型统计树。

统计来源与旭日图一致，均为 ``data_raw/mainlayer_merge.csv``。不同之处是本脚本
不让 S0（佳/皆）参与判定，只比较：S1=麻、S2=歌/戈、S3=模。
"""

from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data_raw" / "mainlayer_merge.csv"
VALUE_DIR = PROJECT_ROOT / "data_clean" / "value_type"
FIGS_DIR = PROJECT_ROOT / "figs" / "mainlayer"

DETAIL_OUTPUT = VALUE_DIR / "s1_s3_magemo_type_assignments.csv"
SUMMARY_OUTPUT = VALUE_DIR / "s1_s3_magemo_type_summary.csv"
PNG_OUTPUT = FIGS_DIR / "s1_s3_magemo_type_tree.png"
SVG_OUTPUT = FIGS_DIR / "s1_s3_magemo_type_tree.svg"

TYPE_ORDER = ["T1", "T2", "T3", "T4", "T5"]
TYPE_META = {
    "T1": {"formula": "歌≠麻≠模", "一级分类": "分立型", "二级分类": "分立"},
    "T2": {"formula": "歌=麻=模", "一级分类": "合流型", "二级分类": "全合并"},
    "T3": {"formula": "歌=模≠麻", "一级分类": "合流型", "二级分类": "单一合并"},
    "T4": {"formula": "歌=麻≠模", "一级分类": "合流型", "二级分类": "单一合并"},
    "T5": {"formula": "模=麻≠歌", "一级分类": "合流型", "二级分类": "单一合并"},
}

COLORS = {
    "root": "#111827",
    "branch": "#374151",
    "T1": "#4B6475",
    "T2": "#7C3AED",
    "T3": "#2563EB",
    "T4": "#D97706",
    "T5": "#C81E1E",
}


def set_chinese_font() -> None:
    """优先使用系统中文字体，并兼容无字体缓存的运行环境。"""
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


def classify_type(row: pd.Series) -> str:
    """按三项等值关系把一行唯一归入 T1–T5。"""
    ma = row["S1"]
    ge = row["S2"]
    mo = row["S3"]

    if ma == ge == mo:
        return "T2"
    if len({ma, ge, mo}) == 3:
        return "T1"
    if ge == mo:
        return "T3"
    if ge == ma:
        return "T4"
    if mo == ma:
        return "T5"
    raise AssertionError(f"无法归类的 S1–S3 组合：{ma!r}, {ge!r}, {mo!r}")


def load_and_classify() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"未找到旭日图数据源：{INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig", dtype=str).fillna("")
    required = {"point_id", "point_name", "onset_class", "S1", "S2", "S3"}
    missing_columns = sorted(required.difference(df.columns))
    if missing_columns:
        raise ValueError(f"数据源缺少字段：{', '.join(missing_columns)}")

    for column in required:
        df[column] = df[column].str.strip()

    missing_values = df[["S1", "S2", "S3"]].eq("").any(axis=1)
    if missing_values.any():
        bad = df.loc[missing_values, ["point_id", "onset_class", "S1", "S2", "S3"]]
        raise ValueError(f"有 {len(bad)} 行缺少 S1/S2/S3 音值，不能判定 T1–T5")

    df["type"] = df.apply(classify_type, axis=1)
    df["type_formula"] = df["type"].map(lambda value: TYPE_META[value]["formula"])
    df["一级分类_S1_S3"] = df["type"].map(lambda value: TYPE_META[value]["一级分类"])
    df["二级分类_S1_S3"] = df["type"].map(lambda value: TYPE_META[value]["二级分类"])
    return df


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    counts = df["type"].value_counts().reindex(TYPE_ORDER, fill_value=0)
    rows = []
    for type_name in TYPE_ORDER:
        count = int(counts[type_name])
        rows.append(
            {
                "type": type_name,
                "formula": TYPE_META[type_name]["formula"],
                "一级分类": TYPE_META[type_name]["一级分类"],
                "二级分类": TYPE_META[type_name]["二级分类"],
                "count": count,
                "percent_total": count / total * 100,
            }
        )
    return pd.DataFrame(rows)


def count_and_percent(summary: pd.DataFrame, types: list[str]) -> tuple[int, float]:
    selected = summary[summary["type"].isin(types)]
    count = int(selected["count"].sum())
    percent = float(selected["percent_total"].sum())
    return count, percent


def format_node(name: str, count: int, percent: float) -> str:
    return f"{name}\n{count} | {percent:.1f}%"


def draw_family_connector(
    ax: plt.Axes,
    parent_out_x: float,
    parent_y: float,
    bracket_x: float,
    child_in_x: float,
    child_ys: list[float],
) -> None:
    """用直角分支画出与参考图相近的树形括线。"""
    color = COLORS["branch"]
    line_width = 1.65
    ax.plot(
        [parent_out_x, bracket_x],
        [parent_y, parent_y],
        color=color,
        lw=line_width,
        solid_capstyle="round",
        zorder=1,
    )
    if len(child_ys) > 1:
        ax.plot(
            [bracket_x, bracket_x],
            [min(child_ys), max(child_ys)],
            color=color,
            lw=line_width,
            solid_capstyle="round",
            zorder=1,
        )
    for child_y in child_ys:
        ax.plot(
            [bracket_x, child_in_x],
            [child_y, child_y],
            color=color,
            lw=line_width,
            solid_capstyle="round",
            zorder=1,
        )


def draw_tree(summary: pd.DataFrame) -> None:
    total = int(summary["count"].sum())
    split_count, split_percent = count_and_percent(summary, ["T1"])
    merge_count, merge_percent = count_and_percent(summary, ["T2", "T3", "T4", "T5"])
    single_count, single_percent = count_and_percent(summary, ["T3", "T4", "T5"])
    full_count, full_percent = count_and_percent(summary, ["T2"])

    type_stats = summary.set_index("type")[["count", "percent_total"]].to_dict("index")

    y_root = 0.525
    y_split = 0.735
    y_merge = 0.315
    y_single = 0.455
    y_full = 0.145
    type_y = {"T1": y_split, "T3": 0.565, "T4": 0.455, "T5": 0.345, "T2": y_full}

    fig, ax = plt.subplots(figsize=(15.5, 8.5), facecolor="white")
    ax.set_facecolor("white")

    # 根节点 → 分立型 / 合流型
    draw_family_connector(ax, 0.205, y_root, 0.245, 0.275, [y_split, y_merge])
    # 分立型 → T1
    draw_family_connector(ax, 0.455, y_split, 0.515, 0.555, [type_y["T1"]])
    # 合流型 → 单一合并 / 全合并
    draw_family_connector(ax, 0.455, y_merge, 0.515, 0.555, [y_single, y_full])
    # 单一合并 → T3 / T4 / T5
    draw_family_connector(
        ax,
        0.725,
        y_single,
        0.785,
        0.825,
        [type_y["T3"], type_y["T4"], type_y["T5"]],
    )
    # 全合并 → T2
    draw_family_connector(ax, 0.725, y_full, 0.785, 0.825, [type_y["T2"]])

    ax.text(
        0.015,
        y_root,
        format_node("S1–S3\n麻・歌・模", total, 100.0),
        ha="left",
        va="center",
        fontsize=15,
        fontweight="bold",
        color=COLORS["root"],
        linespacing=1.28,
    )
    ax.text(
        0.285,
        y_split,
        format_node("分立型", split_count, split_percent),
        ha="left",
        va="center",
        fontsize=14,
        color=COLORS["root"],
        linespacing=1.35,
    )
    ax.text(
        0.285,
        y_merge,
        format_node("合流型", merge_count, merge_percent),
        ha="left",
        va="center",
        fontsize=14,
        color=COLORS["root"],
        linespacing=1.35,
    )
    ax.text(
        0.565,
        y_single,
        format_node("单一合并", single_count, single_percent),
        ha="left",
        va="center",
        fontsize=14,
        color=COLORS["root"],
        linespacing=1.35,
    )
    ax.text(
        0.565,
        y_full,
        format_node("全合并", full_count, full_percent),
        ha="left",
        va="center",
        fontsize=14,
        color=COLORS["root"],
        linespacing=1.35,
    )

    for type_name in ["T1", "T3", "T4", "T5", "T2"]:
        count = int(type_stats[type_name]["count"])
        percent = float(type_stats[type_name]["percent_total"])
        y = type_y[type_name]
        ax.plot(
            [0.835, 0.835],
            [y - 0.032, y + 0.032],
            color=COLORS[type_name],
            lw=4.2,
            solid_capstyle="round",
            zorder=2,
        )
        ax.text(
            0.85,
            y,
            format_node(f"{type_name}  {TYPE_META[type_name]['formula']}", count, percent),
            ha="left",
            va="center",
            fontsize=13.2,
            color=COLORS[type_name],
            linespacing=1.35,
        )

    ax.text(
        0.5,
        0.925,
        "麻—歌—模（S1–S3）五类型统计树",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=22,
        fontweight="bold",
        color=COLORS["root"],
    )
    ax.text(
        0.5,
        0.875,
        "统计单位：方言点 × 核心声组（K / M / P / TS / 零声母）；S0 不参与判定；百分比以全部观察为分母",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=10.8,
        color="#6B7280",
    )

    ax.set_xlim(0.0, 1.12)
    ax.set_ylim(0.02, 0.99)
    ax.axis("off")
    fig.savefig(PNG_OUTPUT, dpi=320, bbox_inches="tight", facecolor="white")
    fig.savefig(SVG_OUTPUT, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    set_chinese_font()
    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    classified = load_and_classify()
    summary = build_summary(classified)

    detail_columns = [
        "point_id",
        "point_name",
        "onset_class",
        "S1",
        "S2",
        "S3",
        "type",
        "type_formula",
        "一级分类_S1_S3",
        "二级分类_S1_S3",
    ]
    classified[detail_columns].to_csv(DETAIL_OUTPUT, index=False, encoding="utf-8-sig")
    summary.to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig", float_format="%.6f")
    draw_tree(summary)

    print(f"统计观察数：{len(classified)}（{classified['point_id'].nunique()} 点）")
    print(summary[["type", "formula", "count", "percent_total"]].to_string(index=False))
    print(f"明细表：{DETAIL_OUTPUT}")
    print(f"汇总表：{SUMMARY_OUTPUT}")
    print(f"PNG：{PNG_OUTPUT}")
    print(f"SVG：{SVG_OUTPUT}")


if __name__ == "__main__":
    main()
