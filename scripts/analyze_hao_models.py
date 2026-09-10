import math
import re
import sys
from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_CLEAN = PROJECT_ROOT / "data_clean"
VALUE_DIR = DATA_CLEAN / "value_type"
FIGS_DIR = PROJECT_ROOT / "figs" / "monophthongization"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from analyze_hao_monophthong_relation import (  # noqa: E402
    BACK_NUCLEI,
    classify_value,
    monophthong_nucleus,
)


RELATION_PATH = VALUE_DIR / "point_hao_monophthong_relation.csv"
VALUE_SUMMARY_PATH = VALUE_DIR / "hao_value_summary.csv"

LOGISTIC_COEF_OUTPUT = VALUE_DIR / "hao_monophthong_logistic_coefficients.csv"
LOGISTIC_PRED_OUTPUT = VALUE_DIR / "hao_monophthong_logistic_predictions.csv"
ATTRACTOR_COEF_OUTPUT = VALUE_DIR / "hao_attractor_softmax_coefficients.csv"
ATTRACTOR_PROB_OUTPUT = VALUE_DIR / "hao_attractor_softmax_probabilities.csv"
ATTRACTOR_SUMMARY_OUTPUT = VALUE_DIR / "hao_attractor_softmax_summary.csv"

LOGISTIC_FIG_OUTPUT = FIGS_DIR / "hao_monophthong_logistic_model.png"
ATTRACTOR_FIG_OUTPUT = FIGS_DIR / "hao_attractor_softmax_model.png"

RIDGE_LAMBDA = 1.0
EPS = 1e-9


def set_chinese_font() -> None:
    available_fonts = [font.name for font in fm.fontManager.ttflist]
    preferred_fonts = [
        "PingFang SC",
        "Heiti SC",
        "SimHei",
        "Microsoft YaHei",
        "Arial Unicode MS",
    ]
    for font_name in preferred_fonts:
        if font_name in available_fonts:
            plt.rcParams["font.sans-serif"] = [font_name]
            break
    plt.rcParams["axes.unicode_minus"] = False


def sigmoid(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, -35, 35)
    return 1.0 / (1.0 + np.exp(-value))


def standardize(series: pd.Series) -> tuple[pd.Series, float, float]:
    mean = float(series.mean())
    std = float(series.std(ddof=0))
    if std < EPS:
        std = 1.0
    return (series - mean) / std, mean, std


def parse_set(value) -> set[str]:
    if pd.isna(value) or not str(value).strip():
        return set()
    return {part.strip() for part in str(value).split(",") if part.strip()}


def parse_counts(value) -> dict[str, int]:
    if pd.isna(value) or not str(value).strip():
        return {}
    counts: dict[str, int] = {}
    for item in str(value).split(","):
        item = item.strip()
        match = re.match(r"(.+)\((\d+)\)$", item)
        if match:
            counts[match.group(1).strip()] = int(match.group(2))
    return counts


def fit_binomial_logistic(
    x: np.ndarray,
    successes: np.ndarray,
    trials: np.ndarray,
    ridge_lambda: float = RIDGE_LAMBDA,
    max_iter: int = 100,
    tol: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray]:
    beta = np.zeros(x.shape[1])
    penalty = np.eye(x.shape[1]) * ridge_lambda
    penalty[0, 0] = 0.0

    for _ in range(max_iter):
        eta = x @ beta
        p = sigmoid(eta)
        weights = np.maximum(trials * p * (1.0 - p), EPS)
        gradient = x.T @ (successes - trials * p) - penalty @ beta
        hessian = x.T @ (weights[:, None] * x) + penalty
        step = np.linalg.solve(hessian, gradient)
        beta += step
        if np.max(np.abs(step)) < tol:
            break

    eta = x @ beta
    p = sigmoid(eta)
    weights = np.maximum(trials * p * (1.0 - p), EPS)
    hessian = x.T @ (weights[:, None] * x) + penalty
    covariance = np.linalg.pinv(hessian)
    return beta, covariance


