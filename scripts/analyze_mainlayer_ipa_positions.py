from __future__ import annotations

from pathlib import Path
import unicodedata

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import font_manager
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data_raw" / "mainlayer_merge.csv"
VALUE_DIR = PROJECT_ROOT / "data_clean" / "value_type"
FIG_DIR = PROJECT_ROOT / "figs" / "mainlayer"
PDF_DIR = PROJECT_ROOT / "output" / "pdf"

VALUE_OUTPUT = VALUE_DIR / "mainlayer_ipa_value_positions.csv"
POINT_OUTPUT = VALUE_DIR / "point_mainlayer_ipa_major_patterns.csv"
PATTERN_OUTPUT = VALUE_DIR / "mainlayer_ipa_major_pattern_summary.csv"
UNPLACED_OUTPUT = VALUE_DIR / "mainlayer_ipa_unplaced_values.csv"
OVERVIEW_OUTPUT = FIG_DIR / "mainlayer_ipa_slot_overview.png"
ATLAS_OUTPUT = PDF_DIR / "mainlayer_ipa_point_atlas.pdf"

SLOTS = ["S0", "S1", "S2", "S3"]
SLOT_META = {
    "S0": {"rhyme": "佳皆", "initial": "ai"},
    "S1": {"rhyme": "麻", "initial": "a"},
    "S2": {"rhyme": "歌戈", "initial": "ɑ"},
    "S3": {"rhyme": "模", "initial": "u"},
}
SLOT_COLORS = {
    "S0": "#0072B2",
    "S1": "#D55E00",
    "S2": "#009E73",
    "S3": "#CC79A7",
}
SLOT_MARKERS = {"S0": "o", "S1": "s", "S2": "D", "S3": "^"}

# Coordinates follow the conventional IPA vowel quadrilateral rather than an
# acoustic F1/F2 scale: x increases from front to back and y from close to open.
# The two project-specific small-cap symbols are placed provisionally according
# to common Chinese-dialectological usage (see COORDINATE_NOTES below).
ATOMIC_COORDS = {
    "i": (0.00, 0.00),
    "y": (0.00, 0.00),
    "ɪ": (0.55, 0.35),
    "ʏ": (0.85, 0.35),
    "e": (0.35, 1.00),
    "ø": (0.35, 1.00),
    "ᴇ": (0.53, 1.55),
    "ɛ": (0.70, 2.00),
    "œ": (0.70, 2.00),
    "æ": (0.88, 2.50),
    "a": (1.05, 3.00),
    "ɨ": (1.50, 0.00),
    "ʉ": (1.50, 0.00),
    "ɘ": (1.60, 1.00),
    "ɵ": (1.60, 1.00),
    "ə": (1.70, 1.50),
    "ɜ": (1.80, 2.00),
    "ɞ": (1.80, 2.00),
    "ɐ": (1.92, 2.50),
    "ᴀ": (2.03, 3.00),
    "ɯ": (3.00, 0.00),
    "u": (3.00, 0.00),
    "ɷ": (3.00, 0.50),
    "ʊ": (2.70, 0.45),
    "ɤ": (3.00, 1.00),
    "o": (3.00, 1.00),
    "ʌ": (3.00, 2.00),
    "ɔ": (3.00, 2.00),
    "ɑ": (3.00, 3.00),
    "ɒ": (3.00, 3.00),
}

# These items are not ordinary vowel targets on the standard IPA quadrilateral.
# Retaining them in the tables, but not assigning invented coordinates, makes
# the uncertainty explicit and prevents them from silently distorting averages.
UNPLACED_SYMBOLS = {"v", "ɥ", "ʮ"}
MODIFIER_CHARS = set("̞̠̹̯̃ː")
COORDINATE_NOTES = {
    "ɷ": "按项目既有口径置于后圆唇 o-u 之间。",
    "ᴀ": "暂按央低不圆唇元音置于 a-ɑ 中间。",
    "ᴇ": "暂按 e-ɛ 之间的前不圆唇元音放置。",
    "o̞": "按 o 的降低变体放在 o 与 ɔ 之间。",
    "v": "辅音/音节化音值，未放入元音舌位图。",
    "ɥ": "唇腭近音，未放入元音舌位图。",
    "ʮ": "汉语音韵学舌尖元音符号，未放入元音舌位图。",
}


