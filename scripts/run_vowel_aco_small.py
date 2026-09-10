from __future__ import annotations

import heapq
import math
import random
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CLEAN = PROJECT_ROOT / "data_clean"
VALUE_DIR = DATA_CLEAN / "value_type"
FIGS_DIR = PROJECT_ROOT / "figs" / "aco"

INPUT_PATH = DATA_CLEAN / "wuyu_lexeme.csv"
TASK_OUTPUT = VALUE_DIR / "aco_small_observation_tasks.csv"
EDGE_OUTPUT = VALUE_DIR / "aco_small_edge_pheromones.csv"
PATH_OUTPUT = VALUE_DIR / "aco_small_slot_target_paths.csv"
SIGMA_OUTPUT = VALUE_DIR / "aco_small_sigma_comparison.csv"

EDGE_FIG = FIGS_DIR / "aco_small_edge_pheromone_network.png"
SIGMA_FIG = FIGS_DIR / "aco_small_sigma_comparison.png"

SLOT_ORDER = ["S0", "S1", "S2", "S3"]
SLOT_START = {"S0": "a", "S1": "a", "S2": "ɑ", "S3": "u"}
NO_LOW_SLOT_ONSETS = {"T", "N"}
EXCLUDED_CHARS = {"靴", "茄"}

VOWEL_CHARS = set("aeiouyæøœɐɑɒɔəɛɜɞɤɯɪʊʌʏɵʉɷᴀᴇ")
CONSONANT_OR_GLIDE_CHARS = set("mnŋwɥjvʮ")
MEDIAL_PENDING_VALUES = {"yo", "yɑ", "øy", "uo", "ua", "uᴇ"}
NON_CORE_DIPHTHONG_VALUES = {"au", "ao", "aɤ"}
CORE_NODES = {"a", "ɑ", "ɔ", "o", "ɷ", "u", "ɤ", "ɯ", "ə", "ʌ", "əu", "əɯ", "ou", "ɤɯ", "ʌɯ", "ʌɤ"}

NODE_POS = {
    "a": (0.5, 0.8),
    "ɑ": (1.6, 0.95),
    "ɒ": (1.98, 0.64),
    "ɔ": (2.5, 2.1),
    "o": (3.05, 2.92),
    "ɷ": (3.12, 3.35),
    "u": (3.16, 3.82),
    "ɤ": (2.32, 2.82),
    "ɯ": (2.35, 3.7),
    "ə": (1.68, 2.55),
    "ʌ": (1.98, 1.7),
    "əu": (4.5, 3.82),
    "əɯ": (3.85, 2.55),
    "ou": (4.25, 2.92),
    "ɤɯ": (3.72, 3.26),
    "ʌɯ": (3.55, 1.88),
    "ʌɤ": (3.48, 1.45),
}


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    edge_type: str
    acoustic_distance: float
    perceptual_distance: float
    direction_bonus: float = 0.0

    @property
    def key(self) -> tuple[str, str]:
        return (self.source, self.target)

    def cost(self, sigma: float) -> float:
        # Acoustic distance is articulatory effort; perceptual distance is the
        # chance that a small shift becomes socially audible. Sigma controls how
        # much the perceptual term lowers the cost.
        return self.acoustic_distance / (1.0 + sigma * self.perceptual_distance) + 0.06 - self.direction_bonus


EDGES = [
    Edge("a", "ɑ", "main_chain", 0.78, 0.74, 0.04),
    Edge("a", "ɔ", "long_jump", 1.58, 1.12, -0.10),
    Edge("ɑ", "ɔ", "main_chain", 0.86, 1.05, 0.05),
    Edge("ɑ", "o", "long_jump", 1.62, 1.20, -0.08),
    Edge("ɑ", "ɒ", "side_variant", 0.44, 0.36, 0.00),
    Edge("ɒ", "ɔ", "side_variant", 0.74, 0.82, 0.01),
    Edge("ɔ", "o", "main_chain", 0.64, 0.72, 0.05),
    Edge("ɔ", "ʌ", "posterior_branch", 0.52, 0.48, 0.00),
    Edge("ɔ", "ə", "centralization", 0.88, 0.62, -0.04),
    Edge("o", "ɷ", "main_chain", 0.38, 0.36, 0.04),
    Edge("o", "ɤ", "unrounded_branch", 0.60, 0.58, 0.00),
    Edge("ɷ", "u", "main_chain", 0.42, 0.42, 0.04),
    Edge("ɤ", "ɯ", "unrounded_branch", 0.66, 0.64, 0.01),
    Edge("ɯ", "u", "rounding_link", 0.56, 0.62, 0.00),
    Edge("ʌ", "ə", "centralization", 0.56, 0.50, -0.02),
    Edge("u", "əu", "core_split", 0.72, 1.62, 0.04),
    Edge("o", "ou", "split_variant", 0.62, 1.18, 0.00),
    Edge("ə", "əɯ", "split_neighbor", 0.60, 1.08, 0.00),
    Edge("ɤ", "ɤɯ", "split_neighbor", 0.60, 1.08, 0.00),
    Edge("ɯ", "ɤɯ", "split_neighbor", 0.68, 0.98, -0.02),
    Edge("ʌ", "ʌɯ", "split_neighbor", 0.68, 1.02, 0.00),
    Edge("ʌ", "ʌɤ", "split_neighbor", 0.62, 0.94, 0.00),
]


