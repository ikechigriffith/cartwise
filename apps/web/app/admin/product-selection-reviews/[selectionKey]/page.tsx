import Link from 'next/link';
import { approveProductFamily } from '../actions';
import { ConfirmSubmitButton } from './ConfirmSubmitButton';

const API_BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:8000';
const ADMIN_API_TOKEN = process.env.ADMIN_API_TOKEN;

type CanonicalProduct = {
  id: string;
  canonical_name: string;
  brand: string | null;
  normalized_brand: string | null;
  selection_key: string;
  size_value: number | null;
  size_unit: string | null;
  package_quantity: number | null;
  product_family_id: string;
  product_family_name: string;
  current_listing_count: number;
  in_stock_listing_count: number;
  current_min_price: number | null;
  latest_price_checked_at: string | null;
  historical_observation_count: number;
  latest_historical_observed_at: string | null;
};

type CurrentListing = {
  id: string;
  raw_name: string;
  raw_brand: string | null;
  price: number | null;
  currency: string;
  stock_availability: string | null;
  price_checked_at: string | null;
  store_name: string;
  retailer_name: string;
  canonical_product_id: string;
  canonical_name: string;
};

type HistoricalObservation = {
  id: string;
  raw_item_name: string | null;
  price: number;
  currency: string;
  observed_at: string;
  raw_store_name: string | null;
  raw_area: string | null;
  raw_region: string | null;
  source: string;
  canonical_product_id: string;
  canonical_name: string;
};

type Review = {
  id: string;
  action: string;
  product_family_id: string | null;
  reviewed_at: string;
  canonical_products_updated: number;
  notes: string | null;
};

type Detail = {
  selection_key: string;
  canonical_products: CanonicalProduct[];
  current_listings: CurrentListing[];
  historical_observations: HistoricalObservation[];
  reviews: Review[];
};

async function getDetail(selectionKey: string): Promise<Detail> {
  const response = await fetch(`${API_BASE_URL}/admin/product-selection-reviews/${encodeURIComponent(selectionKey)}`, {
    cache: 'no-store',
    headers: ADMIN_API_TOKEN ? { 'x-admin-token': ADMIN_API_TOKEN } : {},
  });
  if (!response.ok) throw new Error(`Failed to load product review group: ${response.status}`);
  return response.json();
}

function shortDate(value: string | null) {
  return value ? value.slice(0, 10) : '—';
}

function money(value: number | null, currency = 'TTD') {
  return value == null ? '—' : `${currency} ${Number(value).toFixed(2)}`;
}

function sizeLabel(product: CanonicalProduct) {
  const size = product.size_value != null && product.size_unit ? `${product.size_value} ${product.size_unit}` : null;
  const quantity = product.package_quantity != null ? `${product.package_quantity} pack` : null;
  return [quantity, size].filter(Boolean).join(' / ') || '—';
}

export default async function ProductSelectionReviewDetailPage({ params }: { params: Promise<{ selectionKey: string }> }) {
  const { selectionKey } = await params;
  const detail = await getDetail(selectionKey);
  const families = Array.from(new Map(detail.canonical_products.map((product) => [product.product_family_id, product.product_family_name])).entries());

  return (
    <main className="container">
      <Link href="/admin/product-selection-reviews">← Product selection reviews</Link>
      <h1>{detail.selection_key}</h1>
      <p className="muted">Choose the product family that should own these canonical products. This does not merge canonical products or delete source evidence.</p>

      <section className="card">
        <h2>Approve product family consolidation</h2>
        <form action={approveProductFamily.bind(null, detail.selection_key)}>
          <label>Target product family<br />
            <select name="product_family_id" required className="input">
              <option value="">Select product family…</option>
              {families.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
            </select>
          </label>
          <label>Notes<br /><textarea name="notes" className="input" placeholder="Why this family is correct…" /></label>
          <ConfirmSubmitButton message="Move all canonical products in this selection group to the selected product family?">Approve family consolidation</ConfirmSubmitButton>
        </form>
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Canonical products</h2>
        <div className="table-wrap"><table>
          <thead><tr><th>Canonical product</th><th>Brand</th><th>Size</th><th>Product family</th><th>Current listings</th><th>Historical observations</th></tr></thead>
          <tbody>
            {detail.canonical_products.map((product) => (
              <tr key={product.id}>
                <td>{product.canonical_name}</td>
                <td>{product.brand ?? '—'}</td>
                <td>{sizeLabel(product)}</td>
                <td>{product.product_family_name}</td>
                <td>{product.current_listing_count.toLocaleString()} ({product.in_stock_listing_count.toLocaleString()} in stock)<br /><span className="muted">Min {money(product.current_min_price)} · {shortDate(product.latest_price_checked_at)}</span></td>
                <td>{product.historical_observation_count.toLocaleString()}<br /><span className="muted">Latest {shortDate(product.latest_historical_observed_at)}</span></td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </section>

      <section className="grid" style={{ marginTop: '1rem' }}>
        <div className="card">
          <h2>Current listings</h2>
          <div className="table-wrap"><table>
            <thead><tr><th>Listing</th><th>Retailer / store</th><th>Price</th><th>Stock</th></tr></thead>
            <tbody>
              {detail.current_listings.map((listing) => (
                <tr key={listing.id}>
                  <td>{listing.raw_name}<br /><span className="muted">{listing.canonical_name}</span></td>
                  <td>{listing.retailer_name}<br /><span className="muted">{listing.store_name}</span></td>
                  <td>{money(listing.price, listing.currency)}<br /><span className="muted">{shortDate(listing.price_checked_at)}</span></td>
                  <td>{listing.stock_availability ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>

        <div className="card">
          <h2>Historical observations</h2>
          <div className="table-wrap"><table>
            <thead><tr><th>Observation</th><th>Source location</th><th>Price</th></tr></thead>
            <tbody>
              {detail.historical_observations.map((observation) => (
                <tr key={observation.id}>
                  <td>{observation.raw_item_name ?? observation.canonical_name}<br /><span className="muted">{observation.canonical_name}</span></td>
                  <td>{observation.raw_store_name ?? '—'}<br /><span className="muted">{[observation.raw_area, observation.raw_region].filter(Boolean).join(' / ') || '—'}</span></td>
                  <td>{money(observation.price, observation.currency)}<br /><span className="muted">{shortDate(observation.observed_at)} · {observation.source}</span></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Review history</h2>
        {detail.reviews.length ? (
          <div className="table-wrap"><table>
            <thead><tr><th>Action</th><th>Target family</th><th>Products updated</th><th>Reviewed</th><th>Notes</th></tr></thead>
            <tbody>
              {detail.reviews.map((review) => (
                <tr key={review.id}>
                  <td>{review.action}</td>
                  <td>{review.product_family_id ?? '—'}</td>
                  <td>{review.canonical_products_updated.toLocaleString()}</td>
                  <td>{shortDate(review.reviewed_at)}</td>
                  <td>{review.notes ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        ) : <p>No review history yet.</p>}
      </section>
    </main>
  );
}