def configure_matplotlib() -> None:
    unicode_font_path = Path("/Library/Fonts/Arial Unicode.ttf")
    ipa_font_path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    for font_path in [unicode_font_path, ipa_font_path]:
        if font_path.exists():
            font_manager.fontManager.addfont(font_path)
    plt.rcParams.update(
        {
            "font.family": ["Arial Unicode MS", "Arial", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def vowel_components(value: str) -> list[str]:
    value = clean_text(value)
    if not value or value in UNPLACED_SYMBOLS:
        return []
    if value == "o̞":
        return ["o̞"]

    normalized = unicodedata.normalize("NFD", value)
    components = []
    for char in normalized:
        if char in MODIFIER_CHARS or unicodedata.combining(char):
            continue
        if char in ATOMIC_COORDS:
            components.append(char)
    return components


def vowel_coordinate(value: str) -> tuple[float, float] | None:
    value = clean_text(value)
    if value == "o̞":
        return (3.00, 1.35)
    components = vowel_components(value)
    if not components:
        return None
    points = np.array([ATOMIC_COORDS[component] for component in components])
    return (float(points[:, 0].mean()), float(points[:, 1].mean()))


def component_label(value: str) -> str:
    if value == "o̞":
        return "o̞"
    components = vowel_components(value)
    return "+".join(components)


def is_diphthong(value: str) -> bool:
    return len(vowel_components(value)) >= 2


def front_boundary(height: float) -> float:
    return 0.35 * height


def draw_vowel_frame(ax: plt.Axes, *, compact: bool = False) -> None:
    boundary = np.array([[0, 0], [3, 0], [3, 3], [1.05, 3], [0, 0]])
    ax.plot(boundary[:, 0], boundary[:, 1], color="#777777", lw=1.0, zorder=0)
    for height in [1, 2]:
        ax.plot(
            [front_boundary(height), 3],
            [height, height],
            color="#D2D2D2",
            lw=0.7,
            zorder=0,
        )
    ax.plot([1.5, 2.03], [0, 3], color="#E2E2E2", lw=0.7, zorder=0)

    ax.set_xlim(-0.22, 3.30)
    ax.set_ylim(3.30, -0.25)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([0.0, 1.5, 3.0], labels=["前", "央", "后"])
    ax.set_yticks([0, 1, 2, 3], labels=["高", "中高", "中低", "低"])
    ax.tick_params(length=0, labelsize=7 if compact else 9)
    for spine in ax.spines.values():
        spine.set_visible(False)


def load_mainlayer() -> pd.DataFrame:
    df = pd.read_csv(INPUT_PATH, dtype=str).fillna("")
    required = {"point_id", "point_name", "onset_class", *SLOTS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"mainlayer 表缺少列：{sorted(missing)}")
    for column in required:
        df[column] = df[column].map(clean_text)
    return df


def build_value_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for slot in SLOTS:
        nonempty = df[df[slot].ne("")]
        denominator = len(nonempty)
        for value, value_df in nonempty.groupby(slot, sort=False):
            coord = vowel_coordinate(value)
            components = vowel_components(value)
            rows.append(
                {
                    "slot": slot,
                    "rhyme_group": SLOT_META[slot]["rhyme"],
                    "slot_initial": f"*{SLOT_META[slot]['initial']}",
                    "mainlayer_value": value,
                    "vowel_components": component_label(value),
                    "is_diphthong": len(components) >= 2,
                    "plot_x_front_to_back": coord[0] if coord else np.nan,
                    "plot_y_close_to_open": coord[1] if coord else np.nan,
                    "coordinate_status": "placed" if coord else "needs_confirmation",
                    "mainlayer_row_count": len(value_df),
                    "point_count": value_df["point_id"].nunique(),
                    "share_within_slot": len(value_df) / denominator if denominator else np.nan,
                    "point_examples": "、".join(
                        value_df[["point_id", "point_name"]]
                        .drop_duplicates()
                        .head(12)
                        .apply(lambda row: f"{row['point_id']} {row['point_name']}", axis=1)
                    ),
                    "coordinate_note": COORDINATE_NOTES.get(value, "复元音取组成元音坐标的算术中点。" if len(components) >= 2 else "标准 IPA 舌位。"),
                }
            )
    return pd.DataFrame(rows).sort_values(
        ["slot", "mainlayer_row_count", "mainlayer_value"],
        ascending=[True, False, True],
    )


def modal_candidates(series: pd.Series) -> tuple[list[str], int]:
    values = series[series.ne("")]
    if values.empty:
        return [], 0
    counts = values.value_counts()
    maximum = int(counts.max())
    candidates = sorted(counts[counts.eq(maximum)].index.tolist())
    return candidates, maximum


def build_point_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (point_id, point_name), point_df in df.groupby(["point_id", "point_name"], sort=True):
        record: dict[str, object] = {
            "point_id": point_id,
            "point_name": point_name,
            "mainlayer_onset_rows": len(point_df),
        }
        chain_parts = []
        any_tie = False
        for slot in SLOTS:
            candidates, support = modal_candidates(point_df[slot])
            display = " / ".join(candidates)
            record[f"{slot}_major_value"] = display
            record[f"{slot}_major_support"] = support
            record[f"{slot}_all_values"] = "、".join(
                f"{value}({count})" for value, count in point_df[slot].value_counts().items() if value
            )
            any_tie = any_tie or len(candidates) > 1
            chain_parts.append(display or "∅")

        onset_chains = point_df[SLOTS].agg(" → ".join, axis=1)
        chain_counts = onset_chains.value_counts()
        chain_max = int(chain_counts.max())
        dominant_chains = sorted(chain_counts[chain_counts.eq(chain_max)].index.tolist())
        record["major_chain"] = " → ".join(chain_parts)
        record["major_chain_has_tie"] = any_tie
        record["dominant_onset_chain"] = " | ".join(dominant_chains)
        record["dominant_onset_chain_support"] = chain_max
        record["onset_chain_count"] = onset_chains.nunique()

        unplaced = []
        for _, onset_row in point_df.iterrows():
            for slot in SLOTS:
                value = onset_row[slot]
                if value and vowel_coordinate(value) is None:
                    unplaced.append(f"{onset_row['onset_class']}:{slot}={value}")
        record["unplaced_mainlayer_values"] = "、".join(sorted(set(unplaced)))
        rows.append(record)

    points = pd.DataFrame(rows)
    pattern_counts = points["major_chain"].value_counts()
    points["major_pattern_point_count"] = points["major_chain"].map(pattern_counts)
    points["major_pattern_share"] = points["major_pattern_point_count"] / len(points)
    return points.sort_values(["point_id", "point_name"]).reset_index(drop=True)


def build_pattern_table(points: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pattern, group in points.groupby("major_chain", sort=False):
        rows.append(
            {
                "major_chain": pattern,
                "point_count": len(group),
                "share_of_points": len(group) / len(points),
                "ambiguous_point_count": int(group["major_chain_has_tie"].sum()),
                "point_list": "、".join(
                    group.apply(lambda row: f"{row['point_id']} {row['point_name']}", axis=1)
                ),
            }
        )
    result = pd.DataFrame(rows).sort_values(
        ["point_count", "major_chain"], ascending=[False, True]
    )
    result.insert(0, "rank", range(1, len(result) + 1))
    return result


def build_unplaced_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        for slot in SLOTS:
            value = row[slot]
            if value and vowel_coordinate(value) is None:
                rows.append(
                    {
                        "point_id": row["point_id"],
                        "point_name": row["point_name"],
                        "onset_class": row["onset_class"],
                        "slot": slot,
                        "rhyme_group": SLOT_META[slot]["rhyme"],
                        "mainlayer_value": value,
                        "reason": COORDINATE_NOTES.get(value, "没有可靠的 IPA 舌位坐标。"),
                    }
                )
    return pd.DataFrame(rows)


def label_offsets(values: pd.DataFrame) -> dict[str, tuple[float, float]]:
    offsets: dict[str, tuple[float, float]] = {}
    placed = values.dropna(subset=["plot_x_front_to_back", "plot_y_close_to_open"]).copy()
    groups = placed.groupby(
        [placed["plot_x_front_to_back"].round(2), placed["plot_y_close_to_open"].round(2)]
    )
    candidates = [(-38, -12), (12, -12), (-38, 13), (12, 13), (-52, 0), (17, 0)]
    for _, group in groups:
        for idx, value in enumerate(group["mainlayer_value"]):
            offsets[value] = candidates[idx % len(candidates)]
    return offsets


def plot_overview(values: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(14.5, 12.5))
    for ax, slot in zip(axes.flat, SLOTS):
        draw_vowel_frame(ax)
        slot_values = values[values["slot"].eq(slot)].copy()
        placed = slot_values.dropna(subset=["plot_x_front_to_back", "plot_y_close_to_open"])
        initial = SLOT_META[slot]["initial"]
        initial_coord = vowel_coordinate(initial)
        assert initial_coord is not None
        ax.scatter(
            *initial_coord,
            s=170,
            marker="*",
            facecolor="#F4F4F4",
            edgecolor="#555555",
            linewidth=1,
            zorder=2,
        )
        ax.annotate(
            f"原始 *{initial}",
            xy=initial_coord,
            xytext=(5, -17),
            textcoords="offset points",
            fontsize=8,
            color="#555555",
        )

        offsets = label_offsets(placed)
        label_values = set(
            placed.nlargest(8, "mainlayer_row_count")["mainlayer_value"].tolist()
        )
        for _, row in placed.iterrows():
            size = 38 + 12 * np.sqrt(row["mainlayer_row_count"])
            marker = "D" if row["is_diphthong"] else "o"
            ax.scatter(
                row["plot_x_front_to_back"],
                row["plot_y_close_to_open"],
                s=size,
                marker=marker,
                color=SLOT_COLORS[slot],
                edgecolor="white",
                linewidth=0.6,
                alpha=0.82,
                zorder=3,
            )
            should_label = row["mainlayer_value"] in label_values
            if should_label:
                offset = offsets.get(row["mainlayer_value"], (8, -8))
                ax.annotate(
                    f"{row['mainlayer_value']} · {row['mainlayer_row_count']}",
                    xy=(row["plot_x_front_to_back"], row["plot_y_close_to_open"]),
                    xytext=offset,
                    textcoords="offset points",
                    fontsize=7.5,
                    color="#222222",
                    arrowprops={"arrowstyle": "-", "lw": 0.45, "color": "#999999"},
                    zorder=4,
                )

        unplaced = slot_values[slot_values["coordinate_status"].ne("placed")]
        unplaced_text = ""
        if not unplaced.empty:
            unplaced_text = "；未定位 " + "、".join(
                f"{row.mainlayer_value}({row.mainlayer_row_count})" for row in unplaced.itertuples()
            )
        ax.set_title(
            f"{slot} {SLOT_META[slot]['rhyme']}  |  原始 *{initial}\n"
            f"主体层 {int(slot_values['mainlayer_row_count'].sum())} 格{unplaced_text}",
            fontsize=12,
            pad=10,
        )

    legend = [
        Line2D([0], [0], marker="*", color="none", markeredgecolor="#555555", markerfacecolor="#F4F4F4", markersize=11, label="slot_type_initial"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#666666", markersize=7, label="主体层单元音"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="#666666", markersize=7, label="主体层复元音（组成元音中点）"),
    ]
    fig.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.012),
        ncol=3,
        frameon=False,
        fontsize=9,
    )
    fig.suptitle(
        "吴语 S0-S3 主体层在 IPA 舌位图中的分布",
        fontsize=18,
        y=0.992,
    )
    fig.tight_layout(rect=[0.01, 0.055, 0.99, 0.955], h_pad=2.0, w_pad=2.0)
    fig.savefig(OVERVIEW_OUTPUT, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_point_panel(ax: plt.Axes, point_df: pd.DataFrame, point_row: pd.Series) -> None:
    draw_vowel_frame(ax, compact=True)
    ax.set_title(
        f"{point_row['point_id']} {point_row['point_name']}\n{point_row['major_chain']}",
        fontsize=9,
        pad=5,
    )

    for slot in SLOTS:
        initial_coord = vowel_coordinate(SLOT_META[slot]["initial"])
        assert initial_coord is not None
        ax.scatter(
            *initial_coord,
            s=44,
            marker="*",
            facecolor="white",
            edgecolor=SLOT_COLORS[slot],
            linewidth=0.8,
            alpha=0.8,
            zorder=2,
        )
        candidates, _ = modal_candidates(point_df[slot])
        for candidate in candidates:
            target_coord = vowel_coordinate(candidate)
            if target_coord is None:
                continue
            ax.annotate(
                "",
                xy=target_coord,
                xytext=initial_coord,
                arrowprops={
                    "arrowstyle": "->",
                    "lw": 1.25,
                    "color": SLOT_COLORS[slot],
                    "alpha": 0.75,
                    "shrinkA": 5,
                    "shrinkB": 5,
                },
                zorder=1,
            )

        counts = point_df[slot].value_counts()
        for value, count in counts.items():
            if not value:
                continue
            coord = vowel_coordinate(value)
            if coord is None:
                continue
            is_major = value in candidates
            ax.scatter(
                *coord,
                s=50 + count * 15,
                marker=SLOT_MARKERS[slot],
                facecolor=SLOT_COLORS[slot] if is_major else "white",
                edgecolor=SLOT_COLORS[slot],
                linewidth=1.0,
                alpha=0.88,
                zorder=3,
            )

    labels_by_coord: dict[tuple[float, float], list[str]] = {}
    for slot in SLOTS:
        for value, count in point_df[slot].value_counts().items():
            coord = vowel_coordinate(value)
            if not value or coord is None:
                continue
            key = (round(coord[0], 3), round(coord[1], 3))
            labels_by_coord.setdefault(key, []).append(f"{slot} {value}×{count}")
    for (x, y), labels in labels_by_coord.items():
        ha = "right" if x > 2.55 else "left"
        x_offset = -7 if ha == "right" else 7
        ax.annotate(
            "\n".join(labels),
            xy=(x, y),
            xytext=(x_offset, 0),
            textcoords="offset points",
            ha=ha,
            va="center",
            fontsize=6.3,
            color="#222222",
            zorder=4,
        )

    if point_row["unplaced_mainlayer_values"]:
        ax.text(
            0.01,
            -0.10,
            f"未定位：{point_row['unplaced_mainlayer_values']}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=6.5,
            color="#8B1A1A",
        )


def plot_atlas(df: pd.DataFrame, points: pd.DataFrame) -> None:
    point_lookup = {
        (row.point_id, row.point_name): row
        for row in points.itertuples(index=False)
    }
    groups = list(df.groupby(["point_id", "point_name"], sort=True))
    with PdfPages(ATLAS_OUTPUT) as pdf:
        for page_start in range(0, len(groups), 4):
            page_groups = groups[page_start : page_start + 4]
            if len(page_groups) <= 2:
                fig, axes = plt.subplots(
                    1, len(page_groups), figsize=(11.69, 8.27), squeeze=False
                )
            else:
                fig, axes = plt.subplots(2, 2, figsize=(11.69, 8.27))
            axes_list = list(np.asarray(axes).flat)
            for ax, ((point_id, point_name), point_df) in zip(axes_list, page_groups):
                point_row = pd.Series(point_lookup[(point_id, point_name)]._asdict())
                plot_point_panel(ax, point_df, point_row)
            for ax in axes_list[len(page_groups) :]:
                ax.axis("off")

            handles = [
                Line2D([0], [0], marker=SLOT_MARKERS[slot], color=SLOT_COLORS[slot], lw=1.3, markersize=6, label=f"{slot} {SLOT_META[slot]['rhyme']} (*{SLOT_META[slot]['initial']})")
                for slot in SLOTS
            ]
            fig.legend(
                handles=handles,
                loc="lower center",
                bbox_to_anchor=(0.5, 0.012),
                ncol=4,
                frameon=False,
                fontsize=8,
            )
            fig.suptitle(
                f"方言点主体层主要模式 - IPA 舌位图  {page_start + 1}-{page_start + len(page_groups)} / {len(groups)}",
                fontsize=12,
                y=0.985,
            )
            fig.tight_layout(rect=[0.02, 0.065, 0.98, 0.94], h_pad=1.4, w_pad=1.4)
            pdf.savefig(fig, facecolor="white")
            plt.close(fig)


def main() -> None:
    configure_matplotlib()
    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    mainlayer = load_mainlayer()
    values = build_value_table(mainlayer)
    points = build_point_table(mainlayer)
    patterns = build_pattern_table(points)
    unplaced = build_unplaced_table(mainlayer)

    values.to_csv(VALUE_OUTPUT, index=False, encoding="utf-8-sig")
    points.to_csv(POINT_OUTPUT, index=False, encoding="utf-8-sig")
    patterns.to_csv(PATTERN_OUTPUT, index=False, encoding="utf-8-sig")
    unplaced.to_csv(UNPLACED_OUTPUT, index=False, encoding="utf-8-sig")

    plot_overview(values)
    plot_atlas(mainlayer, points)

    print(f"方言点：{mainlayer['point_id'].nunique()}")
    print(f"主体层格位：{len(mainlayer) * len(SLOTS)}")
    print(f"点级主要模式：{points['major_chain'].nunique()}")
    print(f"未定位主体层值：{len(unplaced)}")
    for output in [VALUE_OUTPUT, POINT_OUTPUT, PATTERN_OUTPUT, UNPLACED_OUTPUT, OVERVIEW_OUTPUT, ATLAS_OUTPUT]:
        print(output.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