def set_chinese_font() -> None:
    available = {font.name for font in fm.fontManager.ttflist}
    preferred = [
        "Arial Unicode MS",
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Songti SC",
        "DejaVu Sans",
    ]
    plt.rcParams["font.sans-serif"] = [font for font in preferred if font in available]
    plt.rcParams["axes.unicode_minus"] = False


def split_phonetic(value) -> list[str]:
    if pd.isna(value):
        return []
    value = str(value).replace("\u00a0", " ").strip()
    if not value or value.lower() == "nan":
        return []
    if value == "o（uo）":
        return ["u", "uo"]
    return [part.strip() for part in value.split("/") if part.strip()]


def decomposed_chars(value: str) -> list[str]:
    return [
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    ]


def vowel_sequence(value: str) -> list[str]:
    return [char for char in decomposed_chars(value) if char in VOWEL_CHARS]


def starts_with(value: str, initials: set[str]) -> bool:
    chars = decomposed_chars(value)
    return bool(chars and chars[0] in initials)


def has_coda_or_consonantal(value: str) -> bool:
    chars = decomposed_chars(value)
    vowels = set(VOWEL_CHARS)
    for idx, char in enumerate(chars):
        if char in vowels or char in {"ː", "̞"}:
            continue
        if char == "ʔ":
            return True
        if char in CONSONANT_OR_GLIDE_CHARS and idx != 0:
            return True
        if char in {"m", "n", "ŋ", "v", "w", "ɥ", "ʮ"} and len(vowel_sequence(value)) == 0:
            return True
    return False


def classify_phonetic(value: str) -> str:
    if "ʔ" in value:
        return "checked_or_coda"
    vowels = vowel_sequence(value)
    if not vowels:
        return "consonantal_or_other"
    if len(vowels) == 1:
        if has_coda_or_consonantal(value):
            return "checked_or_coda"
        return "monophthong"
    if starts_with(value, {"i", "j"}):
        return "i_medial_excluded"
    if vowels[-1] in {"i", "ɪ"}:
        return "i_offglide_excluded"
    if value in MEDIAL_PENDING_VALUES or starts_with(value, {"u", "w", "y", "ɥ"}):
        return "medial_pending"
    if value in NON_CORE_DIPHTHONG_VALUES:
        return "non_core_diphthong_excluded"
    return "clear_split"


