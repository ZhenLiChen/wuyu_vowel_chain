import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# === 1. 路径与参数设置 ===
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = PROJECT_ROOT / "data_raw"
FIGS_DIR = PROJECT_ROOT / "figs" / "overview"
FIGS_DIR.mkdir(parents=True, exist_ok=True)

# 颜色配置 (RGBA)
COLOR_SPLIT = "rgba(189, 195, 199, 0.4)"   # 分立型：中性灰
COLOR_MERGE = "rgba(52, 152, 219, 0.5)"    # 合流型：明亮蓝
COLOR_LEAP = "rgba(230, 126, 34, 0.8)"     # 越级：高饱和橙色
COLOR_NT = "rgba(155, 89, 182, 0.5)"       # N/T组：深紫色

# === 2. 加载与数据对齐 ===
input_path = DATA_RAW / "dialect_evolution_profiles_full.csv"
if not input_path.exists():
    raise FileNotFoundError(f"未找到数据文件：{input_path}")

df = pd.read_csv(input_path)

# --- 步骤 A: 方言点群组化 (基于 Combination 列) ---
# 统计每个组合包含哪些方言点名
group_info = df.groupby('Combination')['point_name'].apply(list).reset_index()

def get_group_label(points):
    points = sorted(list(set(points)))
    if len(points) > 1:
        return f"{points[0]}等{len(points)}点"
    return points[0]

group_info['group_node'] = group_info['point_name'].apply(get_group_label)
# 将群组名称映射回主表
df = df.merge(group_info[['Combination', 'group_node']], on='Combination', how='left')

# --- 步骤 B: 宽表转长表 (处理 5 个核心声组) ---
onsets = ['K', 'M', 'P', 'Ø', 'TS']
melted_rows = []

for _, row in df.iterrows():
    g_node = row['group_node']
    for ons in onsets:
        # 提取该声组的 L1, L2, L3 状态
        l1 = str(row[f'{ons}_L1']).strip()
        l2 = str(row[f'{ons}_L2']).strip()
        l3 = str(row[f'{ons}_L3']).strip()
        
        melted_rows.append({
            'group_node': g_node,
            'onset': ons,
            'L1': l1,
            'L2': l2,
            'L3': l3,
            'N_Status': str(row['N_Status']).strip(),
            'T_Status': str(row['T_Status']).strip()
        })

df_long = pd.DataFrame(melted_rows)

# === 3. 构建桑基图链路 (Links) ===
links = []

def add_link(source, target, value, color):
    links.append({'source': source, 'target': target, 'value': value, 'color': color})

# --- 流 A: 方言群组 -> L1 (一级分类) ---
flow_a = df_long.groupby(['group_node', 'L1']).size().reset_index(name='count')
for _, row in flow_a.iterrows():
    color = COLOR_SPLIT if '分立' in row['L1'] else COLOR_MERGE
    add_link(row['group_node'], "L1:" + row['L1'], row['count'], color)

# --- 流 B: L1 -> L2 (二级分类) ---
flow_b = df_long.groupby(['L1', 'L2']).size().reset_index(name='count')
for _, row in flow_b.iterrows():
    color = COLOR_SPLIT if '分立' in row['L1'] else COLOR_MERGE
    add_link("L1:" + row['L1'], "L2:" + row['L2'], row['count'], color)

# --- 流 C: L2 -> L3 (三级具体模式) ---
flow_c = df_long.groupby(['L2', 'L3']).size().reset_index(name='count')
for _, row in flow_c.iterrows():
    # 逻辑：检测 L3 中是否包含越级信息，或者根据之前的分类结果高亮
    color = COLOR_LEAP if '越级' in row['L3'] or 'S1=S3' in row['L3'] or 'S0=S2' in row['L3'] else COLOR_MERGE
    if '全对立' in row['L2'] or '全不等' in row['L2']:
        color = COLOR_SPLIT
    add_link("L2:" + row['L2'], "L3:" + row['L3'], row['count'], color)

# --- N/T 联动独立路径 ---
# 直接从群组连向 N_Status 和 T_Status
flow_n = df_long.drop_duplicates(['group_node', 'N_Status']).groupby(['group_node', 'N_Status']).size().reset_index(name='count')
for _, row in flow_n.iterrows():
    add_link(row['group_node'], "N组:" + row['N_Status'], row['count'], COLOR_NT)

