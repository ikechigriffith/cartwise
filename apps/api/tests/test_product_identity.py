from app.product_identity import build_product_identity, clean_product_name, derive_family_name, normalize_product_text


def test_clean_product_name_removes_price_artifacts_without_dropping_size():
    assert clean_product_name("MILO (Pack) - 400g $31.99") == "MILO (Pack) 400g"
    assert clean_product_name("Baking Powder Lion 454g $9.99") == "Baking Powder Lion 454g"


def test_selection_key_removes_package_and_size_for_product_family_matching():
    identity = build_product_identity("MILO (Pack) - 400g $31.99")

    assert identity.clean_name == "MILO (Pack) 400g"
    assert identity.family_name == "MILO"
    assert identity.selection_key == "milo"
    assert identity.parsed_size_value == 0.4
    assert identity.parsed_size_unit == "kg"


def test_selection_key_keeps_descriptive_product_intent():
    identity = build_product_identity("Par Excellence Parboiled Rice 9 kg / 19.80 lb", brand="Par Excellence")

    assert identity.selection_key == "par excellence parboiled rice"
    assert identity.normalized_brand == "par excellence"
    assert identity.parsed_size_value == 9.0
    assert identity.parsed_size_unit == "kg"


def test_family_derivation_handles_count_only_products():
    assert derive_family_name("Large EGGS 1 Doz") == "Large EGGS"
    assert normalize_product_text("Member's Selection") == "members selection"
