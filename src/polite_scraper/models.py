"""Schema: every record is checked against Book BEFORE storage;
only description is optional. Failures never reach books.json."""

import re
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator


class Book(BaseModel):
    title: str
    product_url: str
    price_text: str
    availability_text: str
    rating_text: str
    description: str | None
    source_page: str
    fetched_at: datetime
    price_gbp: float

    @field_validator("product_url")
    @classmethod
    def validate_product_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("product_url must be an absolute HTTPS URL")
        return value


def normalize_price(price_text: str | None) -> float:
    """'£51.77' -> 51.77. Raises ValueError when unparseable."""
    if not price_text:
        raise ValueError("price_text is missing")

    cleaned = price_text.strip().replace("£", "").replace(",", "")
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", cleaned):
        raise ValueError(f"invalid price: {price_text!r}")
    return float(cleaned)
