"""Normalize data/raw/<snapshot>/catalog_raw.json into data/catalog.jsonl (§6).

Also writes the Phase 0 validation report to artifacts/eval/data_report.json:
counts per product_type/collection, missingness, price stats, and which
product types have fewer than k+1 items (candidates for the Phase 3 fallback
rule).
"""

import json

import yaml

from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR
from pipeline.schema import Product

TAXONOMY = yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())
SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())

# Phase 1 QC output (pipeline/image_classify.py); optional — clean() runs fine
# without it (image_type stays None), so Phase 0 alone still works.
IMAGE_TYPE_LABELS_PATH = ARTIFACTS_DIR / "eval" / "image_type_labels.json"

# products found under >1 collection page keep only the first, by this
# priority order (docs/DECISIONS.md) — the schema holds a single collection
COLLECTION_PRIORITY = [
    "antique",
    "kundan",
    "zircon",
    "crystal",
    "oxidised",
    "contemporary",
    "sterling_silver",
]

SOURCE_URL_TMPL = SETTINGS["catalog"]["source_url"] + "/product/{sku}"
K_DEFAULT = SETTINGS["fusion"]["k_default"]


def _latest_snapshot_dir():
    raw_root = DATA_DIR / "raw"
    dates = sorted(p.name for p in raw_root.iterdir() if p.is_dir())
    return raw_root / dates[-1], dates[-1]


def _pick_collection(collections: list[str]) -> str | None:
    if not collections:
        return None
    for c in COLLECTION_PRIORITY:
        if c in collections:
            return c
    return collections[0]


def _match_vocab(text: str, vocab: list[str], synonyms: dict[str, str]) -> list[str]:
    text = text.lower()
    for phrase, canon in synonyms.items():
        if phrase in text:
            text = text.replace(phrase, canon)
    found = []
    for term in vocab:
        needle = term.replace("_", " ")
        if (needle in text or term in text) and term not in found:
            found.append(term)
    return found


def clean() -> list[Product]:
    snapshot_dir, snapshot_date = _latest_snapshot_dir()
    raw = json.loads((snapshot_dir / "catalog_raw.json").read_text())

    image_type_labels = {}
    if IMAGE_TYPE_LABELS_PATH.exists():
        image_type_labels = json.loads(IMAGE_TYPE_LABELS_PATH.read_text())

    synonyms = TAXONOMY["synonyms"]
    products = []
    for sku, entry in raw.items():
        title = entry["name"].strip()
        description = entry["description"].strip() or None
        text = f"{title} {description or ''}"

        materials = _match_vocab(text, TAXONOMY["materials_vocab"], synonyms)
        stones = _match_vocab(text, TAXONOMY["stones_vocab"], synonyms)
        colors = _match_vocab(text, TAXONOMY["colors_vocab"], synonyms)
        provenance = {}
        if materials:
            provenance["materials"] = "keyword"
        if stones:
            provenance["stones"] = "keyword"
        if colors:
            provenance["colors"] = "keyword"

        image_type = None
        if sku in image_type_labels:
            label_info = image_type_labels[sku]
            image_type = label_info["image_type"]
            provenance["image_type"] = label_info["provenance"]

        image_urls = [entry["imageUrl"]] + [
            u for u in entry.get("secondaryImageUrl", []) if u
        ]

        products.append(
            Product(
                sku=sku,
                parent_id=None,
                title=title,
                description_raw=description,
                product_type=entry["product_type"],
                collection=_pick_collection(entry["collections"]),
                materials=materials,
                stones=stones,
                colors=colors,
                price_inr=entry.get("sellingPrice"),
                image_urls=image_urls,
                primary_image=None,
                image_type=image_type,
                in_stock=entry.get("inStock"),
                source_url=SOURCE_URL_TMPL.format(sku=sku),
                attr_provenance=provenance,
            )
        )

    products.sort(key=lambda p: p.sku)

    out_path = DATA_DIR / "catalog.jsonl"
    with out_path.open("w") as f:
        for p in products:
            f.write(p.model_dump_json() + "\n")
    print(f"wrote {len(products)} products to {out_path} (from snapshot {snapshot_date})")

    _write_validation_report(products, snapshot_date)
    return products


def _write_validation_report(products: list[Product], snapshot_date: str) -> None:
    n = len(products)
    by_type: dict[str, int] = {}
    by_collection: dict[str, int] = {}
    by_image_type: dict[str, int] = {}
    for p in products:
        by_type[p.product_type] = by_type.get(p.product_type, 0) + 1
        key = p.collection or "(none)"
        by_collection[key] = by_collection.get(key, 0) + 1
        image_key = p.image_type or "(unclassified)"
        by_image_type[image_key] = by_image_type.get(image_key, 0) + 1

    def missing_share(field: str) -> float:
        missing = sum(
            1
            for p in products
            if getattr(p, field) in (None, [], "")
        )
        return round(missing / n, 4)

    fields = [
        "description_raw",
        "collection",
        "materials",
        "stones",
        "colors",
        "price_inr",
        "in_stock",
    ]
    prices = [p.price_inr for p in products if p.price_inr is not None]

    underfilled_types = [
        t for t, count in by_type.items() if count < K_DEFAULT + 1
    ]

    report = {
        "snapshot_date": snapshot_date,
        "n_products": n,
        "counts_by_product_type": by_type,
        "counts_by_collection": by_collection,
        "counts_by_image_type": by_image_type,
        "missingness": {f: missing_share(f) for f in fields},
        "price_inr": {
            "min": min(prices) if prices else None,
            "median": sorted(prices)[len(prices) // 2] if prices else None,
            "max": max(prices) if prices else None,
        },
        "product_types_below_k_plus_1": underfilled_types,
        "k_default": K_DEFAULT,
    }
    out_path = ARTIFACTS_DIR / "eval" / "data_report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"wrote validation report to {out_path}")


if __name__ == "__main__":
    clean()
