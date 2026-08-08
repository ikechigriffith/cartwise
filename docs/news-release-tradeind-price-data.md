# News Release: Turning Public Supermarket Price Publications into Actionable Grocery Intelligence for Trinidad & Tobago

**FOR IMMEDIATE RELEASE**  
**Project:** Grocery price intelligence platform for Trinidad & Tobago  
**Data source:** Ministry of Trade and Industry / Consumer Affairs Division supermarket price publications  
**Imported period:** January 2018 to March 2025  

## Summary

As part of building a grocery price comparison platform for Trinidad & Tobago, we imported and structured public supermarket price data published by the Ministry of Trade and Industry / Consumer Affairs Division.

The work transformed years of monthly spreadsheet publications into a searchable database of supermarket price observations that can support price comparison, inflation tracking, consumer education, food affordability analysis, and future grocery basket optimization.

## What Was Imported

We discovered **130 public supermarket price-related documents** and identified **101 Excel workbook links**. Of those, **84 structured workbook files** were successfully parsed and imported into the database.

The import produced:

- **311,948 supermarket price observations**
- **284 canonical grocery products**
- Coverage from **January 2018 through March 2025**
- **127,728 observations matched directly to known store records**
- **50,983 observations matched to a retailer only**
- **133,237 observations retained as unmatched raw supermarket labels for future review**

Each imported observation preserves the original source URL, workbook file, month, region, area, supermarket label, item name, brand, size, price, and matching confidence.

## Documents Imported

| Month | Observations | Source document |
|---|---:|---|
| 2025-03 | 4,068 | <https://tradeind.gov.tt/wp-content/uploads/2025/04/March-2025-RPS-Publication.xlsx> |
| 2024-12 | 3,956 | <https://tradeind.gov.tt/wp-content/uploads/2024/12/December-2024-RPS.xlsx> |
| 2024-11 | 4,041 | <https://tradeind.gov.tt/wp-content/uploads/2024/12/November-2024-RPS-Publication-All-Items-Final.xlsx> |
| 2024-10 | 4,111 | <https://tradeind.gov.tt/wp-content/uploads/2024/10/October-2024-RPS-Publication.xlsx> |
| 2024-09 | 4,221 | <https://tradeind.gov.tt/wp-content/uploads/2024/09/September-2024-RPS-Publication.xlsx> |
| 2024-08 | 3,828 | <https://tradeind.gov.tt/wp-content/uploads/2024/09/August-2024-RPS-Publication-All-Items-Final.xlsx> |
| 2024-07 | 3,872 | <https://tradeind.gov.tt/wp-content/uploads/2024/07/July-2024-RPS-Publication-All-Items-Final.xlsx> |
| 2024-06 | 4,351 | <https://tradeind.gov.tt/wp-content/uploads/2024/06/Supermarket-RPS-June-2024.xlsx> |
| 2024-05 | 4,284 | <https://tradeind.gov.tt/wp-content/uploads/2024/06/May-2024-RPS.xlsx> |
| 2024-04 | 4,068 | <https://tradeind.gov.tt/wp-content/uploads/2024/05/RPS-April-2024.xlsx> |
| 2024-03 | 4,249 | <https://tradeind.gov.tt/wp-content/uploads/2024/04/RPS-March-2024.xlsx> |
| 2024-02 | 4,234 | <https://tradeind.gov.tt/wp-content/uploads/2024/02/RPS-February-2024.xlsx> |
| 2024-01 | 4,252 | <https://tradeind.gov.tt/wp-content/uploads/2024/01/January-2024-RPS.xlsx> |
| 2023-12 | 4,285 | <https://tradeind.gov.tt/wp-content/uploads/2023/12/December-Retail-Prices.xlsx> |
| 2023-11 | 4,246 | <https://tradeind.gov.tt/wp-content/uploads/2023/12/November-RPS-Publication-All-Items-Final.xlsx> |
| 2023-10 | 4,289 | <https://tradeind.gov.tt/wp-content/uploads/2023/10/Supermarket-Prices-October-2023.xlsx> |
| 2023-09 | 4,336 | <https://tradeind.gov.tt/wp-content/uploads/2023/09/Supermarket-Prices-September.xlsx> |
| 2023-08 | 4,469 | <https://tradeind.gov.tt/wp-content/uploads/2023/08/Supermarket-Prices-August-2023.xlsx> |
| 2023-07 | 4,381 | <https://tradeind.gov.tt/wp-content/uploads/2023/07/Supermarket-Prices-July2023.xlsx> |
| 2023-06 | 4,410 | <https://tradeind.gov.tt/wp-content/uploads/2023/06/Supermarket-Prices-June-2023.xlsx> |
| 2023-05 | 4,371 | <https://tradeind.gov.tt/wp-content/uploads/2023/05/Supermarket-Prices-May-2023.xlsx> |
| 2023-04 | 4,385 | <https://tradeind.gov.tt/wp-content/uploads/2023/05/Supermarket-PricesApril.xlsx> |
| 2023-03 | 4,325 | <https://tradeind.gov.tt/wp-content/uploads/2023/03/Supermarket-Prices-March-2023.xlsx> |
| 2023-02 | 4,256 | <https://tradeind.gov.tt/wp-content/uploads/2023/03/Supermarket-Prices-Feb2023.xlsx> |
| 2023-01 | 4,268 | <https://tradeind.gov.tt/wp-content/uploads/2023/01/Supermarket-Prices-January-2023.xlsx> |
| 2022 | 50,091 | 12 monthly workbook imports from Jan-Dec 2022 |
| 2021 | 42,699 | 12 monthly workbook imports from Jan-Dec 2021 |
| 2020 | 33,218 | 10 workbook imports from Feb-Dec 2020 |
| 2019 | 41,867 | 13 workbook imports, including October Divali 2019 |
| 2018 | 38,517 | 12 monthly workbook imports from Jan-Dec 2018 |