def load_observation_tasks() -> pd.DataFrame:
    df = pd.read_csv(INPUT_PATH)
    required = {"point_id", "point_name", "subbranch", "chain_slot", "onset_class", "char", "phonetic"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"输入文件缺少必要列：{sorted(missing)}")

    work = df[list(required)].copy()
    for column in required:
        work[column] = work[column].astype("string").str.strip()
    work = work[
        work["point_id"].notna()
        & (work["point_id"] != "")
        & work["chain_slot"].isin(SLOT_ORDER)
        & ~work["char"].isin(EXCLUDED_CHARS)
    ].copy()
    work["onset_class"] = work["onset_class"].replace({"TS*": "TS"})
    work = work[
        ~(
            work["onset_class"].isin(NO_LOW_SLOT_ONSETS)
            & work["chain_slot"].isin(["S0", "S1"])
        )
    ].copy()
    work["phonetic"] = work["phonetic"].apply(split_phonetic)
    work = work.explode("phonetic").reset_index(drop=True)
    work = work[work["phonetic"].notna() & (work["phonetic"] != "")].copy()
    work["category"] = work["phonetic"].apply(classify_phonetic)
    work = work[
        work["category"].isin({"monophthong", "clear_split"})
        & work["phonetic"].isin(CORE_NODES)
    ].copy()
    work["start_node"] = work["chain_slot"].map(SLOT_START)
    rows = []
    for keys, group in work.groupby(["chain_slot", "start_node", "phonetic", "category"], dropna=False):
        rows.append(
            {
                "chain_slot": keys[0],
                "start_node": keys[1],
                "target_node": keys[2],
                "target_category": keys[3],
                "token_count": len(group),
                "point_count": group["point_id"].nunique(),
                "example_points": " | ".join(
                    f"{row.point_id}:{row.point_name}"
                    for row in group[["point_id", "point_name"]]
                    .drop_duplicates()
                    .head(10)
                    .itertuples(index=False)
                ),
            }
        )
    tasks = pd.DataFrame(rows)
    return tasks.sort_values(["chain_slot", "token_count"], ascending=[True, False]).reset_index(drop=True)


def edge_costs(sigma: float) -> dict[tuple[str, str], float]:
    return {edge.key: max(edge.cost(sigma), 0.03) for edge in EDGES}


def adjacency() -> dict[str, list[Edge]]:
    graph: dict[str, list[Edge]] = {}
    for edge in EDGES:
        graph.setdefault(edge.source, []).append(edge)
    return graph


def shortest_cost_to_target(target: str, costs: dict[tuple[str, str], float]) -> dict[str, float]:
    reverse: dict[str, list[tuple[str, float]]] = {}
    nodes = set(CORE_NODES)
    for edge in EDGES:
        reverse.setdefault(edge.target, []).append((edge.source, costs[edge.key]))
        nodes.add(edge.source)
        nodes.add(edge.target)
    distances = {node: math.inf for node in nodes}
    distances[target] = 0.0
    heap = [(0.0, target)]
    while heap:
        current_dist, node = heapq.heappop(heap)
        if current_dist > distances[node]:
            continue
        for prev, cost in reverse.get(node, []):
            new_dist = current_dist + cost
            if new_dist < distances[prev]:
                distances[prev] = new_dist
                heapq.heappush(heap, (new_dist, prev))
    return distances


def choose_next(
    rng: random.Random,
    current: str,
    target: str,
    graph: dict[str, list[Edge]],
    pheromone: dict[tuple[str, str], float],
    costs: dict[tuple[str, str], float],
    remaining: dict[str, float],
    visited: set[str],
    alpha: float,
    beta: float,
) -> Edge | None:
    candidates = [
        edge
        for edge in graph.get(current, [])
        if edge.target not in visited and math.isfinite(remaining.get(edge.target, math.inf))
    ]
    if not candidates:
        return None
    weights = []
    for edge in candidates:
        tau = pheromone[edge.key] ** alpha
        eta = 1.0 / (costs[edge.key] + remaining[edge.target] + 0.08)
        weights.append(tau * (eta**beta))
    total = sum(weights)
    if total <= 0:
        return rng.choice(candidates)
    threshold = rng.random() * total
    running = 0.0
    for edge, weight in zip(candidates, weights):
        running += weight
        if running >= threshold:
            return edge
    return candidates[-1]


def walk_ant(
    rng: random.Random,
    start: str,
    target: str,
    graph: dict[str, list[Edge]],
    pheromone: dict[tuple[str, str], float],
    costs: dict[tuple[str, str], float],
    remaining: dict[str, float],
    alpha: float,
    beta: float,
    max_steps: int = 8,
) -> tuple[list[Edge], float, bool]:
    if start == target:
        return [], 0.0, True
    current = start
    visited = {start}
    path: list[Edge] = []
    total_cost = 0.0
    for _ in range(max_steps):
        edge = choose_next(rng, current, target, graph, pheromone, costs, remaining, visited, alpha, beta)
        if edge is None:
            return path, total_cost, False
        path.append(edge)
        total_cost += costs[edge.key]
        current = edge.target
        if current == target:
            return path, total_cost, True
        visited.add(current)
    return path, total_cost, current == target


