from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass

from app.package_parser import parse_package


PRICE_RE = re.compile(r"(?i)(?:\b(?:ttd|usd)\s*)?\$\s*\d+(?:[.,]\d{1,2})?\b|\b(?:ttd|usd)\s+\d+(?:[.,]\d{1,2})\b")
MALFORMED_PRICE_RE = re.compile(r"\b\d+\.\.\d{1,2}\b")
SIZE_RE = re.compile(
    r"(?i)\b\d+(?:[.,]\d+)?\s*(?:fl\.?\s?oz|fluid ounces?|kg|kilograms?|g|grams?|ml|millilit(?:er|re)s?|l|lt|lit(?:er|re)s?|lbs?|pounds?|oz|ounces?)\b"
)
COUNT_RE = re.compile(r"(?i)\b\d+\s*(?:units?|ct|count|packs?|pk|rolls?|slices?|doz|dozen)\b")
MULTIPACK_RE = re.compile(
    r"(?i)\b\d+\s*(?:x|×)\s*\d+(?:[.,]\d+)?\s*(?:fl\.?\s?oz|kg|g|ml|l|lt|lbs?|oz)\b"
)
PACKAGING_PAREN_RE = re.compile(r"(?i)\((?:pack|tin|box|bag|bottle|loose|tray)\)")
PACKAGING_WORD_RE = re.compile(r"(?i)\b(?:pack|tin|box|bag|bottle|loose|tray|unit|units|ct|count|doz|dozen)\b")
PUNCT_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class ProductIdentity:
    clean_name: str
    normalized_name: str
    selection_key: str
    family_name: str
    normalized_brand: str | None
    parsed_size_value: float | None
    parsed_size_unit: str | None
    parsed_package_quantity: float | None


def _ascii_fold(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _clean_spacing(value: str) -> str:
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,/)])", r"\1", value)
    value = re.sub(r"([(])\s+", r"\1", value)
    value = re.sub(r"\s*-\s*(?=$|[/,])", " ", value)
    value = re.sub(r"\s+-\s+", " ", value)
    return value.strip(" -/,\t\n\r")


def clean_product_name(raw_name: str | None, size: str | None = None) -> str:
    parts = [part for part in [raw_name, size] if part and str(part).strip()]
    value = " ".join(str(part).strip() for part in parts)
    value = value.replace("’", "'").replace("–", "-").replace("—", "-").replace("×", "x")
    value = PRICE_RE.sub(" ", value)
    value = MALFORMED_PRICE_RE.sub(" ", value)
    value = _clean_spacing(value)
    return value


def normalize_product_text(value: str | None) -> str:
    if not value:
        return ""
    value = _ascii_fold(value).lower().replace("'", "")
    value = PUNCT_RE.sub(" ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(str(value)).lower().replace("’", "'")
    value = re.sub(r"[^a-z0-9']+", " ", value)
    return re.sub(r"\s+", " ", value).strip()



def derive_family_name(raw_name: str | None, brand: str | None = None, size: str | None = None) -> str:
    value = clean_product_name(raw_name, size)
    value = MULTIPACK_RE.sub(" ", value)
    value = SIZE_RE.sub(" ", value)
    value = COUNT_RE.sub(" ", value)
    value = PACKAGING_PAREN_RE.sub(" ", value)
    value = PACKAGING_WORD_RE.sub(" ", value)
    value = _clean_spacing(value)
    return value or clean_product_name(raw_name) or normalize_product_text(brand)


def selection_key_for(raw_name: str | None, brand: str | None = None, size: str | None = None) -> str:
    return normalize_product_text(derive_family_name(raw_name, brand, size))


def build_product_identity(raw_name: str | None, brand: str | None = None, size: str | None = None) -> ProductIdentity:
    clean_name = clean_product_name(raw_name, size)
    family_name = derive_family_name(raw_name, brand, size)
    parsed = parse_package(clean_name)
    return ProductIdentity(
        clean_name=clean_name,
        normalized_name=normalize_product_text(clean_name),
        selection_key=normalize_product_text(family_name),
        family_name=family_name,
        normalized_brand=normalize_product_text(brand) or None,
        parsed_size_value=parsed.normalized_size_value,
        parsed_size_unit=parsed.normalized_size_unit,
        parsed_package_quantity=parsed.package_quantity,
    )
