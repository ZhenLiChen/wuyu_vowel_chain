# 这个做了一个逻辑处理，文读i层次被删掉了，可以做一个不处理的版本
import pandas as pd
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
from pathlib import Path
import ssl

# === 1. 基础环境修复 (SSL & Font) ===
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

def set_chinese_font():
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    preferred_fonts = ["PingFang SC", "Heiti SC", "SimHei", "Microsoft YaHei", "Arial Unicode MS"]
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams['font.sans-serif'] = [font_name]
            break

set_chinese_font()

# === 2. 路径配置 ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_CSV_PATH = PROJECT_ROOT / "data_clean" / "value_type" / "point_rhyme_inventory.csv"
DATA_DICT = PROJECT_ROOT / "data_dict"
FIGS_DIR = PROJECT_ROOT / "figs" / "vowel_inventory"
FIGS_DIR.mkdir(parents=True, exist_ok=True)

# === 3. 清洗逻辑 (去 i 存 u) ===
def clean_vowel_logic(v_str):
    v = v_str.strip()
    if not v: return None
    # 仅剔除齐齿类介音 i, j
    if len(v) > 1 and v[0] in ['i', 'j']:
        return v[1:]
    return v

# === 4. 核心分析流程 ===
def run_analysis():
    if not TARGET_CSV_PATH.exists():
        print(f"❌ 错误：找不到文件 {TARGET_CSV_PATH}")
        return
    
    df = pd.read_csv(TARGET_CSV_PATH)
    
    # A. 韵部合并
    rhyme_map = {
        '佳': '佳皆', '皆': '佳皆',
        '麻': '麻',
        '歌': '歌戈', '戈': '歌戈',
        '模': '模'
    }
    df = df[df['rhyme_modern'].isin(rhyme_map.keys())].copy()
    df['category'] = df['rhyme_modern'].map(rhyme_map)

    # B. 统计各组音值数
    point_results = []
    for (name, cat), group in df.groupby(['point_name', 'category']):
        all_raw = []
        for p_set in group['rhyme_phonetic_set']:
            all_raw.extend([s.strip() for s in str(p_set).split(',') if s.strip()])
        
        # 去i留u并去重
        cleaned_set = {clean_vowel_logic(v) for v in all_raw}
        point_results.append({
            'point_name': name,
            'category': cat,
            'inv_size': len(set(filter(None, cleaned_set)))
        })

    # C. 计算 4 位指纹 与 总复杂度
    res_df = pd.DataFrame(point_results)
    target_cats = ['佳皆', '麻', '歌戈', '模']
    
    pivot_df = res_df.pivot_table(index='point_name', columns='category', values='inv_size').fillna(0).astype(int)
    pivot_df = pivot_df.reindex(columns=target_cats, fill_value=0)
    
    # 关键计算：总复杂度 (颜色依据)
    pivot_df['total_complexity'] = pivot_df.sum(axis=1)
    # 关键计算：4位指纹 (标注依据)
    pivot_df['pattern'] = pivot_df[target_cats].apply(lambda x: "-".join(x.astype(str)), axis=1)

    # D. 合并地理数据
    coords_df = pd.read_csv(DATA_DICT / "point_coords_master.csv")
    coords_df.columns = coords_df.columns.str.strip()
    final_df = pivot_df.reset_index().merge(coords_df[['point_name', 'lat', 'lon']], on='point_name', how='left')
    final_df = final_df.dropna(subset=['lat', 'lon'])

    gdf = gpd.GeoDataFrame(final_df, geometry=gpd.points_from_xy(final_df.lon, final_df.lat), crs="EPSG:4326").to_crs(epsg=3857)

    # E. 绘图
    fig, ax = plt.subplots(figsize=(15, 12))
    
    # 改用连续色标 (cmap='YlOrRd' 代表从黄到红，红色越深越复杂)
    # 你也可以换成 'viridis' 或 'plasma'
    plot = gdf.plot(
        ax=ax, 
        column='total_complexity', 
        cmap='YlOrRd', 
        legend=True,
        legend_kwds={'label': "元音音值复杂度", 'orientation': "horizontal", 'pad': 0.05},
        markersize=200, 
        edgecolor='black', 
        linewidth=1, 
        alpha=0.9, 
        zorder=3
    )

    try:
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical, alpha=0.7, zorder=1)
    except:
        print("⚠️ 地图下载失败，使用空白底图")

    # 标注点名与 4 位指纹
    for x, y, name, pat, total in zip(gdf.geometry.x, gdf.geometry.y, gdf['point_name'], gdf['pattern'], gdf['total_complexity']):
        ax.text(x + 1200, y + 1200, f"{name}\n{pat}\nΣ={total}", 
                fontsize=8, fontweight='bold', ha='left',
                path_effects=[path_effects.withStroke(linewidth=3, foreground="white", alpha=0.8)])

    ax.set_title("吴语元音音值配列模式及复杂度地理分布 (佳皆/麻/歌戈/模)", fontsize=20, pad=30)
    ax.set_axis_off()

    output_path = FIGS_DIR / "vowel_complexity_gradient_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 大功告成！\n📍 颜色基于总音值数，标注保留 4 位指纹。\n📂 保存至：{output_path}")

if __name__ == "__main__":
    run_analysis()
