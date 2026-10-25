import React from 'react';
import { createRoot } from 'react-dom/client';
import { createClient, type Session } from '@supabase/supabase-js';
import './style.css';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY as string | undefined;
const apiBase = ((import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api').replace(/\/$/, '');
const supabase = supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey, { auth: { autoRefreshToken: true, persistSession: true, detectSessionInUrl: false } })
  : null;

type Report = {
  id: string; sector: string; type: string; notes: string; timestamp: string;
  latitude?: number | null; longitude?: number | null; locationSource?: string | null;
  locationName?: string | null; receivedAt: string; reviewStatus: string;
  reviewNotes?: string | null; reviewedAt?: string | null;
};

const sampleReports: Report[] = [
  { id: 'demo-nest-001', sector: 'Panambur', type: 'Nest found', notes: 'Fresh crawl marks near the northern dune line; area cordoned for morning check.', timestamp: '2026-10-25T04:35:00Z', latitude: 12.95841, longitude: 74.80262, locationSource: 'gps', locationName: 'Current Location', receivedAt: '2026-10-25T04:40:00Z', reviewStatus: 'not_reviewed' },
  { id: 'demo-hatchlings-002', sector: 'Tannirbhavi', type: 'Hatchlings spotted', notes: 'Approximately 30 hatchlings moving toward the water. No artificial lights nearby.', timestamp: '2026-10-24T23:12:00Z', latitude: 12.90695, longitude: 74.80118, locationSource: 'gps', locationName: 'Tannirbhavi beach', receivedAt: '2026-10-24T23:18:00Z', reviewStatus: 'in_review', reviewNotes: 'Ranger follow-up requested at first light.' },
  { id: 'demo-disturbance-003', sector: 'Sasihithlu Delta', type: 'Beach disturbance', notes: 'Vehicle tracks close to the high-tide line.', timestamp: '2026-10-23T16:05:00Z', locationSource: 'preset', receivedAt: '2026-10-23T16:20:00Z', reviewStatus: 'verified', reviewNotes: 'Tracks documented; patrol informed.' },
];

function App() {
  const [session, setSession] = React.useState<Session | null>(null);
  const [restoring, setRestoring] = React.useState(Boolean(supabase));
  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [reports, setReports] = React.useState<Report[]>([]);
  const [selected, setSelected] = React.useState<Report | null>(null);
  const [sector, setSector] = React.useState('');
  const [status, setStatus] = React.useState('');
  const [search, setSearch] = React.useState('');
  const [reviewStatus, setReviewStatus] = React.useState('in_review');
  const [reviewNotes, setReviewNotes] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');
  const [notice, setNotice] = React.useState('');
  const [demoMode, setDemoMode] = React.useState(false);

  React.useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => { setSession(data.session); setRestoring(false); }).catch(() => { setSession(null); setRestoring(false); });
    const { data } = supabase.auth.onAuthStateChange((_event, next) => { setSession(next); setRestoring(false); });
    return () => data.subscription.unsubscribe();
  }, []);

  const loadReports = React.useCallback(async (token: string) => {
    setBusy(true); setError('');
    try {
      const response = await fetch(`${apiBase}/reports?limit=100`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error(await apiError(response));
      const data = await response.json() as Report[];
      setReports(data);
      setSelected((current) => current ? data.find((item) => item.id === current.id) ?? null : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load reports.');
    } finally { setBusy(false); }
  }, []);

  React.useEffect(() => {
    if (session) void loadReports(session.access_token);
    else { setReports([]); setSelected(null); }
  }, [session?.access_token, loadReports]);

  async function signIn(event: React.FormEvent) {
    event.preventDefault(); if (!supabase) return;
    setBusy(true); setError(''); setNotice('');
    const { error: authError } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
    if (authError) setError(authError.message);
    setBusy(false);
  }

  async function saveReview(event: React.FormEvent) {
    event.preventDefault(); if (!session || !selected) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const response = await fetch(`${apiBase}/reports/${encodeURIComponent(selected.id)}/review`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${session.access_token}` },
        body: JSON.stringify({ reviewStatus, reviewNotes }),
      });
      if (!response.ok) throw new Error(await apiError(response));
      const result = await response.json();
      setNotice(result.duplicate ? 'No review changes were needed.' : 'Review saved and recorded by the backend.');
      await loadReports(session.access_token);
    } catch (err) { setError(err instanceof Error ? err.message : 'Review was not saved.'); }
    finally { setBusy(false); }
  }

  if (demoMode) return <Dashboard reports={reports} selected={selected} setSelected={setSelected} search={search} setSearch={setSearch} sector={sector} setSector={setSector} status={status} setStatus={setStatus} reviewStatus={reviewStatus} setReviewStatus={setReviewStatus} reviewNotes={reviewNotes} setReviewNotes={setReviewNotes} busy={false} demoMode onReview={(event) => { event.preventDefault(); if (!selected) return; const updated = { ...selected, reviewStatus, reviewNotes }; setReports((items) => items.map((item) => item.id === selected.id ? updated : item)); setSelected(updated); setNotice('Mock review updated in this browser only.'); }} onRefresh={() => undefined} notice="" onSignOut={() => { setDemoMode(false); setReports([]); setSelected(null); }} />;
  if (!supabase) return <main className="auth-wrap"><section className="auth-card"><Brand /><h1>Dashboard setup needed</h1><p>Copy <code>dashboard/.env.example</code> to <code>dashboard/.env</code> and add the Supabase project URL and publishable key. Never use a service-role key here.</p><p className="muted">No database credentials are used by this dashboard. The API remains responsible for authorization.</p><button className="outline" onClick={() => { setDemoMode(true); setReports(sampleReports); }}>Open local sample demo</button></section></main>;
  if (restoring) return <main className="auth-wrap"><p>Restoring secure sign-in…</p></main>;
  if (!session) return <main className="auth-wrap"><form className="auth-card" onSubmit={signIn}><Brand /><h1>Authority sign in</h1><p>Use your assigned Supabase account. Reviewer/admin access is decided by the API.</p><label>Email<input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>{error && <div className="alert error">{error}</div>}<button disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button><small>Accounts are provisioned through Supabase Auth; dashboard sign-up is disabled.</small><button type="button" className="outline" onClick={() => { setDemoMode(true); setReports(sampleReports); }}>Open local sample demo</button></form></main>;

  return <Dashboard reports={reports} selected={selected} setSelected={setSelected} search={search} setSearch={setSearch} sector={sector} setSector={setSector} status={status} setStatus={setStatus} reviewStatus={reviewStatus} setReviewStatus={setReviewStatus} reviewNotes={reviewNotes} setReviewNotes={setReviewNotes} busy={busy} error={error} notice={notice} onReview={saveReview} onRefresh={() => void loadReports(session.access_token)} onSignOut={() => void supabase.auth.signOut()} account={session.user.email ?? 'Signed in'} />;
}

type DashboardProps = {
  reports: Report[]; selected: Report | null; setSelected: (report: Report) => void;
  search: string; setSearch: (value: string) => void; sector: string; setSector: (value: string) => void;
  status: string; setStatus: (value: string) => void; reviewStatus: string; setReviewStatus: (value: string) => void;
  reviewNotes: string; setReviewNotes: (value: string) => void; busy: boolean; demoMode?: boolean;
  notice: string; error?: string; onReview: (event: React.FormEvent) => void | Promise<void>; onRefresh: () => void; onSignOut: () => void; account?: string;
}

function Dashboard({ reports, selected, setSelected, search, setSearch, sector, setSector, status, setStatus, reviewStatus, setReviewStatus, reviewNotes, setReviewNotes, busy, demoMode, notice, error, onReview, onRefresh, onSignOut, account }: DashboardProps) {
  const visible = reports.filter((report) => (!sector || report.sector === sector)
    && (!status || report.reviewStatus === status)
    && (!search || `${report.type} ${report.sector} ${report.notes} ${report.locationName ?? ''}`.toLowerCase().includes(search.toLowerCase())));
  const sectors = Array.from(new Set(reports.map((item) => item.sector))).sort();
  const pending = reports.filter((item) => item.reviewStatus === 'not_reviewed').length;
  const inReview = reports.filter((item) => item.reviewStatus === 'in_review').length;
  const gps = reports.filter((item) => item.latitude != null && item.longitude != null).length;
  return <div className="shell"><header className="topbar"><Brand /><div className="account"><span>{demoMode ? 'LOCAL MOCK DATA' : account}</span><button className="outline" onClick={onSignOut}>{demoMode ? 'Exit demo' : 'Sign out'}</button></div></header>
    <main className="dashboard"><div className="heading"><div><p className="eyebrow">DAKSHINA KANNADA COAST</p><h1>Field reports</h1><p>Review conservation observations received by TurtleWay.</p></div><button className="outline" disabled={busy} onClick={onRefresh}>↻ Refresh</button></div>
      <RiskSummary />
      {demoMode && <div className="alert warning">DEMO ONLY — fictional sample data; changes stay in this browser and are not sent to TurtleWay.</div>}{error && <div className="alert error">{error}</div>}{notice && <div className="alert success">{notice}</div>}
      <div className="stats"><Stat label="Visible reports" value={reports.length} /><Stat label="Awaiting review" value={pending} /><Stat label="In review" value={inReview} /><Stat label="GPS locations" value={gps} /></div>
      <p className="permission-note">Review operations are authorized by the backend for each request. A failed review may mean this account has reporter-only access or lacks this sector assignment.</p>
      <section className="filters"><input placeholder="Search observations, sectors, notes…" value={search} onChange={(e) => setSearch(e.target.value)} /><select value={sector} onChange={(e) => setSector(e.target.value)}><option value="">All sectors</option>{sectors.map((item) => <option key={item}>{item}</option>)}</select><select value={status} onChange={(e) => setStatus(e.target.value)}><option value="">All statuses</option>{['not_reviewed', 'in_review', 'verified', 'rejected'].map((item) => <option key={item}>{item}</option>)}</select></section>
      <div className="workspace"><section className="list-panel"><div className="panel-heading"><h2>Observations</h2><span>{visible.length} shown</span></div>{busy && reports.length === 0 ? <p className="empty">Loading reports…</p> : visible.length === 0 ? <p className="empty">No reports match these filters.</p> : visible.map((report) => <button className={`report-row ${selected?.id === report.id ? 'selected' : ''}`} key={report.id} onClick={() => { setSelected(report); setReviewStatus(report.reviewStatus === 'not_reviewed' ? 'in_review' : report.reviewStatus); setReviewNotes(report.reviewNotes ?? ''); }}><span className="row-top"><b>{report.type}</b><Status value={report.reviewStatus} /></span><span>{report.sector} · {new Date(report.timestamp).toLocaleString()}</span><span>{report.locationSource === 'gps' ? '📍 GPS coordinates' : report.locationSource === 'preset' ? 'Coastal sector' : 'Location recorded'}</span></button>)}</section>
        <section className="detail-panel">{!selected ? <p className="empty">Choose a report to see its details and review controls.</p> : <><div className="panel-heading"><h2>{selected.type}</h2><Status value={selected.reviewStatus} /></div><dl><dt>Sector</dt><dd>{selected.sector}</dd><dt>Observed</dt><dd>{new Date(selected.timestamp).toLocaleString()}</dd><dt>Received by server</dt><dd>{new Date(selected.receivedAt).toLocaleString()}</dd><dt>Location</dt><dd>{selected.locationName ?? (selected.latitude != null ? 'Current location' : 'Preset sector')}</dd><dt>Coordinates</dt><dd>{selected.latitude != null && selected.longitude != null ? <><a target="_blank" rel="noreferrer" href={`https://maps.google.com/?q=${selected.latitude},${selected.longitude}`}>{selected.latitude.toFixed(6)}, {selected.longitude.toFixed(6)} ↗</a></> : 'Not provided'}</dd><dt>Notes</dt><dd className="notes">{selected.notes || 'No additional notes.'}</dd></dl><form className="review-form" onSubmit={onReview}><h3>Authority review</h3><label>Status<select value={reviewStatus} onChange={(e) => setReviewStatus(e.target.value)}>{['in_review', 'verified', 'rejected'].map((item) => <option key={item}>{item}</option>)}</select></label><label>Review notes<textarea rows={3} maxLength={10000} value={reviewNotes} onChange={(e) => setReviewNotes(e.target.value)} placeholder="Add a field follow-up note…" /></label><button disabled={busy}>Save review</button><small>The server validates roles, sector scope, and allowed status transitions.</small></form></>}</section></div>
    </main></div>;
}

function Brand() { return <div className="brand"><span className="brand-icon">🐢</span><span><b>TurtleWay</b><small>CONSERVATION AUTHORITY</small></span></div>; }
function RiskSummary() {
  const [risk, setRisk] = React.useState<{ riskStatus: string; message: string; dataAsOf: string | null; activityRatio: number | null; source: string; snapshotNote: string; limitations: string } | null>(null);
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(true);
  const load = React.useCallback(async () => {
    setLoading(true); setError('');
    try {
      const response = await fetch(`${apiBase}/risk/fishing-activity`);
      if (!response.ok) throw new Error('Risk assessment is unavailable.');
      setRisk(await response.json());
    } catch (err) { setError(err instanceof Error ? err.message : 'Risk assessment is unavailable.'); }
    finally { setLoading(false); }
  }, []);
  React.useEffect(() => { void load(); }, [load]);
  return <section className="risk-summary"><div><p className="eyebrow">REGIONAL FISHING ACTIVITY</p><h2>{loading ? 'Loading risk assessment…' : risk ? risk.riskStatus.replaceAll('_', ' ') : 'Assessment unavailable'}</h2><p>{risk?.message ?? error}</p><small>{risk ? `${risk.source}${risk.dataAsOf ? ` · data through ${risk.dataAsOf}` : ''}${risk.activityRatio !== null ? ` · ${risk.activityRatio}× reference activity` : ''}` : 'Connect to the TurtleWay API to load the saved assessment.'}</small>{risk && <small className="risk-limit">{risk.snapshotNote} {risk.limitations}</small>}</div><button className="outline" disabled={loading} onClick={() => void load()}>↻ Refresh</button></section>;
}
function Stat({ label, value }: { label: string; value: number }) { return <article className="stat"><span>{label}</span><b>{value}</b></article>; }
function Status({ value }: { value: string }) { return <span className={`status status-${value}`}>{value.replaceAll('_', ' ')}</span>; }
async function apiError(response: Response) { let detail = `API request failed (HTTP ${response.status}).`; try { const data = await response.json(); detail = data.detail?.message ?? data.detail ?? detail; } catch { /* keep safe status-only message */ } return String(detail); }

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
