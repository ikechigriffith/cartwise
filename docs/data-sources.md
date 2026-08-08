# Data Sources

## Trinidad & Tobago store seed data

Initial grocery store data is seeded from OpenStreetMap using the Overpass API, with a manual seed path for major retailers that are missing from the imported OSM shop categories.

Query scope:
- Country: Trinidad & Tobago (`ISO3166-1=TT`)
- OSM shop tags:
  - `supermarket`
  - `convenience`
  - `greengrocer`
  - `general`

Seed behavior:
- OSM nodes, ways, and relations are converted into `Store` rows.
- Store coordinates come from node coordinates or way/relation centers.
- Store address and contact data come from OSM tags when present.
- `Retailer` rows are derived from OSM `brand`, OSM `operator`, known chain names, or cleaned store names.
- Conservative retailer normalization is applied for known variants such as `Massy` → `Massy Stores`, `Jta` → `JTA Supermarkets`, `Tru-Valu` → `Tru Valu`, and `Np` → `National Petroleum`.
- Source attribution is stored on each `Store` via `externalSource = osm`, `externalId`, and `rawTags`.
- Re-running the seed script refreshes existing stores by `externalSource + externalId`, inserts newly seen stores, and marks missing OSM stores as inactive and needing review rather than deleting them.

## Retailer scrape candidates

`apps/api/scripts/seed_retailer_data_sources.py` seeds candidate retailer websites into `retailer_data_sources`.

`apps/api/scripts/check_retailer_data_sources.py` uses Playwright to perform an initial scrape feasibility check. It records whether a source appears to have a product catalog, visible prices, stock signals, login/membership signals, and useful API/network signals.

Current first-pass statuses:
- PriceSmart: strong candidate; catalog, price, stock, login, and API signals detected. Grocery products can currently be imported from `https://www.pricesmart.com/api/br_discovery/getProductsByKeyword` without using credentials.
- JTA Supermarkets: strong candidate; catalog and price signals detected, but needs product-level verification.
- Massy Stores: likely candidate; catalog signals detected, price not confirmed on initial page.
- SuperPharm: likely candidate; catalog/API signals detected, price not confirmed on initial page.
- Xtra Foods: needs verification; initial Playwright navigation timed out.
- Persad's D' Food King: needs verification; initial Playwright navigation timed out.

## Ministry of Trade and Industry price publications

`apps/api/scripts/import_tradeind_price_data.py` discovers Ministry of Trade and Industry / Consumer Affairs Division supermarket price publications from the WordPress API, downloads Excel workbooks, parses regional supermarket price sheets, creates product price observations, and attempts conservative matching to existing `Store`/`Retailer` records.

Current Excel import result:
- 130 published documents discovered
- 101 Excel workbook links discovered/downloaded
- 84 structured workbook documents imported into price observations
- 311,948 price observations imported
- 284 canonical products represented
- observed period: January 2018 through March 2025
- 127,728 observations matched directly to a store in our database
- 50,983 observations matched to a retailer only
- 133,237 observations remain unmatched and need store-alias review

`apps/api/scripts/import_tradeind_pdf_price_data.py` imports the text-based PDF booklet era using `pypdf`, explicit section/column mappings, and the same `product_price_observations` table with source `tradeind_pdf_text`.

Current PDF import result:
- 20 regular PDF booklet documents imported
- 70,042 price observations imported
- 518 canonical products represented
- observed period: April 2016 through December 2017
- 28,432 observations matched directly to a store in our database
- 8,088 observations matched to a retailer only
- 33,522 observations remain unmatched and need store-alias review

Combined Ministry import coverage is now 381,990 observations from April 2016 through March 2025. Special-purpose PDFs (Christmas/budget/media-release documents) and some non-standard layouts still need separate parsing/review. The importers preserve raw region, area, store label, item, brand, size, source URL, and source file metadata for auditability.

Import tracking and review workflow:
- `source_documents` records discovered Ministry documents, file type, observed month, local file path/hash when downloaded, import status, and imported observation counts.
- `import_runs` records import/tracking run summaries.
- `store_candidates` records unmatched Ministry supermarket labels by raw store name + area + region for review before creating verified `Store` rows.
- `store_aliases` records approved source-specific raw labels that should resolve to an existing trusted `Store`.
- `store_candidate_reviews` records human review decisions, including created/linked stores, changed fields, reviewer, notes, and number of observations backfilled.
- `apps/api/scripts/sync_tradeind_import_tracking.py` backfills/syncs these review tables from discovered documents and imported observations.
- Admin API endpoints under `/admin/store-candidates` list candidates, show candidate detail/sample observations, create a store from a candidate, link a candidate to an existing store, mark retailer-only, or reject a candidate.
- See `docs/admin-store-candidate-review.md` for the approval workflow, admin token behavior, and validation commands.

Current review-table sync result:
- 124 Ministry source documents tracked: 84 imported XLSX, 20 imported PDFs, 12 discovered/unimported XLSX, 8 discovered/unimported PDFs.
- 101 store-candidate rows requiring review. These are raw label + area + region combinations from observations that did not match an existing store.

## PriceSmart grocery import

`apps/api/scripts/import_pricesmart_groceries.py` imports PriceSmart Trinidad & Tobago grocery listings from the PriceSmart/Bloomreach product discovery endpoint.

Current import behavior:
- category: Groceries (`G10D03`)
- source: `pricesmart_api`
- currency: `TTD`
- price source field: `price_TT`
- stock source field: `inventory_TT`
- creates/updates product families, canonical products, store-specific product listings, and approved high-confidence mappings
- applies the same PriceSmart online price to all active PriceSmart Trinidad & Tobago stores until we confirm whether prices differ by club

## Manual major-retailer seed data

`apps/api/scripts/seed_manual_tt_stores.py` currently seeds PriceSmart Trinidad & Tobago locations that were missing from the original OSM shop-category import because OSM classifies them as `shop=wholesale` rather than `shop=supermarket`.

Current manual PriceSmart stores:
- PriceSmart Chaguanas
- PriceSmart Debe
- PriceSmart Mausica
- PriceSmart Port of Spain

Manual stores use `externalSource = manual`, are marked active, and have `verifiedAt` set when seeded.

## SuperPharm grocery import

`apps/api/scripts/import_superpharm_groceries.py` imports SuperPharm's public grocery catalog and store network from its application API.

Current import behavior:
- category: Grocery (`546`) across 9 subcategories
- source: `superpharm_api`
- currency: `TTD`
- creates or refreshes the 11 SuperPharm Trinidad & Tobago stores, including public hours and coordinates
- imports product name, brand, description, package normalization, current price, image/API payload, pickup/delivery signals, and store-level stock availability
- creates/updates product families, canonical products, store-specific listings, and approved high-confidence retailer-SKU mappings
- marks listings absent from a later complete API refresh as out of stock rather than deleting them

Current import result:
- 434 grocery products
- 4,774 store-specific listings across 11 stores
- 1,884 listings currently marked in stock

License note:
OpenStreetMap data is available under the Open Database License (ODbL). If this data is used in the product, the app must provide appropriate attribution to OpenStreetMap contributors and comply with ODbL requirements.
