"""生成左下角放大半透明图例的地形图副本，不覆盖原图。"""

from plot_dialect_map import plot_map


if __name__ == "__main__":
    plot_map(
        output_filename="wuyu_topography_map_large_legend.png",
        legend_loc="lower left",
        legend_bbox=(0.018, 0.018),
        legend_style={
            "fontsize": 13.5,
            "title_fontsize": 16,
            "markerscale": 1.55,
            "framealpha": 0.58,
            "facecolor": "white",
            "edgecolor": "#4B5563",
            "fancybox": True,
            "borderpad": 1.0,
            "labelspacing": 0.72,
            "handletextpad": 0.8,
        },
    )
