# Program Design: Guided plan tracer

## Files

### API

- `apps/api/pyproject.toml` and `apps/api/uv.lock` — add the JWT/JWKS verification dependency used for Clerk tokens.
- `apps/api/app/config.py` — add Clerk issuer/domain and secret-key settings.
- `apps/api/app/models.py` — add the local user's unique Clerk subject field and the selected canonical-product reference on list items.
- `apps/api/migrations/versions/0012_add_user_clerk_subject.py` — add/index the Clerk-subject column without changing existing users' list ownership.
- `apps/api/migrations/versions/0013_add_grocery_list_item_canonical_product.py` — add the nullable canonical-product reference required by new tracer list items.
- `apps/api/app/deps.py` — add authenticated-user resolution: verify the bearer token, obtain the verified Clerk identity, find/create the local user, and expose it as a route dependency.
- `apps/api/app/schemas/offers.py` — define public offer/filter response models.
- `apps/api/app/schemas/grocery_lists.py` — define authenticated grocery-list and item request/response models.
- `apps/api/app/schemas/guided_plans.py` — define persisted plan response models.
- `apps/api/app/services/offers.py` — query and filter comparable eligible offers; calculate distance; apply sort order and freshness labels.
- `apps/api/app/services/guided_plans.py` — find a complete single-store plan, create its persisted plan/stop/item assignments, and report uncovered items.
- `apps/api/app/routers/products.py` — keep search public and add the public single-product offers route.
- `apps/api/app/routers/grocery_lists.py` — add authenticated list, list-item, and list-plan routes with ownership checks.
- `apps/api/app/main.py` — register the grocery-list router.
- `apps/api/app/routers/compilation.py` and `apps/api/app/services/compilation.py` — remove the unauthenticated placeholder compilation endpoint in favor of the owned-list plan route.
- `apps/api/tests/test_offers_api.py` — cover public offer eligibility, filters, sorting, and serialization.
- `apps/api/tests/test_grocery_lists_api.py` — cover authenticated list ownership and item operations.
- `apps/api/tests/test_guided_plans.py` — cover one-stop plan selection, persistence, and incomplete coverage.
- `apps/api/tests/test_auth.py` — cover token verification boundary and local-user resolution with mocked Clerk/JWKS calls.

### Web

- `apps/web/package.json` and `pnpm-lock.yaml` — add Clerk's Next.js package.
- `apps/web/app/layout.tsx` — provide Clerk context to the app.
- `apps/web/middleware.ts` — protect list and plan routes while leaving comparison routes public.
- `apps/web/lib/api.ts` — attach the signed-in user's session token to authenticated API calls and centralize API base URL handling.
- `apps/web/lib/types.ts` — define offer, list, item, and plan view types shared by pages/components.
- `apps/web/app/compare/page.tsx` — implement the public item search, comparison layout, filters, sort, map links, and add-to-list sign-in prompt.
- `apps/web/app/sign-in/[[...sign-in]]/page.tsx` — host Clerk's sign-in/create-account journey.
- `apps/web/app/lists/page.tsx` — show the authenticated user's persistent grocery lists and create a list.
- `apps/web/app/lists/[id]/page.tsx` — edit one persistent list and request its plan.
- `apps/web/app/plans/[id]/page.tsx` — display a saved guided plan, coverage, assignments, and freshness notes.
- `apps/web/app/page.tsx` and `apps/web/app/globals.css` — make the comparison flow the product entry point and add the approved visual styling.

## Types & signatures

