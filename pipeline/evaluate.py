"""Phase 4: evaluation (§8 Phase 4). Ranking-quality metrics with bootstrap
CIs over the 25 labeled queries, weight tuning via grid search +
leave-one-query-out validation, system-health proxies computed over the
full catalog, and failure-case surfacing. Writes artifacts/eval/report.json
and artifacts/eval/figures/*.png.
"""

import json
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import yaml

from core.bundle import Bundle, load_bundle
from core.filters import CandidateMeta, exclude_self_and_parent
from pipeline.baselines import random_within_type, same_type_nearest_price
from pipeline.metrics import (
    bootstrap_ci,
    jaccard_at_k,
    ndcg_at_k,
    precision_at_k,
    skewness,
)
from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR
from pipeline.recommend import recommend

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
K = 5
RANDOM_SEEDS = 100

# The roadmap's original LOCKED §3 default, frozen here on purpose. This
# script overwrites config/settings.yaml's and the bundle manifest's
# default_weights with the tuned result — so on any rerun after the first,
# bundle.manifest["default_weights"] *is* the tuned value, and "fused
# (default weights)" vs. "fused (tuned weights)" would silently become the
# same comparison if "default" were read from there. Pinning it here keeps
# the before/after comparison meaningful no matter how many times this runs.
ROADMAP_DEFAULT_WEIGHTS = {"image": 0.5, "text": 0.2, "meta": 0.3}
GRID_STEP = 0.1
FIGURES_DIR = ARTIFACTS_DIR / "eval" / "figures"

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_labels() -> dict[tuple[str, str], int]:
    raw = json.loads((DATA_DIR.parent / "labels" / "relevance_labels.json").read_text())
    return {(r["query_sku"], r["candidate_sku"]): r["label"] for r in raw["labels"]}


def load_query_skus() -> list[str]:
    pool = json.loads((ARTIFACTS_DIR / "eval" / "label_pool.json").read_text())
    return [entry["query_sku"] for entry in pool]


# ---------------------------------------------------------------------------
# Relevance lookup (§: unlabeled pool-external items are treated as
# relevance 0 — standard pooled-IR-evaluation convention, since only the
# original 6-source pool was hand-labeled; see the report's methodology
# notes and DECISIONS.md for the honest limitation this implies for
# fused-tuned and 99/100 random seeds).
# ---------------------------------------------------------------------------


def relevances_for(
    skus: list[str], query_sku: str, labels: dict[tuple[str, str], int]
) -> list[int]:
    return [labels.get((query_sku, sku), 0) for sku in skus]


# ---------------------------------------------------------------------------
# Named-method rankings (full recommend(), used for the 25-query x 7-method
# table — only 175 calls total, breakdown/reasons overhead is irrelevant)
# ---------------------------------------------------------------------------


def _sku_list(bundle: Bundle, query_sku: str, weights: dict) -> list[str]:
    return [item["sku"] for item in recommend(bundle, query_sku, k=K, weights=weights)["items"]]


def method_ranking(
    bundle: Bundle, method: str, query_sku: str, weights: dict | None = None
) -> list[str]:
    if method == "image_only":
        return _sku_list(bundle, query_sku, {"image": 1.0, "text": 0.0, "meta": 0.0})
    if method == "text_only":
        return _sku_list(bundle, query_sku, {"image": 0.0, "text": 1.0, "meta": 0.0})
    if method == "meta_only":
        return _sku_list(bundle, query_sku, {"image": 0.0, "text": 0.0, "meta": 1.0})
    if method == "fused_default":
        return _sku_list(bundle, query_sku, ROADMAP_DEFAULT_WEIGHTS)
    if method == "fused_tuned":
        return _sku_list(bundle, query_sku, weights)
    if method == "same_type_nearest_price":
        return same_type_nearest_price(bundle, query_sku, K)
    raise ValueError(method)


