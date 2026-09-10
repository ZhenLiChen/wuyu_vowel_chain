from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
import textwrap

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data_raw" / "mainlayer_merge.csv"
OUTPUT_DIR = PROJECT_ROOT / "data_clean" / "value_type"
FIG_DIR = PROJECT_ROOT / "figs" / "merge_analysis"

PROFILE_OUTPUT = OUTPUT_DIR / "dialect_onset_merge_pattern_profiles.csv"
PNG_OUTPUT = FIG_DIR / "dialect_onset_merge_pattern_matrix.png"
PDF_OUTPUT = FIG_DIR / "dialect_onset_merge_pattern_matrix.pdf"

ONSET_ORDER = ["K", "M", "P", "TS", "Ø"]
DETAIL_COLUMN = "三级分类(详细模式)"

# Short cell labels keep all 22 profile columns readable. The legend retains
# the exact detailed-pattern labels used by the existing sunburst analysis.
PATTERN_STYLE = OrderedDict(
    [
        ("全对立", {"code": "全异", "fill": "#D9E2E1", "text": "#1F2933"}),
        ("S0=S1", {"code": "01", "fill": "#56B4E9", "text": "#102A43"}),
        ("S1=S2", {"code": "12", "fill": "#E69F00", "text": "#332300"}),
        ("S2=S3", {"code": "23", "fill": "#009E73", "text": "#FFFFFF"}),
        (
            "S0=S1，S2=S3",
            {"code": "01|23", "fill": "#0072B2", "text": "#FFFFFF"},
        ),
        ("S1=S2=S3", {"code": "123", "fill": "#CC79A7", "text": "#2B1223"}),
        (
            "S1=S3 [越级]",
            {"code": "13*", "fill": "#F0003C", "text": "#FFFFFF"},
        ),
    ]
)

SUPERSCRIPT = {
    1: "¹",
    2: "²",
    3: "³",
    4: "⁴",
    5: "⁵",
    6: "⁶",
    7: "⁷",
    8: "⁸",
    9: "⁹",
}


def configure_font() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    for name in [
        "PingFang SC",
        "Heiti SC",
        "Arial Unicode MS",
        "Microsoft YaHei",
        "SimHei",
    ]:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["ps.fonttype"] = 42


def load_mainlayer() -> pd.DataFrame:
    df = pd.read_csv(INPUT_PATH, dtype=str, encoding="utf-8-sig").fillna("")
    required = {"point_id", "point_name", "onset_class", DETAIL_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"mainlayer_merge.csv 缺少列：{sorted(missing)}")

    for column in required:
        df[column] = df[column].astype(str).str.strip()
    df = df[df["onset_class"].isin(ONSET_ORDER)].copy()

    duplicated = df.duplicated(["point_id", "onset_class"], keep=False)
    if duplicated.any():
        examples = df.loc[duplicated, ["point_id", "onset_class"]].head().to_dict("records")
        raise ValueError(f"存在重复的方言点×声母记录：{examples}")

    onset_counts = df.groupby("point_id")["onset_class"].nunique()
    invalid_counts = onset_counts[onset_counts.ne(len(ONSET_ORDER))]
    if not invalid_counts.empty:
        raise ValueError(f"以下方言点没有完整的五组声母记录：{invalid_counts.to_dict()}")

    unknown_patterns = sorted(set(df[DETAIL_COLUMN]) - set(PATTERN_STYLE))
    if unknown_patterns:
        raise ValueError(f"发现未配置的详细模式：{unknown_patterns}")
    return df