```python
# app/deps.py
@dataclass(frozen=True)
class ClerkIdentity:
    subject: str
    email: str


def get_current_user(
    authorization: Annotated[str, Header()],
    db: Annotated[Session, Depends(get_db)],
) -> User: ...

# app/services/offers.py
class OfferFilters(BaseModel):
    origin_latitude: float
    origin_longitude: float
    max_distance_km: float | None = None
    max_price: Decimal | None = None
    retailer_ids: list[UUID] = []
    in_stock_only: bool = True
    sort: Literal["price_asc", "price_desc", "distance_asc"] = "price_asc"

class ProductOffer(BaseModel):
    product_id: UUID
    listing_id: UUID
    retailer_name: str
    store_id: UUID
    store_name: str
    latitude: float
    longitude: float
    distance_km: float
    price: Decimal
    unit_price: Decimal | None
    unit_label: str | None
    stock_availability: str | None
    price_checked_at: datetime | None
    stock_checked_at: datetime | None
    freshness_label: str
    ranking_flag: Literal["cheapest", "nearest"] | None


def find_product_offers(
    db: Session,
    canonical_product_id: UUID,
    filters: OfferFilters,
) -> list[ProductOffer]: ...

# app/services/guided_plans.py
class GeoPoint(BaseModel):
    latitude: float
    longitude: float

class PlanCoverage(BaseModel):
    assigned_item_ids: list[UUID]
    unassigned_item_ids: list[UUID]


def compile_one_stop_plan(
    db: Session,
    user: User,
    grocery_list: GroceryList,
    origin: GeoPoint,
    max_distance_km: float,
) -> ProposedPlan | PlanCoverage: ...

# app/routers/grocery_lists.py
def create_grocery_list(
    payload: CreateGroceryListRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroceryListResponse: ...

def create_guided_plan(
    grocery_list_id: UUID,
    payload: CreateGuidedPlanRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GuidedPlanResponse: ...
```

```ts
// apps/web/lib/api.ts
export type ApiClient = {
  getOffers(productId: string, filters: OfferFilters): Promise<ProductOffer[]>;
  listGroceryLists(): Promise<GroceryListSummary[]>;
  createGroceryList(input: CreateGroceryListInput): Promise<GroceryList>;
  addListItem(listId: string, input: CreateListItemInput): Promise<GroceryList>;
  createGuidedPlan(listId: string, input: GuidedPlanInput): Promise<GuidedPlan>;
};

// apps/web/app/compare/page.tsx
function ComparePage(): React.ReactElement;
function OfferTable({ offers, sort }: { offers: ProductOffer[]; sort: OfferSort }): React.ReactElement;
function OfferFilters({ value, onChange }: { value: OfferFilters; onChange(value: OfferFilters): void }): React.ReactElement;
```

## Call stack

### Public item comparison

`ComparePage` → public product search → selected canonical product → `GET /products/{id}/offers` → `find_product_offers` → approved/current listing + active-store query → sorted offers → comparison table.

### Sign-in and persistent grocery list

comparison “Add to grocery list” → Clerk sign-in → Clerk session token → authenticated web API client → `get_current_user` → verify Clerk token and find/create local `User` → grocery-list router → list service/database → persisted list response.

### Guided plan

list detail “Find guided plan” → authenticated `POST /grocery-lists/{id}/guided-plans` → ownership lookup → `compile_one_stop_plan` → offer query for every list item → choose lowest-subtotal complete store → persist plan, stop, and assignments → plan response → plan page.

## Test plan

- `test_public_offer_query_returns_only_active_approved_high_confidence_current_listings`
- `test_offer_query_applies_price_distance_retailer_and_in_stock_filters`
- `test_offer_query_sorts_by_price_or_distance_and_marks_only_the_leading_offer`
- `test_offer_query_returns_coordinates_and_checked_timestamps_for_map_and_recency_display`
- `test_unauthenticated_requests_cannot_create_or_read_grocery_lists`
- `test_authenticated_user_can_only_read_and_change_owned_lists`
- `test_first_authenticated_request_creates_local_user_from_verified_clerk_subject`
- `test_existing_clerk_subject_resolves_to_same_local_user`
- `test_guided_plan_chooses_lowest_subtotal_single_store_that_covers_every_item`
- `test_guided_plan_reports_uncovered_items_without_persisting_a_misleading_complete_plan`
- `test_guided_plan_persists_stop_and_item_assignments_for_owned_list`
- `test_public_comparison_page_is_not_protected_and_list_plan_pages_are_protected`
- `test_authenticated_web_client_sends_session_token_to_api`
- `test_compare_page_renders_filters_sort_flag_location_link_and_price_recency`

## Least confident decisions

1. **Single-store-only plans:** this is deliberately safe for a tracer, but may fail to show savings when a multi-store list is cheaper.
2. **Exact canonical-product list items:** it avoids unsafe substitutions, but may feel restrictive for people who think in generic product families.
3. **Freshness limit:** the current product has timestamps but no agreed numeric threshold for “current.”
4. **Location source and privacy:** the UI needs an explicit location-input/permission choice and clear handling of location data.
5. **Clerk-to-local-user provisioning:** first authenticated API request is simple, but Clerk webhook synchronization may later be needed for profile changes or account deletion.
