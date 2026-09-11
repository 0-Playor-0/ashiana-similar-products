"""Phase 1: download product images, pick + preprocess the packshot, write thumbnails.

D3 (docs/DECISIONS.md): data/images/ and artifacts/thumbs/ are both gitignored —
nothing image-derived is committed yet.

Every scraped product currently has exactly one image_url (checked against the
committed catalog), so "packshot selection" has nothing to choose between. We
still compute the border-whiteness score from the roadmap spec, both to keep
this working the way the roadmap describes if a product ever has multiple
images, and to flag single-image products whose one photo *isn't* a clean
white-background packshot (logged, not silently dropped — there's no
alternative image to fall back to).
"""

import json

import requests
import yaml
from PIL import Image
from tqdm import tqdm

from pipeline.paths import ARTIFACTS_DIR, CONFIG_DIR, DATA_DIR

SETTINGS = yaml.safe_load((CONFIG_DIR / "settings.yaml").read_text())
PAD_COLOR = tuple(SETTINGS["images"]["pad_color"])
MODEL_SIZE = SETTINGS["images"]["model_size"]
THUMB_SIZE = SETTINGS["images"]["thumb_size"]
WHITE_BORDER_THRESHOLD = 235
BORDER_FRACTION = 0.05

IMAGES_DIR = DATA_DIR / "images"
THUMBS_DIR = ARTIFACTS_DIR / "thumbs"
OVERRIDES_PATH = DATA_DIR / "overrides" / "primary_image.json"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


def _load_catalog() -> list[dict]:
    with (DATA_DIR / "catalog.jsonl").open() as f:
        return [json.loads(line) for line in f]


def download_all(products: list[dict]) -> dict[str, list[str]]:
    """Download every image_url to data/images/{sku}/{n}.jpg. Returns sku -> local paths."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    local_paths: dict[str, list[str]] = {}
    for p in tqdm(products, desc="downloading"):
        sku = p["sku"]
        sku_dir = IMAGES_DIR / sku
        sku_dir.mkdir(exist_ok=True)
        paths = []
        for i, url in enumerate(p["image_urls"]):
            ext = url.split(".")[-1].split("?")[0]
            ext = ext if ext.lower() in ("jpg", "jpeg", "png", "webp") else "jpg"
            dest = sku_dir / f"{i}.{ext}"
            if not dest.exists():
                resp = session.get(url, timeout=20)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
            paths.append(str(dest))
        local_paths[sku] = paths
    return local_paths


def _border_stats(img: Image.Image) -> dict:
    """Stats over the same 5% border strip: whiteness share, mean brightness, std.

    `std` (population stdev of all R/G/B samples in the border) is also the
    input to pipeline/image_classify.py's packshot-vs-lifestyle heuristic: a
    plain studio backdrop is a nearly flat color (low std) regardless of
    whether that color is white, off-white, grey, or a solid backdrop; a
    person's face/hair or a styled scene is not (high std).
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    bw = max(1, int(w * BORDER_FRACTION))
    bh = max(1, int(h * BORDER_FRACTION))
    px = rgb.load()

    def is_white(pixel) -> bool:
        return all(c >= WHITE_BORDER_THRESHOLD for c in pixel)

    total = 0
    white = 0
    samples: list[int] = []
    for x in range(w):
        for y in list(range(0, bh)) + list(range(h - bh, h)):
            pixel = px[x, y]
            total += 1
            white += is_white(pixel)
            samples.extend(pixel)
    for y in range(bh, h - bh):
        for x in list(range(0, bw)) + list(range(w - bw, w)):
            pixel = px[x, y]
            total += 1
            white += is_white(pixel)
            samples.extend(pixel)

    mean_brightness = sum(samples) / len(samples) if samples else 0.0
    if samples:
        variance = sum((s - mean_brightness) ** 2 for s in samples) / len(samples)
        std = variance**0.5
    else:
        std = 0.0

    return {
        "whiteness": white / total if total else 0.0,
        "mean_brightness": mean_brightness,
        "std": std,
    }


def _border_whiteness_score(img: Image.Image) -> float:
    """Share of border-strip pixels with all RGB channels >= threshold."""
    return _border_stats(img)["whiteness"]


def _pad_to_square(img: Image.Image, pad_color) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    side = max(w, h)
    canvas = Image.new("RGB", (side, side), pad_color)
    canvas.paste(img, ((side - w) // 2, (side - h) // 2))
    return canvas


def select_packshots(local_paths: dict[str, list[str]]) -> dict[str, dict]:
    """Pick the primary image per sku (border-whiteness heuristic, or overrides file)."""
    overrides = {}
    if OVERRIDES_PATH.exists():
        overrides = json.loads(OVERRIDES_PATH.read_text())

    results = {}
    for sku, paths in tqdm(local_paths.items(), desc="scoring packshots"):
        if sku in overrides:
            chosen = str(IMAGES_DIR / sku / overrides[sku])
            stats = _border_stats(Image.open(chosen))
        else:
            all_stats = [_border_stats(Image.open(p)) for p in paths]
            best_i = max(range(len(all_stats)), key=lambda i: all_stats[i]["whiteness"])
            chosen = paths[best_i]
            stats = all_stats[best_i]
        results[sku] = {
            "primary_image": chosen,
            "whiteness_score": round(stats["whiteness"], 4),
            "border_mean_brightness": round(stats["mean_brightness"], 4),
            "border_std": round(stats["std"], 4),
        }
    return results


def preprocess_and_thumbnail(packshots: dict[str, dict]) -> None:
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    for sku, info in tqdm(packshots.items(), desc="preprocessing + thumbnails"):
        img = Image.open(info["primary_image"])
        squared = _pad_to_square(img, PAD_COLOR)

        model_input = squared.resize((MODEL_SIZE, MODEL_SIZE), Image.BICUBIC)
        model_dir = IMAGES_DIR / sku
        model_input.save(model_dir / "model_input.png")

        thumb = squared.resize((THUMB_SIZE, THUMB_SIZE), Image.BICUBIC)
        thumb.save(THUMBS_DIR / f"{sku}.webp", "WEBP", quality=85)


PACKSHOT_SCORES_PATH = ARTIFACTS_DIR / "eval" / "packshot_scores.json"


def main() -> None:
    products = _load_catalog()
    local_paths = download_all(products)
    packshots = select_packshots(local_paths)
    preprocess_and_thumbnail(packshots)

    PACKSHOT_SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PACKSHOT_SCORES_PATH.write_text(json.dumps(packshots, indent=2))

    low_score = sorted(
        ((sku, v["whiteness_score"]) for sku, v in packshots.items()),
        key=lambda kv: kv[1],
    )[:15]
    report = {
        "n_products": len(packshots),
        "mean_whiteness_score": round(
            sum(v["whiteness_score"] for v in packshots.values()) / len(packshots), 4
        ),
        "lowest_whiteness_scores": low_score,
    }
    report_path = ARTIFACTS_DIR / "eval" / "packshot_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