def build_profile_table(df: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        df.pivot(
            index=["point_id", "point_name"],
            columns="onset_class",
            values=DETAIL_COLUMN,
        )
        .reindex(columns=ONSET_ORDER)
        .reset_index()
        .sort_values("point_id")
        .reset_index(drop=True)
    )
    if pivot[ONSET_ORDER].isna().any().any():
        raise ValueError("模式矩阵存在缺失值")

    grouped_rows: list[dict[str, object]] = []
    for pattern_values, group in pivot.groupby(ONSET_ORDER, sort=False, dropna=False):
        group = group.sort_values("point_id")
        members = list(group[["point_id", "point_name"]].itertuples(index=False, name=None))
        representative_id, representative_name = members[0]
        row: dict[str, object] = {
            "representative_id": representative_id,
            "representative_name": representative_name,
            "point_count": len(members),
            "same_pattern_points": "、".join(name for _, name in members[1:]),
            "all_points": "、".join(name for _, name in members),
            "all_point_ids": "、".join(point_id for point_id, _ in members),
        }
        row.update(dict(zip(ONSET_ORDER, pattern_values)))
        row["merged_onset_count"] = sum(
            detail != "全对立" for detail in pattern_values
        )
        row["fully_distinct_onset_count"] = sum(
            detail == "全对立" for detail in pattern_values
        )
        row["has_leapfrog"] = any("越级" in detail for detail in pattern_values)
        grouped_rows.append(row)

    profiles = pd.DataFrame(grouped_rows).sort_values(
        [
            "has_leapfrog",
            "merged_onset_count",
            "point_count",
            "fully_distinct_onset_count",
            "representative_id",
        ],
        ascending=[True, False, False, True, True],
    )
    profiles = profiles.reset_index(drop=True)
    profiles.insert(0, "profile_id", [f"P{index:02d}" for index in range(1, len(profiles) + 1)])

    note_number = 0
    note_markers: list[str] = []
    for count in profiles["point_count"]:
        if int(count) > 1:
            note_number += 1
            note_markers.append(SUPERSCRIPT.get(note_number, f"[{note_number}]"))
        else:
            note_markers.append("")
    profiles.insert(4, "footnote_marker", note_markers)
    return profiles


def wrap_note(text: str, width: int = 44) -> str:
    return "\n".join(
        textwrap.wrap(
            text,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
        )
    )


