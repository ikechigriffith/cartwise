import Link from 'next/link';
import { createStore, linkExistingStore, markRetailerOnly, rejectCandidate } from '../actions';
import { ConfirmSubmitButton } from './ConfirmSubmitButton';

const API_BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:8000';
const ADMIN_API_TOKEN = process.env.ADMIN_API_TOKEN;

type Candidate = {
  id: string;
  raw_store_name: string;
  normalized_name: string;
  raw_area: string | null;
  raw_region: string | null;
  retailer_id: string | null;
  retailer_name: string | null;
  matched_store_id: string | null;
  matched_store_name: string | null;
  status: string;
  confidence: number | null;
  observations_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  evidence: Record<string, unknown> | null;
  notes: string | null;
};

type Observation = {
  id: string;
  observed_at: string;
  price: number;
  raw_item_name: string | null;
  raw_store_name: string | null;
  raw_area: string | null;
  raw_region: string | null;
  source: string;
  source_url: string | null;
};

type Store = {
  id: string;
  name: string;
  retailer_name: string | null;
  address: Record<string, unknown> | null;
  latitude: number | null;
  longitude: number | null;
};
type SuggestedStoreMatch = {
  store_id: string;
  store_name: string;
  retailer_name: string | null;
  address: Record<string, unknown> | null;
  latitude: number | null;
  longitude: number | null;
  score: number;
  distance_km: number | null;
  reasons: string[];
};
type Retailer = { id: string; name: string };

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: 'no-store',
    headers: path.startsWith('/admin/') && ADMIN_API_TOKEN ? { 'x-admin-token': ADMIN_API_TOKEN } : {},
  });
  if (!response.ok) throw new Error(`Failed to load ${path}: ${response.status}`);
  return response.json();
}

function shortDate(value: string | null) {
  return value ? value.slice(0, 10) : '—';
}

function formatAddress(address: Record<string, unknown> | null) {
  if (!address) return null;
  const text = address.text ?? address.display_name ?? address.address ?? address.street ?? address.city;
  return typeof text === 'string' && text.trim().length ? text : null;
}

function storeOptionLabel(store: Store) {
  const parts = [
    store.retailer_name ? `${store.retailer_name} — ${store.name}` : store.name,
    formatAddress(store.address),
    store.latitude != null && store.longitude != null ? `${store.latitude.toFixed(5)}, ${store.longitude.toFixed(5)}` : null,
  ].filter(Boolean);
  return parts.join(' | ');
}

