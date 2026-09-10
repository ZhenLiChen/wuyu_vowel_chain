import unicodedata
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = PROJECT_ROOT / "data_clean"
VALUE_DIR = DATA_CLEAN / "value_type"
FIGS_DIR = PROJECT_ROOT / "figs" / "diphthongization"

INPUT_PATH = DATA_CLEAN / "wuyu_lexeme.csv"

VALUE_OUTPUT = VALUE_DIR / "s0_s3_split_value_classification.csv"
MEDIAL_PENDING_OUTPUT = VALUE_DIR / "s0_s3_medial_pending.csv"
I_OFFGLIDE_OUTPUT = VALUE_DIR / "s0_s3_i_offglide_excluded.csv"
NON_CORE_DIPHTHONG_OUTPUT = VALUE_DIR / "s0_s3_non_core_diphthong_excluded.csv"
ONSET_STATS_OUTPUT = VALUE_DIR / "s0_s3_split_onset_stats.csv"
ONSET_SEQUENCE_OUTPUT = VALUE_DIR / "s0_s3_split_onset_sequences.csv"
SLOT_STATS_OUTPUT = VALUE_DIR / "s0_s3_split_slot_stats.csv"
SLOT_ONSET_STATS_OUTPUT = VALUE_DIR / "s0_s3_split_slot_onset_stats.csv"
POINT_ONSET_OUTPUT = VALUE_DIR / "s0_s3_split_point_onset_stats.csv"
POINT_SLOT_OUTPUT = VALUE_DIR / "s0_s3_split_point_slot_stats.csv"
IMPLICATION_OUTPUT = VALUE_DIR / "s0_s3_split_implication_rules.csv"

ONSET_FIG_OUTPUT = FIGS_DIR / "s0_s3_split_onset_rates.png"
SLOT_FIG_OUTPUT = FIGS_DIR / "s0_s3_split_slot_rates.png"

SLOT_ORDER = ["S0", "S1", "S2", "S3"]
NO_LOW_SLOT_ONSETS = {"T", "N"}
EXCLUDED_CHARS = {"靴", "茄"}

VOWEL_CHARS = set("aeiouyæøœɐɑɒɔəɛɜɞɤɯɪʊʌʏɵʉɷᴀᴇ")
CONSONANT_OR_GLIDE_CHARS = set("mnŋwɥjvʮ")
MEDIAL_PENDING_VALUES = {"yo", "yɑ", "øy", "uo", "ua", "uᴇ"}
NON_CORE_DIPHTHONG_VALUES = {"au", "ao", "aɤ"}


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


def split_phonetic(value) -> list[str]:
    if pd.isna(value):
        return []
    value = str(value).replace("\u00a0", " ").strip()
    if not value or value.lower() == "nan":
        return []
    if value == "o（uo）":
        return ["u", "uo"]
    return [part.strip() for part in value.split("/") if part.strip()]


def decomposed_chars(value: str) -> list[str]:
    return [
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    ]


def vowel_sequence(value: str) -> list[str]:
    return [char for char in decomposed_chars(value) if char in VOWEL_CHARS]


def starts_with(value: str, initials: set[str]) -> bool:
    chars = decomposed_chars(value)
    return bool(chars and chars[0] in initials)


def has_coda_or_consonantal(value: str) -> bool:
    chars = decomposed_chars(value)
    vowels = set(VOWEL_CHARS)
    # Leading i/u/y are handled separately for multi-vowel values.
    for idx, char in enumerate(chars):
        if char in vowels:
            continue
        if char in {"ː", "̞"}:
            continue
        if char == "ʔ":
            return True
        if char in CONSONANT_OR_GLIDE_CHARS and idx != 0:
            return True
        if char in {"m", "n", "ŋ", "v", "w", "ɥ", "ʮ"} and len(vowel_sequence(value)) == 0:
            return True
    return False