A full machine-readable source list can be regenerated from the `product_price_observations` table by grouping on `source_url`.

## How the Data Was Extracted

The data pipeline was implemented in `apps/api/scripts/import_tradeind_price_data.py`.

The process was:

1. **Discover publications**  
   The Ministry of Trade and Industry website was queried through its public WordPress API for supermarket price publications.

2. **Extract document links**  
   The importer scanned post content for downloadable files, including direct links and encoded links embedded in page-builder shortcode content.

3. **Download Excel files**  
   Excel files were downloaded into `data/tradeind/raw` for reproducibility and auditability.

4. **Infer observation month**  
   The month and year were inferred from publication titles and document URLs.

5. **Parse workbook structure**  
   The workbooks generally contain regional sheets such as West, North, East, Central, South, and Tobago. The parser identifies the header row, reads supermarket columns, and extracts item, brand, size, supermarket label, area, region, and price.

6. **Normalize products**  
   Product families and canonical products were created from the item, brand, and size fields. Package parsing was used where possible to compute price-per-unit values.

7. **Match supermarkets to existing stores**  
   Supermarket labels from the spreadsheets were compared against existing store records using conservative fuzzy matching. Where a specific store could not be confidently matched, the importer attempted retailer-level matching for chains such as Massy Stores, Tru Valu, Xtra Foods, JTA, Persad's, Penny Savers, Cost Cutters, Food Basket, and others.

8. **Preserve provenance**  
   Every imported price observation stores the original source URL and raw spreadsheet values so future reviewers can trace each database row back to the public source document.

## Why This Data Matters

This dataset is valuable because it transforms public information into practical intelligence.

For consumers, it can help answer questions such as:

- Where can I buy my grocery basket for the lowest total cost?
- Which supermarkets are consistently cheaper for staple items?
- How have prices changed over time?
- Are prices different by region?
- Which products have the largest price variation across stores?

