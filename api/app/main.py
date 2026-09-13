"""FastAPI service (§9). No torch/transformers/sentence_transformers import,
enforced by api/tests/test_no_heavy_deps.py (rule 5) — every embedding is
computed offline (§2); this process only loads precomputed matrices and does
a weighted sum + top-k over them.
"""

from collections import Counter
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.app import service
from api.app.config import ARTIFACTS_DIR, FRONTEND_ORIGINS, K_DEFAULT, K_MAX
from api.app.models import (
    CategoriesResponse,
    HealthResponse,
    ProductDetail,
    ProductSummary,
    SimilarResponse,
    VersionResponse,
)
from core.bundle import load_bundle


@asynccontextmanager
async def lifespan(app: FastAPI):
    bundle = load_bundle(ARTIFACTS_DIR)
    service.configure(bundle)
    yield


app = FastAPI(title="Ashiana Similar Products API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)


class BundleVersionHeaderMiddleware(BaseHTTPMiddleware):
    """Every response carries X-Bundle-Version (§9)."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            response.headers["X-Bundle-Version"] = service.get_bundle().manifest[
                "bundle_version"
            ]
        except service.NotLoadedError:
            pass
        return response


app.add_middleware(BundleVersionHeaderMiddleware)


class CachedStaticFiles(StaticFiles):
    """Adds Cache-Control: public, max-age=86400 to every served file (§9)."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "public, max-age=86400"
        return response


# check_dir=False: artifacts/thumbs/ is gitignored (D3, docs/DECISIONS.md) and
# may not exist on a fresh checkout before `make build` runs — a missing
# directory shouldn't crash startup, individual thumb requests just 404.
app.mount(
    "/thumbs",
    CachedStaticFiles(directory=ARTIFACTS_DIR / "thumbs", check_dir=False),
    name="thumbs",
)


@app.get("/health", response_model=HealthResponse)
def health() -> dict:
    return {"status": "ok"}


@app.get("/version", response_model=VersionResponse)
def version() -> dict:
    manifest = service.get_bundle().manifest
    return {
        "bundle_version": manifest["bundle_version"],
        "models": manifest["models"],
        "default_weights": manifest["default_weights"],
        "n_items": manifest["n_items"],
    }


@app.get("/categories", response_model=CategoriesResponse)
def categories() -> dict:
    bundle = service.get_bundle()
    type_counts = Counter(p["product_type"] for p in bundle.catalog.values())
    collection_counts = Counter(
        p["collection"] for p in bundle.catalog.values() if p.get("collection")
    )
    return {
        "product_types": [
            {"product_type": t, "count": c} for t, c in sorted(type_counts.items())
        ],
        "collections": [
            {"collection": c, "count": n} for c, n in sorted(collection_counts.items())
        ],
    }


@app.get("/products", response_model=list[ProductSummary])
def list_products(
    product_type: str | None = None, collection: str | None = None
) -> list[dict]:
    bundle = service.get_bundle()
    out = []
    for sku in bundle.ids:
        p = bundle.catalog[sku]
        if product_type and p["product_type"] != product_type:
            continue
        if collection and p.get("collection") != collection:
            continue
        out.append(service.product_summary(bundle, sku))
    return out


@app.get("/products/{sku}", response_model=ProductDetail)
def get_product(sku: str) -> dict:
    bundle = service.get_bundle()
    if sku not in bundle.catalog:
        raise HTTPException(404, detail=f"unknown sku: {sku}")
    return service.product_detail(bundle, sku)


@app.get("/products/{sku}/similar", response_model=SimilarResponse)
def similar(
    sku: str,
    k: int | None = Query(default=None, ge=1, le=K_MAX),
    w_image: float | None = Query(default=None, ge=0),
    w_text: float | None = Query(default=None, ge=0),
    w_meta: float | None = Query(default=None, ge=0),
    same_category: bool = Query(default=True),
    max_price_ratio: float | None = Query(default=None, gt=1),
) -> dict:
    bundle = service.get_bundle()
    if sku not in bundle.catalog:
        raise HTTPException(404, detail=f"unknown sku: {sku}")

    defaults = bundle.manifest["default_weights"]
    try:
        return service.get_similar(
            sku,
            k if k is not None else K_DEFAULT,
            w_image if w_image is not None else defaults["image"],
            w_text if w_text is not None else defaults["text"],
            w_meta if w_meta is not None else defaults["meta"],
            same_category,
            max_price_ratio,
        )
    except ValueError as e:
        raise HTTPException(422, detail=str(e)) from e


@app.get("/eval/report")
def eval_report() -> dict:
    try:
        return service.get_eval_report()
    except FileNotFoundError as e:
        raise HTTPException(404, detail="no eval report has been generated yet") from e
