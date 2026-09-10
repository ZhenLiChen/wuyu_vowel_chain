from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from analyze_mainlayer_ipa_positions import (
    ATOMIC_COORDS,
    SLOT_META,
    SLOTS,
    UNPLACED_SYMBOLS,
    clean_text,
    vowel_components,
    vowel_coordinate,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data_raw" / "mainlayer_merge.csv"
OUTPUT_DIR = PROJECT_ROOT / "data_clean" / "value_type"
CSV_OUTPUT = OUTPUT_DIR / "mainlayer_chain_clusters.csv"
SUMMARY_OUTPUT = OUTPUT_DIR / "mainlayer_chain_cluster_summary.csv"
ALL_K_SUMMARY_OUTPUT = OUTPUT_DIR / "mainlayer_chain_all_k_summary.csv"
JSON_OUTPUT = OUTPUT_DIR / "mainlayer_chain_clusters.json"

ONSET_ORDER = ["K", "M", "P", "TS", "Ø"]
ROUNDED = set("yʏøœʉɵɞuɷʊoɔɒ")
K_RANGE = range(2, 9)
MIN_CLUSTER_SIZE = 5


def component_coordinate(value: str, component: str) -> tuple[float, float]:
    if value == "o̞":
        return (3.0, 1.35)
    return ATOMIC_COORDS[component]


def value_descriptor(value: str) -> dict[str, object] | None:
    value = clean_text(value)
    if not value or value in UNPLACED_SYMBOLS:
        return None
    if value == "o̞":
        components = ["o"]
    else:
        components = vowel_components(value)
    if not components:
        return None

    start_symbol = components[0]
    end_symbol = components[-1]
    start = component_coordinate(value, start_symbol)
    end = component_coordinate(value, end_symbol)
    midpoint = vowel_coordinate(value)
    if midpoint is None:
        return None
    return {
        "value": value,
        "start_symbol": start_symbol,
        "end_symbol": end_symbol,
        "start": start,
        "end": end,
        "midpoint": midpoint,
        "is_diphthong": len(components) >= 2,
        "start_rounded": start_symbol in ROUNDED,
        "end_rounded": end_symbol in ROUNDED,
    }


def normalized_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    # Chain types are driven chiefly by raising/lowering. Front/back variation
    # remains present, but receives a smaller weight so close transcription
    # variants do not dominate the clustering.
    dx = (a[0] - b[0]) / 3.0
    dy = (a[1] - b[1]) / 3.0
    return float(np.sqrt((0.35 * dx) ** 2 + dy**2))


def value_distance(left: str, right: str) -> float:
    if left == right:
        return 0.0
    a = value_descriptor(left)
    b = value_descriptor(right)
    if a is None or b is None:
        return 1.25

    position = 0.5 * (
        normalized_distance(a["start"], b["start"])
        + normalized_distance(a["end"], b["end"])
    )
    rounding = 0.03 * (
        int(a["start_rounded"] != b["start_rounded"])
        + int(a["end_rounded"] != b["end_rounded"])
    )
    complexity = 0.12 * int(a["is_diphthong"] != b["is_diphthong"])
    return position + rounding + complexity


def medoid_value(values: Iterable[str]) -> tuple[str, float]:
    cleaned = [clean_text(value) for value in values if clean_text(value)]
    if not cleaned:
        return "", float("nan")
    counts = Counter(cleaned)
    candidates = sorted(counts)
    costs = {
        candidate: sum(value_distance(candidate, other) for other in cleaned)
        for candidate in candidates
    }
    best_cost = min(costs.values())
    tied = [candidate for candidate, cost in costs.items() if np.isclose(cost, best_cost)]
    tied.sort(key=lambda candidate: (-counts[candidate], candidate))
    selected = tied[0]
    dispersion = float(np.mean([value_distance(selected, other) for other in cleaned]))
    return selected, dispersion


def collapsed_chain_label(slots: list[dict[str, object]]) -> str:
    """Collapse consecutive slots only when both IPA value and plotted position match."""
    groups: list[dict[str, object]] = []
    for slot in slots:
        if (
            groups
            and groups[-1]["value"] == slot["value"]
            and groups[-1]["x"] == slot["x"]
            and groups[-1]["y"] == slot["y"]
        ):
            groups[-1]["slots"].append(slot["slot"])
        else:
            groups.append(
                {
                    "slots": [slot["slot"]],
                    "value": slot["value"],
                    "x": slot["x"],
                    "y": slot["y"],
                }
            )
    return " → ".join(
        f"{'–'.join(group['slots'])} {group['value']}" for group in groups
    )


def chain_type_label(point: dict[str, object]) -> str:
    slots = point["slots"]
    s1, s2, s3 = slots[1], slots[2], slots[3]
    if s1["value"] == s2["value"] and s1["x"] == s2["x"] and s1["y"] == s2["y"]:
        return "S1–S2 O并位型"
    if bool(s2["is_diphthong"]) and not bool(s3["is_diphthong"]):
        return "S2 前增生复元音型"
    if s2["value"] == s3["value"] and s2["x"] == s3["x"] and s2["y"] == s3["y"]:
        return "S2–S3 U并位型"
    return "其他链形"


def ordered_diphthong_pattern(point: dict[str, object]) -> str:
    patterns = [
        f"{slot['slot']} {slot['value']}"
        for slot in point["slots"]
        if bool(slot["is_diphthong"])
    ]
    return "；".join(patterns) if patterns else "无"


def build_point_chains(df: pd.DataFrame) -> list[dict[str, object]]:
    points: list[dict[str, object]] = []
    for (point_id, point_name), group in df.groupby(["point_id", "point_name"], sort=True):
        slots: list[dict[str, object]] = []
        for slot in SLOTS:
            value, dispersion = medoid_value(group[slot])
            descriptor = value_descriptor(value)
            if descriptor is None:
                raise ValueError(f"{point_id} {slot} 无法定位代表音值：{value}")
            slots.append(
                {
                    "slot": slot,
                    "rhyme": SLOT_META[slot]["rhyme"],
                    "initial": f"*{SLOT_META[slot]['initial']}",
                    "value": value,
                    "x": round(float(descriptor["midpoint"][0]), 4),
                    "y": round(float(descriptor["midpoint"][1]), 4),
                    "start_x": round(float(descriptor["start"][0]), 4),
                    "start_y": round(float(descriptor["start"][1]), 4),
                    "end_x": round(float(descriptor["end"][0]), 4),
                    "end_y": round(float(descriptor["end"][1]), 4),
                    "is_diphthong": bool(descriptor["is_diphthong"]),
                    "dispersion": round(dispersion, 4),
                    "all_values": "、".join(
                        f"{value}({count})" for value, count in group[slot].value_counts().items()
                    ),
                }
            )
        points.append(
            {
                "point_id": point_id,
                "point_name": point_name,
                "slots": slots,
                "chain": " → ".join(slot["value"] for slot in slots),
                "collapsed_chain": collapsed_chain_label(slots),
            }
        )
        points[-1]["type_label"] = chain_type_label(points[-1])
        points[-1]["ordered_diphthong_pattern"] = ordered_diphthong_pattern(points[-1])
    return points


def chain_distance(left: dict[str, object], right: dict[str, object]) -> float:
    distances = [
        value_distance(a["value"], b["value"])
        for a, b in zip(left["slots"], right["slots"], strict=True)
    ]
    return float(np.mean(distances))


def distance_matrix(points: list[dict[str, object]]) -> np.ndarray:
    n = len(points)
    matrix = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i, j] = matrix[j, i] = chain_distance(points[i], points[j])
    return matrix