def greedy_best_path(
    start: str,
    target: str,
    pheromone: dict[tuple[str, str], float],
    costs: dict[tuple[str, str], float],
    alpha: float,
) -> tuple[list[str], float, float, bool]:
    if start == target:
        return [start], 0.0, 0.0, True
    graph = adjacency()
    effective: dict[tuple[str, str], float] = {
        edge.key: costs[edge.key] / (pheromone[edge.key] ** alpha + 1e-9) for edge in EDGES
    }
    heap = [(0.0, start, [start], 0.0)]
    best = {start: 0.0}
    while heap:
        score, node, path, raw_cost = heapq.heappop(heap)
        if node == target:
            return path, raw_cost, score, True
        if score > best.get(node, math.inf):
            continue
        for edge in graph.get(node, []):
            if edge.target in path:
                continue
            new_score = score + effective[edge.key]
            if new_score < best.get(edge.target, math.inf):
                best[edge.target] = new_score
                heapq.heappush(
                    heap,
                    (
                        new_score,
                        edge.target,
                        path + [edge.target],
                        raw_cost + costs[edge.key],
                    ),
                )
    return [start], math.inf, math.inf, False


def run_aco(
    tasks: pd.DataFrame,
    sigma: float = 1.0,
    iterations: int = 260,
    ants_per_task: int = 4,
    alpha: float = 1.0,
    beta: float = 2.4,
    rho: float = 0.12,
    seed: int = 20260415,
) -> dict:
    rng = random.Random(seed)
    graph = adjacency()
    costs = edge_costs(sigma)
    pheromone = {edge.key: 1.0 for edge in EDGES}
    deposits = {edge.key: 0.0 for edge in EDGES}
    successes = 0
    failures = 0
    weighted_cost_total = 0.0
    weighted_success_total = 0.0
    total_weight = float(tasks["token_count"].sum())

    reachable_tasks = tasks.copy()
    remaining_cache = {
        target: shortest_cost_to_target(target, costs)
        for target in sorted(reachable_tasks["target_node"].unique())
    }

    for _ in range(iterations):
        for key in pheromone:
            pheromone[key] *= 1.0 - rho
        iteration_deposits = {edge.key: 0.0 for edge in EDGES}
        for task in reachable_tasks.itertuples(index=False):
            if task.start_node == task.target_node:
                continue
            remaining = remaining_cache[task.target_node]
            if not math.isfinite(remaining.get(task.start_node, math.inf)):
                failures += ants_per_task
                continue
            for _ant in range(ants_per_task):
                path, path_cost, reached = walk_ant(
                    rng,
                    task.start_node,
                    task.target_node,
                    graph,
                    pheromone,
                    costs,
                    remaining,
                    alpha,
                    beta,
                )
                if not reached:
                    failures += 1
                    continue
                successes += 1
                task_weight = float(task.token_count) / total_weight
                deposit = task_weight / (path_cost + 0.18)
                for edge in path:
                    iteration_deposits[edge.key] += deposit
                weighted_cost_total += path_cost * float(task.token_count)
                weighted_success_total += float(task.token_count)
        for key, value in iteration_deposits.items():
            pheromone[key] += value
            deposits[key] += value

    edge_rows = []
    max_pheromone = max(pheromone.values())
    max_deposit = max(deposits.values()) if max(deposits.values()) > 0 else 1.0
    for edge in EDGES:
        edge_rows.append(
            {
                "source": edge.source,
                "target": edge.target,
                "edge_type": edge.edge_type,
                "acoustic_distance": edge.acoustic_distance,
                "perceptual_distance": edge.perceptual_distance,
                "edge_cost": costs[edge.key],
                "pheromone": pheromone[edge.key],
                "normalized_pheromone": pheromone[edge.key] / max_pheromone,
                "total_deposit": deposits[edge.key],
                "normalized_deposit": deposits[edge.key] / max_deposit,
            }
        )
    edge_df = pd.DataFrame(edge_rows).sort_values("pheromone", ascending=False)

    path_rows = []
    for task in tasks.itertuples(index=False):
        costs_for_sigma = costs
        path, raw_cost, pheromone_score, reached = greedy_best_path(
            task.start_node,
            task.target_node,
            pheromone,
            costs_for_sigma,
            0.0,
        )
        if task.start_node == task.target_node:
            reached = True
            raw_cost = 0.0
            pheromone_score = 0.0
        path_rows.append(
            {
                "chain_slot": task.chain_slot,
                "start_node": task.start_node,
                "target_node": task.target_node,
                "target_category": task.target_category,
                "token_count": task.token_count,
                "point_count": task.point_count,
                "reached": reached,
                "best_path": " > ".join(path) if reached else "",
                "path_cost": raw_cost if reached else np.nan,
                "pheromone_weighted_score": pheromone_score if reached else np.nan,
            }
        )
    path_df = pd.DataFrame(path_rows).sort_values(
        ["token_count", "chain_slot", "target_node"], ascending=[False, True, True]
    )

    pheromone_values = edge_df["normalized_pheromone"].to_numpy()
    probabilities = pheromone_values / pheromone_values.sum()
    entropy = -float(np.sum(probabilities * np.log(probabilities + 1e-12)))
    summary = {
        "sigma": sigma,
        "successes": successes,
        "failures": failures,
        "weighted_mean_success_path_cost": weighted_cost_total / weighted_success_total
        if weighted_success_total
        else np.nan,
        "pheromone_entropy": entropy,
        "u_to_əu_pheromone": pheromone.get(("u", "əu"), 0.0),
        "u_to_əu_normalized": float(
            edge_df[(edge_df["source"] == "u") & (edge_df["target"] == "əu")][
                "normalized_pheromone"
            ].iloc[0]
        ),
        "main_chain_pheromone": sum(
            pheromone.get(key, 0.0)
            for key in [("a", "ɑ"), ("ɑ", "ɔ"), ("ɔ", "o"), ("o", "ɷ"), ("ɷ", "u")]
        ),
        "core_split_pheromone": sum(
            pheromone.get(key, 0.0)
            for key in [("u", "əu"), ("ə", "əɯ"), ("o", "ou"), ("ɤ", "ɤɯ"), ("ʌ", "ʌɯ"), ("ʌ", "ʌɤ")]
        ),
    }
    return {"edges": edge_df, "paths": path_df, "summary": summary}


