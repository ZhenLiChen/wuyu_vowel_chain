import math
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MERGE_DIR = PROJECT_ROOT / "data_clean" / "merge_analysis"
DATA_DICT = PROJECT_ROOT / "data_dict"

INPUT_PATH = MERGE_DIR / "point_onset_merge_rates.csv"
COORD_PATH = DATA_DICT / "point_coords_master.csv"
POINT_OUTPUT = MERGE_DIR / "point_merge_strength_summary.csv"
CLUSTER_OUTPUT = MERGE_DIR / "point_merge_strength_clusters.csv"
REPORT_OUTPUT = MERGE_DIR / "merge_strength_cluster_report.txt"

MERGE_COLS = ["merge_S0_S1", "merge_S1_S2", "merge_S2_S3"]
FEATURE_COLS = ["avg_S0_S1", "avg_S1_S2", "avg_S2_S3"]
METHODS = ["kmeans", "hier_ward", "hier_average", "hier_complete"]
K_RANGE = range(2, 7)


def classify_dominant_stage(row: pd.Series) -> str:
    values = row[FEATURE_COLS].astype(float)
    if values.max() < 0.12:
        return "overall_low"
    if values["avg_S2_S3"] >= values["avg_S1_S2"] and values["avg_S2_S3"] >= values["avg_S0_S1"]:
        if values["avg_S0_S1"] >= 0.20:
            return "S2_S3_plus_S0_S1"
        return "S2_S3_dominant"
    if values["avg_S1_S2"] >= values["avg_S0_S1"]:
        return "S1_S2_dominant"
    return "S0_S1_dominant"


def zscore_matrix(x: np.ndarray) -> np.ndarray:
    means = x.mean(axis=0)
    stds = x.std(axis=0, ddof=0)
    stds[stds == 0] = 1.0
    return (x - means) / stds


def pairwise_distances(x: np.ndarray) -> np.ndarray:
    diff = x[:, None, :] - x[None, :, :]
    return np.sqrt((diff * diff).sum(axis=2))


def initialize_centers(x: np.ndarray, k: int) -> np.ndarray:
    first_idx = int(np.argmin(x.sum(axis=1)))
    centers = [x[first_idx]]
    while len(centers) < k:
        existing = np.vstack(centers)
        distances = ((x[:, None, :] - existing[None, :, :]) ** 2).sum(axis=2)
        min_distances = distances.min(axis=1)
        centers.append(x[int(np.argmax(min_distances))])
    return np.vstack(centers)


def kmeans(x: np.ndarray, k: int, max_iter: int = 100) -> np.ndarray:
    centers = initialize_centers(x, k)
    labels = np.zeros(len(x), dtype=int)
    for _ in range(max_iter):
        distances = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        new_labels = distances.argmin(axis=1)
        if np.array_equal(labels, new_labels):
            break
        labels = new_labels
        for cluster_id in range(k):
            mask = labels == cluster_id
            if mask.any():
                centers[cluster_id] = x[mask].mean(axis=0)
    return relabel_by_centroid(labels, x)


def agglomerative(x: np.ndarray, k: int, linkage: str) -> np.ndarray:
    dist = pairwise_distances(x)
    clusters = [{"members": [i], "size": 1, "centroid": x[i]} for i in range(len(x))]

    while len(clusters) > k:
        best_pair = None
        best_value = math.inf
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                value = cluster_distance(clusters[i], clusters[j], dist, linkage)
                if value < best_value:
                    best_value = value
                    best_pair = (i, j)

        i, j = best_pair
        merged_members = clusters[i]["members"] + clusters[j]["members"]
        merged_size = clusters[i]["size"] + clusters[j]["size"]
        merged_centroid = (
            clusters[i]["centroid"] * clusters[i]["size"] + clusters[j]["centroid"] * clusters[j]["size"]
        ) / merged_size
        clusters[i] = {"members": merged_members, "size": merged_size, "centroid": merged_centroid}
        clusters.pop(j)

    labels = np.zeros(len(x), dtype=int)
    for cluster_id, cluster in enumerate(clusters):
        labels[cluster["members"]] = cluster_id
    return relabel_by_centroid(labels, x)


def cluster_distance(cluster_a: dict, cluster_b: dict, dist: np.ndarray, linkage: str) -> float:
    members_a = cluster_a["members"]
    members_b = cluster_b["members"]
    pairwise = dist[np.ix_(members_a, members_b)]

    if linkage == "average":
        return float(pairwise.mean())
    if linkage == "complete":
        return float(pairwise.max())
    if linkage == "ward":
        n_a = cluster_a["size"]
        n_b = cluster_b["size"]
        diff = cluster_a["centroid"] - cluster_b["centroid"]
        return float((n_a * n_b) / (n_a + n_b) * np.dot(diff, diff))
    raise ValueError(f"Unsupported linkage: {linkage}")


