import ssl
from pathlib import Path

import contextily as ctx
import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
import matplotlib.pyplot as plt
import pandas as pd


try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
DATA_DICT = PROJECT_ROOT / "data_dict"
DATA_CLEAN = PROJECT_ROOT / "data_clean"
VALUE_DIR = DATA_CLEAN / "value_type"
FIGS_DIR = PROJECT_ROOT / "figs"

INPUT_PATH = DATA_RAW / "mainlayer_merge.csv"
COORD_PATH = DATA_DICT / "point_coords_master.csv"
OUTPUT_CSV = VALUE_DIR / "point_s0_s3_mainlayer_merge_vowel_complexity.csv"
UNIQUE_MAP = FIGS_DIR / "s0_s3_mainlayer_merge_vowel_complexity_unique_map.png"
REPEAT_MAP = FIGS_DIR / "s0_s3_mainlayer_merge_vowel_complexity_repeat_map.png"

TARGET_SLOTS = ["S0", "S1", "S2", "S3"]
TILE_SOURCES = [
    ctx.providers.Esri.WorldTopoMap,
    ctx.providers.OpenStreetMap.Mapnik,
    ctx.providers.CartoDB.Positron,
]


def set_chinese_font() -> None:
    available = {f.name for f in fm.fontManager.ttflist}
    for name in ["PingFang SC", "Heiti SC", "SimHei", "Microsoft YaHei", "Arial Unicode MS"]:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def clean_symbol(value) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).replace("\u00a0", " ").strip()
    if not value or value.lower() == "nan":
        return None
    return value


def build_complexity_table() -> pd.DataFrame:
    df = pd.read_csv(INPUT_PATH)
    coords = pd.read_csv(COORD_PATH)
    coords.columns = [col.strip().lstrip("\ufeff") for col in coords.columns]
    coords["point_name"] = coords["point_name"].astype("string").str.strip()

    for col in ["point_id", "point_name", "onset_class", *TARGET_SLOTS]:
        df[col] = df[col].astype("string").str.strip()

    rows = []
    for (point_id, point_name), group in df.groupby(["point_id", "point_name"], dropna=False):
        slot_values: dict[str, list[str]] = {slot: [] for slot in TARGET_SLOTS}
        all_values: list[str] = []
        for slot in TARGET_SLOTS:
            values = [clean_symbol(v) for v in group[slot].tolist()]
            values = [v for v in values if v is not None]
            slot_values[slot] = values
            all_values.extend(values)

        unique_values = sorted(set(all_values))
        token_count = len(all_values)
        unique_count = len(unique_values)
        repeat_load = token_count - unique_count
        repeat_ratio = repeat_load / token_count if token_count else 0.0

        row = {
            "point_id": point_id,
            "point_name": point_name,
            "token_count": token_count,
            "unique_vowel_count": unique_count,
            "repeat_load": repeat_load,
            "repeat_ratio": repeat_ratio,
            "unique_vowel_set": ", ".join(unique_values),
        }
        for slot in TARGET_SLOTS:
            slot_unique = sorted(set(slot_values[slot]))
            row[f"{slot}_unique_vowel_count"] = len(slot_unique)
            row[f"{slot}_vowel_set"] = ", ".join(slot_unique)
        rows.append(row)

    summary = pd.DataFrame(rows)
    summary = summary.merge(coords[["point_name", "subbranch", "lat", "lon"]], on="point_name", how="left")
    return summary.sort_values(["subbranch", "point_id", "point_name"]).reset_index(drop=True)


def add_basemap(ax) -> str | None:
    errors = []
    for source in TILE_SOURCES:
        try:
            ctx.add_basemap(ax, source=source, zoom=8, alpha=0.72, zorder=1)
            return None
        except Exception as exc:
            errors.append(f"{source['name']}: {type(exc).__name__}: {exc}")
    return " ; ".join(errors)


def draw_map(
    gdf: gpd.GeoDataFrame,
    column: str,
    title: str,
    output: Path,
    legend_label: str,
) -> str | None:
    fig, ax = plt.subplots(figsize=(12, 10))
    gdf.plot(
        ax=ax,
        column=column,
        cmap="YlOrRd",
        legend=True,
        legend_kwds={"label": legend_label, "orientation": "horizontal", "pad": 0.03},
        markersize=160,
        edgecolor="white",
        linewidth=0.9,
        alpha=0.95,
        zorder=3,
    )

    tile_error = add_basemap(ax)

    for _, row in gdf.iterrows():
        label = f"{row['point_name']}\n{row[column]:.2f}" if isinstance(row[column], float) and column == "repeat_ratio" else f"{row['point_name']}\n{int(round(row[column]))}"
        text = ax.text(
            row.geometry.x + 1600,
            row.geometry.y + 1200,
            label,
            fontsize=6.8,
            ha="left",
            va="bottom",
            zorder=4,
        )
        text.set_path_effects([path_effects.withStroke(linewidth=2, foreground="white", alpha=0.75)])

    ax.set_title(title, fontsize=16, pad=18)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output, dpi=260, bbox_inches="tight")
    plt.close(fig)
    return tile_error


def run() -> None:
    set_chinese_font()
    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    summary = build_complexity_table()
    summary.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    map_df = summary.dropna(subset=["lat", "lon"]).copy()
    gdf = gpd.GeoDataFrame(
        map_df,
        geometry=gpd.points_from_xy(map_df["lon"], map_df["lat"]),
        crs="EPSG:4326",
    ).to_crs(epsg=3857)

    unique_tile_error = draw_map(
        gdf,
        column="unique_vowel_count",
        title="S0-S3 主体层元音复杂度地图（去重库藏，基于 mainlayer_merge）",
        output=UNIQUE_MAP,
        legend_label="音值复杂度",
    )
    repeat_tile_error = draw_map(
        gdf,
        column="repeat_load",
        title="S0-S3 主体层元音复杂度地图（不去重重复压力，基于 mainlayer_merge）",
        output=REPEAT_MAP,
        legend_label="重复压力",
    )

    print(f"已生成主体层复杂度表：{OUTPUT_CSV}")
    print(f"已生成去重复杂度地图：{UNIQUE_MAP}")
    print(f"已生成不去重重复压力地图：{REPEAT_MAP}")
    print("说明：mainlayer_merge 下每点固定 20 个 token，因此“不去重总数”恒为 20，不适合作图。")
    print("本脚本改用 repeat_load = token_count - unique_vowel_count 作为不去重视角。")
    if unique_tile_error:
        print(f"去重图底图加载失败：{unique_tile_error}")
    if repeat_tile_error:
        print(f"重复压力图底图加载失败：{repeat_tile_error}")


if __name__ == "__main__":
    run()