def random_within_type_mean_scores(
    bundle: Bundle, query_sku: str, labels: dict, n_seeds: int = RANDOM_SEEDS
) -> tuple[float, float]:
    ndcgs, precisions = [], []
    for seed in range(n_seeds):
        ranked = random_within_type(bundle, query_sku, K, seed)
        rels = relevances_for(ranked, query_sku, labels)
        ndcgs.append(ndcg_at_k(rels, K))
        precisions.append(precision_at_k(rels, K))
    return sum(ndcgs) / len(ndcgs), sum(precisions) / len(precisions)


# ---------------------------------------------------------------------------
# Weight tuning: fast path (raw matrix ops, no per-item overhead) so a
# 66-point grid x 25 leave-one-out folds is cheap.
# ---------------------------------------------------------------------------


def weight_grid(step: float = GRID_STEP) -> list[tuple[float, float, float]]:
    n = round(1 / step)
    return [
        (a / n, b / n, (n - a - b) / n)
        for a in range(n + 1)
        for b in range(n + 1 - a)
    ]


def _candidate_indices(bundle: Bundle, query_sku: str) -> tuple[int, np.ndarray]:
    """Same-type candidate indices for query_sku (self/parent excluded).
    Fallback is skipped here (Phase 0's data report: every product_type has
    >= k+1 members, so it never triggers at k=5 either) — documented, not
    silently different behavior for a case that can't arise on this catalog.
    """
    query_idx = bundle.index_of(query_sku)
    query_meta = CandidateMeta(
        sku=query_sku,
        product_type=bundle.catalog[query_sku]["product_type"],
        parent_id=bundle.catalog[query_sku].get("parent_id"),
    )
    all_meta = [
        CandidateMeta(
            sku=sku,
            product_type=bundle.catalog[sku]["product_type"],
            parent_id=bundle.catalog[sku].get("parent_id"),
        )
        for sku in bundle.ids
    ]
    candidates = exclude_self_and_parent(all_meta, query_meta)
    same_type = [c.sku for c in candidates if c.product_type == query_meta.product_type]
    idx = np.array([bundle.index_of(sku) for sku in same_type], dtype=int)
    return query_idx, idx


def _ndcg_for_weight_fast(
    bundle: Bundle,
    fused: np.ndarray,
    query_sku: str,
    candidate_cache: dict,
    labels: dict,
) -> float:
    query_idx, cand_idx = candidate_cache[query_sku]
    if len(cand_idx) == 0:
        return 0.0
    scores = fused[query_idx, cand_idx]
    order = np.argsort(-scores)[:K]
    top_skus = [bundle.ids[i] for i in cand_idx[order]]
    return ndcg_at_k(relevances_for(top_skus, query_sku, labels), K)


def mean_ndcg_for_weight(
    bundle: Bundle,
    weight: tuple[float, float, float],
    query_skus: list[str],
    candidate_cache: dict,
    labels: dict,
) -> list[float]:
    fused = (
        weight[0] * bundle.Z["image"] + weight[1] * bundle.Z["text"] + weight[2] * bundle.Z["meta"]
    )
    return [_ndcg_for_weight_fast(bundle, fused, q, candidate_cache, labels) for q in query_skus]


