# Decision log

Short entries: decision, reason, alternatives considered. Newest last.

## 2026-09-11 — D1: data source = scrape Ashiana's public site

**Decision.** Scrape `https://www.ashianayouronestopshop.com` rather than use a provided
export or a public/synthetic fallback dataset.
**Reason.** User choice; no dataset was provided.
**Alternatives considered.** Provided dataset (none available), public/synthetic fallback
(would misrepresent the actual Ashiana catalog).

## 2026-09-11 — D2 + scope checkpoint: which categories are in scope

**Decision.** `include_site_categories` (config/settings.yaml) = Bracelet, Brooch, Earrings,
Hair accessories, Home Decor, Necklace and Jewellery Sets, Rings. Excluded: Candles, Key
Chain, Rakhi/Lumba/Hampers, SCARF.
**Reason.** User chose "jewelry + home decor + hair accessories" for D2, then explicitly
added Brooch (jewelry-adjacent, worn like a pin) but excluded the remaining gift/accessory
categories as not being "substitutes" for jewelry, home decor, or hair accessories in the
sense the brief defines similarity (§1: "other pieces a shopper might buy *instead of* this
one").
**Alternatives considered.** All 11 categories (rejected — candles/keychains aren't
substitutes for rings); jewelry-only, the roadmap's stated default (rejected — user wanted
home decor + hair accessories included too).

## 2026-09-11 — Real catalog size is ~659 products, not 30–100

**Finding, not a decision requiring a choice**, but worth recording: the roadmap's assumed
30–100 SKU cold-start catalog was a design assumption, not a fact about Ashiana's real site.
The sitemap lists 659 products across 11 site categories. With scope narrowed to the 7
categories above the in-scope count will be smaller but still likely in the hundreds. This
doesn't change any LOCKED decision (exact search, no ANN, is still fine at this scale on a
MacBook Air) but does mean Phase 3's evaluation pool and Phase 4's hand-labeling should
expect a denser catalog than the roadmap's running example implied.

## 2026-09-11 — Scraping approach: render pages, don't call Amazon's internal API directly

**Decision.** `pipeline/ingest/scrape_site.py` uses Playwright to load each in-scope
category and product page as a real browser would, waits for the page's own client-side
data fetch to populate the DOM, and extracts fields from the rendered page. It does not call
`smartpos.amazon.in` / `api.smartbiz.in` directly.
**Reason.** Ashiana's storefront is built on Amazon's SmartBiz / "Buy with Amazon" commerce
platform (shop ID 55418). Investigating network traffic (as the roadmap's Phase 0 step
directed) showed the category/product listing data is fetched client-side from
`smartpos.amazon.in/api-unauthenticated/...` and `api.smartbiz.in/stores/55418/...`. Despite
the "unauthenticated" path segment, direct calls return `403 Missing Authentication Token`
(an AWS API Gateway error), and the page's own JS is blocked from calling it cross-origin
with a plain fetch too — both signal this is Amazon's internal, access-controlled backend,
not a documented public API meant for third-party consumption. `robots.txt` on
ashianayouronestopshop.com only speaks to that domain's own pages, not to Amazon's separate
API domains, so scraping the rendered storefront pages (which robots.txt explicitly allows)
is the approach that stays inside both the letter and the spirit of what's actually
authorized, while still getting complete, accurate data.
**Alternatives considered.** Reverse-engineering the SmartBiz API's auth headers (rejected —
crosses from "polite scraping of a small merchant's public storefront" into circumventing
Amazon's own access controls on infrastructure that isn't Ashiana's to authorize); Next.js
`_next/data/<buildId>/...json` static-props endpoints (checked — these all 404 because the
listing/product pages aren't statically generated; only the app shell is).
**No terms-of-service page was found** on the storefront domain (all common `/terms*` paths
404, nothing in the rendered footer) — consistent with the site running on a shared
platform rather than publishing its own terms.

## 2026-09-11 — Interactive collection, and the "load more" pagination was flaky

**Decision/finding.** The 472-product raw snapshot (`data/raw/2026-09-11/`) was collected by
manually driving an interactive browser through each of the 7 in-scope category pages and 7
collection pages, running the React-props extraction JS from
`pipeline/ingest/scrape_site.py` on each, and saving the result. Category/collection page
counts: Earrings 338, Necklace and Jewellery Sets 78, Hair accessories 17, Bracelet 10,
Home Decor 10, Rings 10, Brooch 9; collections: Contemporary 57, 92.5 Sterling Silver 49,
Antique 10, Zircon 10, Crystal 10, Kundan 9, Oxidised 10.
**Why this needed care.** The site's infinite-scroll "load more" is unreliable — repeatedly,
a page would render an initial batch (usually 10 items) and then simply stop firing further
paginated fetches even after 30+ seconds of continued scrolling, with no error and no visible
loading indicator. The same category could report 10 on one attempt and its true, much larger
count (e.g. Necklace and Jewellery Sets: 10 → 20 → 78; Contemporary: 10 → 57) on a later,
otherwise-identical attempt. Every count above was therefore confirmed by at least two
independent extended scroll passes (each 20-35 iterations) agreeing before being accepted;
Earrings (338) and the ones already showing clear multi-step growth were additionally
cross-checked by re-running from a fresh page load. Small counts that reproduced identically
across 2-3 separate fresh attempts (Bracelet, Brooch, Home Decor, Rings, and the four
smaller collections) are treated as genuine, not truncated.
**Consequence.** `pipeline/ingest/scrape_site.py`'s scripted version of this same logic is
not run unattended (see its module docstring and the WAF entry above) — it documents the
extraction method but the actual data collection was manual and is not currently
reproducible by a single `make data` run. A future session re-scraping this catalog should
budget for this flakiness (retry with fresh page loads, don't trust a single stable-looking
scroll trace) regardless of how the UA/access issue is resolved.

## 2026-09-11 — Keyword-extraction simplifications in `pipeline/clean.py`

**Decision.** Two simplifications in the Phase 0 `clean.py`, both fine for now but worth
revisiting in Phase 3: (1) `materials_vocab` and `colors_vocab` both include "gold" and
"silver" — a listing that says "gold color" sets both `materials: [gold]` and
`colors: [gold]` from the same word, since Ashiana's copy uses "gold"/"silver" ambiguously
for both plating and color. (2) 6 products are tagged under two collections on the site
(e.g. both Antique and Zircon); since `Product.collection` is a single value, `clean.py`
picks one via a fixed priority order (antique > kundan > zircon > crystal > oxidised >
contemporary > sterling_silver) and drops the other. Neither loses catalog-critical
information (both raw signals are still visible in title/description text for Phase 2's
text pipeline), but Phase 3's metadata similarity should be aware materials/colors overlap
and multi-collection items are collapsed to one label.

## 2026-09-11 — Python 3.11 via `uv`, no Node yet

**Decision.** Pinned the project venv to Python 3.11.15 via `uv python install 3.11` (host
had 3.14 by default). Did not install Node — it's only needed for the Phase 6 frontend, and
the scraper's headless-browser needs are covered by Playwright's Python binding instead.
**Reason.** Rule 9 (pin Python 3.11); avoids an unnecessary Node install this early.
