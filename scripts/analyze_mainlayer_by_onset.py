from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from analyze_mainlayer_ipa_positions import (
    SLOT_META,
    SLOTS,
    clean_text,
    component_label,
    is_diphthong,
    vowel_coordinate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data_raw" / "mainlayer_merge.csv"
OUTPUT_DIR = PROJECT_ROOT / "data_clean" / "value_type"

ONSET_SUMMARY_OUTPUT = OUTPUT_DIR / "mainlayer_onset_summary.csv"
STRUCTURE_OUTPUT = OUTPUT_DIR / "mainlayer_onset_structure_patterns.csv"
CHAIN_OUTPUT = OUTPUT_DIR / "mainlayer_onset_chain_patterns.csv"
SLOT_SUMMARY_OUTPUT = OUTPUT_DIR / "mainlayer_onset_slot_summary.csv"
SLOT_VALUE_OUTPUT = OUTPUT_DIR / "mainlayer_onset_slot_value_positions.csv"
POINT_OUTPUT = OUTPUT_DIR / "point_mainlayer_onset_chains.csv"

ONSET_ORDER = ["K", "M", "P", "TS", "Ø"]
STRUCTURE_ORDER = [
    "全对立",
    "S0=S1",
    "S1=S2",
    "S2=S3",
    "S0=S1，S2=S3",
    "S1=S2=S3",
    "S1=S3 [越级]",
]


def load_data() -> pd.DataFrame:
    df = pd.read_csv(INPUT_PATH, dtype=str).fillna("")
    required = {
        "point_id",
        "point_name",
        "onset_class",
        *SLOTS,
        "一级分类",
        "二级分类",
        "三级分类(详细模式)",
        "是否越级",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"mainlayer 表缺少列：{sorted(missing)}")

    for column in required:
        df[column] = df[column].map(clean_text)
    df = df[df["onset_class"].isin(ONSET_ORDER)].copy()
    df["onset_class"] = pd.Categorical(
        df["onset_class"], categories=ONSET_ORDER, ordered=True
    )
    df["exact_chain"] = df[SLOTS].agg(" → ".join, axis=1)
    df["slot_distinct_count"] = df[SLOTS].nunique(axis=1)
    df["is_leapfrog"] = (
        df["是否越级"].str.lower().eq("true")
        | df["三级分类(详细模式)"].str.contains("越级", regex=False)
    )
    return df.sort_values(["onset_class", "point_id"]).reset_index(drop=True)


def point_list(group: pd.DataFrame) -> str:
    points = group[["point_id", "point_name"]].drop_duplicates()
    return "、".join(points.apply(lambda r: f"{r['point_id']} {r['point_name']}", axis=1))


def top_item(series: pd.Series, rank: int = 0) -> tuple[str, int]:
    counts = series.value_counts()
    if rank >= len(counts):
        return "", 0
    return str(counts.index[rank]), int(counts.iloc[rank])


def build_onset_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for onset in ONSET_ORDER:
        group = df[df["onset_class"].eq(onset)].copy()
        n = len(group)
        top_structure, top_structure_n = top_item(group["三级分类(详细模式)"])
        top_chain, top_chain_n = top_item(group["exact_chain"])
        slot_modes = []
        for slot in SLOTS:
            value, count = top_item(group[slot])
            slot_modes.append(f"{slot}={value} ({count}/{n})")
        rows.append(
            {
                "onset_class": onset,
                "point_count": n,
                "merged_point_count": int(group["一级分类"].eq("合流型").sum()),
                "merged_point_share": group["一级分类"].eq("合流型").mean(),
                "fully_distinct_point_count": int(
                    group["三级分类(详细模式)"].eq("全对立").sum()
                ),
                "fully_distinct_point_share": group[
                    "三级分类(详细模式)"
                ].eq("全对立").mean(),
                "leapfrog_point_count": int(group["is_leapfrog"].sum()),
                "leapfrog_point_share": group["is_leapfrog"].mean(),
                "S0_equals_S1_count": int(group["S0"].eq(group["S1"]).sum()),
                "S0_equals_S1_share": group["S0"].eq(group["S1"]).mean(),
                "S1_equals_S2_count": int(group["S1"].eq(group["S2"]).sum()),
                "S1_equals_S2_share": group["S1"].eq(group["S2"]).mean(),
                "S2_equals_S3_count": int(group["S2"].eq(group["S3"]).sum()),
                "S2_equals_S3_share": group["S2"].eq(group["S3"]).mean(),
                "structure_pattern_count": group[
                    "三级分类(详细模式)"
                ].nunique(),
                "top_structure_pattern": top_structure,
                "top_structure_count": top_structure_n,
                "top_structure_share": top_structure_n / n if n else np.nan,
                "exact_chain_count": group["exact_chain"].nunique(),
                "top_exact_chain": top_chain,
                "top_exact_chain_count": top_chain_n,
                "top_exact_chain_share": top_chain_n / n if n else np.nan,
                "slot_modal_values": "；".join(slot_modes),
            }
        )
    return pd.DataFrame(rows)


def build_structure_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for onset in ONSET_ORDER:
        group = df[df["onset_class"].eq(onset)]
        n = len(group)
        grouped = group.groupby(
            ["一级分类", "二级分类", "三级分类(详细模式)", "is_leapfrog"],
            observed=True,
            sort=False,
        )
        onset_rows = []
        for (level1, level2, detail, leapfrog), pattern_group in grouped:
            onset_rows.append(
                {
                    "onset_class": onset,
                    "level_1": level1,
                    "level_2": level2,
                    "structure_pattern": detail,
                    "is_leapfrog": bool(leapfrog),
                    "point_count": len(pattern_group),
                    "share_within_onset": len(pattern_group) / n if n else np.nan,
                    "point_list": point_list(pattern_group),
                }
            )
        onset_rows.sort(
            key=lambda r: (
                -int(r["point_count"]),
                STRUCTURE_ORDER.index(r["structure_pattern"])
                if r["structure_pattern"] in STRUCTURE_ORDER
                else 999,
            )
        )
        for rank, row in enumerate(onset_rows, start=1):
            row["rank_within_onset"] = rank
            rows.append(row)
    columns = [
        "onset_class",
        "rank_within_onset",
        "level_1",
        "level_2",
        "structure_pattern",
        "is_leapfrog",
        "point_count",
        "share_within_onset",
        "point_list",
    ]
    return pd.DataFrame(rows)[columns]


def build_chain_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for onset in ONSET_ORDER:
        group = df[df["onset_class"].eq(onset)]
        n = len(group)
        chain_rows = []
        for chain, chain_group in group.groupby("exact_chain", sort=False):
            first = chain_group.iloc[0]
            chain_rows.append(
                {
                    "onset_class": onset,
                    "exact_chain": chain,
                    "S0": first["S0"],
                    "S1": first["S1"],
                    "S2": first["S2"],
                    "S3": first["S3"],
                    "structure_pattern": first["三级分类(详细模式)"],
                    "point_count": len(chain_group),
                    "share_within_onset": len(chain_group) / n if n else np.nan,
                    "point_list": point_list(chain_group),
                }
            )
        chain_rows.sort(key=lambda r: (-int(r["point_count"]), str(r["exact_chain"])))
        for rank, row in enumerate(chain_rows, start=1):
            row["rank_within_onset"] = rank
            rows.append(row)
    columns = [
        "onset_class",
        "rank_within_onset",
        "exact_chain",
        "S0",
        "S1",
        "S2",
        "S3",
        "structure_pattern",
        "point_count",
        "share_within_onset",
        "point_list",
    ]
    return pd.DataFrame(rows)[columns]


def build_slot_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    value_rows: list[dict[str, object]] = []
    for onset in ONSET_ORDER:
        group = df[df["onset_class"].eq(onset)]
        n = len(group)
        for slot in SLOTS:
            slot_values = group[slot]
            top_value, top_n = top_item(slot_values, 0)
            second_value, second_n = top_item(slot_values, 1)
            diph_mask = slot_values.map(is_diphthong)
            unplaced_mask = slot_values.map(lambda value: vowel_coordinate(value) is None)
            summary_rows.append(
                {
                    "onset_class": onset,
                    "slot": slot,
                    "rhyme_group": SLOT_META[slot]["rhyme"],
                    "slot_initial": f"*{SLOT_META[slot]['initial']}",
                    "point_count": n,
                    "unique_value_count": slot_values.nunique(),
                    "top_value": top_value,
                    "top_value_count": top_n,
                    "top_value_share": top_n / n if n else np.nan,
                    "second_value": second_value,
                    "second_value_count": second_n,
                    "second_value_share": second_n / n if n else np.nan,
                    "diphthong_count": int(diph_mask.sum()),
                    "diphthong_share": diph_mask.mean(),
                    "unplaced_count": int(unplaced_mask.sum()),
                    "unplaced_share": unplaced_mask.mean(),
                }
            )

            counts = slot_values.value_counts()
            for rank, (value, count) in enumerate(counts.items(), start=1):
                value_group = group[group[slot].eq(value)]
                coord = vowel_coordinate(value)
                value_rows.append(
                    {
                        "onset_class": onset,
                        "slot": slot,
                        "rhyme_group": SLOT_META[slot]["rhyme"],
                        "slot_initial": f"*{SLOT_META[slot]['initial']}",
                        "rank_within_onset_slot": rank,
                        "mainlayer_value": value,
                        "vowel_components": component_label(value),
                        "is_diphthong": is_diphthong(value),
                        "plot_x_front_to_back": coord[0] if coord else np.nan,
                        "plot_y_close_to_open": coord[1] if coord else np.nan,
                        "coordinate_status": "placed" if coord else "needs_confirmation",
                        "point_count": int(count),
                        "share_within_onset_slot": count / n if n else np.nan,
                        "point_list": point_list(value_group),
                    }
                )
    return pd.DataFrame(summary_rows), pd.DataFrame(value_rows)


def build_point_table(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    unplaced_values = []
    for _, row in result.iterrows():
        items = []
        for slot in SLOTS:
            value = row[slot]
            if value and vowel_coordinate(value) is None:
                items.append(f"{slot}={value}")
        unplaced_values.append("、".join(items))
    result["unplaced_values"] = unplaced_values
    result["onset_class"] = result["onset_class"].astype(str)
    columns = [
        "point_id",
        "point_name",
        "onset_class",
        *SLOTS,
        "exact_chain",
        "slot_distinct_count",
        "一级分类",
        "二级分类",
        "三级分类(详细模式)",
        "is_leapfrog",
        "unplaced_values",
    ]
    return result[columns]


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def validate(
    df: pd.DataFrame,
    onset_summary: pd.DataFrame,
    structure: pd.DataFrame,
    chains: pd.DataFrame,
    slot_summary: pd.DataFrame,
    slot_values: pd.DataFrame,
    points: pd.DataFrame,
) -> None:
    assert len(df) == 410
    assert df["point_id"].nunique() == 82
    assert set(df["onset_class"].astype(str)) == set(ONSET_ORDER)
    assert df.groupby("onset_class", observed=True).size().eq(82).all()
    assert len(onset_summary) == 5
    assert structure.groupby("onset_class")["point_count"].sum().eq(82).all()
    assert chains.groupby("onset_class")["point_count"].sum().eq(82).all()
    assert len(slot_summary) == 20
    assert slot_values.groupby(["onset_class", "slot"])["point_count"].sum().eq(82).all()
    assert len(points) == 410


def main() -> None:
    df = load_data()
    onset_summary = build_onset_summary(df)
    structure = build_structure_table(df)
    chains = build_chain_table(df)
    slot_summary, slot_values = build_slot_tables(df)
    points = build_point_table(df)

    validate(df, onset_summary, structure, chains, slot_summary, slot_values, points)

    write_csv(onset_summary, ONSET_SUMMARY_OUTPUT)
    write_csv(structure, STRUCTURE_OUTPUT)
    write_csv(chains, CHAIN_OUTPUT)
    write_csv(slot_summary, SLOT_SUMMARY_OUTPUT)
    write_csv(slot_values, SLOT_VALUE_OUTPUT)
    write_csv(points, POINT_OUTPUT)

    print(onset_summary.to_string(index=False))
    print("\n输出：")
    for path in [
        ONSET_SUMMARY_OUTPUT,
        STRUCTURE_OUTPUT,
        CHAIN_OUTPUT,
        SLOT_SUMMARY_OUTPUT,
        SLOT_VALUE_OUTPUT,
        POINT_OUTPUT,
    ]:
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
