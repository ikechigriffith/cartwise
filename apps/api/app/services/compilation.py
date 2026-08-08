from typing import List, Optional
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from app.models import (
    GroceryList,
    GroceryListItem,
    ProposedPlan,
    PlanAlternative,
    Stop,
    ItemAssignment,
    CanonicalProduct,
    Store,
    ProductListing,
)
class CompilationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def compile_plan(
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
        # 1. Fetch the grocery list and its items
        result = await self.session.execute(
            select(GroceryList).where(GroceryList.id == grocery_list_id)
        )
        grocery_list = await result.scalar_one_or_none()
        if not grocery_list:
            raise ValueError("Grocery list not found")

        items = await self.session.execute(
            select(GroceryListItem).where(GroceryListItem.grocery_list_id == grocery_list_id)
        )
        grocery_items = items.scalars().all()

        # 2. Resolve items to CanonicalProducts
        # This is where we handle substitutions and preferences
        # For now, we'll just take the first match or something simple
        resolved_items = []
        for item in grocery_items:
            # For now, we'll just use a placeholder logic to find a canonical product
            # In a real implementation, this would involve more complex logic
            canonical_product = await self._resolve_item_to_canonical(item)
            resolved_items.append((item, canonical_product))

        if fulfillment_method == "guided":
            plan = await self._compile_guided_plan(resolved_items, start_location, transit_mode, radius)
        elif fulfillment_method == "outsourced":
            plan = await self._compile_outsourced_plan(resolved_items, start_location, transit_mode, radius)
        else:
            raise ValueError(f"Unknown fulfillment method: {fulfillment_method}")

        return plan

    async def _resolve_item_to_canonical(self, item: GroceryListItem) -> CanonicalProduct:
        # Placeholder: find any canonical product for this product family
        result = await self.session.execute(
            select(CanonicalProduct).where(CanonicalProduct.product_family_id == item.product_family_id)
        )
        canonical_product = await result.scalar_one_or_none()
        if not canonical_product:
            # If no canonical product, maybe we have to create one or handle the error
            raise ValueError(f"No canonical product found for product family {item.product_family_id}")
        return canonical_product

    async def _compile_guided_plan(
        self,
        resolved_items: List[tuple[GroceryListItem, CanonicalProduct]],
        start_location: dict,
        transit_mode: str,
        radius: float,
    ) -> ProposedPlan:
        # 1. Find stores and best listings for each canonical product
        # 2. Select the best stores (e.g., cheapest, closest)
        # 3. Optimize the route (TSP/VRP)
        # 4. Create stops and item assignments
        # 5. Calculate metrics
        
        # For now, return a dummy plan to get the structure right
        plan = ProposedPlan(
            grocery_list_id=resolved_items[0][0].grocery_list_id,
            fulfillment_method="guided",
            planned_start_time=datetime.now(timezone.utc),
            start_location=start_location,
            radius=radius,
            transit_mode=transit_mode,
            metrics={"total_cost": 0.0, "total_time": 0.0, "stops": 0},
            freshness_labels={},
        )
        self.session.add(plan)
        await self.session.commit()
        return plan

    async def _compile_outsourced_plan(
        self,
        resolved_items: List[tuple[GroceryListItem, CanonicalProduct]],
        start_location: dict,
        transit_mode: str,
        radius: float,
    ) -> ProposedPlan:
        # 1. Find a store/service that offers outsourced fulfillment
        # 2. Create a plan with a single stop
        # 3. Calculate metrics
        
        plan = ProposedPlan(
            grocery_list_id=resolved_items[0][0].grocery_list_id,
            fulfillment_method="outsourced",
            planned_start_time=datetime.now(timezone.utc),
            start_location=start_location,
            radius=radius,
            transit_mode=transit_mode,
            metrics={"total_cost": 0.0, "total_time": 0.0, "stops": 1},
            freshness_labels={},
        )
        self.session.add(plan)
        await self.session.commit()
        return plan
