from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

UNIT_ALIASES = {
    "g": "g",
    "gram": "g",
    "grams": "g",
    "kg": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "ml": "ml",
    "milliliter": "ml",
    "milliliters": "ml",
    "millilitre": "ml",
    "millilitres": "ml",
    "l": "l",
    "lt": "l",
    "liter": "l",
    "liters": "l",
    "litre": "l",
    "litres": "l",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "lb": "lb",
    "lbs": "lb",
    "pound": "lb",
    "pounds": "lb",
    "fl oz": "fl_oz",
    "floz": "fl_oz",
    "fluid ounce": "fl_oz",
    "fluid ounces": "fl_oz",
    "unit": "count",
    "units": "count",
    "ct": "count",
    "count": "count",
    "pack": "count",
    "packs": "count",
    "pk": "count",
    "roll": "count",
    "rolls": "count",
}

UNIT_FAMILY = {
    "g": "mass",
    "kg": "mass",
    "oz": "mass",
    "lb": "mass",
    "ml": "volume",
    "l": "volume",
    "fl_oz": "volume",
    "count": "count",
}

# canonical normalized units for apples-to-apples comparison
NORMALIZED_UNIT = {
    "mass": "kg",
    "volume": "l",
    "count": "count",
}

UNIT_PATTERN = r"fl\.?\s?oz|fluid ounces?|kg|kilograms?|g|grams?|ml|millilit(?:er|re)s?|l|lt|lit(?:er|re)s?|lbs?|pounds?|oz|ounces?|units?|ct|count|packs?|pk|rolls?"
AMOUNT_UNIT_RE = re.compile(rf"(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>{UNIT_PATTERN})\b", re.I)
MULTIPACK_RE = re.compile(rf"(?P<count>\d+)\s*(?:x|×)\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>{UNIT_PATTERN})\b", re.I)
COUNT_RE = re.compile(r"(?P<count>\d+)\s*(?:units?|ct|count|packs?|pk|rolls?)\b", re.I)


@dataclass(frozen=True)
class PackageParseResult:
    package_quantity: float | None = None
    unit_size_value: float | None = None
    unit_size_unit: str | None = None
    total_size_value: float | None = None
    total_size_unit: str | None = None
    normalized_size_value: float | None = None
    normalized_size_unit: str | None = None
    computed_price_per_unit: Decimal | None = None
    computed_price_unit: str | None = None
    confidence: str = "low"
    needs_review: bool = False


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except Exception:
        return None


def _normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    clean = unit.lower().replace(".", "").strip()
    clean = re.sub(r"\s+", " ", clean)
    return UNIT_ALIASES.get(clean)


def _to_normalized(value: Decimal, unit: str) -> tuple[Decimal, str] | None:
    family = UNIT_FAMILY.get(unit)
    if not family:
        return None
    normalized_unit = NORMALIZED_UNIT[family]
    if unit == normalized_unit:
        return value, normalized_unit
    if unit == "g":
        return value / Decimal("1000"), "kg"
    if unit == "oz":
        return value * Decimal("0.028349523125"), "kg"
    if unit == "lb":
        return value * Decimal("0.45359237"), "kg"
    if unit == "ml":
        return value / Decimal("1000"), "l"
    if unit == "fl_oz":
        return value * Decimal("0.0295735295625"), "l"
    if unit == "count":
        return value, "count"
    return None


def _round_decimal(value: Decimal, places: str = "0.0001") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _choose_best_amount(text: str) -> tuple[Decimal, str] | None:
    matches = []
    for match in AMOUNT_UNIT_RE.finditer(text):
        value = _decimal(match.group("value"))
        unit = _normalize_unit(match.group("unit"))
        if value is None or unit is None or unit == "count":
            continue
        # Prefer metric units over imperial when both are listed.
        priority = {"kg": 1, "g": 1, "l": 1, "ml": 1, "lb": 2, "oz": 2, "fl_oz": 2}.get(unit, 9)
        matches.append((priority, value, unit))
    if not matches:
        return None
    _, value, unit = sorted(matches, key=lambda item: item[0])[0]
    return value, unit


def parse_package(raw_name: str, price: Decimal | None = None, retailer_payload: dict[str, Any] | None = None) -> PackageParseResult:
    payload = retailer_payload or {}
    text = raw_name or ""

    package_quantity: Decimal | None = None
    unit_size_value: Decimal | None = None
    unit_size_unit: str | None = None
    total_size_value: Decimal | None = None
    total_size_unit: str | None = None
    confidence = "low"

    # Retailer fields first, if they are structured enough.
    retailer_weight = _decimal(payload.get("weight_TT"))
    retailer_weight_unit = _normalize_unit(payload.get("weight_uom_description_TT"))
    if retailer_weight and retailer_weight_unit:
        total_size_value = retailer_weight
        total_size_unit = retailer_weight_unit
        confidence = "high"

    # Multipack examples: 24 x 500 ml, 6×1.5 L
    multipack = MULTIPACK_RE.search(text)
    if multipack:
        count = _decimal(multipack.group("count"))
        value = _decimal(multipack.group("value"))
        unit = _normalize_unit(multipack.group("unit"))
        if count and value and unit:
            package_quantity = count
            unit_size_value = value
            unit_size_unit = unit
            if unit != "count":
                total_size_value = count * value
                total_size_unit = unit
            confidence = "high"

    # Count plus size examples: 12 Units / 355 mL / 12 oz
    if package_quantity is None:
        count_match = COUNT_RE.search(text)
        if count_match:
            package_quantity = _decimal(count_match.group("count"))

    if total_size_value is None or total_size_unit is None:
        amount = _choose_best_amount(text)
        if amount:
            value, unit = amount
            if package_quantity and unit != "count":
                unit_size_value = value
                unit_size_unit = unit
                total_size_value = package_quantity * value
                total_size_unit = unit
            else:
                total_size_value = value
                total_size_unit = unit
            confidence = "medium" if confidence == "low" else confidence

    # Count-only fallback.
    if total_size_value is None and package_quantity:
        total_size_value = package_quantity
        total_size_unit = "count"
        confidence = "medium" if confidence == "low" else confidence

    normalized_size_value = None
    normalized_size_unit = None
    if total_size_value is not None and total_size_unit is not None:
        normalized = _to_normalized(total_size_value, total_size_unit)
        if normalized:
            normalized_size_value, normalized_size_unit = normalized

    computed_price_per_unit = None
    computed_price_unit = None
    if price is not None and normalized_size_value and normalized_size_value > 0:
        computed_price_per_unit = _round_decimal(price / normalized_size_value)
        computed_price_unit = normalized_size_unit

    needs_review = normalized_size_value is None or normalized_size_unit is None

    return PackageParseResult(
        package_quantity=float(package_quantity) if package_quantity is not None else None,
        unit_size_value=float(unit_size_value) if unit_size_value is not None else None,
        unit_size_unit=unit_size_unit,
        total_size_value=float(total_size_value) if total_size_value is not None else None,
        total_size_unit=total_size_unit,
        normalized_size_value=float(normalized_size_value) if normalized_size_value is not None else None,
        normalized_size_unit=normalized_size_unit,
        computed_price_per_unit=computed_price_per_unit,
        computed_price_unit=computed_price_unit,
        confidence=confidence,
        needs_review=needs_review,
    )
