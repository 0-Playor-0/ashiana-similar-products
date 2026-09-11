"""Phase 1 CHECKPOINT artifacts: packshot contact sheet + nearest-image-neighbor grids.

Both are image-derived (product photography), so — per D3 (docs/DECISIONS.md) —
they're written under artifacts/eval/figures/, which is gitignored. They exist
only for this session's review (sent to the user directly), not for the repo.
"""

import json
import random

import numpy as np
from PIL import Image, ImageDraw

from pipeline.paths import ARTIFACTS_DIR, DATA_DIR

FIGURES_DIR = ARTIFACTS_DIR / "eval" / "figures"
CELL = 72
COLS = 24
NEIGHBOR_QUERIES = 5
NEIGHBOR_K = 6
NEIGHBOR_CELL = 160


def _load_ids_embeddings():
    embeddings = np.load(ARTIFACTS_DIR / "embeddings" / "E_image.npy")
    ids = json.loads((ARTIFACTS_DIR / "embeddings" / "ids.json").read_text())
    return ids, embeddings


def build_contact_sheet() -> None:
    ids, _ = _load_ids_embeddings()
    rows = (len(ids) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * CELL, rows * CELL), (240, 240, 240))
    for i, sku in enumerate(ids):
        thumb_path = ARTIFACTS_DIR / "thumbs" / f"{sku}.webp"
        img = Image.open(thumb_path).convert("RGB").resize((CELL, CELL))
        x, y = (i % COLS) * CELL, (i // COLS) * CELL
        sheet.paste(img, (x, y))
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "packshots.png"
    sheet.save(out_path)
    print(f"wrote {out_path} ({len(ids)} packshots, {COLS}x{rows} grid)")


def build_neighbor_grids(seed: int = 0) -> None:
    ids, embeddings = _load_ids_embeddings()
    with (DATA_DIR / "catalog.jsonl").open() as f:
        catalog = {(p := json.loads(line))["sku"]: p for line in f}

    random.seed(seed)
    query_skus = random.sample(ids, NEIGHBOR_QUERIES)

    grid = Image.new(
        "RGB",
        ((NEIGHBOR_K + 1) * NEIGHBOR_CELL, NEIGHBOR_QUERIES * NEIGHBOR_CELL),
        (255, 255, 255),
    )
    draw = ImageDraw.Draw(grid)

    for row, q_sku in enumerate(query_skus):
        q_idx = ids.index(q_sku)
        sims = embeddings @ embeddings[q_idx]
        ranked = np.argsort(-sims)
        neighbor_idx = [i for i in ranked if ids[i] != q_sku][:NEIGHBOR_K]

        cells = [(q_sku, 1.0)] + [(ids[i], float(sims[i])) for i in neighbor_idx]
        for col, (sku, sim) in enumerate(cells):
            thumb = Image.open(ARTIFACTS_DIR / "thumbs" / f"{sku}.webp").convert("RGB")
            thumb = thumb.resize((NEIGHBOR_CELL - 10, NEIGHBOR_CELL - 30))
            x, y = col * NEIGHBOR_CELL, row * NEIGHBOR_CELL
            grid.paste(thumb, (x + 5, y + 5))
            label = "QUERY" if col == 0 else f"{sim:.2f}"
            draw.text((x + 5, y + NEIGHBOR_CELL - 22), label, fill=(0, 0, 0))
            title = catalog[sku]["title"][:22]
            draw.text((x + 5, y), title, fill=(80, 80, 80))
        draw.line(
            [(NEIGHBOR_CELL, row * NEIGHBOR_CELL), (NEIGHBOR_CELL, (row + 1) * NEIGHBOR_CELL)],
            fill=(0, 0, 0),
            width=2,
        )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "image_neighbors.png"
    grid.save(out_path)
    print(f"wrote {out_path} ({NEIGHBOR_QUERIES} queries x top-{NEIGHBOR_K} neighbors)")
    for sku in query_skus:
        print(" query:", sku, catalog[sku]["title"])


if __name__ == "__main__":
    build_contact_sheet()
    build_neighbor_grids()
