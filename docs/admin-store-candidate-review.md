# Admin Store Candidate Review

The store-candidate review workflow is the bridge between raw source labels and trusted app data.

## Principle

`stores` is the source of truth for the app. `store_candidates` is a staging queue only. A candidate must be reviewed before it can affect user-facing grocery recommendations.

## Admin access

Admin endpoints are under:

```txt
/admin/store-candidates
```

The API supports optional token protection. If `ADMIN_API_TOKEN` is set on the API process, admin requests must include:

```txt
X-Admin-Token: <token>
```

The Next.js admin pages/actions read the same `ADMIN_API_TOKEN` server-side and forward it to the API.

## UI

Admin pages:

```txt
/apps/web/app/admin/store-candidates
/apps/web/app/admin/store-candidates/[id]
```

Features:

- status filter
- free-text search by store label, normalized label, area, or region
- pagination
- observation-count prioritization
- status badges
- candidate detail/evidence
- sample observations
- confirmation prompts before destructive/backfill actions

## Review actions

### Link to existing store

Use when the candidate is an alias for a known physical store.

Effects:

- creates/updates `store_aliases`
- marks candidate `approved_existing_store`
- backfills matching `product_price_observations.store_id`
- writes `store_candidate_reviews`

### Create new store

Use when the candidate is a real store missing from the trusted DB.

Effects:

- creates `stores`
- creates `store_aliases`
- marks candidate `approved_created_store`
- backfills matching observations
- writes `store_candidate_reviews`

### Mark retailer-only

Use when the label is valid but not precise enough to identify a branch.

Effects:

- marks candidate `approved_retailer_only`
- does not backfill `store_id`
- writes `store_candidate_reviews`

### Reject

Use for noisy, malformed, or unusable labels.

Effects:

- marks candidate `rejected`
- writes `store_candidate_reviews`

## Backfill matching rule

Backfills use exact provenance fields:

```txt
source in ('tradeind_xlsx', 'tradeind_pdf_text')
raw_store_name
raw_area
raw_region
```

This avoids linking unrelated historical observations.

## Validation

Current automated checks:

```bash
cd apps/api
PYTHONPATH=. DATABASE_URL=postgresql+psycopg://groceries:change-me@localhost:5432/groceries uv run pytest -q
```

Current web build check:

```bash
pnpm --filter groceries-web build
```

Playwright smoke screenshots are written to:

```txt
data/ui-smoke/store-candidates-list.png
data/ui-smoke/store-candidate-detail.png
```
