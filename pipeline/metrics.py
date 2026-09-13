"""Phase 4: ranking-quality metrics + bootstrap CIs (§8 Phase 4). Pure
functions, no I/O — pipeline/evaluate.py does the loading/orchestration.
"""

import math

import numpy as np


def dcg_at_k(relevances: list[float], k: int) -> float:
    return sum(rel / math.log2(i + 2) for i, rel in enumerate(relevances[:k]))


def ndcg_at_k(relevances: list[float], k: int) -> float:
    """Graded-relevance NDCG@k using the 0/1/2 labels directly as gains."""
    dcg = dcg_at_k(relevances, k)
    ideal = dcg_at_k(sorted(relevances, reverse=True), k)
    return dcg / ideal if ideal > 0 else 0.0


def precision_at_k(relevances: list[float], k: int, threshold: float = 1.0) -> float:
    top = relevances[:k]
    if not top:
        return 0.0
    return sum(1 for r in top if r >= threshold) / len(top)


def bootstrap_ci(
    values: list[float], n_resamples: int = 1000, alpha: float = 0.05, seed: int = 0
) -> dict:
    """95% (default) bootstrap CI over queries — resample query-level scores
    with replacement, per §8 Phase 4 ("mandatory" given only 25 queries).
    """
    values_arr = np.array(values, dtype=np.float64)
    n = len(values_arr)
    if n == 0:
        return {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0}

    rng = np.random.default_rng(seed)
    means = np.empty(n_resamples)
    for i in range(n_resamples):
        sample = rng.choice(values_arr, size=n, replace=True)
        means[i] = sample.mean()

    return {
        "mean": float(values_arr.mean()),
        "ci_low": float(np.percentile(means, 100 * alpha / 2)),
        "ci_high": float(np.percentile(means, 100 * (1 - alpha / 2))),
    }


def jaccard_at_k(a: list[str], b: list[str], k: int) -> float:
    sa, sb = set(a[:k]), set(b[:k])
    union = sa | sb
    return len(sa & sb) / len(union) if union else 0.0


def skewness(values: list[float]) -> float:
    """Fisher-Pearson adjusted skewness coefficient."""
    arr = np.array(values, dtype=np.float64)
    n = len(arr)
    if n < 3:
        return 0.0
    mean = arr.mean()
    std = arr.std(ddof=0)
    if std == 0:
        return 0.0
    g1 = np.mean(((arr - mean) / std) ** 3)
    return float((math.sqrt(n * (n - 1)) / (n - 2)) * g1)
