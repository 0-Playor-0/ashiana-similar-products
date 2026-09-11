"""Apply the user's confirmation pass over the 87 ambiguous image_type labels
(pipeline/image_classify.py) back into artifacts/eval/image_type_labels.json.

Corrections (see docs/DECISIONS.md): the proposed label was wrong for 4 of the
87 ambiguous items; those get provenance "user_confirmed" with the corrected
label. The other 83 were reviewed and accepted as proposed; those get
provenance "heuristic_confirmed" (distinct from a plain "heuristic" label
that has never been looked at by a person). Items that were already
confident (never ambiguous) are untouched.
"""

import json

from pipeline.paths import ARTIFACTS_DIR

LABELS_PATH = ARTIFACTS_DIR / "eval" / "image_type_labels.json"
INDEX_PATH = ARTIFACTS_DIR / "eval" / "ambiguous_review_index.json"

# index -> corrected image_type, from the user's review of ambiguous_review.png
CORRECTIONS_BY_INDEX = {
    61: "lifestyle",
    5: "lifestyle",
    41: "packshot",
    35: "packshot",
}


def main() -> None:
    labels = json.loads(LABELS_PATH.read_text())
    review_index = json.loads(INDEX_PATH.read_text())
    index_to_sku = {entry["index"]: entry["sku"] for entry in review_index}
    ambiguous_skus = {entry["sku"] for entry in review_index}

    corrections_by_sku = {
        index_to_sku[i]: label for i, label in CORRECTIONS_BY_INDEX.items()
    }

    n_corrected = 0
    n_confirmed_as_is = 0
    for sku in ambiguous_skus:
        info = labels[sku]
        if sku in corrections_by_sku:
            info["image_type"] = corrections_by_sku[sku]
            info["provenance"] = "user_confirmed"
            n_corrected += 1
        else:
            info["provenance"] = "heuristic_confirmed"
            n_confirmed_as_is += 1
        info["confident"] = True

    LABELS_PATH.write_text(json.dumps(labels, indent=2))
    print(f"corrected {n_corrected}, confirmed-as-is {n_confirmed_as_is}")
    print(f"wrote {LABELS_PATH}")


if __name__ == "__main__":
    main()