For policymakers and researchers, it can support:

- Food inflation monitoring
- Cost-of-living analysis
- Regional affordability studies
- Consumer protection work
- Market competition analysis
- Evidence-based social support planning

For entrepreneurs and civic technologists, it creates a foundation for:

- Grocery comparison apps
- Price alert tools
- Household budgeting tools
- Nutrition and affordability dashboards
- Open data visualizations

## Challenges Encountered and How They Were Addressed

### 1. Publications were not exposed as a clean open dataset

The data was available as monthly website posts and downloadable files, not as a single API or structured open data feed.

**How we addressed it:**  
We used the public WordPress API, extracted links from post content, and downloaded the source workbooks for repeatable processing.

### 2. Document links appeared in multiple formats

Some links were direct Excel URLs, while others were embedded inside encoded page-builder shortcode fields.

**How we addressed it:**  
The importer included URL cleanup and extraction logic for both direct links and encoded shortcode links.

### 3. Workbook layouts changed over time

Different years used slightly different spreadsheet formats. Header rows were not always in the same place.

**How we addressed it:**  
The parser searches for the row containing expected labels such as `No.` and `ITEMS`, instead of assuming one fixed row number.

### 4. Store names were inconsistent

The same supermarket could appear under different labels, abbreviations, spelling variations, or location-specific names.

Examples include chain-level names, branch-level names, and spelling differences such as Cost Cutters / Coss Cutters.

**How we addressed it:**  
We used conservative fuzzy matching against the existing store database and retained match confidence values. When store-level matching was uncertain, we fell back to retailer-level matching where possible.

### 5. Some observations could not be matched safely

A large number of rows still have raw supermarket names that need human review before being attached to a specific store.

**How we addressed it:**  
Rather than forcing inaccurate matches, the importer preserves unmatched observations with raw labels, regions, and areas. This keeps the data usable while protecting accuracy and trust.

### 6. Historical files included non-standard or special-purpose workbooks

Some publications were Christmas or Divali lists, and some older or PDF-era files are less standardized.

**How we addressed it:**  
The current import focuses on structured Excel workbooks. Non-standard files remain candidates for a future specialized parser or manual review.

## Nation-Building Opportunity: Making This Data More Useful for Everyone

This work shows that Trinidad & Tobago already has valuable public consumer price data. The next step is to make it easier for citizens, researchers, businesses, and civic builders to use it.

Recommended improvements:

1. **Publish a structured open data feed**  
   Release supermarket price data as CSV, JSON, and API endpoints in addition to PDFs and spreadsheets.

2. **Use stable supermarket identifiers**  
   Assign each supermarket branch a unique ID so prices can be tracked accurately over time, even if display names change.

3. **Use stable product identifiers**  
   Publish product categories, brands, package sizes, and units in standardized fields.

4. **Include geocoded store locations**  
   Add latitude, longitude, address, region, and area for each supermarket branch.

5. **Publish historical archives in one place**  
   Provide a single downloadable archive of all monthly price observations.

6. **Add data dictionaries and licensing terms**  
   Clearly document what each field means and how the public may reuse the data.

7. **Offer a simple public API**  
   A public API would allow developers to build grocery comparison tools, dashboards, and research applications without scraping website pages.

8. **Publish validation metadata**  
   Include collection date, survey method, store participation notes, and whether prices are regular prices, specials, or promotional prices.

9. **Encourage civic collaboration**  
   Government, universities, consumer groups, and local developers could collaborate to improve data quality, store matching, product normalization, and public dashboards.

## Closing Statement

The import of more than 300,000 supermarket price observations demonstrates the power of turning public documents into structured, reusable national data infrastructure.

With better publication formats and stable identifiers, this data can help households make better spending decisions, support evidence-based policy, and create opportunities for local innovation around food affordability and consumer protection.