flow_t = df_long.drop_duplicates(['group_node', 'T_Status']).groupby(['group_node', 'T_Status']).size().reset_index(name='count')
for _, row in flow_t.iterrows():
    add_link(row['group_node'], "T组:" + row['T_Status'], row['count'], COLOR_NT)

# === 4. 节点编码与渲染 ===
all_nodes = sorted(list(set([l['source'] for l in links] + [l['target'] for l in links])))
node_map = {node: i for i, node in enumerate(all_nodes)}

sankey_data = {
    'source': [node_map[l['source']] for l in links],
    'target': [node_map[l['target']] for l in links],
    'value': [l['value'] for l in links],
    'color': [l['color'] for l in links]
}

# 清理节点标签（去除内部使用的前缀）
clean_labels = []
for n in all_nodes:
    label = n
    for p in ["L1:", "L2:", "L3:", "N组:", "T组:"]:
        label = label.replace(p, "")
    clean_labels.append(label)

fig = go.Figure(data=[go.Sankey(
    node = dict(pad = 15, thickness = 20, line = dict(color = "black", width = 0.5), label = clean_labels),
    link = sankey_data
)])

fig.update_layout(
    title_text="吴语太湖片各方言点歌、模、麻、佳皆韵合并模式桑基图",
    font_size=12, width=1600, height=900
)

# 保存
html_path = FIGS_DIR / "sankey_evolution_profiles.html"
fig.write_html(str(html_path))
print(f"✅ 桑基图已保存：{html_path}")

# === 5. 描述性统计展示 (优化可读性版) ===
print("\n" + "="*60)
print("吴语元音演变模式描述性统计总结")
print("="*60)

# 1. 预先提取每个 Combination 对应的各声组特征 (取该组第一个方言点作为代表)
# 这一步是为了让输出能读到 K_L3, M_L3 等具体内容
features_rep = df.drop_duplicates('Combination').set_index('Combination')

# 2. 统计 Combination 出现的频次
pattern_counts = df.groupby('Combination')['point_name'].apply(list).reset_index()
pattern_counts['count'] = pattern_counts['point_name'].apply(len)
pattern_counts = pattern_counts.sort_values(
    by=['count', 'Combination'],
    ascending=[False, True],
).reset_index(drop=True)

top_n = 3
print(f"\n【演变模式 Top {top_n} 画像分析】")

stats_content = [] # 用于保存到文件


def describe_pattern(comb_id):
    k_v = features_rep.loc[comb_id, 'K_L3']
    m_v = features_rep.loc[comb_id, 'M_L3']
    p_v = features_rep.loc[comb_id, 'P_L3']
    o_v = features_rep.loc[comb_id, 'Ø_L3']
    ts_v = features_rep.loc[comb_id, 'TS_L3']
    n_v = features_rep.loc[comb_id, 'N_Status']
    t_v = features_rep.loc[comb_id, 'T_Status']
    return (
        f"K: {k_v}, M: {m_v}, P: {p_v}, "
        f"Ø: {o_v}, TS: {ts_v}, "
        f"N: {n_v}, T: {t_v}"
    )


def format_pattern_entry(index, row, total_points):
    comb_id = row['Combination']
    dialects = "、".join(row['point_name'])
    percent = row['count'] / total_points * 100
    return (
        f"NO.{index} 模式: {comb_id}\n"
        f"   核心特征: {describe_pattern(comb_id)}\n"
        f"   出现频次: {row['count']} 个方言点，占 {percent:.1f}%\n"
        f"   详细名单: {dialects}\n\n"
    )


