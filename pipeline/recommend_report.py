"""Phase 3 checkpoint: render artifacts/eval/recommendations.json as an HTML
page — query + top-6, one row per product, all 472 — for the user to eyeball
(§8 Phase 3: "a recommendations grid ... saved for every product", "the user
eyeballs the full-catalog grid, a PDF or HTML page of every query with its
top-6").

Image-derived (product photography), so — per D3 — written under
artifacts/eval/figures/, which is gitignored, and referenced by relative
path to artifacts/thumbs/ (not embedded) since this is meant to be opened
locally, not shipped anywhere.
"""

import base64
import json
import random

from pipeline.paths import ARTIFACTS_DIR

FIGURES_DIR = ARTIFACTS_DIR / "eval" / "figures"
THUMBS_DIR = ARTIFACTS_DIR / "thumbs"

CSS = """
body { background:#241C17; color:#FBF7F0; font-family:-apple-system,Inter,sans-serif;
       margin:0; padding:24px; }
h1 { font-weight:500; }
.row { display:flex; gap:12px; align-items:flex-start; border-bottom:1px solid #4a3f34;
       padding:16px 0; }
.cell { width:120px; flex-shrink:0; text-align:center; }
.cell img { width:110px; height:110px; object-fit:contain; background:#FBF7F0;
            border:1px solid #C9A55C; border-radius:4px; }
.cell .label { font-size:11px; color:#B7DEE0; margin-top:4px; }
.cell .title { font-size:11px; color:#FBF7F0; margin-top:2px; max-height:2.6em;
               overflow:hidden; }
.cell .reasons { font-size:10px; color:#8A8D8C; margin-top:2px; }
.query .cell img { border:2px solid #C9A55C; }
.fallback .label { color:#C9A55C; }
"""


def _row_html(sku_query: str, rec: dict, catalog: dict, thumb_prefix: str) -> str:
    q_title = catalog[sku_query]["title"]
    cells = [
        f'<div class="cell query"><img src="{thumb_prefix}{sku_query}.webp" '
        f'alt="{q_title}"><div class="label">QUERY</div>'
        f'<div class="title">{q_title[:40]}</div></div>'
    ]
    for item in rec["items"]:
        title = item["title"]
        reasons = " · ".join(item["reasons"])
        fb_class = " fallback" if item["fallback"] else ""
        cells.append(
            f'<div class="cell{fb_class}"><img src="{thumb_prefix}{item["sku"]}.webp" '
            f'alt="{title}"><div class="label">{item["score"]:.2f}'
            f'{" (fallback)" if item["fallback"] else ""}</div>'
            f'<div class="title">{title[:40]}</div>'
            f'<div class="reasons">{reasons}</div></div>'
        )
    return f'<div class="row">{"".join(cells)}</div>'


def build_full_report() -> None:
    recommendations = json.loads((ARTIFACTS_DIR / "eval" / "recommendations.json").read_text())
    catalog = json.loads((ARTIFACTS_DIR / "catalog.json").read_text())

    rows = [
        _row_html(sku, rec, catalog, "../../thumbs/")
        for sku, rec in sorted(recommendations.items())
    ]
    html = (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Ashiana similar-products — full catalog check</title>"
        f"<style>{CSS}</style></head><body>"
        f"<h1>All {len(rows)} queries, top-6 each</h1>"
        f"{''.join(rows)}</body></html>"
    )
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "recommendations_full.html"
    out_path.write_text(html)
    print(f"wrote {out_path} ({len(rows)} rows, open locally — thumbnail paths are relative)")


def build_sample_report(n: int = 18, seed: int = 0) -> None:
    """Same thing, but a small sample with images embedded as base64 data URIs
    so the single file is self-contained and can be sent/rendered anywhere.
    """
    recommendations = json.loads((ARTIFACTS_DIR / "eval" / "recommendations.json").read_text())
    catalog = json.loads((ARTIFACTS_DIR / "catalog.json").read_text())

    random.seed(seed)
    sample_skus = random.sample(list(recommendations.keys()), n)

    def data_uri(sku: str) -> str:
        data = (THUMBS_DIR / f"{sku}.webp").read_bytes()
        return "data:image/webp;base64," + base64.b64encode(data).decode()

    rows = []
    for sku in sample_skus:
        rec = recommendations[sku]
        q_title = catalog[sku]["title"]
        cells = [
            f'<div class="cell query"><img src="{data_uri(sku)}" alt="{q_title}">'
            f'<div class="label">QUERY</div><div class="title">{q_title[:40]}</div></div>'
        ]
        for item in rec["items"]:
            reasons = " · ".join(item["reasons"])
            fb_class = " fallback" if item["fallback"] else ""
            cells.append(
                f'<div class="cell{fb_class}"><img src="{data_uri(item["sku"])}" '
                f'alt="{item["title"]}"><div class="label">{item["score"]:.2f}</div>'
                f'<div class="title">{item["title"][:40]}</div>'
                f'<div class="reasons">{reasons}</div></div>'
            )
        rows.append(f'<div class="row">{"".join(cells)}</div>')

    html = (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Ashiana similar-products — sample check</title>"
        f"<style>{CSS}</style></head><body>"
        f"<h1>{n}-query sample, top-6 each</h1>"
        f"{''.join(rows)}</body></html>"
    )
    out_path = FIGURES_DIR / "recommendations_sample.html"
    out_path.write_text(html)
    print(f"wrote {out_path} ({n} rows, self-contained)")


if __name__ == "__main__":
    build_full_report()
    build_sample_report()