def select_flat_region_weight(
    bundle: Bundle,
    grid: list[tuple[float, float, float]],
    query_skus: list[str],
    candidate_cache: dict,
    labels: dict,
) -> dict:
    scored = [
        (w, mean_ndcg_for_weight(bundle, w, query_skus, candidate_cache, labels)) for w in grid
    ]
    means = [(w, sum(s) / len(s)) for w, s in scored]
    best_w, best_mean = max(means, key=lambda x: x[1])
    best_scores = next(s for w, s in scored if w == best_w)
    if len(best_scores) > 1:
        se = float(np.std(best_scores, ddof=1) / np.sqrt(len(best_scores)))
    else:
        se = 0.0
    tolerance = max(se, 1e-6)

    plateau = [w for w, m in means if m >= best_mean - tolerance]
    centroid = tuple(sum(w[i] for w in plateau) / len(plateau) for i in range(3))
    chosen = min(grid, key=lambda w: sum((w[i] - centroid[i]) ** 2 for i in range(3)))
    chosen_mean = next(m for w, m in means if w == chosen)

    return {
        "best_single_point": {"weights": best_w, "mean_ndcg": best_mean},
        "tolerance_se": tolerance,
        "plateau_size": len(plateau),
        "plateau_weights": plateau,
        "chosen_weights": chosen,
        "chosen_weights_mean_ndcg": chosen_mean,
        "all_scores": means,
    }


def leave_one_query_out(
    bundle: Bundle,
    grid: list[tuple[float, float, float]],
    query_skus: list[str],
    candidate_cache: dict,
    labels: dict,
) -> list[float]:
    held_out_scores = []
    for i, held_out in enumerate(query_skus):
        train = query_skus[:i] + query_skus[i + 1 :]
        selection = select_flat_region_weight(bundle, grid, train, candidate_cache, labels)
        scores = mean_ndcg_for_weight(
            bundle, selection["chosen_weights"], [held_out], candidate_cache, labels
        )
        held_out_scores.append(scores[0])
    return held_out_scores


# ---------------------------------------------------------------------------
# Proxies (full catalog — no labels needed)
# ---------------------------------------------------------------------------


