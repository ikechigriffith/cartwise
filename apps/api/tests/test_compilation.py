import uuid
from unittest.mock import MagicMock

from app.models import CanonicalProduct, GroceryList, GroceryListItem
from app.services.compilation import CompilationService


def test_compilation_service_guided_plan_with_mock():
    mock_session = MagicMock()
    grocery_list_id = uuid.uuid4()
    product_family_id = uuid.uuid4()

    mock_grocery_list = GroceryList(id=grocery_list_id, user_id=uuid.uuid4(), name="Test List")
    mock_item = GroceryListItem(
        grocery_list_id=grocery_list_id,
        product_family_id=product_family_id,
        needed_amount=1.0,
        unit="count",
    )
    mock_canonical = CanonicalProduct(
        product_family_id=product_family_id,
        canonical_name="Test Product",
    )

    mock_session.scalar.side_effect = [mock_grocery_list, mock_canonical]
    mock_session.scalars.return_value.all.return_value = [mock_item]

    service = CompilationService(mock_session)
    plan = service.compile_plan(
        grocery_list_id=grocery_list_id,
        fulfillment_method="guided",
        start_location={"latitude": 10.6, "longitude": -61.5},
    )

    assert plan is not None
    assert plan.fulfillment_method == "guided"
    assert plan.grocery_list_id == grocery_list_id
    assert plan.metrics["stops"] == 0
    assert mock_session.add.called
    assert mock_session.commit.called