def classify_phonetic(value: str) -> str:
    if "ʔ" in value:
        return "checked_or_coda"
    vowels = vowel_sequence(value)
    vowel_count = len(vowels)
    if vowel_count == 0:
        return "consonantal_or_other"
    if vowel_count == 1:
        if has_coda_or_consonantal(value):
            return "checked_or_coda"
        return "monophthong"
    if starts_with(value, {"i", "j"}):
        return "i_medial_excluded"
    if vowels[-1] in {"i", "ɪ"}:
        return "i_offglide_excluded"
    if value in MEDIAL_PENDING_VALUES or starts_with(value, {"u", "w", "y", "ɥ"}):
        return "medial_pending"
    if value in NON_CORE_DIPHTHONG_VALUES:
        return "non_core_diphthong_excluded"
    return "clear_split"


def is_clear_eligible(category: str) -> bool:
    return category in {"monophthong", "clear_split"}


def format_values(values) -> str:
    return ", ".join(sorted(str(value) for value in values if str(value)))


def format_counts(counts: pd.Series) -> str:
    counts = counts.sort_values(ascending=False)
    return ", ".join(f"{value}({int(count)})" for value, count in counts.items())


def safe_rate(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return np.nan
    return numerator / denominator


def load_expanded() -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"未找到输入文件：{INPUT_PATH}")

    required = {
        "point_id",
        "point_name",
        "subbranch",
        "chain_slot",
        "onset_class",
        "rhyme_modern",
        "char",
        "phonetic",
    }
    df = pd.read_csv(INPUT_PATH)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"输入文件缺少必要列：{sorted(missing)}")

    work = df[list(required)].copy()
    for column in required:
        work[column] = work[column].astype("string").str.strip()
    work = work[
        work["point_id"].notna()
        & (work["point_id"] != "")
        & work["chain_slot"].isin(SLOT_ORDER)
        & ~work["char"].isin(EXCLUDED_CHARS)
    ].copy()
    work["onset_class"] = work["onset_class"].replace({"TS*": "TS"})
    work = work[
        ~(
            work["onset_class"].isin(NO_LOW_SLOT_ONSETS)
            & work["chain_slot"].isin(["S0", "S1"])
        )
    ].copy()

    work["phonetic"] = work["phonetic"].apply(split_phonetic)
    work = work.explode("phonetic")
    work = work[work["phonetic"].notna() & (work["phonetic"] != "")].copy()
    work = work.reset_index(drop=True)
    work["split_category"] = work["phonetic"].apply(classify_phonetic)
    work["clear_split_flag"] = work["split_category"] == "clear_split"
    work["clear_eligible_flag"] = work["split_category"].apply(is_clear_eligible)
    return work