def compute_proxies(bundle: Bundle, weights: dict) -> dict:
    """Proxies describe the *shipped* system's behavior, so they use
    `weights` (the tuned weights, passed in explicitly from main() — not
    ROADMAP_DEFAULT_WEIGHTS, and not read back off bundle.manifest either,
    since by the time this runs manifest.json has already been overwritten
    with the same tuned value; passing it explicitly avoids depending on
    that ordering).
    """
    all_skus = bundle.ids

    fused_top5: dict[str, list[str]] = {}
    image_top5: dict[str, list[str]] = {}
    text_top5: dict[str, list[str]] = {}
    meta_zeroed_top5: dict[str, list[str]] = {}

    meta_zeroed_weights = {"image": weights["image"], "text": weights["text"], "meta": 0.0}

    for sku in all_skus:
        fused_top5[sku] = _sku_list(bundle, sku, weights)
        image_top5[sku] = method_ranking(bundle, "image_only", sku)
        text_top5[sku] = method_ranking(bundle, "text_only", sku)
        meta_zeroed_top5[sku] = [
            i["sku"] for i in recommend(bundle, sku, k=K, weights=meta_zeroed_weights)["items"]
        ]

    # Held-out attribute agreement: share of top-5 (meta excluded) matching
    # the query's own collection, over queries that actually have one.
    agreement_scores = []
    for sku in all_skus:
        collection = bundle.catalog[sku].get("collection")
        if not collection:
            continue
        recs = meta_zeroed_top5[sku]
        match = sum(1 for r in recs if bundle.catalog[r].get("collection") == collection)
        agreement_scores.append(match / len(recs) if recs else 0.0)
    held_out_attribute_agreement = float(np.mean(agreement_scores)) if agreement_scores else None

    # Cross-signal agreement: Jaccard@5(image-only, text-only)
    jaccards = [jaccard_at_k(image_top5[sku], text_top5[sku], K) for sku in all_skus]
    cross_signal_agreement = float(np.mean(jaccards))

    # Coverage
    recommended_union = set()
    for recs in fused_top5.values():
        recommended_union.update(recs)
    coverage = {
        "share": len(recommended_union) / len(all_skus),
        "n_unique_recommended": len(recommended_union),
        "n_catalog": len(all_skus),
    }

    # Hubness: in-degree over fused (tuned weights) top-5 lists
    indegree: dict[str, int] = {sku: 0 for sku in all_skus}
    for recs in fused_top5.values():
        for r in recs:
            indegree[r] += 1
    indegree_values = list(indegree.values())
    top_hubs = sorted(indegree.items(), key=lambda kv: -kv[1])[:5]
    hubness = {
        "mean_indegree": float(np.mean(indegree_values)),
        "std_indegree": float(np.std(indegree_values)),
        "skewness": skewness(indegree_values),
        "top_hubs": [
            {"sku": sku, "title": bundle.catalog[sku]["title"], "count": count}
            for sku, count in top_hubs
        ],
        # for chart_hubness only — popped before this dict is written to report.json
        "_indegree_values": indegree_values,
    }

    # Diversity: mean intra-list similarity within each fused top-5, using
    # the same weighted blend of *raw* S (not Z, which is unbounded/can be
    # negative — S stays roughly 0..1 and is more readable as a "diversity"
    # number).
    S_fused = (
        weights["image"] * bundle.S["image"]
        + weights["text"] * bundle.S["text"]
        + weights["meta"] * bundle.S["meta"]
    )
    intra_list_sims = []
    for recs in fused_top5.values():
        idxs = [bundle.index_of(r) for r in recs]
        if len(idxs) < 2:
            continue
        pairs = [
            S_fused[a, b] for i, a in enumerate(idxs) for b in idxs[i + 1 :]
        ]
        intra_list_sims.append(float(np.mean(pairs)))
    diversity = float(np.mean(intra_list_sims)) if intra_list_sims else None

    # Price sanity: median price ratio, query vs. each fused (tuned weights) rec
    ratios = []
    for sku, recs in fused_top5.items():
        p_query = bundle.catalog[sku].get("price_inr")
        if p_query is None:
            continue
        for r in recs:
            p_rec = bundle.catalog[r].get("price_inr")
            if p_rec is None:
                continue
            ratios.append(max(p_query, p_rec) / min(p_query, p_rec))
    price_sanity_median_ratio = float(np.median(ratios)) if ratios else None

    # Robustness: pull Phase 1's augmentation sanity check
    robustness_path = ARTIFACTS_DIR / "eval" / "image_sanity_check.json"
    robustness = None
    if robustness_path.exists():
        sanity = json.loads(robustness_path.read_text())
        robustness = {"hits": sanity["hits"], "n_samples": sanity["n_samples"]}

    return {
        "held_out_attribute_agreement": held_out_attribute_agreement,
        "cross_signal_agreement_jaccard5": cross_signal_agreement,
        "coverage": coverage,
        "hubness": hubness,
        "diversity_mean_intra_list_similarity": diversity,
        "price_sanity_median_ratio": price_sanity_median_ratio,
        "image_augmentation_robustness": robustness,
    }


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------


def failure_cases(
    bundle: Bundle,
    query_skus: list[str],
    per_query_ndcg: dict[str, float],
    labels: dict,
    weights: dict,
    n: int = 5,
) -> list[dict]:
    """Surfaces the n worst queries under the *shipped* (tuned) model —
    what the actual final system struggles with, not the pre-tuning
    roadmap default.
    """
    worst = sorted(query_skus, key=lambda q: per_query_ndcg[q])[:n]
    cases = []
    for q in worst:
        ranked = _sku_list(bundle, q, weights)
        rels = relevances_for(ranked, q, labels)
        cases.append(
            {
                "query_sku": q,
                "query_title": bundle.catalog[q]["title"],
                "ndcg_at_5": per_query_ndcg[q],
                "top5": [
                    {"sku": sku, "title": bundle.catalog[sku]["title"], "label": rel}
                    for sku, rel in zip(ranked, rels, strict=True)
                ],
            }
        )
    return cases


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def _style_ax(ax):
    ax.set_facecolor("#241C17")
    ax.figure.set_facecolor("#241C17")
    ax.tick_params(colors="#FBF7F0")
    ax.xaxis.label.set_color("#FBF7F0")
    ax.yaxis.label.set_color("#FBF7F0")
    ax.title.set_color("#FBF7F0")
    for spine in ax.spines.values():
        spine.set_color("#8A8D8C")


