import argparse
import json

from app.db import SessionLocal
from app.models import CanonicalProduct, ProductFamily, ProductListing
from app.product_identity import build_product_identity


def backfill(apply: bool) -> dict[str, int]:
    summary = {
        "product_families_seen": 0,
        "product_families_updated": 0,
        "canonical_products_seen": 0,
        "canonical_products_updated": 0,
        "canonical_product_sizes_backfilled": 0,
        "product_listings_seen": 0,
        "product_listings_updated": 0,
    }
    with SessionLocal() as session:
        for family in session.query(ProductFamily).yield_per(500):
            summary["product_families_seen"] += 1
            identity = build_product_identity(family.name)
            changed = False
            if family.normalized_name != identity.normalized_name:
                family.normalized_name = identity.normalized_name
                changed = True
            if family.selection_key != identity.selection_key:
                family.selection_key = identity.selection_key
                changed = True
            if changed:
                summary["product_families_updated"] += 1

        for product in session.query(CanonicalProduct).yield_per(500):
            summary["canonical_products_seen"] += 1
            identity = build_product_identity(product.canonical_name, brand=product.brand)
            changed = False
            if product.normalized_name != identity.normalized_name:
                product.normalized_name = identity.normalized_name
                changed = True
            if product.selection_key != identity.selection_key:
                product.selection_key = identity.selection_key
                changed = True
            if product.normalized_brand != identity.normalized_brand:
                product.normalized_brand = identity.normalized_brand
                changed = True
            if product.size_value is None and identity.parsed_size_value is not None:
                product.size_value = identity.parsed_size_value
                product.size_unit = identity.parsed_size_unit
                summary["canonical_product_sizes_backfilled"] += 1
                changed = True
            if product.package_quantity is None and identity.parsed_package_quantity is not None:
                product.package_quantity = int(identity.parsed_package_quantity)
                changed = True
            if changed:
                summary["canonical_products_updated"] += 1

        for listing in session.query(ProductListing).yield_per(500):
            summary["product_listings_seen"] += 1
            identity = build_product_identity(listing.raw_name, brand=listing.raw_brand)
            changed = False
            if listing.normalized_name != identity.normalized_name:
                listing.normalized_name = identity.normalized_name
                changed = True
            if listing.selection_key != identity.selection_key:
                listing.selection_key = identity.selection_key
                changed = True
            if listing.normalized_brand != identity.normalized_brand:
                listing.normalized_brand = identity.normalized_brand
                changed = True
            if changed:
                summary["product_listings_updated"] += 1

        if apply:
            session.commit()
        else:
            session.rollback()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill normalized product identity fields used for product selection.")
    parser.add_argument("--apply", action="store_true", help="Commit changes. Without this flag the script is a dry run.")
    args = parser.parse_args()
    print(json.dumps({"applied": args.apply, **backfill(args.apply)}, indent=2))


if __name__ == "__main__":
    main()