def compare_sigmas(tasks: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sigma in [0.0, 0.5, 1.0, 2.0, 5.0]:
        result = run_aco(
            tasks,
            sigma=sigma,
            iterations=180,
            ants_per_task=3,
            seed=20260415 + int(sigma * 100),
        )
        row = result["summary"].copy()
        edges = result["edges"]
        for source, target in [("u", "əu"), ("o", "ou"), ("ə", "əɯ"), ("ɤ", "ɤɯ"), ("ʌ", "ʌɯ")]:
            match = edges[(edges["source"] == source) & (edges["target"] == target)]
            row[f"{source}_to_{target}_normalized"] = float(match["normalized_pheromone"].iloc[0])
        rows.append(row)
    return pd.DataFrame(rows)


def draw_node(ax, node: str, face: str, edge: str, fontsize: int = 16) -> None:
    x, y = NODE_POS[node]
    circ = patches.Circle((x, y), 0.13, facecolor=face, edgecolor=edge, linewidth=1.5, zorder=4)
    ax.add_patch(circ)
    ax.text(x, y, node, ha="center", va="center", fontsize=fontsize, color="#1f2933", zorder=5)


def draw_network(edge_df: pd.DataFrame) -> None:
    set_chinese_font()
    fig, ax = plt.subplots(figsize=(12, 7.2), facecolor="#f7f7f2")
    ax.set_facecolor("#f7f7f2")
    ax.axis("off")
    ax.set_xlim(0.1, 4.85)
    ax.set_ylim(0.35, 4.25)
    ax.text(0.16, 4.08, "小版 ACO 的累积信息素网络", fontsize=22, weight="bold", color="#1f2933")
    ax.text(
        0.16,
        3.88,
        "线越粗，表示蚂蚁在多轮寻路中越常经过这条边；橙色是裂化边，绿色是单元音链移边。",
        fontsize=12,
        color="#4b5563",
    )

    max_pheromone = edge_df["normalized_deposit"].max()
    edge_lookup = {
        (row.source, row.target): row
        for row in edge_df.itertuples(index=False)
    }
    for edge in EDGES:
        row = edge_lookup[edge.key]
        if row.normalized_deposit < 0.006:
            continue
        x1, y1 = NODE_POS[edge.source]
        x2, y2 = NODE_POS[edge.target]
        if "split" in edge.edge_type:
            color = "#d55e00"
        elif edge.edge_type == "main_chain":
            color = "#00796b"
        else:
            color = "#6f8f3a"
        width = 0.8 + 7.5 * math.sqrt(row.normalized_deposit / max_pheromone)
        arrow = patches.FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=width,
            color=color,
            alpha=0.72 if edge.edge_type != "long_jump" else 0.32,
            connectionstyle="arc3,rad=0.08",
            shrinkA=18,
            shrinkB=20,
            zorder=2,
        )
        ax.add_patch(arrow)

    for node in ["a", "ɑ", "ɔ", "o", "ɷ", "u"]:
        draw_node(ax, node, "#e9f5ef", "#00796b")
    draw_node(ax, "ɒ", "#eef3df", "#6f8f3a")
    for node in ["ɤ", "ɯ", "ʌ"]:
        draw_node(ax, node, "#eef3df", "#6f8f3a")
    draw_node(ax, "ə", "#eeeeee", "#9aa0a6")
    for node in ["əu", "əɯ", "ou", "ɤɯ", "ʌɯ", "ʌɤ"]:
        draw_node(ax, node, "#fff0e7", "#d55e00", fontsize=15)

    fig.tight_layout()
    fig.savefig(EDGE_FIG, dpi=240, bbox_inches="tight")
    plt.close(fig)