def prepare_logistic_data(relation: pd.DataFrame) -> tuple[pd.DataFrame, list[str], dict[str, tuple[float, float]]]:
    df = relation.copy()
    df = df[df["hao_total_token_count"] > 0].copy()
    df["observed_monophthong_share"] = (
        df["hao_monophthong_token_count"] / df["hao_total_token_count"]
    )
    df["has_core_open_mid_back"] = df["back_monophthong_nuclei"].apply(
        lambda value: int(bool(parse_set(value) & {"ɔ", "ɒ"}))
    )
    df["core_back_nucleus_size"] = df["back_monophthong_nucleus_size"].astype(float)
    df["log_core_back_token_count"] = np.log1p(
        df["back_monophthong_token_count"].astype(float)
    )
    df["core_back_token_share"] = (
        df["back_monophthong_token_count"].astype(float)
        / df["monophthong_token_count"].replace(0, np.nan).astype(float)
    ).fillna(0.0)

    scalers = {}
    for column in [
        "core_back_nucleus_size",
        "log_core_back_token_count",
        "core_back_token_share",
    ]:
        df[f"{column}_z"], mean, std = standardize(df[column])
        scalers[column] = (mean, std)

    feature_columns = [
        "intercept",
        "has_core_open_mid_back",
        "core_back_nucleus_size_z",
        "log_core_back_token_count_z",
        "core_back_token_share_z",
    ]
    df["intercept"] = 1.0
    return df, feature_columns, scalers


