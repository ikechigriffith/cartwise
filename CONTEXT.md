# Grocery Shopping Optimization

This context describes the language for a grocery planning product that helps users find the most cost-effective way to buy a grocery list within a chosen area.

## Language

**User**:
A person who owns grocery lists and chooses how those lists should be fulfilled.
_Avoid_: Customer, shopper

**Grocery List**:
A persistent collection of grocery items owned by a user. A user can reuse recent lists and choose a fulfillment method for a list.
_Avoid_: Cart, basket, shopping trip

**Fulfillment Method**:
The way a grocery list is acted on after the user is ready to shop. The supported methods are Guided and Outsourced.
_Avoid_: Mode, workflow

**Guided**:
A fulfillment method where the user shops for the list themselves using an app-generated route and item assignments.
_Avoid_: Manual

**Outsourced**:
A fulfillment method where the user submits the grocery list to an external service or third party to be shopped for them.
_Avoid_: Delivery-only, handoff

**Retailer**:
A grocery business or brand that may operate one or more stores and expose shared integration surfaces such as websites, APIs, or loyalty programs.
_Avoid_: Store, merchant, vendor

**Retailer Data Source**:
A source that may provide retailer product, price, stock, or store data, such as a website, API, scrape target, partner feed, or manual source.
_Avoid_: Store website, integration

**Store**:
A physical retail location operated by a retailer where grocery items may be bought.
_Avoid_: Retailer, merchant, vendor

**Store Type**:
A classification of a store by the kind of grocery experience it offers, such as supermarket, convenience, or specialty.
_Avoid_: Category

**Service Capability**:
A way a store generally supports grocery fulfillment, such as delivery, pickup, or in-store shopping.
_Avoid_: Feature

**Service Availability**:
Whether a store's service capability is available for a specific user, time, or location.
_Avoid_: Capability

**Product Family**:
The general product intent a user may ask for, such as 2% milk or sandwich bread. Product families can contain multiple canonical products.
_Avoid_: Search term, generic product

**Canonical Product**:
The app's clean representation of an exact comparable grocery product across stores, including brand, size, and package quantity where relevant. Store-specific listings map to canonical products.
_Avoid_: SKU, listing, raw product, product family

**Product Listing**:
A store-specific representation of a product, including that store's name, identifier, price, and availability.
_Avoid_: Canonical product

**Product Mapping**:
The relationship between a product listing and a canonical product. Proposed plans use only high-confidence product mappings, while medium-confidence mappings are kept for internal review.
_Avoid_: Match, merge

**Mapping Review**:
An internal review process for approving or rejecting medium-confidence product mappings before they can influence proposed plans.
_Avoid_: User confirmation

**Store Brand**:
A brand owned or exclusive to a store and treated as a brand in product identity.
_Avoid_: Generic brand

**Category**:
A broad grouping for products, such as dairy, produce, frozen, or pantry.
_Avoid_: Department

**Subcategory**:
A more specific grouping within a category, such as milk within dairy.
_Avoid_: Tag

**Estimated Price**:
A price believed to be accurate based on retailer data, scraping, or cached observations, but not guaranteed unless explicitly backed by a retailer integration.
_Avoid_: Guaranteed price

**Price Per Unit**:
A normalized price for comparing product listings across compatible sizes and package quantities.
_Avoid_: Sticker price

**Package Normalization**:
The process of turning retailer-specific package descriptions into structured, comparable units such as kilograms, liters, or count.
_Avoid_: Size parsing

**Unit Family**:
A compatible measurement family used for apples-to-apples comparison, such as mass, volume, or count.
_Avoid_: Unit type

**Substitution**:
An acceptable replacement of one canonical product with another within the same product family, constrained by the user's preferences.
_Avoid_: Alternative, duplicate

**Product Requirement**:
A hard constraint that must be satisfied for a substitution or product match to be acceptable, such as lactose-free, gluten-free, nut-free, or a required brand.
_Avoid_: Preference

