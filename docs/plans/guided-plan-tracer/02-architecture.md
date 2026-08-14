# Architecture: Guided plan tracer

## Fit

- Reuse the existing Next.js web app for the public item-comparison screen, Clerk sign-in screen, authenticated grocery-list screen, and authenticated guided-plan screen.
- Extend the existing FastAPI product/catalog surface. `product_listings`, approved high-confidence `product_mappings`, active `stores`, and their coordinates already contain the data needed for a current-price comparison.
- Keep the current admin review and import workflows unchanged; they remain the source of trusted catalog and store data.
- Add Clerk authentication to the web app. FastAPI verifies the Clerk session token and resolves its subject to the existing local `User` record. Lists and plans remain owned by local users and are therefore independent of Clerk's user-data model.

## Endpoints

- `GET /products/search?q=` — existing public canonical-product search; a broad query returns exact-product choices, one of which must be selected before comparison or list addition.
- `GET /products/{canonical_product_id}/offers` — public; return eligible current offers for one exact product, including store coordinates, distance from a supplied origin, stock/freshness, filters, and ordering.
- `GET /grocery-lists` — authenticated; return the signed-in user's persistent grocery lists.
- `POST /grocery-lists` — authenticated; create a persistent grocery list for the signed-in user.
- `GET /grocery-lists/{id}` and item create/update/delete routes — authenticated; read or change only a list owned by the signed-in user.
- `POST /grocery-lists/{id}/guided-plans` — authenticated; compile, persist, and return an explainable guided plan for the owned list.

## Data

- Add a unique, indexed external-auth-subject field to `users`, populated from the verified Clerk subject. The API creates the local `User` record on the first authenticated request; it never accepts a user ID from the browser as proof of ownership.
- Add a canonical-product reference to `grocery_list_items`. It is the authoritative selected item for every new tracer list item; the existing product-family reference is retained only for compatibility with existing data. The new reference is nullable for existing rows.
- Add a product-image URL to `product_listings`, populated from retailer catalog imports. Broad-search results select a representative current retailer image for every returned exact product; products without a current image are not included in the first-release search grid.
- An eligible offer joins a current `ProductListing` to an approved, high-confidence `ProductMapping`, an active `Store`, and its `Retailer`.
- Eligibility excludes missing prices and, by default, listings not believed to be in stock. It applies the chosen distance, price, and retailer filters.
- Distance is calculated from the supplied origin and stored store latitude/longitude. Offer responses expose price/stock timestamps and classify recency with an app-defined freshness limit.
- Existing `GroceryList`, `GroceryListItem`, `ProposedPlan`, `PlanAlternative`, `Stop`, and `ItemAssignment` tables persist signed-in users' lists and generated plans; the tracer adds the Clerk-subject, exact-list-item, and product-image fields described above.
- The first plan supports exact selected canonical products only. It deliberately excludes substitutions, package combinations, historical-price observations, routing, and outsourced fulfillment.

## Flow

1. A guest supplies a location and searches broadly. Search results present exact products; the guest selects one exact product before receiving eligible store offers ordered by price or proximity.
2. A guest can filter offers and follow a store-location link. Adding the selected exact product to a list or requesting a plan presents the Clerk sign-in/create-account journey.
3. The authenticated web app sends the Clerk session token with list and plan requests. The API verifies it, finds or creates the corresponding local user, and enforces list ownership on every request.
4. The signed-in user creates or reuses a persistent grocery list and adds exact selected products with quantities.
5. For a guided plan, the API finds eligible offers for every item and initially chooses the active single store with the lowest grocery subtotal that covers the complete list. It persists the plan, its one stop, and item assignments.
6. The API returns the selected store, offers, subtotal, coverage, and price/stock recency. The web app renders the saved plan.

## External

- Clerk provides passwordless email links and Google sign-in. Required configuration names: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, and `CLERK_JWT_ISSUER_DOMAIN`.
- Store-location links are map deep links built from stored coordinates; no map API request or map-provider credential is required.