def chart_ndcg_by_method(methods: dict) -> None:
    names = list(methods.keys())
    means = [methods[m]["ndcg_at_5"]["mean"] for m in names]
    lo = [methods[m]["ndcg_at_5"]["mean"] - methods[m]["ndcg_at_5"]["ci_low"] for m in names]
    hi = [methods[m]["ndcg_at_5"]["ci_high"] - methods[m]["ndcg_at_5"]["mean"] for m in names]

    fig, ax = plt.subplots(figsize=(8, 5))
    _style_ax(ax)
    y = range(len(names))
    ax.barh(y, means, xerr=[lo, hi], color="#C9A55C", ecolor="#B7DEE0", capsize=4)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.set_xlabel("NDCG@5 (95% bootstrap CI, 1000 resamples)")
    ax.set_title("Ranking quality by method")
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "ndcg_by_method.png", dpi=150)
    plt.close(fig)


def chart_hubness(indegree_values: list[int]) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    _style_ax(ax)
    ax.hist(indegree_values, bins=range(0, max(indegree_values) + 2), color="#C9A55C")
    ax.set_xlabel("Times a product appears in another product's top-5")
    ax.set_ylabel("Number of products")
    ax.set_title("Hubness: in-degree distribution (fused, tuned weights, full catalog)")
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "hubness_histogram.png", dpi=150)
    plt.close(fig)


