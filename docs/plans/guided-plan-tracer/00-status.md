# Status: Guided plan tracer

- Gate 1 — Product: APPROVED 2026-08-08
- Gate 2 — Architecture: in progress
- Gate 3 — Program Design: pending
- Gate 4 — Slice plan: pending

## Slices
- [ ] Slice 1 — tracer bullet: pending Gate 4

## Notes for a fresh session
- Goal is to pivot from horizontal data/admin work to one visible, end-to-end guided grocery-plan flow using a deliberately small trusted catalog.
- Gate 1 layout: individual-item comparison uses a compact item overview, Amazon-style left filter sidebar, offer table, price-first sort, location links, and an adaptive top flag (CHEAPEST or NEAREST). Layout may be refined later.
- Gate 1 approved: users may search broadly, but must select an exact product before comparing offers or adding it to a list. Guests can compare individual exact items only; signing in is required to create a persistent grocery list and receive a guided plan.
- Gate 2 will make the exact canonical product authoritative for new list items while retaining the current product-family reference for existing data. Product photos are required for searchable product cards and will be stored from retailer-source data. Clerk provides managed passwordless email-link and Google sign-in. Authenticated users own persistent lists and saved one-stop guided plans. A local user is matched by the verified Clerk subject. No implementation work is approved for this feature yet.