def summarize_values(work: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for value, group in work.groupby("phonetic"):
        rows.append(
            {
                "phonetic": value,
                "split_category": classify_phonetic(value),
                "vowel_sequence": "".join(vowel_sequence(value)),
                "token_count": len(group),
                "point_count": group["point_id"].nunique(),
                "slot_counts": format_counts(group["chain_slot"].value_counts()),
                "onset_counts": format_counts(group["onset_class"].value_counts()),
                "example_points": " | ".join(
                    f"{row.point_id}:{row.point_name}"
                    for row in group[["point_id", "point_name"]]
                    .drop_duplicates()
                    .head(12)
                    .itertuples(index=False)
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["split_category", "token_count", "phonetic"], ascending=[True, False, True]
    )


def summarize_medial_pending(work: pd.DataFrame) -> pd.DataFrame:
    pending = work[work["split_category"] == "medial_pending"].copy()
    if pending.empty:
        return pd.DataFrame(
            columns=[
                "point_id",
                "point_name",
                "subbranch",
                "chain_slot",
                "onset_class",
                "phonetic",
                "token_count",
                "char_count",
                "example_chars",
            ]
        )
    rows = []
    group_cols = ["point_id", "point_name", "subbranch", "chain_slot", "onset_class", "phonetic"]
    for keys, group in pending.groupby(group_cols, dropna=False):
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "token_count": len(group),
                "char_count": group["char"].nunique(),
                "example_chars": " / ".join(sorted(set(group["char"].dropna()))[:12]),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["phonetic", "point_id", "chain_slot", "onset_class"]
    )


def summarize_i_offglide(work: pd.DataFrame) -> pd.DataFrame:
    excluded = work[work["split_category"] == "i_offglide_excluded"].copy()
    if excluded.empty:
        return pd.DataFrame(
            columns=[
                "point_id",
                "point_name",
                "subbranch",
                "chain_slot",
                "onset_class",
                "phonetic",
                "token_count",
                "char_count",
                "example_chars",
            ]
        )
    rows = []
    group_cols = ["point_id", "point_name", "subbranch", "chain_slot", "onset_class", "phonetic"]
    for keys, group in excluded.groupby(group_cols, dropna=False):
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "token_count": len(group),
                "char_count": group["char"].nunique(),
                "example_chars": " / ".join(sorted(set(group["char"].dropna()))[:12]),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["phonetic", "point_id", "chain_slot", "onset_class"]
    )


def summarize_non_core_diphthong(work: pd.DataFrame) -> pd.DataFrame:
    excluded = work[work["split_category"] == "non_core_diphthong_excluded"].copy()
    if excluded.empty:
        return pd.DataFrame(
            columns=[
                "point_id",
                "point_name",
                "subbranch",
                "chain_slot",
                "onset_class",
                "phonetic",
                "token_count",
                "char_count",
                "example_chars",
            ]
        )
    rows = []
    group_cols = ["point_id", "point_name", "subbranch", "chain_slot", "onset_class", "phonetic"]
    for keys, group in excluded.groupby(group_cols, dropna=False):
        rows.append(
            {
                **dict(zip(group_cols, keys)),
                "token_count": len(group),
                "char_count": group["char"].nunique(),
                "example_chars": " / ".join(sorted(set(group["char"].dropna()))[:12]),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["phonetic", "point_id", "chain_slot", "onset_class"]
    )


def aggregate_counts(work: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = (
        work.groupby(group_cols, dropna=False)
        .agg(
            total_tokens=("phonetic", "size"),
            eligible_tokens=("clear_eligible_flag", "sum"),
            clear_split_tokens=("clear_split_flag", "sum"),
            i_medial_tokens=(
                "split_category",
                lambda values: int((values == "i_medial_excluded").sum()),
            ),
            i_offglide_tokens=(
                "split_category",
                lambda values: int((values == "i_offglide_excluded").sum()),
            ),
            non_core_diphthong_tokens=(
                "split_category",
                lambda values: int((values == "non_core_diphthong_excluded").sum()),
            ),
            medial_pending_tokens=(
                "split_category",
                lambda values: int((values == "medial_pending").sum()),
            ),
            checked_or_coda_tokens=(
                "split_category",
                lambda values: int((values == "checked_or_coda").sum()),
            ),
            monophthong_tokens=(
                "split_category",
                lambda values: int((values == "monophthong").sum()),
            ),
            point_count=("point_id", "nunique"),
            value_types=("phonetic", lambda values: len(set(values.dropna()))),
            clear_split_values=(
                "phonetic",
                lambda values: format_values(
                    set(
                        work.loc[
                            values.index[
                                work.loc[values.index, "split_category"] == "clear_split"
                            ],
                            "phonetic",
                        ]
                    )
                ),
            ),
        )
        .reset_index()
    )
    grouped["clear_split_rate"] = grouped.apply(
        lambda row: safe_rate(row["clear_split_tokens"], row["eligible_tokens"]),
        axis=1,
    )
    grouped["raw_clear_split_share"] = grouped.apply(
        lambda row: safe_rate(row["clear_split_tokens"], row["total_tokens"]),
        axis=1,
    )
    grouped["medial_pending_share"] = grouped.apply(
        lambda row: safe_rate(row["medial_pending_tokens"], row["total_tokens"]),
        axis=1,
    )
    grouped["i_offglide_share"] = grouped.apply(
        lambda row: safe_rate(row["i_offglide_tokens"], row["total_tokens"]),
        axis=1,
    )
    grouped["non_core_diphthong_share"] = grouped.apply(
        lambda row: safe_rate(row["non_core_diphthong_tokens"], row["total_tokens"]),
        axis=1,
    )
    return grouped


def build_implication_rules(
    point_slot: pd.DataFrame, point_onset: pd.DataFrame
) -> pd.DataFrame:
    rows = []

    slot_flags = point_slot.copy()
    slot_flags["has_clear_split"] = slot_flags["clear_split_tokens"] > 0
    slot_pivot = slot_flags.pivot_table(
        index=["point_id", "point_name", "subbranch"],
        columns="chain_slot",
        values="has_clear_split",
        aggfunc="max",
        fill_value=False,
    )
    for slot in SLOT_ORDER:
        if slot not in slot_pivot.columns:
            slot_pivot[slot] = False
    slot_pivot = slot_pivot.reset_index()

    slot_exprs = {
        "S0": slot_pivot["S0"],
        "S1": slot_pivot["S1"],
        "S2": slot_pivot["S2"],
        "S3": slot_pivot["S3"],
        "S0或S1": slot_pivot["S0"] | slot_pivot["S1"],
        "S2或S3": slot_pivot["S2"] | slot_pivot["S3"],
    }
    slot_rules = [
        ("S0", "S2"),
        ("S1", "S2"),
        ("S0或S1", "S2"),
        ("S3", "S2"),
        ("S2", "S3"),
        ("S0", "S3"),
        ("S1", "S3"),
        ("S0或S1", "S3"),
        ("S2或S3", "S0或S1"),
    ]
    for antecedent, consequent in slot_rules:
        ant = slot_exprs[antecedent]
        cons = slot_exprs[consequent]
        ant_count = int(ant.sum())
        joint = ant & cons
        exceptions = slot_pivot.loc[
            ant & ~cons, ["point_id", "point_name", "subbranch"]
        ]
        rows.append(
            {
                "rule_group": "slot",
                "antecedent": f"{antecedent}有清晰裂化",
                "consequent": f"{consequent}有清晰裂化",
                "total_point_count": len(slot_pivot),
                "antecedent_point_count": ant_count,
                "joint_point_count": int(joint.sum()),
                "confidence": safe_rate(int(joint.sum()), ant_count),
                "exception_count": len(exceptions),
                "exception_points": " | ".join(
                    f"{row.point_id}:{row.point_name}"
                    for row in exceptions.itertuples(index=False)
                ),
            }
        )

    onset_flags = point_onset.copy()
    onset_flags["has_clear_split"] = onset_flags["clear_split_tokens"] > 0
    onset_pivot = onset_flags.pivot_table(
        index=["point_id", "point_name", "subbranch"],
        columns="onset_class",
        values="has_clear_split",
        aggfunc="max",
        fill_value=False,
    )
    onset_pivot = onset_pivot.reset_index()
    onset_classes = [
        column
        for column in onset_pivot.columns
        if column not in {"point_id", "point_name", "subbranch"}
    ]
    for antecedent in onset_classes:
        for consequent in onset_classes:
            if antecedent == consequent:
                continue
            ant = onset_pivot[antecedent]
            cons = onset_pivot[consequent]
            ant_count = int(ant.sum())
            if ant_count < 5:
                continue
            joint = ant & cons
            confidence = safe_rate(int(joint.sum()), ant_count)
            if confidence < 0.8:
                continue
            exceptions = onset_pivot.loc[
                ant & ~cons, ["point_id", "point_name", "subbranch"]
            ]
            rows.append(
                {
                    "rule_group": "onset",
                    "antecedent": f"{antecedent}声母条件有清晰裂化",
                    "consequent": f"{consequent}声母条件有清晰裂化",
                    "total_point_count": len(onset_pivot),
                    "antecedent_point_count": ant_count,
                    "joint_point_count": int(joint.sum()),
                    "confidence": confidence,
                    "exception_count": len(exceptions),
                    "exception_points": " | ".join(
                        f"{row.point_id}:{row.point_name}"
                        for row in exceptions.itertuples(index=False)
                    ),
                }
            )

    return pd.DataFrame(rows).sort_values(
        ["rule_group", "confidence", "antecedent_point_count"],
        ascending=[True, False, False],
    )


def build_onset_stats(work: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    onset = aggregate_counts(work, ["onset_class"])
    total_clear = onset["clear_split_tokens"].sum()
    onset["clear_split_contribution_share"] = onset["clear_split_tokens"] / total_clear

    point_onset = aggregate_counts(work, ["point_id", "point_name", "subbranch", "onset_class"])
    point_onset_valid = point_onset[point_onset["eligible_tokens"] > 0].copy()
    point_mean = (
        point_onset_valid.groupby("onset_class")
        .agg(
            point_normalized_rate=("clear_split_rate", "mean"),
            point_onset_cell_count=("clear_split_rate", "size"),
            point_prevalence_any_split=("clear_split_tokens", lambda values: (values > 0).mean()),
        )
        .reset_index()
    )

    slot_onset = aggregate_counts(work, ["onset_class", "chain_slot"])
    slot_valid = slot_onset[slot_onset["eligible_tokens"] > 0].copy()
    slot_mean = (
        slot_valid.groupby("onset_class")
        .agg(
            slot_balanced_rate=("clear_split_rate", "mean"),
            slot_cell_count=("clear_split_rate", "size"),
        )
        .reset_index()
    )

    point_slot = aggregate_counts(
        work, ["point_id", "point_name", "subbranch", "onset_class", "chain_slot"]
    )
    point_slot_valid = point_slot[point_slot["eligible_tokens"] > 0].copy()
    point_slot_mean = (
        point_slot_valid.groupby("onset_class")
        .agg(
            point_slot_balanced_rate=("clear_split_rate", "mean"),
            point_slot_cell_count=("clear_split_rate", "size"),
        )
        .reset_index()
    )

    onset = (
        onset.merge(point_mean, on="onset_class", how="left")
        .merge(slot_mean, on="onset_class", how="left")
        .merge(point_slot_mean, on="onset_class", how="left")
    )

    ranking_metrics = [
        "clear_split_rate",
        "point_normalized_rate",
        "slot_balanced_rate",
        "point_slot_balanced_rate",
        "point_prevalence_any_split",
    ]
    for metric in ranking_metrics:
        onset[f"{metric}_rank"] = onset[metric].rank(ascending=False, method="min")
    onset["mean_rank"] = onset[[f"{metric}_rank" for metric in ranking_metrics]].mean(axis=1)
    onset = onset.sort_values(["mean_rank", "onset_class"]).reset_index(drop=True)
    return onset, point_onset, slot_onset


def build_sequences(onset_stats: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        ("clear_split_contribution_share", "传统 token 贡献份额"),
        ("clear_split_rate", "全局 token rate"),
        ("point_normalized_rate", "方言点等权 rate"),
        ("slot_balanced_rate", "链位等权 rate"),
        ("point_slot_balanced_rate", "方言点+链位等权 rate"),
        ("point_prevalence_any_split", "出现裂化的方言点-声母格比例"),
        ("mean_rank", "综合平均名次"),
    ]
    rows = []
    for metric, label in metrics:
        ascending = metric == "mean_rank"
        ranked = onset_stats.sort_values([metric, "onset_class"], ascending=[ascending, True])
        rows.append(
            {
                "method": metric,
                "method_label": label,
                "sequence": " > ".join(
                    f"{row.onset_class}({getattr(row, metric):.4f})"
                    for row in ranked.itertuples(index=False)
                    if pd.notna(getattr(row, metric))
                ),
            }
        )
    return pd.DataFrame(rows)


def build_slot_stats(work: pd.DataFrame) -> pd.DataFrame:
    slot = aggregate_counts(work, ["chain_slot"])
    point_slot = aggregate_counts(work, ["point_id", "point_name", "subbranch", "chain_slot"])
    point_slot = point_slot[point_slot["eligible_tokens"] > 0]
    point_mean = (
        point_slot.groupby("chain_slot")
        .agg(
            point_normalized_rate=("clear_split_rate", "mean"),
            point_slot_cell_count=("clear_split_rate", "size"),
        )
        .reset_index()
    )
    slot = slot.merge(point_mean, on="chain_slot", how="left")
    slot["slot_order"] = slot["chain_slot"].map({slot: idx for idx, slot in enumerate(SLOT_ORDER)})
    return slot.sort_values("slot_order").drop(columns=["slot_order"])


def plot_onset(onset_stats: pd.DataFrame) -> None:
    set_chinese_font()
    plot_df = onset_stats.sort_values("point_slot_balanced_rate")
    y = np.arange(len(plot_df))
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(y - 0.18, plot_df["clear_split_rate"], height=0.36, label="全局token rate", color="#4C78A8")
    ax.barh(
        y + 0.18,
        plot_df["point_slot_balanced_rate"],
        height=0.36,
        label="方言点+链位等权 rate",
        color="#F58518",
    )
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["onset_class"])
    ax.set_xlabel("清晰裂化比例，已排除 i 介音与 y/u 介音待判")
    ax.set_title("S0-S3 各声母类别的裂化推动力")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ONSET_FIG_OUTPUT, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_slot(slot_stats: pd.DataFrame) -> None:
    set_chinese_font()
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(slot_stats))
    ax.bar(x - 0.18, slot_stats["clear_split_rate"], width=0.36, label="全局token rate", color="#54A24B")
    ax.bar(
        x + 0.18,
        slot_stats["point_normalized_rate"],
        width=0.36,
        label="方言点等权 rate",
        color="#E45756",
    )
    ax.set_xticks(x)
    ax.set_xticklabels(slot_stats["chain_slot"])
    ax.set_ylabel("清晰裂化比例")
    ax.set_title("S0-S3 链位与裂化的关系")
    ax.legend()
    fig.tight_layout()
    fig.savefig(SLOT_FIG_OUTPUT, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run_analysis() -> None:
    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    work = load_expanded()
    value_summary = summarize_values(work)
    medial_pending = summarize_medial_pending(work)
    i_offglide = summarize_i_offglide(work)
    non_core_diphthong = summarize_non_core_diphthong(work)
    onset_stats, point_onset, slot_onset = build_onset_stats(work)
    sequences = build_sequences(onset_stats)
    slot_stats = build_slot_stats(work)
    point_slot = aggregate_counts(work, ["point_id", "point_name", "subbranch", "chain_slot"])
    implication_rules = build_implication_rules(point_slot, point_onset)

    value_summary.to_csv(VALUE_OUTPUT, index=False, encoding="utf-8-sig")
    medial_pending.to_csv(MEDIAL_PENDING_OUTPUT, index=False, encoding="utf-8-sig")
    i_offglide.to_csv(I_OFFGLIDE_OUTPUT, index=False, encoding="utf-8-sig")
    non_core_diphthong.to_csv(
        NON_CORE_DIPHTHONG_OUTPUT, index=False, encoding="utf-8-sig"
    )
    onset_stats.to_csv(ONSET_STATS_OUTPUT, index=False, encoding="utf-8-sig")
    sequences.to_csv(ONSET_SEQUENCE_OUTPUT, index=False, encoding="utf-8-sig")
    slot_stats.to_csv(SLOT_STATS_OUTPUT, index=False, encoding="utf-8-sig")
    slot_onset.to_csv(SLOT_ONSET_STATS_OUTPUT, index=False, encoding="utf-8-sig")
    point_onset.to_csv(POINT_ONSET_OUTPUT, index=False, encoding="utf-8-sig")
    point_slot.to_csv(POINT_SLOT_OUTPUT, index=False, encoding="utf-8-sig")
    implication_rules.to_csv(IMPLICATION_OUTPUT, index=False, encoding="utf-8-sig")

    plot_onset(onset_stats)
    plot_slot(slot_stats)

    print(f"已生成音值分类表：{VALUE_OUTPUT}")
    print(f"已生成 y/u 介音待判表：{MEDIAL_PENDING_OUTPUT}")
    print(f"已生成 i 尾复合音排除表：{I_OFFGLIDE_OUTPUT}")
    print(f"已生成非核心复合音排除表：{NON_CORE_DIPHTHONG_OUTPUT}")
    print(f"已生成声母裂化统计：{ONSET_STATS_OUTPUT}")
    print(f"已生成声母裂化序列：{ONSET_SEQUENCE_OUTPUT}")
    print(f"已生成链位裂化统计：{SLOT_STATS_OUTPUT}")
    print(f"已生成链位-声母裂化统计：{SLOT_ONSET_STATS_OUTPUT}")
    print(f"已生成方言点-声母裂化统计：{POINT_ONSET_OUTPUT}")
    print(f"已生成方言点-链位裂化统计：{POINT_SLOT_OUTPUT}")
    print(f"已生成蕴涵关系表：{IMPLICATION_OUTPUT}")
    print(f"已生成图：{ONSET_FIG_OUTPUT}")
    print(f"已生成图：{SLOT_FIG_OUTPUT}")


if __name__ == "__main__":
    run_analysis()