def point_feature_frame(profile_df):
    core_onsets = ['K', 'M', 'P', 'Ø', 'TS']
    main_path = DATA_RAW / "mainlayer_merge.csv"

    if main_path.exists():
        main_df = pd.read_csv(main_path)
        for column in main_df.select_dtypes(include='object').columns:
            main_df[column] = main_df[column].astype(str).str.strip()

        for col, left, right in [
            ('m01', 'S0', 'S1'),
            ('m12', 'S1', 'S2'),
            ('m23', 'S2', 'S3'),
            ('m13', 'S1', 'S3'),
        ]:
            main_df[col] = (
                main_df[left].eq(main_df[right])
                & main_df[left].ne('')
                & main_df[right].ne('')
            )
        main_df['leap13'] = main_df['m13'] & ~main_df['m12'] & ~main_df['m23']
        main_df['merge_any'] = main_df['一级分类'].eq('合流型')

        feature_df = (
            main_df.groupby('point_name')
            .agg(
                core_merge_count=('merge_any', 'sum'),
                s23_count=('m23', 'sum'),
                s12_count=('m12', 'sum'),
                s01_count=('m01', 'sum'),
                leap13_count=('leap13', 'sum'),
                any_s23=('m23', 'any'),
                any_s12=('m12', 'any'),
                any_s01=('m01', 'any'),
                any_leap13=('leap13', 'any'),
                all_core_merge=('merge_any', 'all'),
            )
            .reset_index()
        )
        feature_df['core_split_count'] = len(core_onsets) - feature_df['core_merge_count']
        feature_df['all_core_split'] = feature_df['core_merge_count'].eq(0)
        feature_df['s23_count_ge4'] = feature_df['s23_count'].ge(4)

        for ons in core_onsets:
            onset_df = main_df[main_df['onset_class'].eq(ons)].set_index('point_name')
            feature_df[f'{ons}_L3'] = feature_df['point_name'].map(onset_df['三级分类(详细模式)'])
            feature_df[f'{ons}_m23'] = feature_df['point_name'].map(onset_df['m23'])
            feature_df[f'{ons}_m12'] = feature_df['point_name'].map(onset_df['m12'])
            feature_df[f'{ons}_m01'] = feature_df['point_name'].map(onset_df['m01'])
    else:
        feature_df = profile_df.copy()
        for ons in core_onsets:
            l1_col = f'{ons}_L1'
            l3_col = f'{ons}_L3'
            feature_df[f'{ons}_merge'] = feature_df[l1_col].eq('合流型')
            feature_df[f'{ons}_s23'] = feature_df[l3_col].str.contains('S2=S3', na=False)
            feature_df[f'{ons}_s12'] = feature_df[l3_col].str.contains('S1=S2', na=False)
            feature_df[f'{ons}_s01'] = feature_df[l3_col].str.contains('S0=S1', na=False)
            feature_df[f'{ons}_leap13'] = feature_df[l3_col].str.contains('S1=S3', na=False)

        feature_df['core_merge_count'] = feature_df[[f'{ons}_merge' for ons in core_onsets]].sum(axis=1)
        feature_df['core_split_count'] = len(core_onsets) - feature_df['core_merge_count']
        feature_df['s23_count'] = feature_df[[f'{ons}_s23' for ons in core_onsets]].sum(axis=1)
        feature_df['s12_count'] = feature_df[[f'{ons}_s12' for ons in core_onsets]].sum(axis=1)
        feature_df['s01_count'] = feature_df[[f'{ons}_s01' for ons in core_onsets]].sum(axis=1)
        feature_df['leap13_count'] = feature_df[[f'{ons}_leap13' for ons in core_onsets]].sum(axis=1)

        feature_df['all_core_split'] = feature_df['core_merge_count'].eq(0)
        feature_df['all_core_merge'] = feature_df['core_merge_count'].eq(len(core_onsets))
        feature_df['any_s23'] = feature_df['s23_count'].gt(0)
        feature_df['any_s12'] = feature_df['s12_count'].gt(0)
        feature_df['any_s01'] = feature_df['s01_count'].gt(0)
        feature_df['any_leap13'] = feature_df['leap13_count'].gt(0)
        feature_df['s23_count_ge4'] = feature_df['s23_count'].ge(4)

    status_df = profile_df.drop_duplicates('point_name').set_index('point_name')
    feature_df['N_Status'] = feature_df['point_name'].map(status_df['N_Status'])
    feature_df['T_Status'] = feature_df['point_name'].map(status_df['T_Status'])
    feature_df['Combination'] = feature_df['point_name'].map(status_df['Combination'])

    feature_df['K_dual'] = feature_df['K_L3'].eq('S0=S1，S2=S3')
    feature_df['M_continuous'] = feature_df['M_L3'].eq('S1=S2=S3')
    feature_df['N_merge'] = feature_df['N_Status'].eq('合流')
    feature_df['T_merge'] = feature_df['T_Status'].eq('合流')
    feature_df['NT_both_merge'] = feature_df['N_merge'] & feature_df['T_merge']
    feature_df['NT_both_split'] = ~feature_df['N_merge'] & ~feature_df['T_merge']
    feature_df['NT_same'] = feature_df['N_merge'].eq(feature_df['T_merge'])

    return feature_df