def average_linkage_snapshots(matrix: np.ndarray) -> dict[int, list[list[int]]]:
    clusters = [[index] for index in range(len(matrix))]
    snapshots: dict[int, list[list[int]]] = {}
    while len(clusters) > 1:
        if len(clusters) in K_RANGE:
            snapshots[len(clusters)] = [cluster.copy() for cluster in clusters]
        best: tuple[float, int, int] | None = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                block = matrix[np.ix_(clusters[i], clusters[j])]
                candidate = (float(block.mean()), i, j)
                if best is None or candidate < best:
                    best = candidate
        assert best is not None
        _, i, j = best
        merged = sorted(clusters[i] + clusters[j])
        clusters = [cluster for index, cluster in enumerate(clusters) if index not in {i, j}]
        clusters.append(merged)
    return snapshots


def kmedoids_solution(
    matrix: np.ndarray, k: int, *, restarts: int = 240
) -> list[list[int]]:
    n = len(matrix)
    rng = np.random.default_rng(20260906 + k)
    seeds: list[list[int]] = []

    global_medoid = int(np.argmin(matrix.sum(axis=1)))
    farthest_first = [global_medoid]
    while len(farthest_first) < k:
        nearest = np.min(matrix[:, farthest_first], axis=1)
        farthest_first.append(int(np.argmax(nearest)))
    seeds.append(farthest_first)
    seeds.extend(rng.choice(n, size=k, replace=False).tolist() for _ in range(restarts))

    best: tuple[float, np.ndarray, np.ndarray] | None = None
    for seed in seeds:
        medoids = np.asarray(sorted(set(seed)), dtype=int)
        if len(medoids) != k:
            continue
        for _ in range(100):
            labels = np.argmin(matrix[:, medoids], axis=1)
            new_medoids = []
            valid = True
            for cluster_id in range(k):
                members = np.flatnonzero(labels == cluster_id)
                if len(members) == 0:
                    valid = False
                    break
                within = matrix[np.ix_(members, members)]
                new_medoids.append(int(members[np.argmin(within.sum(axis=1))]))
            if not valid:
                break
            updated = np.asarray(sorted(new_medoids), dtype=int)
            if np.array_equal(updated, np.sort(medoids)):
                medoids = updated
                break
            medoids = updated
        else:
            labels = np.argmin(matrix[:, medoids], axis=1)

        if not valid:
            continue
        labels = np.argmin(matrix[:, medoids], axis=1)
        objective = float(matrix[np.arange(n), medoids[labels]].sum())
        candidate = (objective, medoids.copy(), labels.copy())
        if best is None or candidate[0] < best[0] - 1e-12:
            best = candidate

    if best is None:
        raise RuntimeError(f"k={k} 的 k-medoids 未得到有效解。")
    _, _, labels = best
    return [np.flatnonzero(labels == cluster_id).tolist() for cluster_id in range(k)]


