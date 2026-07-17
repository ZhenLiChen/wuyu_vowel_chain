import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DICT = PROJECT_ROOT / "data_dict"
FIGS_DIR = PROJECT_ROOT / "figs"
FIGS_DIR.mkdir(exist_ok=True)

SHANGHAI_DENSE_BOUNDS = {
    "lon_min": 120.85,
    "lon_max": 121.82,
    "lat_min": 30.92,
    "lat_max": 31.68,
}

LABEL_OFFSETS = {
    "杭州城区": (-6000, -1500),
    "彭埠镇": (2200, 3200),
    "启东吕四": (2400, 1200),
}


def set_chinese_font():
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    preferred_fonts = ["PingFang SC", "Heiti SC", "SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def plot_map():
    coord_file = DATA_DICT / "point_coords_master.csv"
    if not coord_file.exists():
        print("❌ 错误：找不到坐标映射文件。请先填写坐标。")
        return

    df = pd.read_csv(coord_file)
    df = df.dropna(subset=["lat", "lon"])
    if df.empty:
        print("⚠️ 警告：坐标映射表中没有有效的经纬度数据。")
        return

    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["lon"], df["lat"]),
        crs="EPSG:4326",
    )
    gdf_web = gdf.to_crs(epsg=3857)

    set_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 12))

    subbranches = gdf_web["subbranch"].unique()
    cmap = plt.get_cmap("tab10")
    color_map = {sub: cmap(i) for i, sub in enumerate(subbranches)}

    for sub in subbranches:
        subset = gdf_web[gdf_web["subbranch"] == sub]
        subset.plot(
            ax=ax,
            color=color_map[sub],
            label=sub,
            markersize=80,
            edgecolor="white",
            linewidth=1,
            alpha=0.9,
            zorder=3,
        )

    ctx.add_basemap(
        ax,
        source=ctx.providers.Esri.WorldPhysical,
        alpha=0.6,
        zorder=1,
    )

    dense_mask = (
        (df["lon"] >= SHANGHAI_DENSE_BOUNDS["lon_min"])
        & (df["lon"] <= SHANGHAI_DENSE_BOUNDS["lon_max"])
        & (df["lat"] >= SHANGHAI_DENSE_BOUNDS["lat_min"])
        & (df["lat"] <= SHANGHAI_DENSE_BOUNDS["lat_max"])
    )

    for x, y, label, is_dense in zip(
        gdf_web.geometry.x,
        gdf_web.geometry.y,
        gdf_web["point_name"],
        dense_mask,
    ):
        x_offset, y_offset = LABEL_OFFSETS.get(label, (1500, 1500))
        text = ax.text(
            x + x_offset,
            y + y_offset,
            label,
            fontsize=7.6 if is_dense else 8.8,
            ha="left",
            va="bottom",
            fontweight="bold",
            zorder=4,
        )
        text.set_path_effects(
            [path_effects.withStroke(linewidth=2, foreground="white", alpha=0.7)]
        )

    ax.legend(
        title="吴语小片分类",
        loc="upper left",
        bbox_to_anchor=(0.76, 0.995),
        frameon=True,
    )
    ax.set_title("吴语太湖片方言采样点地理分布及地形地貌图", fontsize=18, pad=20)
    ax.set_axis_off()

    output_png = FIGS_DIR / "wuyu_topography_map.png"
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ 地图已成功生成并保存至: {output_png}")


if __name__ == "__main__":
    plot_map()