def draw_matrix(profiles: pd.DataFrame) -> None:
    configure_font()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    n_profiles = len(profiles)
    figure_width = max(18.5, 0.78 * n_profiles + 2.8)
    fig = plt.figure(figsize=(figure_width, 9.5), facecolor="white")
    ax = fig.add_axes([0.055, 0.45, 0.925, 0.30])

    for column_index, profile in profiles.iterrows():
        for row_index, onset in enumerate(ONSET_ORDER):
            detail = str(profile[onset])
            style = PATTERN_STYLE[detail]
            is_leapfrog_cell = detail == "S1=S3 [越级]"
            ax.add_patch(
                Rectangle(
                    (column_index, row_index),
                    1,
                    1,
                    facecolor=style["fill"],
                    edgecolor="#850021" if is_leapfrog_cell else "white",
                    linewidth=3.0 if is_leapfrog_cell else 1.4,
                    zorder=3 if is_leapfrog_cell else 1,
                )
            )
            ax.text(
                column_index + 0.5,
                row_index + 0.5,
                style["code"],
                ha="center",
                va="center",
                color=style["text"],
                fontsize=9.4,
                fontweight="bold",
                zorder=4,
            )

        summary_fill = "#FFE3EA" if bool(profile["has_leapfrog"]) else "#EEF2F3"
        ax.add_patch(
            Rectangle(
                (column_index, 5.08),
                1,
                0.38,
                facecolor=summary_fill,
                edgecolor="white",
                linewidth=1.2,
                zorder=1,
            )
        )
        ax.text(
            column_index + 0.5,
            5.27,
            f"{int(profile['merged_onset_count'])}/{int(profile['fully_distinct_onset_count'])}",
            ha="center",
            va="center",
            fontsize=8.4,
            color="#9D0028" if bool(profile["has_leapfrog"]) else "#455A64",
            fontweight="bold",
            zorder=4,
        )

        if bool(profile["has_leapfrog"]):
            ax.add_patch(
                Rectangle(
                    (column_index, 0),
                    1,
                    5.46,
                    facecolor="none",
                    edgecolor="#F0003C",
                    linewidth=2.8,
                    zorder=5,
                )
            )

    previous_sort_group: tuple[bool, int] | None = None
    for column_index, profile in profiles.iterrows():
        sort_group = (bool(profile["has_leapfrog"]), int(profile["merged_onset_count"]))
        if previous_sort_group is not None and sort_group != previous_sort_group:
            ax.axvline(
                column_index,
                color="#F0003C" if sort_group[0] else "#78909C",
                linewidth=2.4,
                zorder=6,
            )
        previous_sort_group = sort_group

    ax.set_xlim(0, n_profiles)
    ax.set_ylim(5.55, 0)
    ax.set_yticks(
        [index + 0.5 for index in range(len(ONSET_ORDER))] + [5.27]
    )
    ax.set_yticklabels(
        ONSET_ORDER + ["合/异"], fontsize=11, fontweight="bold"
    )
    ax.tick_params(axis="y", length=0, pad=10)

    column_labels = []
    for profile in profiles.itertuples(index=False):
        marker = profile.footnote_marker
        column_labels.append(
            f"{profile.profile_id}  {profile.representative_name}{marker}  "
            f"合{profile.merged_onset_count}/异{profile.fully_distinct_onset_count}  "
            f"n={profile.point_count}"
        )
    ax.set_xticks([index + 0.5 for index in range(n_profiles)])
    ax.set_xticklabels(
        column_labels,
        rotation=58,
        ha="left",
        va="bottom",
        rotation_mode="anchor",
        fontsize=8.6,
    )
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", length=0, pad=6)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(
        -0.55,
        -0.18,
        "声母组",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
    )

    fig.suptitle(
        "太湖片吴语主体层：各方言声母条件合并模式矩阵",
        x=0.515,
        y=0.972,
        fontsize=20,
        fontweight="bold",
    )
    fig.text(
        0.515,
        0.938,
        (
            f"统计口径与 sunburst 一致：82 个方言点 × 5 个声母组；"
            f"五组详细模式完全一致的方言合并为一列，共 {n_profiles} 套组合；"
            "排序：合并声组数↓ → 同型点数↓ → 全异声组数↑，含 13* 者置末"
        ),
        ha="center",
        va="top",
        fontsize=10.5,
        color="#455A64",
    )

    legend_handles = [
        Patch(
            facecolor=style["fill"],
            edgecolor="none",
            label=f"{style['code']}  {detail}",
        )
        for detail, style in PATTERN_STYLE.items()
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.515, 0.405),
        ncol=len(legend_handles),
        frameon=False,
        fontsize=9,
        handlelength=1.2,
        handleheight=1.0,
        columnspacing=1.6,
    )

    fig.text(
        0.055,
        0.352,
        (
            "脚注：n 为该列覆盖的方言点数；代表点按 point_id 最小者选取。"
            "合/异行依次给出发生合并与全异的声母组数；脚注仅列出同型点。"
        ),
        ha="left",
        va="top",
        fontsize=9.2,
        color="#455A64",
    )

    notes = []
    repeated = profiles[profiles["point_count"].gt(1)]
    for profile in repeated.itertuples(index=False):
        note = (
            f"{profile.footnote_marker} {profile.representative_name}（{profile.profile_id}）同型点："
            f"{profile.same_pattern_points}。"
        )
        notes.append(wrap_note(note))

    # Distribute long notes across three balanced columns so the names remain
    # readable without colliding or forcing a disproportionately tall canvas.
    note_columns: list[list[str]] = [[], [], []]
    column_line_counts = [0, 0, 0]
    for note in notes:
        target = min(range(3), key=column_line_counts.__getitem__)
        note_columns[target].append(note)
        column_line_counts[target] += note.count("\n") + 3
    for x, column_notes in zip([0.055, 0.375, 0.695], note_columns):
        fig.text(
            x,
            0.312,
            "\n\n".join(column_notes),
            ha="left",
            va="top",
            fontsize=8.2,
            linespacing=1.2,
        )

    fig.text(
        0.98,
        0.16,
        "数据：data_raw/mainlayer_merge.csv｜详细模式：三级分类(详细模式)",
        ha="right",
        va="bottom",
        fontsize=8.3,
        color="#607D8B",
    )

    fig.savefig(PNG_OUTPUT, dpi=300, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    fig.savefig(PDF_OUTPUT, facecolor="white", bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_mainlayer()
    profiles = build_profile_table(df)
    profiles.to_csv(PROFILE_OUTPUT, index=False, encoding="utf-8-sig")
    draw_matrix(profiles)

    print(f"方言点：{df['point_id'].nunique()}")
    print(f"方言点×声母记录：{len(df)}")
    print(f"完整声母模式组合：{len(profiles)}")
    print(f"单例组合：{int(profiles['point_count'].eq(1).sum())}")
    print(f"组合表：{PROFILE_OUTPUT}")
    print(f"PNG：{PNG_OUTPUT}")
    print(f"PDF：{PDF_OUTPUT}")


if __name__ == "__main__":
    main()
