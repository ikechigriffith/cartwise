from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    CanonicalProduct,
    GroceryList,
    GroceryListItem,
    ProposedPlan,
)


class CompilationService:
    def __init__(self, session: Session):
        self.session = session

    def compile_plan(
        self,
        grocery_list_id: UUID,
        fulfillment_method: str,
        start_location: dict,
        transit_mode: str = "driving",
        radius: float = 50000.0,
    ) -> ProposedPlan:
        """
        Compiles a grocery list into a proposed plan.
        
        Args:
            grocery_list_id: The ID of the grocery list to compile.
            fulfillment_method: The fulfillment method ('guided' or 'outsourced').
            start_location: The starting location for the plan.
            transit_mode: The mode of transit (e.g., 'driving', 'walking').
            radius: The maximum radius to search for stores.

        Returns:
            The generated ProposedPlan.
        """
        grocery_list = self.session.scalar(
            select(GroceryList).where(GroceryList.id == grocery_list_id)
        )
        if not grocery_list:
            raise ValueError("Grocery list not found")

        grocery_items = list(
            self.session.scalars(
                select(GroceryListItem).where(GroceryListItem.grocery_list_id == grocery_list_id)
            ).all()
        )

        resolved_items = []
        for item in grocery_items:
            canonical_product = self._resolve_item_to_canonical(item)
            resolved_items.append((item, canonical_product))

        if fulfillment_method == "guided":
            plan = self._compile_guided_plan(grocery_list_id, resolved_items, start_location, transit_mode, radius)
        elif fulfillment_method == "outsourced":
            plan = self._compile_outsourced_plan(grocery_list_id, resolved_items, start_location, transit_mode, radius)
        else:
            raise ValueError(f"Unknown fulfillment method: {fulfillment_method}")

        return plan

    def _resolve_item_to_canonical(self, item: GroceryListItem) -> CanonicalProduct:
        canonical_product = self.session.scalar(
            select(CanonicalProduct).where(CanonicalProduct.product_family_id == item.product_family_id)
        )
        if not canonical_product:
            raise ValueError(f"No canonical product found for product family {item.product_family_id}")
        return canonical_product

    def _compile_guided_plan(
        self,
        grocery_list_id: UUID,
        resolved_items: list[tuple[GroceryListItem, CanonicalProduct]],
        start_location: dict,
        transit_mode: str,
        radius: float,
    ) -> ProposedPlan:
        plan = ProposedPlan(
            grocery_list_id=grocery_list_id,
            fulfillment_method="guided",
            planned_start_time=datetime.now(timezone.utc),
            start_location=start_location,
            radius=radius,
            transit_mode=transit_mode,
            metrics={"total_cost": 0.0, "total_time": 0.0, "stops": 0},
            freshness_labels={},
        )
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan

    def _compile_outsourced_plan(
        self,
        grocery_list_id: UUID,
        resolved_items: list[tuple[GroceryListItem, CanonicalProduct]],
        start_location: dict,
        transit_mode: str,
        radius: float,
    ) -> ProposedPlan:
        plan = ProposedPlan(
            grocery_list_id=grocery_list_id,
            fulfillment_method="outsourced",
            planned_start_time=datetime.now(timezone.utc),
            start_location=start_location,
            radius=radius,
            transit_mode=transit_mode,
            metrics={"total_cost": 0.0, "total_time": 0.0, "stops": 1},
            freshness_labels={},
        )
        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)
        return plan