def run_logistic_model(relation: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    data, feature_columns, _ = prepare_logistic_data(relation)
    x = data[feature_columns].to_numpy(dtype=float)
    y = data["hao_monophthong_token_count"].to_numpy(dtype=float)
    n = data["hao_total_token_count"].to_numpy(dtype=float)

    beta, covariance = fit_binomial_logistic(x, y, n)
    std_error = np.sqrt(np.maximum(np.diag(covariance), 0.0))

    labels = {
        "intercept": "截距",
        "has_core_open_mid_back": "S0-S3已有ɔ/ɒ",
        "core_back_nucleus_size_z": "后元音库藏大小",
        "log_core_back_token_count_z": "后元音token数",
        "core_back_token_share_z": "后元音token占比",
    }
    coef = pd.DataFrame(
        {
            "term": feature_columns,
            "term_label": [labels[column] for column in feature_columns],
            "coefficient": beta,
            "std_error_approx": std_error,
            "odds_ratio_or_multiplier": np.exp(beta),
            "model": "ridge_binomial_logistic",
            "ridge_lambda": RIDGE_LAMBDA,
        }
    )

    data["predicted_monophthong_probability"] = sigmoid(x @ beta)
    data["predicted_monophthong_token_count"] = (
        data["predicted_monophthong_probability"] * data["hao_total_token_count"]
    )
    pred_cols = [
        "point_id",
        "point_name",
        "subbranch",
        "hao_value_counts",
        "hao_total_token_count",
        "hao_monophthong_token_count",
        "observed_monophthong_share",
        "predicted_monophthong_probability",
        "predicted_monophthong_token_count",
        "has_core_open_mid_back",
        "core_back_nucleus_size",
        "back_monophthong_nuclei",
        "back_monophthong_token_count",
        "core_back_token_share",
        "hao_status",
        "hao_core_relation",
    ]
    predictions = data[pred_cols].sort_values(
        ["predicted_monophthong_probability", "point_id"],
        ascending=[True, True],
    )
    return coef, predictions


def vowel_features(nucleus: str) -> tuple[float, float, float]:
    feature_map = {
        "u": (0.0, 1.0, 1.0),
        "ʊ": (0.2, 1.0, 1.0),
        "ɯ": (0.0, 1.0, 0.0),
        "o": (0.35, 1.0, 1.0),
        "ɔ": (0.65, 1.0, 1.0),
        "ɒ": (0.85, 1.0, 1.0),
        "ɑ": (1.0, 1.0, 0.0),
        "ɤ": (0.45, 1.0, 0.0),
        "ʌ": (0.60, 0.5, 0.0),
        "ə": (0.50, 0.0, 0.0),
        "ɜ": (0.55, 0.0, 0.0),
        "ɐ": (0.80, 0.0, 0.0),
        "a": (1.0, 0.0, 0.0),
        "æ": (0.90, -0.8, 0.0),
        "ɛ": (0.65, -0.8, 0.0),
        "ɪ": (0.20, -0.8, 0.0),
        "i": (0.0, -1.0, 0.0),
        "y": (0.0, -1.0, 1.0),
        "ø": (0.35, -1.0, 1.0),
        "ᴇ": (0.55, -0.8, 0.0),
        "ᴀ": (0.95, 0.0, 0.0),
        "ɷ": (0.55, 1.0, 1.0),
    }
    return feature_map.get(nucleus, (0.5, 0.0, 0.0))


def distance_to_au(nucleus: str) -> float:
    # *au 单音化在本数据中主要落向 ɔ，其次是 ɒ。
    # 因此把自然目标设在开中、后、圆唇区域，并稍微加重高度距离，
    # 避免高后元音 u 仅因“后圆唇”而被过度视作同等目标。
    target = np.array([0.65, 1.0, 1.0])
    value = np.array(vowel_features(nucleus))
    weights = np.array([1.8, 1.0, 1.0])
    return float(np.linalg.norm((value - target) * weights))


def monophthong_counts_from_hao(value_counts: str) -> dict[str, int]:
    counts = {}
    for value, count in parse_counts(value_counts).items():
        if classify_value(value) != "monophthong":
            continue
        nucleus = monophthong_nucleus(value)
        if nucleus:
            counts[nucleus] = counts.get(nucleus, 0) + count
    return counts


def prepare_attractor_data(
    relation: pd.DataFrame, value_summary: pd.DataFrame
) -> tuple[pd.DataFrame, list[str], list[str]]:
    candidates = sorted(
        {
            monophthong_nucleus(row.hao_value)
            for row in value_summary.itertuples(index=False)
            if row.value_class == "monophthong" and monophthong_nucleus(row.hao_value)
        }
    )

    rows = []
    for point in relation.itertuples(index=False):
        observed = monophthong_counts_from_hao(point.hao_value_counts)
        total_observed = sum(observed.values())
        if total_observed <= 0:
            continue
        core_counts = parse_counts(point.monophthong_nucleus_counts)
        core_set = set(core_counts)
        core_back_set = parse_set(point.back_monophthong_nuclei)
        for candidate in candidates:
            core_count = core_counts.get(candidate, 0)
            rows.append(
                {
                    "point_id": point.point_id,
                    "point_name": point.point_name,
                    "subbranch": point.subbranch,
                    "candidate_nucleus": candidate,
                    "observed_token_count": observed.get(candidate, 0),
                    "point_monophthong_token_count": total_observed,
                    "in_core_nucleus": int(candidate in core_set),
                    "in_core_back_nucleus": int(candidate in core_back_set),
                    "core_nucleus_token_count": core_count,
                    "log_core_nucleus_token_count": math.log1p(core_count),
                    "candidate_is_back": int(candidate in BACK_NUCLEI),
                    "distance_to_au": distance_to_au(candidate),
                    "phonetic_fit_to_au": -distance_to_au(candidate),
                }
            )

    data = pd.DataFrame(rows)
    for column in ["log_core_nucleus_token_count", "phonetic_fit_to_au"]:
        data[f"{column}_z"], _, _ = standardize(data[column])

    feature_columns = [
        "in_core_nucleus",
        "phonetic_fit_to_au_z",
    ]
    return data, candidates, feature_columns


def fit_conditional_softmax(
    data: pd.DataFrame,
    feature_columns: list[str],
    ridge_lambda: float = RIDGE_LAMBDA,
    max_iter: int = 100,
    tol: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    beta = np.zeros(len(feature_columns))
    groups = []
    for _, group in data.groupby(["point_id", "point_name"], sort=False):
        x = group[feature_columns].to_numpy(dtype=float)
        y = group["observed_token_count"].to_numpy(dtype=float)
        groups.append((group.index.to_numpy(), x, y))

    for _ in range(max_iter):
        gradient = -ridge_lambda * beta
        hessian = np.eye(len(beta)) * ridge_lambda
        for _, x, y in groups:
            total = float(y.sum())
            scores = np.clip(x @ beta, -35, 35)
            scores = scores - scores.max()
            probs = np.exp(scores)
            probs = probs / probs.sum()
            expected = probs @ x
            observed = y @ x
            gradient += observed - total * expected
            centered = x - expected
            hessian += total * (centered.T @ (probs[:, None] * centered))

        step = np.linalg.solve(hessian, gradient)
        beta += step
        if np.max(np.abs(step)) < tol:
            break

    covariance = np.linalg.pinv(hessian)

    result = data.copy()
    probs_all = []
    for indices, x, _ in groups:
        scores = np.clip(x @ beta, -35, 35)
        scores = scores - scores.max()
        probs = np.exp(scores)
        probs = probs / probs.sum()
        probs_all.extend(zip(indices, probs))
    prob_series = pd.Series({int(idx): float(prob) for idx, prob in probs_all})
    result["predicted_probability"] = result.index.map(prob_series)
    result["predicted_token_count"] = (
        result["predicted_probability"] * result["point_monophthong_token_count"]
    )
    return beta, covariance, result


def run_attractor_model(
    relation: pd.DataFrame, value_summary: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data, _, feature_columns = prepare_attractor_data(relation, value_summary)
    beta, covariance, probabilities = fit_conditional_softmax(data, feature_columns)
    std_error = np.sqrt(np.maximum(np.diag(covariance), 0.0))

    labels = {
        "in_core_nucleus": "S0-S3已有该元音",
        "phonetic_fit_to_au_z": "与*au单音化方向相近",
    }
    coef = pd.DataFrame(
        {
            "term": feature_columns,
            "term_label": [labels[column] for column in feature_columns],
            "coefficient": beta,
            "std_error_approx": std_error,
            "choice_multiplier": np.exp(beta),
            "model": "ridge_conditional_softmax",
            "ridge_lambda": RIDGE_LAMBDA,
        }
    )

    summary = (
        probabilities.groupby("candidate_nucleus", as_index=False)
        .agg(
            observed_token_count=("observed_token_count", "sum"),
            predicted_token_count=("predicted_token_count", "sum"),
            point_count_observed=("observed_token_count", lambda x: int((x > 0).sum())),
        )
        .sort_values("observed_token_count", ascending=False)
    )
    total_obs = summary["observed_token_count"].sum()
    total_pred = summary["predicted_token_count"].sum()
    summary["observed_share"] = summary["observed_token_count"] / total_obs
    summary["predicted_share"] = summary["predicted_token_count"] / total_pred

    probabilities = probabilities.sort_values(
        ["point_id", "point_name", "predicted_probability"],
        ascending=[True, True, False],
    )
    return coef, probabilities, summary


def plot_logistic(coef: pd.DataFrame, predictions: pd.DataFrame) -> None:
    set_chinese_font()
    plot_coef = coef[coef["term"] != "intercept"].copy()
    plot_coef = plot_coef.sort_values("coefficient")

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    axes[0].barh(plot_coef["term_label"], plot_coef["coefficient"], color="#4C78A8")
    axes[0].axvline(0, color="black", linewidth=1)
    axes[0].set_xlabel("log-odds 系数")
    axes[0].set_title("模型1：豪韵单音化的影响因素")

    colors = predictions["has_core_open_mid_back"].map({1: "#F58518", 0: "#54A24B"})
    sizes = 20 + np.sqrt(predictions["hao_total_token_count"]) * 9
    axes[1].scatter(
        predictions["observed_monophthong_share"],
        predictions["predicted_monophthong_probability"],
        s=sizes,
        c=colors,
        edgecolor="black",
        alpha=0.8,
    )
    axes[1].plot([0, 1], [0, 1], color="gray", linestyle="--")
    axes[1].set_xlabel("观察到的豪韵单音化比例")
    axes[1].set_ylabel("模型预测的单音化概率")
    axes[1].set_title("点越大，豪韵 token 越多")
    axes[1].text(
        0.02,
        0.10,
        "橙色：S0-S3已有ɔ/ɒ\n绿色：S0-S3未见ɔ/ɒ",
        transform=axes[1].transAxes,
        fontsize=10,
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "none"},
    )

    fig.tight_layout()
    fig.savefig(LOGISTIC_FIG_OUTPUT, dpi=220, bbox_inches="tight")
    plt.close(fig)


def plot_attractor(coef: pd.DataFrame, summary: pd.DataFrame) -> None:
    set_chinese_font()
    plot_coef = coef.sort_values("coefficient")
    plot_summary = summary.sort_values("observed_token_count", ascending=False)
    x = np.arange(len(plot_summary))

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    axes[0].barh(plot_coef["term_label"], plot_coef["coefficient"], color="#72B7B2")
    axes[0].axvline(0, color="black", linewidth=1)
    axes[0].set_xlabel("choice log-odds 系数")
    axes[0].set_title("模型2：目标元音的吸引因素")

    width = 0.38
    axes[1].bar(
        x - width / 2,
        plot_summary["observed_token_count"],
        width=width,
        label="观察 token",
        color="#E45756",
    )
    axes[1].bar(
        x + width / 2,
        plot_summary["predicted_token_count"],
        width=width,
        label="模型预测 token",
        color="#4C78A8",
    )
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(plot_summary["candidate_nucleus"])
    axes[1].set_ylabel("豪韵单元音 token")
    axes[1].set_title("豪韵单音化目标：观察 vs 预测")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(ATTRACTOR_FIG_OUTPUT, dpi=220, bbox_inches="tight")
    plt.close(fig)


def run_analysis() -> None:
    if not RELATION_PATH.exists():
        raise FileNotFoundError(f"未找到输入文件：{RELATION_PATH}")
    if not VALUE_SUMMARY_PATH.exists():
        raise FileNotFoundError(f"未找到输入文件：{VALUE_SUMMARY_PATH}")

    relation = pd.read_csv(RELATION_PATH)
    value_summary = pd.read_csv(VALUE_SUMMARY_PATH)

    VALUE_DIR.mkdir(parents=True, exist_ok=True)
    FIGS_DIR.mkdir(parents=True, exist_ok=True)

    logistic_coef, logistic_predictions = run_logistic_model(relation)
    attractor_coef, attractor_probabilities, attractor_summary = run_attractor_model(
        relation, value_summary
    )

    logistic_coef.to_csv(LOGISTIC_COEF_OUTPUT, index=False, encoding="utf-8-sig")
    logistic_predictions.to_csv(LOGISTIC_PRED_OUTPUT, index=False, encoding="utf-8-sig")
    attractor_coef.to_csv(ATTRACTOR_COEF_OUTPUT, index=False, encoding="utf-8-sig")
    attractor_probabilities.to_csv(
        ATTRACTOR_PROB_OUTPUT, index=False, encoding="utf-8-sig"
    )
    attractor_summary.to_csv(
        ATTRACTOR_SUMMARY_OUTPUT, index=False, encoding="utf-8-sig"
    )

    plot_logistic(logistic_coef, logistic_predictions)
    plot_attractor(attractor_coef, attractor_summary)

    print(f"已生成单音化logistic系数：{LOGISTIC_COEF_OUTPUT}")
    print(f"已生成单音化logistic预测：{LOGISTIC_PRED_OUTPUT}")
    print(f"已生成吸引子softmax系数：{ATTRACTOR_COEF_OUTPUT}")
    print(f"已生成吸引子softmax概率：{ATTRACTOR_PROB_OUTPUT}")
    print(f"已生成吸引子softmax汇总：{ATTRACTOR_SUMMARY_OUTPUT}")
    print(f"已生成图：{LOGISTIC_FIG_OUTPUT}")
    print(f"已生成图：{ATTRACTOR_FIG_OUTPUT}")


if __name__ == "__main__":
    run_analysis()