def point_list(feature_df, mask, limit=12):
    points = feature_df.loc[mask, 'point_name'].tolist()
    shown = "、".join(points[:limit])
    if len(points) > limit:
        shown += f"等{len(points)}点"
    return shown if shown else "无"


def implication_line(feature_df, condition, target, label):
    mask = feature_df[condition].astype(bool)
    target_mask = feature_df[target].astype(bool)
    support = int(mask.sum())
    hit = int((mask & target_mask).sum())
    exceptions = feature_df.loc[mask & ~target_mask, 'point_name'].tolist()
    confidence = hit / support * 100 if support else 0
    exception_text = "无" if not exceptions else "、".join(exceptions)
    return (
        f"- {label}: {hit}/{support}，置信度 {confidence:.1f}%；"
        f"反例：{exception_text}\n"
    )


def append_point_implication_section(stats_content, profile_df):
    feature_df = point_feature_frame(profile_df)
    total_points = len(feature_df)

    stats_content.append("\n点级分合类型学蕴涵关系\n")
    stats_content.append("="*60 + "\n")
    stats_content.append(
        "口径：每个方言点作为 1 个单位；核心声母条件为 K/M/P/Ø/TS；"
        "N/T 因 S0、S1 缺位较多，作为独立状态观察。\n\n"
    )

    stats_content.append("一、点级指标总览\n")
    stats_content.append(
        f"- 五个核心声母全分立：{int(feature_df['all_core_split'].sum())}/{total_points} 点；"
        f"名单：{point_list(feature_df, feature_df['all_core_split'])}\n"
    )
    stats_content.append(
        f"- 五个核心声母全有合流：{int(feature_df['all_core_merge'].sum())}/{total_points} 点。\n"
    )
    stats_content.append(
        f"- 至少一个核心声母有 S2=S3：{int(feature_df['any_s23'].sum())}/{total_points} 点。\n"
    )
    stats_content.append(
        f"- 至少一个核心声母有 S1=S2：{int(feature_df['any_s12'].sum())}/{total_points} 点。\n"
    )
    stats_content.append(
        f"- 至少一个核心声母有 S0=S1：{int(feature_df['any_s01'].sum())}/{total_points} 点。\n"
    )
    stats_content.append(
        f"- N/T 同进退：{int(feature_df['NT_same'].sum())}/{total_points} 点；"
        f"其中 N/T 均合流 {int(feature_df['NT_both_merge'].sum())} 点，"
        f"N/T 均分立 {int(feature_df['NT_both_split'].sum())} 点。\n\n"
    )

    stats_content.append("二、强蕴涵关系\n")
    stats_content.append(
        implication_line(
            feature_df,
            'all_core_split',
            'NT_both_split',
            "五个核心声母全分立 => N/T 也均分立",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            'any_s01',
            'any_s23',
            "方言点内只要出现 S0=S1 => 同点也出现 S2=S3",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            'M_continuous',
            'all_core_merge',
            "M 组达到 S1=S2=S3 => 五个核心声母均已有某种合流",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            's23_count_ge4',
            'NT_both_merge',
            "S2=S3 扩展到至少四个核心声母 => N/T 均合流",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            'any_leap13',
            'any_s23',
            "出现 S1=S3 越级 => 同点也出现 S2=S3",
        )
    )
    stats_content.append("注意：S1=S3 越级只有 2 点，支持量低，只能作为边缘现象记录。\n\n")

    stats_content.append("三、高概率蕴涵关系\n")
    stats_content.append(
        implication_line(
            feature_df,
            'K_dual',
            'NT_both_merge',
            "K 组出现 S0=S1，S2=S3 断裂双合并 => N/T 多数均合流",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            'NT_both_merge',
            'all_core_merge',
            "N/T 均合流 => 五个核心声母多数也全有合流",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            'any_s01',
            'all_core_merge',
            "出现 S0=S1 => 多数已经不是局部合流，而是核心声母广泛合流",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            'any_s12',
            'any_s23',
            "出现 S1=S2 => 多数同点也出现 S2=S3",
        )
    )
    stats_content.append(
        implication_line(
            feature_df,
            'all_core_merge',
            'NT_both_merge',
            "五个核心声母全有合流 => 多数 N/T 也均合流",
        )
    )
    stats_content.append("\n")

    stats_content.append("四、关键反例与分支解释\n")
    stats_content.append(
        "- 五个核心声母全有合流但 N/T 没有均合流的点："
        f"{point_list(feature_df, feature_df['all_core_merge'] & ~feature_df['NT_both_merge'], limit=20)}。\n"
    )
    stats_content.append(
        "  这些点说明“核心声母全合流”本身有两条路：一条是 S2=S3 向外扩展的高端合流路，"
        "另一条是 S1=S2 较突出的中层合流路；后者不一定带动 N/T。\n"
    )
    stats_content.append(
        "- N/T 不同进退的点："
        f"{point_list(feature_df, ~feature_df['NT_same'], limit=20)}。\n"
    )
    stats_content.append(
        "  N/T 总体高度同向，但这几个点提示鼻音、塞音条件仍可能有局部差异。\n\n"
    )

    stats_content.append("五、类型学解释\n")
    stats_content.append(
        "1. S2=S3 是最基础的合流层。只要一个方言点已经出现 S0=S1，"
        "它一定也已经在某处出现 S2=S3，因此低端合流不是独立起步，而是建立在高端合流之后。\n"
    )
    stats_content.append(
        "2. K 组的 S0=S1，S2=S3 是“高级阶段”信号。它几乎总是伴随 N/T 均合流，"
        "说明 K 组一旦发生断裂双合并，往往已经进入系统性重组。\n"
    )
    stats_content.append(
        "3. M 组的 S1=S2=S3 是“核心声母全面合流”信号。它不必然带动 N/T，"
        "但一旦出现，五个核心声母通常都不再保持全分立。\n"
    )
    stats_content.append(
        "4. N/T 均合流比单个核心声母合流更像系统阈值。尤其当 S2=S3 扩展到四个以上核心声母时，"
        "N/T 均合流没有反例。\n"
    )
    stats_content.append(
        "5. 因此点级演变可以粗略理解为：全分立 -> 局部 S2=S3 -> 多声母 S2=S3 -> "
        "K 组断裂双合并或 M 组连续三合一 -> N/T 也进入合流。"
        "但临绍、萧山、象山等点显示出另一条以 S1=S2 为中心的分支，不一定同步带动 N/T。\n\n"
    )


