from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

Slug = Annotated[str, Field(min_length=1, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CategoryWrite(Input):
    name: str = Field(min_length=1, max_length=100)
    slug: Slug
    description: str = Field(default="", max_length=4000)
    active: bool = True
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=160)


class ProductWrite(Input):
    category_id: UUID
    name: str = Field(min_length=1, max_length=200)
    slug: Slug
    description: str = Field(default="", max_length=8000)
    specifications: dict[str, str] = Field(default_factory=dict, max_length=30)
    active: bool = True
    seo_title: str | None = Field(default=None, max_length=70)
    seo_description: str | None = Field(default=None, max_length=160)

    @field_validator("specifications")
    @classmethod
    def bounded_specs(cls, value):
        if any(not k.strip() or len(k) > 80 or len(v) > 500 for k, v in value.items()):
            raise ValueError("Specifications require short names and values")
        return value


class VariantWrite(Input):
    sku: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z0-9][A-Z0-9_-]*$")
    label: str = Field(min_length=1, max_length=100)
    price: Money
    compare_at_price: Money | None = None
    active: bool = True

    @model_validator(mode="after")
    def compare_price(self):
        if self.compare_at_price is not None and self.compare_at_price < self.price:
            raise ValueError("Compare-at price must be at least price")
        return self


class StockWrite(Input):
    on_hand: int = Field(ge=0, le=2_000_000_000, strict=True)


class ImageWrite(Input):
    public_id: str = Field(min_length=1, max_length=255)
    url: HttpUrl
    alt: str = Field(min_length=1, max_length=300)
    position: int = Field(ge=0, le=100)
    width: int = Field(gt=0, le=20000)
    height: int = Field(gt=0, le=20000)

    @field_validator("url")
    @classmethod
    def cloudinary_only(cls, value):
        if (
            value.scheme != "https"
            or value.host != "res.cloudinary.com"
            or "/image/upload/" not in value.path
        ):
            raise ValueError("Use an HTTPS Cloudinary image upload URL")
        return value


class CatalogQuery(Input):
    q: str = Field(default="", max_length=100)
    category: Slug | None = None
    min_price: Money | None = None
    max_price: Money | None = None
    in_stock: bool = False
    on_sale: bool = False
    sort: Literal["newest", "price_asc", "price_desc", "name", "best_sellers"] = "newest"
    page: int = Field(default=1, ge=1, le=10000)
    page_size: int = Field(default=12, ge=1, le=48)

    @model_validator(mode="after")
    def price_range(self):
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            raise ValueError("Invalid price range")
        return self