def chart_weight_grid(all_scores: list[tuple[tuple[float, float, float], float]], chosen) -> None:
    wi = [w[0] for w, _ in all_scores]
    wt = [w[1] for w, _ in all_scores]
    ndcg = [s for _, s in all_scores]

    fig, ax = plt.subplots(figsize=(6, 5))
    _style_ax(ax)
    sc = ax.scatter(wi, wt, c=ndcg, cmap="YlOrBr", s=120, edgecolors="#8A8D8C")
    ax.scatter(
        [chosen[0]], [chosen[1]], marker="*", s=400, color="#B7DEE0", zorder=5, label="chosen"
    )
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label("mean NDCG@5 (all 25 labeled queries)", color="#FBF7F0")
    cbar.ax.yaxis.set_tick_params(color="#FBF7F0")
    plt.setp(plt.getp(cbar.ax, "yticklabels"), color="#FBF7F0")
    ax.set_xlabel("w_image")
    ax.set_ylabel("w_text  (w_meta = 1 - w_image - w_text)")
    ax.set_title("Weight grid search — full-simplex NDCG@5 surface")
    ax.legend(facecolor="#241C17", labelcolor="#FBF7F0")
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "weight_grid.png", dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def main() -> None:
    bundle = load_bundle(ARTIFACTS_DIR)
    labels = load_labels()
    query_skus = load_query_skus()

    label_values = [v for v in labels.values()]
    labels_summary = {
        "total": len(label_values),
        "by_value": {str(v): label_values.count(v) for v in (0, 1, 2)},
    }

    print(f"loaded {len(labels)} labels across {len(query_skus)} queries")

    # --- Named-method ablation table -------------------------------------
    methods: dict[str, dict] = {}
    per_query_ndcg: dict[str, dict[str, float]] = {}

    named_methods = (
        "image_only",
        "text_only",
        "meta_only",
        "fused_default",
        "same_type_nearest_price",
    )
    for method in named_methods:
        ndcgs, precisions = [], []
        per_query_ndcg[method] = {}
        for q in query_skus:
            ranked = method_ranking(bundle, method, q)
            rels = relevances_for(ranked, q, labels)
            ndcg = ndcg_at_k(rels, K)
            ndcgs.append(ndcg)
            precisions.append(precision_at_k(rels, K))
            per_query_ndcg[method][q] = ndcg
        methods[method] = {
            "ndcg_at_5": bootstrap_ci(ndcgs),
            "p_at_5": bootstrap_ci(precisions),
        }
        print(f"{method}: NDCG@5={methods[method]['ndcg_at_5']['mean']:.4f}")

    # random-within-type: mean of 100 seeds, per query, then the usual
    # 25-query bootstrap over those per-query means
    ndcgs, precisions = [], []
    per_query_ndcg["random_within_type"] = {}
    for q in query_skus:
        ndcg, prec = random_within_type_mean_scores(bundle, q, labels)
        ndcgs.append(ndcg)
        precisions.append(prec)
        per_query_ndcg["random_within_type"][q] = ndcg
    methods["random_within_type"] = {
        "ndcg_at_5": bootstrap_ci(ndcgs),
        "p_at_5": bootstrap_ci(precisions),
    }
    print(f"random_within_type: NDCG@5={methods['random_within_type']['ndcg_at_5']['mean']:.4f}")

    # --- Weight tuning ------------------------------------------------
    print("running weight grid search + leave-one-query-out validation...")
    grid = weight_grid(GRID_STEP)
    candidate_cache = {q: _candidate_indices(bundle, q) for q in query_skus}

    full_selection = select_flat_region_weight(bundle, grid, query_skus, candidate_cache, labels)
    loo_scores = leave_one_query_out(bundle, grid, query_skus, candidate_cache, labels)

    tuned_weights_tuple = full_selection["chosen_weights"]
    tuned_weights = {
        "image": tuned_weights_tuple[0],
        "text": tuned_weights_tuple[1],
        "meta": tuned_weights_tuple[2],
    }
    plateau_n = full_selection["plateau_size"]
    print(f"tuned weights: {tuned_weights} (plateau size {plateau_n}/{len(grid)})")

    weight_tuning = {
        "grid_step": GRID_STEP,
        "n_grid_points": len(grid),
        "best_single_point": {
            "weights": full_selection["best_single_point"]["weights"],
            "mean_ndcg_at_5": full_selection["best_single_point"]["mean_ndcg"],
        },
        "tolerance_se": full_selection["tolerance_se"],
        "plateau_size": full_selection["plateau_size"],
        "chosen_weights": tuned_weights,
        "chosen_weights_mean_ndcg_at_5": full_selection["chosen_weights_mean_ndcg"],
        "leave_one_query_out_ndcg_at_5": bootstrap_ci(loo_scores),
    }

    # fused_tuned as a named method too, using the chosen weights
    ndcgs, precisions = [], []
    per_query_ndcg["fused_tuned"] = {}
    for q in query_skus:
        ranked = method_ranking(bundle, "fused_tuned", q, weights=tuned_weights)
        rels = relevances_for(ranked, q, labels)
        ndcg = ndcg_at_k(rels, K)
        ndcgs.append(ndcg)
        precisions.append(precision_at_k(rels, K))
        per_query_ndcg["fused_tuned"][q] = ndcg
    methods["fused_tuned"] = {
        "ndcg_at_5": bootstrap_ci(ndcgs),
        "p_at_5": bootstrap_ci(precisions),
    }
    print(f"fused_tuned: NDCG@5={methods['fused_tuned']['ndcg_at_5']['mean']:.4f}")

    # --- Plain fused-vs-baseline comparison -------------------------------
    fused_ndcg = methods["fused_default"]["ndcg_at_5"]["mean"]
    baseline_ndcg = methods["same_type_nearest_price"]["ndcg_at_5"]["mean"]
    beats_baseline = fused_ndcg > baseline_ndcg
    fused_vs_baseline = {
        "fused_default_ndcg_at_5": fused_ndcg,
        "same_type_nearest_price_ndcg_at_5": baseline_ndcg,
        "fused_beats_baseline": beats_baseline,
        "note": (
            "fused (default weights) beats the same-type + nearest-price baseline on NDCG@5."
            if beats_baseline
            else (
                "fused (default weights) does NOT beat the same-type + nearest-price baseline "
                "on NDCG@5. Reported plainly, not papered over — see the report's "
                "'methodology_notes' for discussion."
            )
        ),
    }
    print(fused_vs_baseline["note"])

    # --- Proxies ------------------------------------------------------
    print("computing proxies over the full catalog...")
    proxies = compute_proxies(bundle, tuned_weights)

    # --- Failure cases --------------------------------------------------
    # Surfaced under the shipped (tuned) model, not the pre-tuning roadmap default.
    cases = failure_cases(
        bundle, query_skus, per_query_ndcg["fused_tuned"], labels, weights=tuned_weights
    )

    # --- Charts ---------------------------------------------------------
    indegree_values = proxies["hubness"].pop("_indegree_values")
    chart_ndcg_by_method(methods)
    chart_hubness(indegree_values)
    chart_weight_grid(full_selection["all_scores"], tuned_weights_tuple)

    # --- Write chosen weights back -----------------------------------
    # A regex substitution on just the default_weights line, not
    # yaml.safe_load + yaml.safe_dump of the whole file — the latter is
    # correct but silently drops every comment in settings.yaml (found the
    # hard way: it did exactly that the first time this ran). This preserves
    # everything else in the file byte-for-byte.
    settings_path = CONFIG_DIR / "settings.yaml"
    settings_text = settings_path.read_text()
    new_line = (
        "  default_weights: "
        f"{{image: {tuned_weights['image']}, text: {tuned_weights['text']}, "
        f"meta: {tuned_weights['meta']}}}"
    )
    settings_text = re.sub(
        r"^  default_weights:.*$", new_line, settings_text, count=1, flags=re.MULTILINE
    )
    settings_path.write_text(settings_text)

    manifest_path = ARTIFACTS_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["default_weights"] = tuned_weights
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print("wrote tuned weights back to config/settings.yaml and artifacts/manifest.json")

    # --- Report -----------------------------------------------------------
    report = {
        "n_queries": len(query_skus),
        "k": K,
        "labels_summary": labels_summary,
        "methods": methods,
        "fused_vs_baseline": fused_vs_baseline,
        "weight_tuning": weight_tuning,
        "proxies": proxies,
        "failure_cases": cases,
        "methodology_notes": [
            "NDCG@5/P@5 use graded relevance (labels 0/1/2 as gains) over the 25 "
            "stratified queries labeled per docs/LABELING_GUIDE.md, with 95% "
            "bootstrap CIs (1000 resamples over queries).",
            "Only the original 6-source label pool (image-only/text-only/meta-only/"
            "fused-default/random-within-type-seed-0/same-type-nearest-price, top-8 "
            "each) was hand-labeled. Any candidate outside that pool — which fused-"
            "tuned and 99/100 of random-within-type's seeds can surface — is scored "
            "as relevance 0 (standard pooled-IR-evaluation convention), not "
            "re-labeled. This is a real limitation: fused-tuned and the random "
            "baseline's off-seed-0 scores are conservative lower bounds, not exact.",
            "Weight tuning selects the centroid of the grid points within one "
            "standard error of the best point (not the single best point), then "
            "snaps to the nearest 0.1-grid weight, per the roadmap's 'prefer a flat "
            "region' instruction. leave_one_query_out_ndcg_at_5 re-runs that full "
            "selection procedure per held-out query so it isn't overfit to all 25.",
            "Proxies (coverage/hubness/diversity/price-sanity/cross-signal "
            "agreement/held-out attribute agreement) run over the full 472-product "
            "catalog, not just the 25 labeled queries — they don't need labels.",
        ],
    }
    out_path = ARTIFACTS_DIR / "eval" / "report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