**Product Preference**:
A strong but non-mandatory constraint that should be honored in the default plan and used to rank acceptable products, such as organic, local, preferred brand, or store brand acceptance. The app may show explicit trade-offs when violating a preference would save meaningful money, time, or stops.
_Avoid_: Requirement

**Substitution Preference**:
A user preference that controls which substitutions are acceptable, such as brand flexibility, size flexibility, store brand acceptance, or required dietary tags. Substitution preferences can exist as global user defaults or per-item overrides and may include both product requirements and product preferences.
_Avoid_: Filter, setting

**Stock Availability**:
Whether a product listing is currently believed to be available at a store.
_Avoid_: Inventory count

**Proposed Plan**:
An app-generated plan for fulfilling a grocery list, including stores, item assignments, route, planned start time, estimated cost metrics, one primary recommendation, and optional alternatives.
_Avoid_: Itinerary, shopping trip

**Best Balance**:
The default primary recommendation for a proposed plan. It satisfies product requirements, honors product preferences, avoids unavailable items, uses data that meets freshness and confidence thresholds, minimizes total trip cost, and penalizes excessive stops or time.
_Avoid_: Cheapest, fastest

**Freshness Threshold**:
An app-defined minimum recency required for price, stock, or store data to be used in a primary recommendation.
_Avoid_: Expiration date

**Confidence Threshold**:
An app-defined minimum trust level required for product mappings or data observations to be used in a primary recommendation.
_Avoid_: Accuracy score

**Uncertain Override**:
A user-approved use of an uncertain product match or data observation that remains excluded from the primary recommendation and is clearly marked as uncertain.
_Avoid_: Force include

**Plan Metrics**:
The estimated values used to explain a proposed plan, including total estimated cost, grocery subtotal, travel cost, total time, number of stops, and estimated savings. Advanced details may include data freshness, per-store subtotals, and confidence notes.
_Avoid_: Analytics

**Freshness Label**:
A user-facing summary of how recently price, stock, or store data was checked, such as prices updated today or stock checked just now.
_Avoid_: Confidence score

**Plan Alternative**:
A non-primary proposed plan optimized for a specific trade-off, such as cheapest, fastest, or fewest stops.
_Avoid_: Secondary route

**Planned Start Time**:
The time a user intends to begin a proposed plan. It defaults to now but may be set to a future time.
_Avoid_: Schedule time

**Stop**:
A store visit within a proposed plan.
_Avoid_: Destination

**Needed Amount**:
The total amount of a product family the user wants to buy, expressed with a quantity and unit such as 2 gallons, 5 pounds, or 12 count.
_Avoid_: Item count

**Package Flexibility**:
Whether a needed amount can be satisfied by different package sizes or combinations, such as two 1-gallon containers or four half-gallon containers.
_Avoid_: Quantity flexibility

**Item Assignment**:
The assignment of a grocery list item to a specific stop in a proposed plan.
_Avoid_: Pick task

**Store Hours**:
The times when a store is open for shopping or fulfillment. Store hours affect whether a proposed plan is viable and how it is ranked.
_Avoid_: Business hours

**Store Candidate**:
A possible store discovered from source data that has not yet been accepted as a trusted store. Store candidates require review before they can affect user-facing recommendations.
_Avoid_: Store, retailer, source of truth

**Store Alias**:
An approved source-specific name for a trusted store, used to recognize future source data that refers to the same physical location.
_Avoid_: Duplicate store, alternate retailer

**Store Candidate Review**:
An internal review process for creating, linking, merging, marking retailer-only, or rejecting store candidates before they affect trusted store data.
_Avoid_: Automatic merge

**Route**:
The ordered path from the user's starting location through all stops and back to the ending location.
_Avoid_: Directions

**Compilation**:
The moment a grocery list is turned into a proposed plan using current product, price, stock, and route information.
_Avoid_: Checkout, submission
