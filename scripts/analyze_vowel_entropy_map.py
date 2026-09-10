import pandas as pd
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patheffects as path_effects
from pathlib import Path
import ssl

# === 1. 环境配置 ===
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError: pass

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
    if len(v) > 1 and v[0] in ['i', 'j']:
        return v[1:]
    return v

# === 4. 实际复杂度分析 ===
def run_entropy_analysis():
    if not TARGET_CSV_PATH.exists(): return
    df = pd.read_csv(TARGET_CSV_PATH)
    
    rhyme_map = {'佳': '佳皆', '皆': '佳皆', '麻': '麻', '歌': '歌戈', '戈': '歌戈', '模': '模'}
    df = df[df['rhyme_modern'].isin(rhyme_map.keys())].copy()
    
    # 按照方言点进行全局聚合
    point_data = []
    for name, group in df.groupby('point_name'):
        nominal_sum = 0
        all_unique_vowels = set()
        
        # 统计每个韵部的情况（用于计算名义总数和实际去重总数）
        for _, row in group.iterrows():
            raw_vals = [s.strip() for s in str(row['rhyme_phonetic_set']).split(',') if s.strip()]
            cleaned_vals = {clean_vowel_logic(v) for v in raw_vals if clean_vowel_logic(v)}
            
            nominal_sum += len(cleaned_vals) # 名义上的累加
            all_unique_vowels.update(cleaned_vals) # 全局去重
            
        actual_unique = len(all_unique_vowels)
        
        point_data.append({
            'point_name': name,
            'nominal_sum': nominal_sum,
            'actual_unique': actual_unique,
            'redundancy': nominal_sum - actual_unique, # 重合度/归并度
            'vowel_list': ",".join(sorted(list(all_unique_vowels)))
        })

    entropy_df = pd.DataFrame(point_data)

    # 合并坐标
    coords_df = pd.read_csv(DATA_DICT / "point_coords_master.csv")
    coords_df.columns = coords_df.columns.str.strip()
    final_df = entropy_df.merge(coords_df[['point_name', 'lat', 'lon']], on='point_name', how='left').dropna()
    
    gdf = gpd.GeoDataFrame(final_df, geometry=gpd.points_from_xy(final_df.lon, final_df.lat), crs="EPSG:4326").to_crs(epsg=3857)

    # --- 绘图：实际复杂度地图 ---
    fig, ax = plt.subplots(figsize=(15, 12))
    
    # 使用 YlGnBu 色标，深蓝色代表实际音位存量最丰富的地区
    gdf.plot(
        ax=ax, column='actual_unique', cmap='YlGnBu', legend=True,
        legend_kwds={'label': "实际音位复杂度 (跨韵部去重后的音值总数)", 'orientation': "horizontal", 'pad': 0.05},
        markersize=250, edgecolor='black', linewidth=1.5, alpha=0.9, zorder=3
    )

    try:
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical, alpha=0.7, zorder=1)
    except: pass

    for x, y, name, act, nom, red in zip(gdf.geometry.x, gdf.geometry.y, gdf['point_name'], 
                                        gdf['actual_unique'], gdf['nominal_sum'], gdf['redundancy']):
        # 标注：实际数 (名义数/重合数)
        label = f"{name}\nU={act}\n(Σ={nom}, R={red})"
        ax.text(x + 1200, y + 1200, label, fontsize=8, fontweight='bold', ha='left',
                path_effects=[path_effects.withStroke(linewidth=3, foreground="white", alpha=0.8)])

    ax.set_title("佳皆、麻韵、歌戈、模韵音值复杂度的地理分布 ", fontsize=20, pad=30)
    ax.set_axis_off()

    output_path = FIGS_DIR / "vowel_actual_entropy_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    
    print(f"\n✅ 实际复杂度分析完成！保存至：{output_path}")
    print("\n🔍 重点关注：")
    print("- U (Unique): 整个系统的实际音位‘弹药库’。")
    print("- R (Redundancy): 音值重合度。R 越高，说明该系统‘熵灭’越严重，跨韵部归并越彻底。")

if __name__ == "__main__":
    run_entropy_analysis()
