import pandas as pd
import plotly.express as px
from pathlib import Path

# === 1. 路径设置 ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
FIGS_DIR = PROJECT_ROOT / "figs"
FIGS_DIR.mkdir(parents=True, exist_ok=True)

# === 2. 加载数据 ===
file_name = "mainlayer_merge.csv"
input_path = DATA_RAW / file_name

if not input_path.exists():
    raise FileNotFoundError(f"未找到输入文件：{input_path}")

df = pd.read_csv(input_path, encoding='utf-8')

# === 3. 数据清洗与描述性统计计算 ===
# 清洗分类列的空格
for col in ['一级分类', '二级分类', '三级分类(详细模式)']:
    df[col] = df[col].astype(str).str.strip()

# 统一处理布尔值
df['is_leap'] = df['是否越级'].apply(lambda x: str(x).strip().lower() == 'true')

# 统计描述
def count_percent(series):
    counts = series.value_counts()
    return [
        f"• {idx}: {int(val)} ({val / len(df) * 100:.1f}%)"
        for idx, val in counts.items()
    ]

l1_lines = count_percent(df['一级分类'])
l2_lines = count_percent(df['二级分类'])
l3_lines = count_percent(df['三级分类(详细模式)'])
leap_count = int(df['is_leap'].sum())
leap_percent = leap_count / len(df) * 100

stats_text = (
    "<b>描述性统计</b><br>"
    "--------------------------------<br>"
    "<b>[一级分类]</b><br>"
    + "<br>".join(l1_lines)
    + "<br><br><b>[二级分类]</b><br>"
    + "<br>".join(l2_lines)
    + "<br><br><b>[详细模式 Top 5]</b><br>"
    + "<br>".join(l3_lines[:5])
    + "<br><br><b>[越级合并]</b><br>"
    + f"• <span style='color:#9f1239;'><b>S1=S3 [越级]: {leap_count} ({leap_percent:.1f}%)</b></span>"
)

# === 4. 视觉编码 (颜色映射) ===
def assign_visual_group(row):
    if row['一级分类'] == '分立型':
        return '全对立'
    if row['is_leap']:
        return '越级合并'
    if row['二级分类'] == '多元合并':
        return '多元合并'
    return '单一合并'

df['VisualGroup'] = df.apply(assign_visual_group, axis=1)
df['label'] = df['point_name'] + "(" + df['onset_class'] + ")"
df['sunburst_l2'] = df.apply(
    lambda row: '全对立' if row['一级分类'] == '分立型'
    else f"{row['二级分类']}｜{row['三级分类(详细模式)']}",
    axis=1,
)

color_map = {
    '全对立': '#5b8c85',
    '单一合并': '#e6a23c',
    '多元合并': '#d97706',
    '越级合并': '#9f1239',
}

# === 5. 绘制旭日图 ===
fig = px.sunburst(
    df,
    path=['一级分类', 'sunburst_l2', 'label'],
    color='VisualGroup',
    color_discrete_map=color_map,
    branchvalues='total'
)

# 样式精修：增加百分比显示
fig.update_traces(
    # label: 名字, percent entry: 占总体的百分比
    textinfo='label+percent entry', 
    insidetextorientation='radial',
    marker=dict(line=dict(color='white', width=1)),
    hovertemplate='<b>%{label}</b><br>占比: %{percentEntry:.1%}'
)

# === 6. 添加侧边描述性统计看板 (Annotation) ===
fig.add_annotation(
    text=stats_text,
    align='left',
    showarrow=False,
    xref='paper', yref='paper',
    x=1.18, y=0.5,  # 将看板置于图表右侧
    bordercolor='black',
    borderwidth=1,
    borderpad=10,
    bgcolor='rgba(255,255,255,0.8)', # 半透明背景
    font=dict(size=11, family="Arial")
)

# 调整整体布局，给右侧看板留出空间
fig.update_layout(
    title_text="太湖片吴语歌、模、麻、佳皆韵主体层合并模式图",
    title_x=0.38,
    margin=dict(t=80, l=50, r=250, b=50), # 增加右边距 (r=250)
    width=1100, height=800
)

# === 7. 导出文件 ===
html_out = FIGS_DIR / "vowel_chain_sunburst_stats.html"
fig.write_html(str(html_out))

# 如果需要图片导出，请确保安装了 kaleido (pip install kaleido)
img_out = FIGS_DIR / "vowel_chain_sunburst_stats.png"
try:
    fig.write_image(str(img_out), scale=3)
    print(f"✅ 带有统计看板的图片已保存：{img_out}")
except:
    print("⚠️ 仅生成交互式 HTML 报告。")

print(f"✅ 描述性统计旭日图已完成！")
