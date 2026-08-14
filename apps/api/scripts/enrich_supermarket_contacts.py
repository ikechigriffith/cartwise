import json
import re
from sqlalchemy import select

from app.db import SessionLocal
from app.models import Retailer, Store, now_utc

KNOWN_RETAILER_CONTACTS = {
    "Massy Stores": {
        "website": "https://massystores.com",
        "facebook": "https://www.facebook.com/massystorestt",
        "instagram": "https://www.instagram.com/massystorestt",
        "phone": "+1 868-225-4672",
        "email": "customercare.tt@massystores.com",
        "customer_support_line": "+1 868-225-4672",
    },
    "PriceSmart": {
        "website": "https://www.pricesmart.com/site/tt/en",
        "facebook": "https://www.facebook.com/pricesmarttrinidad",
        "instagram": "https://www.instagram.com/pricesmarttt",
        "phone": "+1 868-665-9000",
        "customer_support_line": "+1 868-665-9000",
    },
    "SuperPharm": {
        "website": "https://superpharmtt.com",
        "facebook": "https://www.facebook.com/superpharmtt",
        "instagram": "https://www.instagram.com/superpharmtt",
        "phone": "+1 868-800-4742",
        "email": "info@superpharmtt.com",
        "customer_support_line": "800-4PHARM",
    },
    "JTA Supermarkets": {
        "website": "https://www.jtasupermarkets.com",
        "facebook": "https://www.facebook.com/jtasupermarkets",
        "instagram": "https://www.instagram.com/jtasupermarkets",
        "phone": "+1 868-652-3611",
        "email": "info@jtasupermarkets.com",
    },
    "Xtra Foods": {
        "website": "https://xtrafoods.com",
        "facebook": "https://www.facebook.com/xtrafoodssupermarket",
        "instagram": "https://www.instagram.com/xtrafoods",
        "phone": "+1 868-672-9721",
        "email": "customercare@xtrafoods.com",
    },
    "Tru Valu": {
        "website": "https://truvalusupermarkets.com",
        "facebook": "https://www.facebook.com/truvalustores",
        "instagram": "https://www.instagram.com/truvalutt",
        "phone": "+1 868-645-8825",
    },
    "Persad's D' Food King": {
        "facebook": "https://www.facebook.com/persadsdfoodking",
        "instagram": "https://www.instagram.com/persadsdfoodking",
        "phone": "+1 868-654-1240",
    },
    "Cost Cutters": {
        "facebook": "https://www.facebook.com/costcutterssupermarket",
        "phone": "+1 868-668-3721",
    },
    "Food Basket": {
        "facebook": "https://www.facebook.com/foodbasketmarket",
        "phone": "+1 868-674-2101",
    },
    "Penny Savers": {
        "facebook": "https://www.facebook.com/pennysaversupermarket",
        "phone": "+1 868-639-2708",
    },
    "Bel Air Store": {
        "website": "https://belairstore.com",
        "facebook": "https://www.facebook.com/belairstoreltd",
        "instagram": "https://www.instagram.com/belairstoreltd",
        "phone": "+1 868-658-3545",
        "whatsapp": "+1 868-385-2395",
        "customer_support_line": "+1 868-658-0191",
    },
    "West Bees": {
        "website": "https://westbees.com",
        "facebook": "https://www.facebook.com/westbeessupermarket",
        "instagram": "https://www.instagram.com/westbeessupermarket",
        "phone": "+1 868-632-8150",
    },
}


def enrich_contacts() -> dict[str, int]:
    retailers_updated = 0
    stores_updated = 0
    now = now_utc()

    with SessionLocal() as session:
        retailers = session.scalars(select(Retailer)).all()
        for retailer in retailers:
            info = KNOWN_RETAILER_CONTACTS.get(retailer.name) or {}
            existing = retailer.contact_info or {}
            merged = {**existing, **info}
            if merged != existing or retailer.website_url != info.get("website"):
                retailer.contact_info = merged
                if info.get("website") and not retailer.website_url:
                    retailer.website_url = info.get("website")
                retailer.updated_at = now
                retailers_updated += 1

        stores = session.scalars(select(Store)).all()
        for store in stores:
            raw_tags = store.raw_tags or {}
            contact = store.contact_info or {}
            r_info = KNOWN_RETAILER_CONTACTS.get(store.retailer.name if store.retailer else "") or {}

            # Extract phone, website, email from raw_tags (OpenStreetMap tags)
            osm_phone = raw_tags.get("phone") or raw_tags.get("contact:phone") or raw_tags.get("contact:mobile")
            osm_website = raw_tags.get("website") or raw_tags.get("contact:website")
            osm_facebook = raw_tags.get("facebook") or raw_tags.get("contact:facebook")
            osm_instagram = raw_tags.get("instagram") or raw_tags.get("contact:instagram")
            osm_email = raw_tags.get("email") or raw_tags.get("contact:email")

            phone = osm_phone or contact.get("phone") or r_info.get("phone")
            website = osm_website or contact.get("website") or store.retailer.website_url if store.retailer else None
            facebook = osm_facebook or contact.get("facebook") or r_info.get("facebook")
            instagram = osm_instagram or contact.get("instagram") or r_info.get("instagram")
            email = osm_email or contact.get("email") or r_info.get("email")

            new_contact = {
                "phone": phone,
                "website": website,
                "facebook": facebook,
                "instagram": instagram,
                "email": email,
            }
            # Strip null entries
            new_contact = {k: v for k, v in new_contact.items() if v is not None}

            if new_contact != contact:
                store.contact_info = new_contact
                store.updated_at = now
                stores_updated += 1

        session.commit()

    return {
        "retailers_updated": retailers_updated,
        "stores_updated": stores_updated,
    }


if __name__ == "__main__":
    res = enrich_contacts()
    print(json.dumps(res, indent=2))