def cluster_medoid(cluster: list[int], matrix: np.ndarray) -> int:
    block = matrix[np.ix_(cluster, cluster)]
    costs = block.sum(axis=1)
    return cluster[int(np.argmin(costs))]


def ordered_solution(
    clusters: list[list[int]], matrix: np.ndarray, points: list[dict[str, object]]
) -> tuple[np.ndarray, list[dict[str, object]]]:
    records = []
    for cluster in clusters:
        medoid = cluster_medoid(cluster, matrix)
        records.append((points[medoid]["chain"], points[medoid]["point_id"], cluster, medoid))
    records.sort(key=lambda item: (item[0], item[1]))

    labels = np.zeros(len(points), dtype=int)
    output = []
    for label, (_, _, members, medoid) in enumerate(records, start=1):
        for member in members:
            labels[member] = label
        output.append(
            {
                "cluster": label,
                "size": len(members),
                "medoid_id": points[medoid]["point_id"],
                "medoid_name": points[medoid]["point_name"],
                "medoid_chain": points[medoid]["chain"],
                "medoid_collapsed_chain": points[medoid]["collapsed_chain"],
                "type_label": points[medoid]["type_label"],
                "members": [points[index]["point_id"] for index in members],
            }
        )
    return labels, output


def silhouette_score(matrix: np.ndarray, labels: np.ndarray) -> float:
    scores = []
    for index, label in enumerate(labels):
        same = np.flatnonzero(labels == label)
        same = same[same != index]
        if len(same) == 0:
            scores.append(0.0)
            continue
        a = float(matrix[index, same].mean())
        b = min(
            float(matrix[index, np.flatnonzero(labels == other)].mean())
            for other in np.unique(labels)
            if other != label
        )
        scores.append((b - a) / max(a, b) if max(a, b) else 0.0)
    return float(np.mean(scores))


