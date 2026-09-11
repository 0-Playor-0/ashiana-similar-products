"""Merge the per-page raw JSON files collected in data/raw/<snapshot>/ into a
single catalog_raw.json keyed by sku, the input pipeline/clean.py expects.

The per-page files (category_*.json with full product fields, collection_*.json
with just sku lists — see pipeline/ingest/scrape_site.py and docs/DECISIONS.md
for how they were collected) are the source of truth; this script only
reshapes and merges them, using the same product_type_map / collection_map as
the rest of the pipeline (config/taxonomy.yaml) so there is one place that
defines the site-name -> normalized-value mapping.
"""

import json

import yaml

from pipeline.paths import CONFIG_DIR, DATA_DIR

TAXONOMY = yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())

CATEGORY_FILES = {
    "Bracelet": "category_Bracelet.json",
    "Brooch": "category_Brooch.json",
    "Earrings": "category_Earrings.json",
    "Hair accessories": "category_Hair_accessories.json",
    "Home Decor": "category_Home_Decor.json",
    "Necklace and Jewellery Sets": "category_Necklace_and_Jewellery_Sets.json",
    "Rings": "category_Rings.json",
}
COLLECTION_FILES = {
    "Antique Jewellery": "collection_Antique_Jewellery.json",
    "Zircon Jewellery": "collection_Zircon_Jewellery.json",
    "Crystal Jewellery": "collection_Crystal_Jewellery.json",
    "Kundan Jewellery": "collection_Kundan_Jewellery.json",
    "92.5 Sterling Silver": "collection_92.5_Sterling_Silver.json",
    "Oxidised Jewellery": "collection_Oxidised_Jewellery.json",
    "Contemporary Jewellery": "collection_Contemporary_Jewellery.json",
}


def merge(snapshot_dir) -> dict:
    product_type_map = TAXONOMY["product_type_map"]
    collection_map = TAXONOMY["collection_map"]

    catalog: dict[str, dict] = {}
    dupe_categories = []

    for site_name, fname in CATEGORY_FILES.items():
        items = json.loads((snapshot_dir / fname).read_text())
        ptype = product_type_map[site_name]
        for item in items:
            sku = item["sku"]
            if sku in catalog:
                dupe_categories.append((sku, catalog[sku]["product_type"], ptype))
                continue
            catalog[sku] = {
                "product_type": ptype,
                "collections": [],
                "name": item["name"],
                "mrp": item["mrp"],
                "sellingPrice": item["sellingPrice"],
                "description": item["description"],
                "imageUrl": item["imageUrl"],
                "secondaryImageUrl": item.get("secondaryImageUrl", []),
                "numberOfVariants": item.get("numberOfVariants", 1),
                "inStock": item.get("inStock"),
            }

    for site_name, fname in COLLECTION_FILES.items():
        skus = json.loads((snapshot_dir / fname).read_text())
        coll = collection_map[site_name]
        for sku in skus:
            if sku in catalog:
                catalog[sku]["collections"].append(coll)

    out_path = snapshot_dir / "catalog_raw.json"
    out_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False))

    print(f"total in-scope products: {len(catalog)}")
    if dupe_categories:
        print(f"skus appearing in >1 category (kept first): {len(dupe_categories)}")
        for d in dupe_categories:
            print("  dupe:", d)
    print(f"wrote {out_path}")
    return catalog


if __name__ == "__main__":
    raw_root = DATA_DIR / "raw"
    latest = sorted(p for p in raw_root.iterdir() if p.is_dir())[-1]
    merge(latest)
