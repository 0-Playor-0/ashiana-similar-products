"""Phase 1 CHECKPOINT artifacts: packshot contact sheet + nearest-image-neighbor grids.

Both are image-derived (product photography), so — per D3 (docs/DECISIONS.md) —
they're written under artifacts/eval/figures/, which is gitignored. They exist
only for this session's review (sent to the user directly), not for the repo.

Every image is bordered by its image_type label (pipeline/image_classify.py):
  green  = packshot (confident)
  red    = lifestyle (confident)
  gold   = ambiguous (proposed label, pending user confirmation)
  grey   = unclassified (no labels file yet)
This also builds a separate, ambiguous-only sub-sheet for the user to confirm
or correct proposed labels on.
"""

import json
import random

import numpy as np
from PIL import Image, ImageDraw

from pipeline.paths import ARTIFACTS_DIR, DATA_DIR

FIGURES_DIR = ARTIFACTS_DIR / "eval" / "figures"
CELL = 76
BORDER = 4
COLS = 24
NEIGHBOR_QUERIES = 5
NEIGHBOR_K = 6
NEIGHBOR_CELL = 160

LABEL_COLORS = {
    "packshot": (34, 139, 34),
    "lifestyle": (200, 40, 40),
    "ambiguous": (218, 165, 32),
    None: (180, 180, 180),
}

AMBIGUOUS_COLS = 6
AMBIGUOUS_CELL = 190


def _load_ids_embeddings():
    embeddings = np.load(ARTIFACTS_DIR / "embeddings" / "E_image.npy")
    ids = json.loads((ARTIFACTS_DIR / "embeddings" / "ids.json").read_text())
    return ids, embeddings


def _load_image_labels() -> dict[str, dict]:
    path = ARTIFACTS_DIR / "eval" / "image_type_labels.json"
    return json.loads(path.read_text()) if path.exists() else {}


def _border_color(sku: str, labels: dict[str, dict]) -> tuple[int, int, int]:
    info = labels.get(sku)
    if info is None:
        return LABEL_COLORS[None]
    if not info["confident"]:
        return LABEL_COLORS["ambiguous"]
    return LABEL_COLORS[info["image_type"]]


def build_contact_sheet() -> None:
    ids, _ = _load_ids_embeddings()
    labels = _load_image_labels()
    rows = (len(ids) + COLS - 1) // COLS
    cell_total = CELL + 2 * BORDER
    sheet = Image.new("RGB", (COLS * cell_total, rows * cell_total), (240, 240, 240))
    draw = ImageDraw.Draw(sheet)
    for i, sku in enumerate(ids):
        thumb_path = ARTIFACTS_DIR / "thumbs" / f"{sku}.webp"
        img = Image.open(thumb_path).convert("RGB").resize((CELL, CELL))
        x, y = (i % COLS) * cell_total, (i // COLS) * cell_total
        color = _border_color(sku, labels)
        draw.rectangle([x, y, x + cell_total - 1, y + cell_total - 1], fill=color)
        sheet.paste(img, (x + BORDER, y + BORDER))
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "packshots.png"
    sheet.save(out_path)
    print(f"wrote {out_path} ({len(ids)} packshots, {COLS}x{rows} grid)")
    print("border legend: green=packshot red=lifestyle gold=ambiguous grey=unclassified")


def build_neighbor_grids(seed: int = 0) -> None:
    ids, embeddings = _load_ids_embeddings()
    labels = _load_image_labels()
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
            color = _border_color(sku, labels)
            draw.rectangle(
                [x + 2, y + 2, x + NEIGHBOR_CELL - 3, y + NEIGHBOR_CELL - 3],
                outline=color,
                width=3,
            )
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


def build_ambiguous_sheet() -> list[str]:
    """Ambiguous-only contact sheet for user confirmation. Returns the sku list
    in the same left-to-right, top-to-bottom order as the grid, so a reply like
    "flip #3 and #17 to lifestyle" can be mapped back to skus."""
    labels = _load_image_labels()
    with (DATA_DIR / "catalog.jsonl").open() as f:
        catalog = {(p := json.loads(line))["sku"]: p for line in f}

    ambiguous_skus = sorted(sku for sku, info in labels.items() if not info["confident"])
    rows = (len(ambiguous_skus) + AMBIGUOUS_COLS - 1) // AMBIGUOUS_COLS
    sheet = Image.new(
        "RGB", (AMBIGUOUS_COLS * AMBIGUOUS_CELL, rows * AMBIGUOUS_CELL), (255, 255, 255)
    )
    draw = ImageDraw.Draw(sheet)

    for i, sku in enumerate(ambiguous_skus):
        info = labels[sku]
        thumb = Image.open(ARTIFACTS_DIR / "thumbs" / f"{sku}.webp").convert("RGB")
        thumb = thumb.resize((AMBIGUOUS_CELL - 20, AMBIGUOUS_CELL - 50))
        x, y = (i % AMBIGUOUS_COLS) * AMBIGUOUS_CELL, (i // AMBIGUOUS_COLS) * AMBIGUOUS_CELL
        color = LABEL_COLORS[info["image_type"]]
        draw.rectangle(
            [x + 2, y + 2, x + AMBIGUOUS_CELL - 3, y + AMBIGUOUS_CELL - 3],
            outline=color,
            width=3,
        )
        sheet.paste(thumb, (x + 10, y + 10))
        draw.text((x + 10, y + AMBIGUOUS_CELL - 38), f"#{i}", fill=(0, 0, 0))
        draw.text(
            (x + 10, y + AMBIGUOUS_CELL - 24),
            f"proposed: {info['image_type']} (std={info['border_std']:.0f})",
            fill=color,
        )
        title = catalog[sku]["title"][:26]
        draw.text((x + 10, y), title, fill=(80, 80, 80))

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURES_DIR / "ambiguous_review.png"
    sheet.save(out_path)
    print(f"wrote {out_path} ({len(ambiguous_skus)} ambiguous images)")

    index_path = ARTIFACTS_DIR / "eval" / "ambiguous_review_index.json"
    index_path.write_text(
        json.dumps(
            [
                {
                    "index": i,
                    "sku": sku,
                    "title": catalog[sku]["title"],
                    "proposed": labels[sku]["image_type"],
                    "border_std": labels[sku]["border_std"],
                }
                for i, sku in enumerate(ambiguous_skus)
            ],
            indent=2,
        )
    )
    print(f"wrote {index_path}")
    return ambiguous_skus


if __name__ == "__main__":
    build_contact_sheet()
    build_neighbor_grids()
    build_ambiguous_sheet()