def write_outputs(
    points: list[dict[str, object]],
    solutions: dict[int, dict[str, object]],
    default_k: int,
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for index, point in enumerate(points):
        row: dict[str, object] = {
            "point_id": point["point_id"],
            "point_name": point["point_name"],
            "representative_chain": point["chain"],
            "representative_chain_collapsed": point["collapsed_chain"],
            "default_cluster_count": default_k,
            "default_cluster": solutions[default_k]["labels"][index],
            "ordered_diphthong_pattern": point["ordered_diphthong_pattern"],
        }
        for slot in point["slots"]:
            prefix = slot["slot"]
            row[f"{prefix}_representative_value"] = slot["value"]
            row[f"{prefix}_all_onset_values"] = slot["all_values"]
            row[f"{prefix}_is_diphthong"] = slot["is_diphthong"]
            row[f"{prefix}_midpoint_x"] = slot["x"]
            row[f"{prefix}_midpoint_y"] = slot["y"]
            row[f"{prefix}_dispersion"] = slot["dispersion"]
        for k in K_RANGE:
            row[f"cluster_k{k}"] = solutions[k]["labels"][index]
        rows.append(row)
    pd.DataFrame(rows).to_csv(CSV_OUTPUT, index=False, encoding="utf-8-sig")

    point_by_id = {point["point_id"]: point for point in points}
    summary_rows = []
    for cluster in solutions[default_k]["clusters"]:
        member_points = [point_by_id[point_id] for point_id in cluster["members"]]
        summary_rows.append(
            {
                "cluster": cluster["cluster"],
                "point_count": cluster["size"],
                "type_label": cluster["type_label"],
                "main_pattern": cluster["medoid_collapsed_chain"],
                "medoid_id": cluster["medoid_id"],
                "medoid_name": cluster["medoid_name"],
                "s3_diphthong_point_count": sum(
                    point["slots"][3]["is_diphthong"] for point in member_points
                ),
                "members": "、".join(cluster["members"]),
            }
        )
    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUTPUT, index=False, encoding="utf-8-sig")

    all_k_rows = []
    for k in K_RANGE:
        for cluster in solutions[k]["clusters"]:
            all_k_rows.append(
                {
                    "k": k,
                    "silhouette": round(float(solutions[k]["score"]), 4),
                    "cluster": cluster["cluster"],
                    "point_count": cluster["size"],
                    "type_label": cluster["type_label"],
                    "main_pattern": cluster["medoid_collapsed_chain"],
                    "medoid_id": cluster["medoid_id"],
                    "medoid_name": cluster["medoid_name"],
                    "members": "、".join(cluster["members"]),
                }
            )
    pd.DataFrame(all_k_rows).to_csv(
        ALL_K_SUMMARY_OUTPUT, index=False, encoding="utf-8-sig"
    )

    s3_diphthong_points = [
        {
            "point_id": point["point_id"],
            "point_name": point["point_name"],
            "value": point["slots"][3]["value"],
            "chain": point["collapsed_chain"],
            "all_onset_values": point["slots"][3]["all_values"],
        }
        for point in points
        if point["slots"][3]["is_diphthong"]
    ]
    ordered_pattern_counts = Counter(
        point["ordered_diphthong_pattern"] for point in points
    )
    uo_points = [
        {
            "point_id": point["point_id"],
            "point_name": point["point_name"],
            "chain": point["collapsed_chain"],
            "default_cluster": solutions[default_k]["labels"][index],
        }
        for index, point in enumerate(points)
        if any(slot["value"] == "uo" for slot in point["slots"])
    ]

    payload = {
        "method": {
            "point_count": len(points),
            "default_k": default_k,
            "minimum_cluster_size": MIN_CLUSTER_SIZE,
            "slot_order": SLOTS,
            "initial_reference": {slot: f"*{SLOT_META[slot]['initial']}" for slot in SLOTS},
            "clustering": "k-medoids；固定比较对应的 S0、S1、S2、S3。",
            "model_selection": "在最小类别数不少于 5 的解中，选择 silhouette 最高者。",
            "note": "构拟初始值仅作参照，不在图中显示；聚类距离保留复元音起止顺序，绘图将复元音放在两个成分的 IPA 几何中点且不另画内部轨迹。",
        },
        "diagnostics": {
            "point_level_s3_diphthong_count": len(s3_diphthong_points),
            "point_level_s3_diphthongs": s3_diphthong_points,
            "ordered_diphthong_pattern_counts": dict(ordered_pattern_counts),
            "uo_points": uo_points,
        },
        "scores": {str(k): round(float(solutions[k]["score"]), 4) for k in K_RANGE},
        "solutions": {
            str(k): {"clusters": solutions[k]["clusters"]} for k in K_RANGE
        },
        "points": points,
    }
    JSON_OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    df = pd.read_csv(INPUT_PATH, dtype=str).fillna("")
    df = df[df["onset_class"].isin(ONSET_ORDER)].copy()
    if len(df) != 410 or df["point_id"].nunique() != 82:
        raise ValueError("预期 82 个方言点 × 5 类声母，共 410 行。")

    points = build_point_chains(df)
    matrix = distance_matrix(points)
    solutions: dict[int, dict[str, object]] = {}
    for k in K_RANGE:
        labels, clusters = ordered_solution(kmedoids_solution(matrix, k), matrix, points)
        solutions[k] = {
            "labels": labels.tolist(),
            "clusters": clusters,
            "score": silhouette_score(matrix, labels),
        }
    eligible_k = [
        k
        for k in K_RANGE
        if min(cluster["size"] for cluster in solutions[k]["clusters"])
        >= MIN_CLUSTER_SIZE
    ]
    if not eligible_k:
        raise RuntimeError("没有满足最小类别规模的聚类解。")
    default_k = max(eligible_k, key=lambda k: (solutions[k]["score"], -k))
    write_outputs(points, solutions, default_k)

    print("k  silhouette  sizes")
    for k in K_RANGE:
        sizes = [cluster["size"] for cluster in solutions[k]["clusters"]]
        print(f"{k:<2} {solutions[k]['score']:.4f}      {sizes}")
    print(f"selected_k={default_k} (min_cluster_size>={MIN_CLUSTER_SIZE})")
    print(CSV_OUTPUT.relative_to(PROJECT_ROOT))
    print(SUMMARY_OUTPUT.relative_to(PROJECT_ROOT))
    print(ALL_K_SUMMARY_OUTPUT.relative_to(PROJECT_ROOT))
    print(JSON_OUTPUT.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
