"""Response models for the API contract (§9). Pydantic only — no numpy
types cross this boundary; service.py converts everything to plain
floats/lists first.
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    bundle_version: str
    models: dict[str, str]
    default_weights: dict[str, float]
    n_items: int


class ProductTypeCount(BaseModel):
    product_type: str
    count: int


class CollectionCount(BaseModel):
    collection: str
    count: int


class CategoriesResponse(BaseModel):
    product_types: list[ProductTypeCount]
    collections: list[CollectionCount]


class ProductSummary(BaseModel):
    sku: str
    title: str
    product_type: str
    collection: str | None = None
    price_inr: float | None = None
    thumb_url: str


class ProductDetail(ProductSummary):
    # "summary + descriptor + normalized metadata" (§9)
    descriptor_sentence: str | None = None
    materials: list[str] = []
    stones: list[str] = []
    colors: list[str] = []
    in_stock: bool | None = None
    attr_provenance: dict[str, str] = {}


class SignalBreakdown(BaseModel):
    cosine: float
    z: float
    contribution: float


class ItemBreakdown(BaseModel):
    image: SignalBreakdown
    text: SignalBreakdown
    meta: SignalBreakdown


class SimilarItem(BaseModel):
    product: ProductSummary
    score: float
    breakdown: ItemBreakdown
    reasons: list[str]
    fallback: bool


class SimilarResponse(BaseModel):
    query_sku: str
    bundle_version: str
    weights_used: dict[str, float]
    fallback_used: bool
    items: list[SimilarItem]
