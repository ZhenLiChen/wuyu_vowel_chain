import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
from pathlib import Path
from PIL import Image
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import LightSource


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DICT = PROJECT_ROOT / "data_dict"
FIGS_DIR = PROJECT_ROOT / "figs" / "overview"
FIGS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_TERRAIN = DATA_DICT / "terrarium_wuyu_z8.png"

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
    "岱山岱西镇": (-22000, 1800),
}


def draw_cached_terrain(ax):
    """Render an unlabeled terrain background from Terrarium elevation tiles."""
    if not LOCAL_TERRAIN.exists():
        raise FileNotFoundError(f"Missing elevation mosaic: {LOCAL_TERRAIN}")
    radius = 20037508.342789244
    zoom = 8
    tile_width = 2 * radius / (2**zoom)
    extent = (
        -radius + 212 * tile_width,
        -radius + 216 * tile_width,
        radius - 107 * tile_width,
        radius - 103 * tile_width,
    )
    current_xlim = ax.get_xlim()
    xlim = (current_xlim[0] - 18_000, current_xlim[1] + 32_000)
    current_ylim = ax.get_ylim()
    ylim = (current_ylim[0] - 85_000, current_ylim[1] + 18_000)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    map_aspect = (xlim[1] - xlim[0]) / (ylim[1] - ylim[0])
    fig = ax.figure
    fig.set_size_inches(12, 12 / map_aspect, forward=True)
    tile = Image.open(LOCAL_TERRAIN).convert("RGB")
    width, height = tile.size
    left = max(0, int((xlim[0] - extent[0]) / (extent[1] - extent[0]) * width))
    right = min(width, int((xlim[1] - extent[0]) / (extent[1] - extent[0]) * width))
    top = max(0, int((extent[3] - ylim[1]) / (extent[3] - extent[2]) * height))
    bottom = min(height, int((extent[3] - ylim[0]) / (extent[3] - extent[2]) * height))
    rgb = np.asarray(tile.crop((left, top, right, bottom))).astype(np.float32)
    elevation = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768
    sea_mask = elevation < 0
    land_elevation = np.clip(elevation, 0, 1800)
    relief_cmap = LinearSegmentedColormap.from_list(
        "wuyu_relief",
        [
            (0.00, "#dce8c7"),
            (0.07, "#bed39f"),
            (0.28, "#92b57c"),
            (0.54, "#b7ad7f"),
            (0.78, "#d3c49b"),
            (1.00, "#f1eee3"),
        ],
    )
    cell_size = tile_width / 256
    image = LightSource(azdeg=315, altdeg=45).shade(
        land_elevation,
        cmap=relief_cmap,
        vert_exag=7,
        dx=cell_size,
        dy=cell_size,
        blend_mode="soft",
        vmin=0,
        vmax=1800,
    )
    image[sea_mask] = (0.58, 0.79, 0.86, 1.0)
    ax.imshow(
        image,
        extent=(xlim[0], xlim[1], ylim[0], ylim[1]),
        origin="upper",
        alpha=1.0,
        zorder=0,
        interpolation="bilinear",
    )
    if sea_mask.any() and (~sea_mask).any():
        crop_height, crop_width = elevation.shape
        xcoords = np.linspace(
            xlim[0] + (xlim[1] - xlim[0]) / (2 * crop_width),
            xlim[1] - (xlim[1] - xlim[0]) / (2 * crop_width),
            crop_width,
        )
        ycoords = np.linspace(
            ylim[0] + (ylim[1] - ylim[0]) / (2 * crop_height),
            ylim[1] - (ylim[1] - ylim[0]) / (2 * crop_height),
            crop_height,
        )
        ax.contour(
            xcoords,
            ycoords,
            elevation[::-1, :],
            levels=[0],
            colors=["#547b89"],
            linewidths=0.45,
            zorder=2,
        )
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_facecolor("#d2e0e2")
    return True


def set_chinese_font():
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    preferred_fonts = ["PingFang SC", "Heiti SC", "SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            plt.rcParams["font.sans-serif"] = [font_name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def plot_map(
    output_filename="wuyu_topography_map.png",
    legend_loc="upper left",
    legend_bbox=(0.76, 0.995),
    legend_style=None,
):
    coord_file = DATA_DICT / "point_coords_master.csv"
    if not coord_file.exists():
        print("❌ 错误：找不到坐标映射文件。请先填写坐标。")
        return

    df = pd.read_csv(coord_file)
    active_names = set()
    canonical_names = {}
    for point_file in (PROJECT_ROOT / "data_raw" / "points").glob("*.csv"):
        point_names = pd.read_csv(
            point_file,
            usecols=["point_name"],
            dtype=str,
            encoding="utf-8-sig",
        )["point_name"]
        names = point_names.dropna().str.strip()
        active_names.update(names)
        canonical_names.update({name: name for name in names})
    df["point_name"] = df["point_name"].astype(str).str.strip()
    df = df[df["point_name"].isin(active_names)].copy()
    df["point_name"] = df["point_name"].map(canonical_names)
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

    draw_cached_terrain(ax)
    print("已从高程栅格生成无地名地形底图。")

    for x, y, label in zip(
        gdf_web.geometry.x,
        gdf_web.geometry.y,
        gdf_web["point_name"],
    ):
        x_offset, y_offset = LABEL_OFFSETS.get(label, (1500, 1500))
        text = ax.text(
            x + x_offset,
            y + y_offset,
            label,
            fontsize=14,
            ha="left",
            va="bottom",
            fontweight="bold",
            zorder=4,
        )
        text.set_path_effects(
            [path_effects.withStroke(linewidth=2, foreground="white", alpha=0.7)]
        )

    legend_kwargs = {
        "title": "吴语小片分类",
        "loc": legend_loc,
        "bbox_to_anchor": legend_bbox,
        "frameon": True,
    }
    if legend_style:
        legend_kwargs.update(legend_style)
    ax.legend(**legend_kwargs)
    fig.text(
        0.99,
        0.006,
        "Elevation: AWS Terrain Tiles (Terrarium) · shaded relief generated from elevation data",
        ha="right",
        va="bottom",
        fontsize=6.5,
        color="#4B5563",
    )
    ax.set_axis_off()
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    output_png = FIGS_DIR / output_filename
    plt.savefig(
        output_png,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0,
        facecolor="white",
    )
    plt.close(fig)
    print(f"✅ 地图已成功生成并保存至: {output_png}")


if __name__ == "__main__":
    plot_map()
