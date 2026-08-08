import Link from 'next/link';

const API_BASE_URL = process.env.API_BASE_URL ?? 'http://localhost:8000';
const ADMIN_API_TOKEN = process.env.ADMIN_API_TOKEN;

type Candidate = {
  id: string;
  raw_store_name: string;
  raw_area: string | null;
  raw_region: string | null;
  status: string;
  observations_count: number;
  first_seen_at: string | null;
  last_seen_at: string | null;
  matched_store_id: string | null;
};

type Response = {
  counts_by_status: Record<string, number>;
  total: number;
  limit: number;
  offset: number;
  items: Candidate[];
};

async function getCandidates(status: string | null, q: string | null, offset: number): Promise<Response> {
  const params = new URLSearchParams({ limit: '25', offset: String(offset) });
  if (status) params.set('status', status);
  if (q) params.set('q', q);
  const response = await fetch(`${API_BASE_URL}/admin/store-candidates?${params}`, {
    cache: 'no-store',
    headers: ADMIN_API_TOKEN ? { 'x-admin-token': ADMIN_API_TOKEN } : {},
  });
  if (!response.ok) throw new Error(`Failed to load candidates: ${response.status}`);
  return response.json();
}

function shortDate(value: string | null) {
  return value ? value.slice(0, 10) : '—';
}

export default async function StoreCandidatesPage({ searchParams }: { searchParams: Promise<{ status?: string; q?: string; offset?: string }> }) {
  const params = await searchParams;
  const status = params.status ?? 'needs_review';
  const q = params.q?.trim() || null;
  const offset = Number(params.offset ?? '0');
  const data = await getCandidates(status, q, offset);
  const previousOffset = Math.max(0, offset - data.limit);
  const nextOffset = offset + data.limit;
  const statuses = ['needs_review', 'approved_existing_store', 'approved_created_store', 'approved_retailer_only', 'rejected', 'all'];

  return (
    <main className="container">
      <Link href="/">← Home</Link>
      <h1>Store Candidate Approval Queue</h1>
      <p>Review Ministry of Trade and Industry store labels before merging them into trusted store data.</p>

      <form className="toolbar" action="/admin/store-candidates">
        <label>Search<br /><input className="input" name="q" defaultValue={q ?? ''} placeholder="Store, area, region…" /></label>
        <label>Status<br />
          <select className="input" name="status" defaultValue={status}>
            {statuses.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <button type="submit">Search</button>
      </form>

      <nav style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', margin: '1rem 0' }}>
        {statuses.map((item) => (
          <Link key={item} href={`/admin/store-candidates?status=${item}${q ? `&q=${encodeURIComponent(q)}` : ''}`} style={{ fontWeight: item === status ? 700 : 400 }}>
            {item} {item !== 'all' && data.counts_by_status[item] ? `(${data.counts_by_status[item]})` : ''}
          </Link>
        ))}
      </nav>

      <p className="muted">Showing {data.items.length.toLocaleString()} of {data.total.toLocaleString()} candidates.</p>

      <div className="table-wrap"><table>
        <thead>
          <tr>
            <th style={th}>Store label</th>
            <th style={th}>Area</th>
            <th style={th}>Region</th>
            <th style={th}>Observations</th>
            <th style={th}>Seen</th>
            <th style={th}>Status</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((candidate) => (
            <tr key={candidate.id}>
              <td style={td}><Link href={`/admin/store-candidates/${candidate.id}`}>{candidate.raw_store_name}</Link></td>
              <td style={td}>{candidate.raw_area ?? '—'}</td>
              <td style={td}>{candidate.raw_region ?? '—'}</td>
              <td style={td}>{candidate.observations_count.toLocaleString()}</td>
              <td style={td}>{shortDate(candidate.first_seen_at)} → {shortDate(candidate.last_seen_at)}</td>
              <td style={td}><span className={`badge ${candidate.status}`}>{candidate.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table></div>

      <nav className="toolbar" aria-label="Pagination">
        {offset > 0 ? <Link href={`/admin/store-candidates?status=${status}${q ? `&q=${encodeURIComponent(q)}` : ''}&offset=${previousOffset}`}>← Previous</Link> : <span className="muted">← Previous</span>}
        {nextOffset < data.total ? <Link href={`/admin/store-candidates?status=${status}${q ? `&q=${encodeURIComponent(q)}` : ''}&offset=${nextOffset}`}>Next →</Link> : <span className="muted">Next →</span>}
      </nav>
    </main>
  );
}

const th = { textAlign: 'left' as const };
const td = { verticalAlign: 'top' as const };
