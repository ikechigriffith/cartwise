import Link from 'next/link';

const API_BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:8000';
const ADMIN_API_TOKEN = process.env.ADMIN_API_TOKEN;

type ReviewGroup = {
  selection_key: string;
  canonical_product_count: number;
  product_family_count: number;
  current_listing_count: number;
  current_listing_product_count: number;
  historical_observation_count: number;
  historical_product_count: number;
  latest_seen_at: string | null;
  last_reviewed_at: string | null;
};

type Response = {
  total: number;
  limit: number;
  offset: number;
  items: ReviewGroup[];
};

async function getGroups(q: string | null, offset: number): Promise<Response> {
  const params = new URLSearchParams({ limit: '25', offset: String(offset) });
  if (q) params.set('q', q);
  const response = await fetch(`${API_BASE_URL}/admin/product-selection-reviews?${params}`, {
    cache: 'no-store',
    headers: ADMIN_API_TOKEN ? { 'x-admin-token': ADMIN_API_TOKEN } : {},
  });
  if (!response.ok) throw new Error(`Failed to load product review groups: ${response.status}`);
  return response.json();
}

function shortDate(value: string | null) {
  return value ? value.slice(0, 10) : '—';
}

export default async function ProductSelectionReviewsPage({ searchParams }: { searchParams: Promise<{ q?: string; offset?: string }> }) {
  const params = await searchParams;
  const q = params.q?.trim() || null;
  const offset = Number(params.offset ?? '0');
  const data = await getGroups(q, offset);
  const previousOffset = Math.max(0, offset - data.limit);
  const nextOffset = offset + data.limit;

  return (
    <main className="container">
      <Link href="/">← Home</Link>
      <h1>Product Selection Review Queue</h1>
      <p>Review normalized product groups before using them for user-facing product selection and proposed plans.</p>

      <form className="toolbar" action="/admin/product-selection-reviews">
        <label>Search<br /><input className="input" name="q" defaultValue={q ?? ''} placeholder="milo, rice, milk…" /></label>
        <button type="submit">Search</button>
      </form>

      <p className="muted">Showing {data.items.length.toLocaleString()} of {data.total.toLocaleString()} groups needing review.</p>

      <div className="table-wrap"><table>
        <thead>
          <tr>
            <th>Selection key</th>
            <th>Families</th>
            <th>Canonical products</th>
            <th>Current listings</th>
            <th>Historical observations</th>
            <th>Latest seen</th>
            <th>Last reviewed</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((group) => (
            <tr key={group.selection_key}>
              <td><Link href={`/admin/product-selection-reviews/${encodeURIComponent(group.selection_key)}`}>{group.selection_key}</Link></td>
              <td>{group.product_family_count.toLocaleString()}</td>
              <td>{group.canonical_product_count.toLocaleString()}</td>
              <td>{group.current_listing_count.toLocaleString()} across {group.current_listing_product_count.toLocaleString()} products</td>
              <td>{group.historical_observation_count.toLocaleString()} across {group.historical_product_count.toLocaleString()} products</td>
              <td>{shortDate(group.latest_seen_at)}</td>
              <td>{shortDate(group.last_reviewed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table></div>

      <nav className="toolbar" aria-label="Pagination">
        {offset > 0 ? <Link href={`/admin/product-selection-reviews?${q ? `q=${encodeURIComponent(q)}&` : ''}offset=${previousOffset}`}>← Previous</Link> : <span className="muted">← Previous</span>}
        {nextOffset < data.total ? <Link href={`/admin/product-selection-reviews?${q ? `q=${encodeURIComponent(q)}&` : ''}offset=${nextOffset}`}>Next →</Link> : <span className="muted">Next →</span>}
      </nav>
    </main>
  );
}