def relabel_by_centroid(labels: np.ndarray, x: np.ndarray) -> np.ndarray:
    centers = []
    for cluster_id in sorted(np.unique(labels)):
        centers.append((cluster_id, x[labels == cluster_id].mean(axis=0)))
    ordered = sorted(centers, key=lambda item: tuple(item[1]))
    remap = {old_id: new_id for new_id, (old_id, _) in enumerate(ordered)}
    return np.array([remap[label] for label in labels], dtype=int)


def silhouette_score_from_distance(dist: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    if len(unique_labels) < 2:
        return float("-inf")

    silhouettes = []
    for idx in range(len(labels)):
        same_mask = labels == labels[idx]
        same_indices = np.where(same_mask)[0]
        if len(same_indices) <= 1:
            silhouettes.append(0.0)
            continue

        a_i = dist[idx, same_indices[same_indices != idx]].mean()
        b_i = math.inf
        for other_label in unique_labels:
            if other_label == labels[idx]:
                continue
            other_indices = np.where(labels == other_label)[0]
            b_i = min(b_i, float(dist[idx, other_indices].mean()))
        denom = max(a_i, b_i)
        silhouettes.append(0.0 if denom == 0 else (b_i - a_i) / denom)
    return float(np.mean(silhouettes))


def calinski_harabasz_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    n_samples = len(x)
    n_clusters = len(unique_labels)
    if n_clusters < 2 or n_clusters >= n_samples:
        return float("-inf")

    overall_mean = x.mean(axis=0)
    between = 0.0
    within = 0.0
    for cluster_id in unique_labels:
        members = x[labels == cluster_id]
        cluster_mean = members.mean(axis=0)
        between += len(members) * float(np.dot(cluster_mean - overall_mean, cluster_mean - overall_mean))
        centered = members - cluster_mean
        within += float((centered * centered).sum())
    if within == 0:
        return float("inf")
    return (between / (n_clusters - 1)) / (within / (n_samples - n_clusters))


def davies_bouldin_score(x: np.ndarray, labels: np.ndarray) -> float:
    unique_labels = np.unique(labels)
    n_clusters = len(unique_labels)
    if n_clusters < 2:
        return float("inf")

    centroids = []
    scatters = []
    for cluster_id in unique_labels:
        members = x[labels == cluster_id]
        centroid = members.mean(axis=0)
        centroids.append(centroid)
        scatters.append(float(np.sqrt(((members - centroid) ** 2).sum(axis=1)).mean()))
    centroids = np.vstack(centroids)
    scatters = np.array(scatters)

    centroid_dist = pairwise_distances(centroids)
    db_values = []
    for i in range(n_clusters):
        ratios = []
        for j in range(n_clusters):
            if i == j:
                continue
            denom = centroid_dist[i, j]
            if denom == 0:
                ratios.append(float("inf"))
            else:
                ratios.append((scatters[i] + scatters[j]) / denom)
        db_values.append(max(ratios))
    return float(np.mean(db_values))


def evaluate_solution(x: np.ndarray, dist: np.ndarray, labels: np.ndarray) -> dict:
    counts = pd.Series(labels).value_counts().sort_index()
    return {
        "n_clusters": int(len(np.unique(labels))),
        "min_cluster_size": int(counts.min()),
        "max_cluster_size": int(counts.max()),
        "silhouette": silhouette_score_from_distance(dist, labels),
        "calinski_harabasz": calinski_harabasz_score(x, labels),
        "davies_bouldin": davies_bouldin_score(x, labels),
    }


def generate_labels(x: np.ndarray, method: str, k: int) -> np.ndarray:
    if method == "kmeans":
        return kmeans(x, k)
    if method == "hier_ward":
        return agglomerative(x, k, linkage="ward")
    if method == "hier_average":
        return agglomerative(x, k, linkage="average")
    if method == "hier_complete":
        return agglomerative(x, k, linkage="complete")
    raise ValueError(f"Unsupported method: {method}")


def rank_solutions(score_df: pd.DataFrame) -> pd.DataFrame:
    ranked = score_df.copy()
    ranked["rank_silhouette"] = ranked["silhouette"].rank(method="min", ascending=False)
    ranked["rank_calinski"] = ranked["calinski_harabasz"].rank(method="min", ascending=False)
    ranked["rank_davies"] = ranked["davies_bouldin"].rank(method="min", ascending=True)
    ranked["rank_sum"] = ranked[["rank_silhouette", "rank_calinski", "rank_davies"]].sum(axis=1)
    ranked["min_cluster_penalty"] = (ranked["min_cluster_size"] < 3).astype(int) * 100
    ranked["final_rank_score"] = ranked["rank_sum"] + ranked["min_cluster_penalty"]
    return ranked.sort_values(
        ["final_rank_score", "rank_silhouette", "rank_calinski", "rank_davies", "method", "k"]
    ).reset_index(drop=True)


def label_clusters(df: pd.DataFrame, cluster_col: str) -> dict[int, str]:
    labels = {}
    centers = df.groupby(cluster_col)[FEATURE_COLS].mean()
    for cluster_id, row in centers.iterrows():
        labels[int(cluster_id)] = classify_dominant_stage(row)
    return labels


def run_analysis() -> None:
    rates = pd.read_csv(INPUT_PATH)
    rates.columns = [col.strip().lstrip("\ufeff") for col in rates.columns]
    for col in ["point_id", "point_name", "onset_class"]:
        rates[col] = rates[col].astype("string").str.strip()
    for col in MERGE_COLS:
        rates[col] = pd.to_numeric(rates[col], errors="coerce")

    summary = (
        rates.groupby(["point_id", "point_name"], dropna=False)
        .agg(
            avg_S0_S1=("merge_S0_S1", "mean"),
            avg_S1_S2=("merge_S1_S2", "mean"),
            avg_S2_S3=("merge_S2_S3", "mean"),
            valid_S0_S1_cells=("merge_S0_S1", "count"),
            valid_S1_S2_cells=("merge_S1_S2", "count"),
            valid_S2_S3_cells=("merge_S2_S3", "count"),
        )
        .reset_index()
    )

    coords = pd.read_csv(COORD_PATH)
    coords.columns = [col.strip().lstrip("\ufeff") for col in coords.columns]
    coords["point_name"] = coords["point_name"].astype("string").str.strip()
    coords = coords[["point_name", "subbranch", "lat", "lon"]]
    summary = summary.merge(coords, on="point_name", how="left")

    summary["dominant_stage_type"] = summary.apply(classify_dominant_stage, axis=1)
    summary = summary[
        [
            "point_id",
            "point_name",
            "subbranch",
            "lat",
            "lon",
            *FEATURE_COLS,
            "valid_S0_S1_cells",
            "valid_S1_S2_cells",
            "valid_S2_S3_cells",
            "dominant_stage_type",
        ]
    ].sort_values(["subbranch", "point_id", "point_name"])
    summary.to_csv(POINT_OUTPUT, index=False, encoding="utf-8-sig")

    cluster_df = summary.copy()
    x_raw = cluster_df[FEATURE_COLS].to_numpy(dtype=float)
    x = zscore_matrix(x_raw)
    dist = pairwise_distances(x)

    solutions = []
    label_store = {}
    for method in METHODS:
        for k in K_RANGE:
            labels = generate_labels(x, method, k)
            metrics = evaluate_solution(x, dist, labels)
            solutions.append({"method": method, "k": k, **metrics})
            label_store[(method, k)] = labels

    solution_df = rank_solutions(pd.DataFrame(solutions))
    best = solution_df.iloc[0]
    best_method = str(best["method"])
    best_k = int(best["k"])
    best_labels = label_store[(best_method, best_k)] + 1

    cluster_df["nbclust_method"] = best_method
    cluster_df["nbclust_k"] = best_k
    cluster_df["nbclust_cluster"] = best_labels
    cluster_df["nbclust_solution_id"] = cluster_df["nbclust_method"] + "_k" + cluster_df["nbclust_k"].astype(str)
    label_map = label_clusters(cluster_df, "nbclust_cluster")
    cluster_df["nbclust_cluster_label"] = cluster_df["nbclust_cluster"].map(label_map)
    cluster_df["nbclust_display_label"] = (
        "C" + cluster_df["nbclust_cluster"].astype(str) + " " + cluster_df["nbclust_cluster_label"].astype(str)
    )

    for _, row in solution_df.iterrows():
        method = str(row["method"])
        k = int(row["k"])
        prefix = f"{method}_k{k}"
        labels = label_store[(method, k)] + 1
        cluster_df[prefix] = labels
        label_map = label_clusters(cluster_df.assign(temp_cluster=labels), "temp_cluster")
        cluster_df[f"{prefix}_label"] = pd.Series(labels, index=cluster_df.index).map(label_map)

    cluster_df.to_csv(CLUSTER_OUTPUT, index=False, encoding="utf-8-sig")

    report_lines = [
        "合并强度与聚类结果说明",
        "=" * 40,
        "",
        "说明：",
        "严格来说，NbClust 是 R 里常用的聚类比较包。",
        "本脚本没有直接调用 R/NbClust，而是用 Python 手工复现了它的核心思路：",
        "在多种聚类方法、多个 k 值、多个内部评价指标之间做并行比较，再选综合最优方案。",
        "",
        "指标口径：",
        "avg_S0_S1 = 每个方言点内所有有效声母条件的 S0-S1 merge_rate 平均值",
        "avg_S1_S2 = 每个方言点内所有有效声母条件的 S1-S2 merge_rate 平均值",
        "avg_S2_S3 = 每个方言点内所有有效声母条件的 S2-S3 merge_rate 平均值",
        "N/T 在低位链段为无效格位，平均时自动按 NaN 跳过。",
        "",
        "本轮采用 NbClust 风格比较：",
        "- 方法：kmeans / hierarchical(ward, average, complete)",
        "- 聚类数：k = 2..6",
        "- 评价指标：silhouette / Calinski-Harabasz / Davies-Bouldin",
        "- 数据预处理：先对 avg_S0_S1 / avg_S1_S2 / avg_S2_S3 做 z-score 标准化",
        "- 距离口径：连续空间统一使用 Euclidean distance",
        "- kmeans 参数：deterministic farthest-point 初始化，max_iter = 100",
        "- 层次聚类参数：分别测试 ward / average / complete linkage",
        "- 选择原则：三指标分别排序后求 rank_sum；若最小簇规模 < 3，则额外加罚分，避免过碎切分。",
        "",
        "按最大链段强度的规则分类：",
    ]
    for label, group in summary.groupby("dominant_stage_type"):
        points = "、".join(group["point_name"].astype(str))
        report_lines.append(f"- {label}: {len(group)} 点；{points}")

    report_lines.extend(["", "候选方案评分表："])
    for _, row in solution_df.iterrows():
        report_lines.append(
            f"- {row['method']} k={int(row['k'])}: "
            f"silhouette={row['silhouette']:.4f}, "
            f"CH={row['calinski_harabasz']:.4f}, "
            f"DB={row['davies_bouldin']:.4f}, "
            f"min_cluster={int(row['min_cluster_size'])}, "
            f"rank_score={row['final_rank_score']:.1f}"
        )

    kmeans_only = solution_df[solution_df["method"] == "kmeans"].copy()
    report_lines.extend(["", "kmeans 单独比较："])
    for _, row in kmeans_only.iterrows():
        report_lines.append(
            f"- k={int(row['k'])}: silhouette={row['silhouette']:.4f}, "
            f"CH={row['calinski_harabasz']:.4f}, DB={row['davies_bouldin']:.4f}, "
            f"min_cluster={int(row['min_cluster_size'])}, rank_score={row['final_rank_score']:.1f}"
        )

    report_lines.extend(
        [
            "",
            f"最优方案：{best_method} / k={best_k}",
            f"最优指标：silhouette={best['silhouette']:.4f}, CH={best['calinski_harabasz']:.4f}, DB={best['davies_bouldin']:.4f}",
            "注意：虽然 C1 与 C3 都会被自动命名为 S2_S3_dominant，但它们不是同一个簇。",
            "C1 是弱后段型：三段整体都偏低，只是 S2-S3 相对最高。",
            "C3 是强后段型：S2-S3 显著升高，和 C1 不在同一强度等级。",
            "",
            "最优方案聚类摘要：",
        ]
    )
    for cluster_id, group in cluster_df.groupby("nbclust_cluster"):
        center = group[FEATURE_COLS].mean()
        label = group["nbclust_cluster_label"].iloc[0]
        subbranch_counts = " | ".join(
            f"{idx}({val})" for idx, val in group["subbranch"].value_counts().items()
        )
        report_lines.append(
            f"- C{cluster_id} {label}: {len(group)} 点；"
            f"中心=({center['avg_S0_S1']:.3f}, {center['avg_S1_S2']:.3f}, {center['avg_S2_S3']:.3f})；"
            f"{subbranch_counts}"
        )

    REPORT_OUTPUT.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"已生成平均合并强度表：{POINT_OUTPUT}")
    print(f"已生成聚类结果表：{CLUSTER_OUTPUT}")
    print(f"已生成聚类说明：{REPORT_OUTPUT}")
    print(f"最优方案：{best_method} / k={best_k}")


if __name__ == "__main__":
    run_analysis()