export default async function StoreCandidateDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const detail = await getJson<{ candidate: Candidate; suggested_store_matches: SuggestedStoreMatch[]; sample_observations: Observation[] }>(`/admin/store-candidates/${id}`);
  const stores = await getJson<{ items: Store[] }>(`/stores?limit=500`);
  const retailers = await getJson<{ items: Retailer[] }>(`/retailers?limit=500`);
  const candidate = detail.candidate;

  return (
    <main className="container">
      <Link href="/admin/store-candidates">← Store candidates</Link>
      <h1>{candidate.raw_store_name}</h1>
      <p><strong>{candidate.raw_area ?? 'Unknown area'}</strong> / {candidate.raw_region ?? 'Unknown region'} <span className={`badge ${candidate.status}`}>{candidate.status}</span></p>

      <section className="card">
        <h2>Candidate evidence</h2>
        <dl style={{ display: 'grid', gridTemplateColumns: '12rem 1fr', gap: '0.5rem' }}>
          <dt>Status</dt><dd>{candidate.status}</dd>
          <dt>Observations</dt><dd>{candidate.observations_count.toLocaleString()}</dd>
          <dt>First seen</dt><dd>{shortDate(candidate.first_seen_at)}</dd>
          <dt>Last seen</dt><dd>{shortDate(candidate.last_seen_at)}</dd>
          <dt>Confidence</dt><dd>{candidate.confidence?.toFixed(3) ?? '—'}</dd>
          <dt>Suggested retailer</dt><dd>{candidate.retailer_name ?? candidate.retailer_id ?? '—'}</dd>
          <dt>Matched store</dt><dd>{candidate.matched_store_name ?? candidate.matched_store_id ?? '—'}</dd>
          <dt>Notes</dt><dd>{candidate.notes ?? '—'}</dd>
        </dl>
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Suggested existing store matches</h2>
        <p className="muted">Suggestions use retailer/name similarity, source area text, and approximate distance from the source area to existing store coordinates. They are advisory only; an admin must still approve the match.</p>
        {detail.suggested_store_matches.length ? (
          <div className="table-wrap"><table>
            <thead><tr><th style={th}>Store</th><th style={th}>Address / coordinates</th><th style={th}>Score</th><th style={th}>Distance</th><th style={th}>Why suggested</th></tr></thead>
            <tbody>
              {detail.suggested_store_matches.map((match) => (
                <tr key={match.store_id}>
                  <td style={td}>{match.retailer_name ? `${match.retailer_name} — ` : ''}{match.store_name}</td>
                  <td style={td}>{formatAddress(match.address) ?? '—'}<br /><span className="muted">{match.latitude != null && match.longitude != null ? `${match.latitude.toFixed(5)}, ${match.longitude.toFixed(5)}` : 'No coordinates'}</span></td>
                  <td style={td}>{match.score.toFixed(3)}</td>
                  <td style={td}>{match.distance_km != null ? `${match.distance_km.toFixed(2)} km` : '—'}</td>
                  <td style={td}>{match.reasons.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table></div>
        ) : <p>No suggested existing-store matches found.</p>}
      </section>

      <section className="grid" style={{ marginTop: '1rem' }}>
        <form action={linkExistingStore.bind(null, candidate.id)} className="card">
          <h2>Link to existing store</h2>
          <label>Store<br />
            <select name="store_id" required className="input">
              <option value="">Select store…</option>
              {stores.items.map((store) => <option key={store.id} value={store.id}>{storeOptionLabel(store)}</option>)}
            </select>
          </label>
          <label>Notes<br /><textarea name="notes" className="input" /></label>
          <p className="muted">Tip: coordinates are shown in the dropdown. Use them to distinguish branches with similar names.</p>
          <ConfirmSubmitButton message="Approve this alias, link it to the selected store, and backfill all matching historical observations?">Approve existing store + backfill</ConfirmSubmitButton>
        </form>

        <form action={createStore.bind(null, candidate.id)} className="card">
          <h2>Create new store</h2>
          <label>Retailer<br />
            <select name="retailer_id" required defaultValue={candidate.retailer_id ?? ''} className="input">
              <option value="">Select retailer…</option>
              {retailers.items.map((retailer) => <option key={retailer.id} value={retailer.id}>{retailer.name}</option>)}
            </select>
          </label>
          <label>Store name<br /><input name="name" required defaultValue={candidate.raw_store_name} className="input" /></label>
          <label>Address / location note<br /><input name="address" defaultValue={[candidate.raw_area, candidate.raw_region].filter(Boolean).join(', ')} className="input" /></label>
          <label>Latitude<br /><input name="latitude" required type="number" step="any" className="input" /></label>
          <label>Longitude<br /><input name="longitude" required type="number" step="any" className="input" /></label>
          <label>Notes<br /><textarea name="notes" className="input" /></label>
          <ConfirmSubmitButton message="Create a new trusted store and backfill all matching historical observations?">Create store + backfill</ConfirmSubmitButton>
        </form>

        <form action={markRetailerOnly.bind(null, candidate.id)} className="card">
          <h2>Mark retailer-only</h2>
          <p>Use when the label is valid but not precise enough for a branch.</p>
          <label>Notes<br /><textarea name="notes" required className="input" /></label>
          <ConfirmSubmitButton message="Mark this candidate as retailer-only? No store backfill will be performed." className="secondary">Mark retailer-only</ConfirmSubmitButton>
        </form>

        <form action={rejectCandidate.bind(null, candidate.id)} className="card">
          <h2>Reject</h2>
          <p>Use for bad, noisy, or non-useful source labels.</p>
          <label>Notes<br /><textarea name="notes" required className="input" /></label>
          <ConfirmSubmitButton message="Reject this candidate and remove it from the review queue?" className="danger">Reject candidate</ConfirmSubmitButton>
        </form>
      </section>

      <section className="card" style={{ marginTop: '1rem' }}>
        <h2>Sample observations</h2>
        <div className="table-wrap"><table>
          <thead><tr><th style={th}>Observed</th><th style={th}>Item</th><th style={th}>Price</th><th style={th}>Source</th></tr></thead>
          <tbody>
            {detail.sample_observations.map((observation) => (
              <tr key={observation.id}>
                <td style={td}>{shortDate(observation.observed_at)}</td>
                <td style={td}>{observation.raw_item_name}</td>
                <td style={td}>TTD {observation.price?.toFixed(2)}</td>
                <td style={td}>{observation.source_url ? <a href={observation.source_url}>{observation.source}</a> : observation.source}</td>
              </tr>
            ))}
          </tbody>
        </table></div>
      </section>
    </main>
  );
}

const th = { textAlign: 'left' as const };
const td = { verticalAlign: 'top' as const };