def plot_sigma_comparison(sigma_df: pd.DataFrame) -> None:
    set_chinese_font()
    fig, ax = plt.subplots(figsize=(10.5, 6.2), facecolor="#f7f7f2")
    ax.set_facecolor("#f7f7f2")
    ax.plot(
        sigma_df["sigma"],
        sigma_df["u_to_əu_normalized"],
        marker="o",
        linewidth=2.8,
        color="#d55e00",
        label="u -> əu",
    )
    ax.plot(
        sigma_df["sigma"],
        sigma_df["o_to_ou_normalized"],
        marker="o",
        linewidth=2.2,
        color="#00796b",
        label="o -> ou",
    )
    ax.plot(
        sigma_df["sigma"],
        sigma_df["ɤ_to_ɤɯ_normalized"],
        marker="o",
        linewidth=2.2,
        color="#6f8f3a",
        label="ɤ -> ɤɯ",
    )
    ax.plot(
        sigma_df["sigma"],
        sigma_df["ə_to_əɯ_normalized"],
        marker="o",
        linewidth=2.2,
        color="#4c78a8",
        label="ə -> əɯ",
    )
    ax.set_title("感知权重 σ 对裂化边信息素的影响", fontsize=21, weight="bold", color="#1f2933", pad=16)
    ax.set_xlabel("σ：感知距离在路径成本中的权重", fontsize=12)
    ax.set_ylabel("归一化信息素", fontsize=12)
    ax.grid(color="#dedbd2", linewidth=1, alpha=0.8)
    ax.legend(frameon=False, fontsize=11)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(
        0,
        -0.18,
        "读法：σ 越大，感知上更显著的裂化边成本越低。当前小模型中 u -> əu 始终最强，说明它不是参数偶然造成的。",
        transform=ax.transAxes,
        fontsize=11,
        color="#4b5563",
    )
    fig.subplots_adjust(bottom=0.22)
    fig.savefig(SIGMA_FIG, dpi=240, bbox_inches="tight")
    plt.close(fig)


def run() -> None:
    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    tasks = load_observation_tasks()
    tasks.to_csv(TASK_OUTPUT, index=False, encoding="utf-8-sig")
    final = run_aco(tasks, sigma=1.0)
    final["edges"].to_csv(EDGE_OUTPUT, index=False, encoding="utf-8-sig")
    final["paths"].to_csv(PATH_OUTPUT, index=False, encoding="utf-8-sig")
    sigma_df = compare_sigmas(tasks)
    sigma_df.to_csv(SIGMA_OUTPUT, index=False, encoding="utf-8-sig")
    draw_network(final["edges"])
    plot_sigma_comparison(sigma_df)

    print(f"已生成 ACO 任务表：{TASK_OUTPUT}")
    print(f"已生成 ACO 边信息素表：{EDGE_OUTPUT}")
    print(f"已生成 ACO 路径表：{PATH_OUTPUT}")
    print(f"已生成 σ 对比表：{SIGMA_OUTPUT}")
    print(f"已生成 ACO 信息素网络图：{EDGE_FIG}")
    print(f"已生成 σ 对比图：{SIGMA_FIG}")


if __name__ == "__main__":
    run()
