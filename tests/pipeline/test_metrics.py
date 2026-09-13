import math

import pytest

from pipeline.metrics import (
    bootstrap_ci,
    dcg_at_k,
    jaccard_at_k,
    ndcg_at_k,
    precision_at_k,
    skewness,
)


def test_ndcg_perfect_ranking_is_one():
    assert ndcg_at_k([2, 2, 1, 1, 0], 5) == pytest.approx(1.0)


def test_ndcg_empty_or_all_zero_is_zero():
    assert ndcg_at_k([], 5) == 0.0
    assert ndcg_at_k([0, 0, 0], 5) == 0.0


def test_ndcg_worse_ordering_scores_lower_than_ideal():
    ideal = [2, 1, 1, 0, 0]
    worse = [0, 0, 1, 1, 2]
    assert ndcg_at_k(worse, 5) < ndcg_at_k(ideal, 5)
    assert ndcg_at_k(ideal, 5) == pytest.approx(1.0)


def test_ndcg_matches_hand_computed_value():
    rels = [2, 1, 0, 0, 1]
    dcg = 2 / math.log2(2) + 1 / math.log2(3) + 0 + 0 + 1 / math.log2(6)
    idcg = 2 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4) + 0 + 0
    assert ndcg_at_k(rels, 5) == pytest.approx(dcg / idcg)


def test_dcg_at_k_respects_k():
    assert dcg_at_k([1, 1, 1, 1, 1], 2) == pytest.approx(1 + 1 / math.log2(3))


def test_precision_at_k_counts_relevant_threshold():
    assert precision_at_k([2, 1, 0, 0, 1], 5, threshold=1.0) == pytest.approx(3 / 5)
    assert precision_at_k([2, 1, 0, 0, 1], 5, threshold=2.0) == pytest.approx(1 / 5)


def test_precision_at_k_empty_is_zero():
    assert precision_at_k([], 5) == 0.0


def test_bootstrap_ci_contains_mean_and_is_sane():
    values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
    result = bootstrap_ci(values, n_resamples=500, seed=1)
    assert result["ci_low"] <= result["mean"] <= result["ci_high"]
    assert result["mean"] == pytest.approx(sum(values) / len(values))


def test_bootstrap_ci_is_narrower_with_less_variance():
    low_var = bootstrap_ci([0.5] * 20, n_resamples=500, seed=1)
    high_var = bootstrap_ci([0.0, 1.0] * 10, n_resamples=500, seed=1)
    assert (low_var["ci_high"] - low_var["ci_low"]) < (
        high_var["ci_high"] - high_var["ci_low"]
    )


def test_jaccard_at_k():
    assert jaccard_at_k(["a", "b", "c"], ["a", "b", "c"], 3) == 1.0
    assert jaccard_at_k(["a", "b"], ["c", "d"], 2) == 0.0
    assert jaccard_at_k(["a", "b", "c"], ["b", "c", "d"], 3) == pytest.approx(2 / 4)


def test_skewness_symmetric_distribution_near_zero():
    values = [1, 2, 3, 4, 5, 4, 3, 2, 1]
    assert skewness(values) == pytest.approx(0.0, abs=0.3)


def test_skewness_right_skewed_is_positive():
    values = [1, 1, 1, 1, 1, 2, 10]
    assert skewness(values) > 0
