"""Score normalization and fusion (§3 LOCKED, §8 Phase 3). numpy-only —
imported by both the offline pipeline and the API (rule 4).
"""

import numpy as np


def offdiag_zscore(S: np.ndarray) -> np.ndarray:
    """Z-score an N×N similarity matrix over its off-diagonal entries only.

    The diagonal (self-similarity = 1.0) would inflate the mean and std if
    included — every item is maximally similar to itself, which isn't a
    signal about how the *rest* of the catalog spreads out.
    """
    n = len(S)
    mask = ~np.eye(n, dtype=bool)
    off_diag = S[mask]
    return (S - off_diag.mean()) / (off_diag.std() + 1e-8)


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Validate and normalize fusion weights to sum to 1.

    Raises ValueError for a negative weight or an all-zero set — both are
    the API's job to turn into a 422, not silently coerce.
    """
    if any(w < 0 for w in weights.values()):
        raise ValueError(f"weights must be >= 0, got {weights}")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("weights must not all be zero")
    return {signal: w / total for signal, w in weights.items()}


def fuse_row(Z: dict[str, np.ndarray], q: int, weights: dict[str, float]) -> np.ndarray:
    """Weighted sum of one query row across signals. Z[signal] is N×N; weights
    need not be pre-normalized (fuse_row normalizes them itself).
    """
    w = normalize_weights(weights)
    signals = list(w.keys())
    return sum(w[s] * Z[s][q] for s in signals)


def topk_indices(
    scores: np.ndarray, ids: list[str], k: int, exclude: set[int] = frozenset()
) -> list[int]:
    """Indices of the top-k scores, descending, tie-broken by ascending sku
    (§3 LOCKED: "Score descending, then sku ascending" — deterministic
    output when scores tie, which off-diagonal z-scored floats can do at
    this catalog's scale, e.g. two identical rows).
    """
    eligible = [i for i in range(len(scores)) if i not in exclude]
    eligible.sort(key=lambda i: (-scores[i], ids[i]))
    return eligible[:k]
