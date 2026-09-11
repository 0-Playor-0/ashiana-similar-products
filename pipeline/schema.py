from pydantic import BaseModel, Field


class Product(BaseModel):
    sku: str
    parent_id: str | None = None
    title: str
    description_raw: str | None = None
    product_type: str
    collection: str | None = None
    materials: list[str] = Field(default_factory=list)
    stones: list[str] = Field(default_factory=list)
    colors: list[str] = Field(default_factory=list)
    price_inr: float | None = None
    image_urls: list[str] = Field(default_factory=list)
    primary_image: str | None = None
    in_stock: bool | None = None
    source_url: str | None = None
    attr_provenance: dict[str, str] = Field(default_factory=dict)
