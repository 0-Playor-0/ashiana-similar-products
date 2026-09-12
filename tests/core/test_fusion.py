import numpy as np
import pytest

from core.fusion import fuse_row, normalize_weights, offdiag_zscore, topk_indices


def test_offdiag_zscore_excludes_diagonal():
    # A huge diagonal that would badly skew a naive z-score if included.
    S = np.array(
        [
            [1000.0, 0.1, 0.2],
            [0.1, 1000.0, 0.3],
            [0.2, 0.3, 1000.0],
        ]
    )
    Z = offdiag_zscore(S)
    off_diag = Z[~np.eye(3, dtype=bool)]
    # off-diagonal entries, once z-scored among themselves, average to ~0
    assert abs(off_diag.mean()) < 1e-6
    # the diagonal was excluded from the normalization stats, so it lands far
    # from 0 rather than being folded into a near-zero-mean distribution
    assert Z[0, 0] > 100


def test_normalize_weights_sums_to_one():
    w = normalize_weights({"image": 2.0, "text": 1.0, "meta": 1.0})
    assert pytest.approx(sum(w.values())) == 1.0
    assert pytest.approx(w["image"]) == 0.5


def test_normalize_weights_rejects_all_zero():
    with pytest.raises(ValueError):
        normalize_weights({"image": 0.0, "text": 0.0, "meta": 0.0})


def test_normalize_weights_rejects_negative():
    with pytest.raises(ValueError):
        normalize_weights({"image": -1.0, "text": 1.0})


def test_fuse_row_weighted_sum():
    Z = {
        "image": np.array([[1.0, 2.0], [3.0, 4.0]]),
        "text": np.array([[10.0, 20.0], [30.0, 40.0]]),
    }
    row = fuse_row(Z, q=0, weights={"image": 1.0, "text": 1.0})
    # normalized to 0.5/0.5
    assert row.tolist() == pytest.approx([0.5 * 1.0 + 0.5 * 10.0, 0.5 * 2.0 + 0.5 * 20.0])


def test_fuse_row_rankings_unchanged_by_constant_shift_of_z():
    """§11: rankings are unchanged when a constant is added to any Z matrix —
    fusion is a weighted sum, so a uniform shift just shifts every score by
    the same amount and never changes their relative order."""
    rng = np.random.default_rng(0)
    Z = {
        "image": rng.normal(size=(6, 6)),
        "text": rng.normal(size=(6, 6)),
        "meta": rng.normal(size=(6, 6)),
    }
    weights = {"image": 0.5, "text": 0.2, "meta": 0.3}
    ids = [f"sku{i}" for i in range(6)]

    before = fuse_row(Z, q=0, weights=weights)
    ranking_before = topk_indices(before, ids, k=6, exclude={0})

    shifted = {signal: matrix + 7.0 for signal, matrix in Z.items()}
    after = fuse_row(shifted, q=0, weights=weights)
    ranking_after = topk_indices(after, ids, k=6, exclude={0})

    assert ranking_before == ranking_after


def test_topk_indices_tie_break_is_score_desc_then_sku_asc():
    scores = np.array([1.0, 1.0, 0.5, 1.0])
    ids = ["c", "a", "z", "b"]
    # three-way tie at 1.0 among indices 0,1,3 -> sku order a(1), b(3), c(0)
    assert topk_indices(scores, ids, k=3) == [1, 3, 0]


def test_topk_indices_deterministic_across_repeated_calls():
    scores = np.array([0.3, 0.9, 0.9, 0.1])
    ids = ["d", "b", "a", "c"]
    results = {tuple(topk_indices(scores, ids, k=4)) for _ in range(10)}
    assert len(results) == 1
