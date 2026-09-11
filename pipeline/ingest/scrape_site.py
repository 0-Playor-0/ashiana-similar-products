"""Scrape Ashiana's storefront (D1) into data/raw/.

NOT CURRENTLY RUNNABLE UNATTENDED. The site's CloudFront/WAF returns 403 to
any client whose User-Agent doesn't look like a real desktop browser,
including an honest, self-identifying bot UA. Spoofing a browser UA to get
past that would be bypassing the site's bot detection, which this project
won't do (see docs/DECISIONS.md, "Scraping approach"). The committed
data/raw/2026-09-11/ snapshot was instead collected by driving an actual
interactive browser by hand, one page at a time, using the exact same
extraction logic below (the "load more" pagination on several pages needed
multiple retries — it's flaky independent of the UA issue; see DECISIONS.md).

This script is kept as executable documentation of that extraction logic —
useful background reading before a future re-scrape, and it would work as-is
if pointed at a context that isn't UA-blocked (e.g. a real, human-driven
browser profile). `make data` does not call it; it rebuilds catalog.jsonl
from the committed raw snapshot via pipeline/clean.py.

The category and collection listing pages are client-rendered: the product
grid is populated by a React component that keeps the full product object as
a React prop on each `[data-testid="producttile-container"]` DOM node (see
docs/DECISIONS.md for how this was found, and why we read the rendered page
rather than call the site's backend API directly).

Output: one raw JSON snapshot per category/collection page under
data/raw/<snapshot_date>/, plus a merged data/raw/<snapshot_date>/catalog_raw.json
mapping sku -> {product_type, collections: [...], **product fields}.
pipeline/clean.py turns that into the canonical data/catalog.jsonl.
"""

import datetime
import json
import time

import yaml
from playwright.sync_api import sync_playwright

from pipeline.paths import CONFIG_DIR, DATA_DIR

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
TAXONOMY = yaml.safe_load((CONFIG_DIR / "taxonomy.yaml").read_text())

BASE_URL = SETTINGS["catalog"]["source_url"]
RATE_LIMIT_S = SETTINGS["scraping"]["rate_limit_s"]
USER_AGENT = SETTINGS["scraping"]["user_agent"]

# site category/collection name -> UUID, from https://www.ashianayouronestopshop.com/sitemap.xml
# (checked 2026-09-11; robots.txt allows /category/* and /collection/*)
CATEGORY_IDS = {
    "Bracelet": "05fe2783-441d-43ac-b1f8-22859a495602",
    "Brooch": "888be1c9-bf4c-4adb-be9c-67a19ff3abfa",
    "Earrings": "7747b876-3c05-49c2-82a7-6e1efe959d50",
    "Hair accessories": "157150ce-65d7-4ee6-af48-d947373ef160",
    "Home Decor": "51937043-c719-48a0-9c51-370f83c35c2c",
    "Necklace and Jewellery Sets": "9eed5f58-d22e-409a-af87-1fa9e0c5433d",
    "Rings": "6c2421fd-5fb3-406e-a0ef-c92ee6e64263",
}
COLLECTION_IDS = {
    "Antique Jewellery": "5a4f30c1-fd5c-4c7a-a58e-ea2340c12a57",
    "Zircon Jewellery": "4984c526-2d69-47f2-970f-96abcd5b212a",
    "Crystal Jewellery": "7b105a50-adde-49c4-b2e5-2966578a31f1",
    "Kundan Jewellery": "51824174-5a1d-4c0d-88a4-7f2aedcf86e8",
    "92.5 Sterling Silver": "003ba148-a622-4987-a6ac-930637eb6d8a",
    "Oxidised Jewellery": "d51c42ac-7490-4f62-977c-9cbb40c3628b",
    "Contemporary Jewellery": "db111bcf-ae18-4d68-a4b2-0684d2f08474",
}

IN_SCOPE_CATEGORIES = SETTINGS["catalog"]["include_site_categories"]

EXTRACT_TILES_JS = """
() => {
  function getReactProps(el) {
    const key = Object.keys(el).find(k => k.startsWith('__reactProps$'));
    return key ? el[key] : null;
  }
  const tiles = Array.from(document.querySelectorAll('[data-testid="producttile-container"]'));
  return tiles
    .map(t => getReactProps(t)?.product)
    .filter(Boolean);
}
"""


def _fetch_listing(page, url: str) -> list[dict]:
    page.goto(url, wait_until="networkidle")
    page.wait_for_selector('[data-testid="producttile-container"]', timeout=15_000)
    # the grid loads in one client-side fetch (confirmed empirically: no
    # "load more" pagination was observed even for a 338-product category),
    # but give any trailing re-render a moment to settle before reading.
    page.wait_for_timeout(500)
    return page.evaluate(EXTRACT_TILES_JS)


def scrape() -> dict:
    snapshot_date = datetime.date.today().isoformat()
    raw_dir = DATA_DIR / "raw" / snapshot_date
    raw_dir.mkdir(parents=True, exist_ok=True)

    catalog: dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        for name in IN_SCOPE_CATEGORIES:
            cat_id = CATEGORY_IDS[name]
            url = f"{BASE_URL}/category/{cat_id}/{name.replace(' ', '%20')}"
            print(f"[category] {name}: {url}")
            products = _fetch_listing(page, url)
            (raw_dir / f"category_{cat_id}.json").write_text(json.dumps(products, indent=2))
            product_type = TAXONOMY["product_type_map"][name]
            for prod in products:
                sku = prod["itemSku"]
                entry = catalog.setdefault(sku, {"collections": []})
                entry["product_type"] = product_type
                entry["raw"] = prod
            time.sleep(RATE_LIMIT_S)

        for name, coll_id in COLLECTION_IDS.items():
            url = f"{BASE_URL}/collection/{coll_id}/{name.replace(' ', '%20')}"
            print(f"[collection] {name}: {url}")
            products = _fetch_listing(page, url)
            (raw_dir / f"collection_{coll_id}.json").write_text(json.dumps(products, indent=2))
            collection = TAXONOMY["collection_map"][name]
            for prod in products:
                sku = prod["itemSku"]
                if sku in catalog:  # only tag products already in our category scope
                    catalog[sku]["collections"].append(collection)
            time.sleep(RATE_LIMIT_S)

        browser.close()

    out_path = raw_dir / "catalog_raw.json"
    out_path.write_text(json.dumps(catalog, indent=2))
    print(f"Wrote {len(catalog)} in-scope products to {out_path}")
    return catalog


if __name__ == "__main__":
    scrape()