for i, (_, row) in enumerate(pattern_counts.head(top_n).iterrows()):
    comb_id = row['Combination']
    dialects = "、".join(row['point_name'])
    feature_desc = describe_pattern(comb_id)
    
    # 打印到控制台
    print(f"NO.{i+1} 模式: {comb_id}")
    print(f"   ➤ 核心特征: {feature_desc}")
    print(f"   ➤ 出现频次: {row['count']} 个方言点")
    print(f"   ➤ 代表方言: {dialects}\n")
    
    # 存入列表准备写入文件
    stats_content.append(format_pattern_entry(i + 1, row, len(df)))

high_to_low = pattern_counts.reset_index(drop=True)
low_to_high = pattern_counts.sort_values(
    by=['count', 'Combination'],
    ascending=[True, True],
).reset_index(drop=True)

stats_content.append("\n所有模式频次排行（高到低）\n")
stats_content.append("="*60 + "\n")
for i, row in high_to_low.iterrows():
    stats_content.append(format_pattern_entry(i + 1, row, len(df)))

stats_content.append("\n所有模式频次索引（低到高）\n")
stats_content.append("="*60 + "\n")
for i, row in low_to_high.iterrows():
    stats_content.append(format_pattern_entry(i + 1, row, len(df)))

append_point_implication_section(stats_content, df)

# 3. 将美化后的结果保存到文件
stats_path = FIGS_DIR / "evolution_descriptive_stats.txt"
with open(stats_path, "w", encoding="utf-8") as f:
    f.write("吴语元音演变模式描述性统计总结\n")
    f.write("="*60 + "\n")
    f.writelines(stats_content)

print(f"✅ 易读版统计报告已保存至: {stats_path}")
