"""Phase 1 QC: classify each product's primary image as packshot vs lifestyle.

Metadata/QC only (see docs/DECISIONS.md) — this does not change preprocessing,
encoding, or fused scoring, and isn't shopper-facing. It exists so the Phase 6
inspector can optionally note "styled photo" later, and so reviewers can tell
which image-similarity neighbors might be noisier (a lifestyle photo's
embedding partly encodes a model's skin/hair, not just the product).

Method: border-region color uniformity — the same 5% border strip already
sampled for the whiteness score (pipeline/images.py._border_stats), but using
its standard deviation across R/G/B samples rather than a hard whiteness
threshold. A plain studio backdrop (white, off-white, grey, or a solid color)
is nearly flat regardless of its actual color, so std stays low; a person's
face/hair or a styled scene varies a lot, so std is high. This was chosen
over a bespoke face/skin detector (no proven-reliable one available cheaply)
and over a vision-LLM call per image (no LLM key configured yet at this point
in the roadmap — Phase 2's D4 comes right after this). See DECISIONS.md for
the calibration: thresholds were picked by manually inspecting images across
the std range, not guessed.

Thresholds:
  std <= PACKSHOT_STD_MAX   -> confident "packshot"
  std >= LIFESTYLE_STD_MIN  -> confident "lifestyle"
  otherwise                 -> ambiguous. A proposed label is still attached
                                (whichever side of the midpoint it falls on)
                                but provenance stays "heuristic" — these go
                                to the user for confirmation via the
                                ambiguous-only contact sheet
                                (pipeline/image_review.py) before anything
                                is treated as final.
"""

import json

from pipeline.images import PACKSHOT_SCORES_PATH
from pipeline.paths import ARTIFACTS_DIR

PACKSHOT_STD_MAX = 25.0
LIFESTYLE_STD_MIN = 70.0
MIDPOINT = (PACKSHOT_STD_MAX + LIFESTYLE_STD_MIN) / 2

LABELS_PATH = ARTIFACTS_DIR / "eval" / "image_type_labels.json"


def classify_std(std: float) -> tuple[str, bool]:
    """Returns (label, confident)."""
    if std <= PACKSHOT_STD_MAX:
        return "packshot", True
    if std >= LIFESTYLE_STD_MIN:
        return "lifestyle", True
    return ("packshot" if std < MIDPOINT else "lifestyle"), False


def classify_all() -> dict[str, dict]:
    scores = json.loads(PACKSHOT_SCORES_PATH.read_text())
    labels = {}
    for sku, info in scores.items():
        label, confident = classify_std(info["border_std"])
        labels[sku] = {
            "image_type": label,
            "confident": confident,
            "provenance": "heuristic",
            "border_std": info["border_std"],
            "whiteness_score": info["whiteness_score"],
        }
    return labels


def main() -> None:
    labels = classify_all()
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LABELS_PATH.write_text(json.dumps(labels, indent=2))

    n = len(labels)
    n_packshot_confident = sum(
        1 for v in labels.values() if v["image_type"] == "packshot" and v["confident"]
    )
    n_lifestyle_confident = sum(
        1 for v in labels.values() if v["image_type"] == "lifestyle" and v["confident"]
    )
    n_ambiguous = sum(1 for v in labels.values() if not v["confident"])
    print(
        f"n={n} packshot(confident)={n_packshot_confident} "
        f"lifestyle(confident)={n_lifestyle_confident} ambiguous={n_ambiguous}"
    )
    print(f"wrote {LABELS_PATH}")


if __name__ == "__main__":
    main()
