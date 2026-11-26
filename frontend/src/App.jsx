import { useState, useEffect } from 'react'
import {
  BrowserRouter, Routes, Route, Link, Navigate, NavLink, Outlet, useParams, useNavigate,
} from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
})

const API_BASE = 'http://localhost:4000'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  if (res.status === 204) return null
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(body.detail || `Request failed: ${res.status}`)
  return body
}

export const api = {
  get: (p) => request(p, { method: 'GET' }),
  post: (p, b) => request(p, { method: 'POST', body: JSON.stringify(b) }),
  put: (p, b) => request(p, { method: 'PUT', body: JSON.stringify(b) }),
  del: (p) => request(p, { method: 'DELETE' }),
}

const cn = (...classes) => classes.filter(Boolean).join(' ')

const formSubmit = (onSubmit) => (e) => {
  e.preventDefault()
  const data = Object.fromEntries(new FormData(e.currentTarget).entries())
  return onSubmit(data)
}

function useApiData(path, fallback) {
  const [data, setData] = useState(fallback)
  useEffect(() => {
    let active = true
    api.get(path).then((d) => { if (active && d) setData(d) }).catch(() => {})
    return () => { active = false }
  }, [path])
  return data
}

// ---------------------------------------------------------------------------
// Shared components
// ---------------------------------------------------------------------------

function Button({ variant = 'primary', size = 'md', children, className = '', ...props }) {
  return (
    <button className={cn('btn', `btn-${variant}`, `btn-${size}`, className)} {...props}>
      {children}
    </button>
  )
}

const TONES = {
  urgent: 'urgent', high: 'high', due: 'due', active: 'active', done: 'done',
  open: 'open', pending: 'pending', approved: 'approved', blocked: 'blocked',
  draft: 'draft', info: 'info', neutral: 'neutral', success: 'success',
}

function Pill({ tone = 'neutral', children }) {
  return <span className={cn('pill', `pill-${TONES[tone] || 'neutral'}`)}>{children}</span>
}

function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="page-header">
      <div className="page-header-main">
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-description">{description}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  )
}

function Panel({ title, subtitle, actions, children, className = '' }) {
  return (
    <section className={cn('panel', className)}>
      {(title || actions) && (
        <div className="panel-head">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="panel-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="panel-actions">{actions}</div>}
        </div>
      )}
      <div className="panel-body">{children}</div>
    </section>
  )
}

function DataTable({ columns, rows, empty = 'Nothing to show yet.' }) {
  if (!rows || rows.length === 0) return <EmptyState message={empty} />
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={row.id || i}>
              {columns.map((c) => (
                <td key={c.key}>
                  {c.render ? c.render(row) : (row[c.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function EmptyState({ message }) {
  return (
    <div className="empty-state">
      <span className="empty-mark" aria-hidden="true" />
      <p>{message}</p>
    </div>
  )
}

function Field({ label, hint, name, children, ...props }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children || <input name={name} {...props} />}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

function KeyValue({ label, value }) {
  return (
    <div className="key-value">
      <dt>{label}</dt>
      <dd>{value ?? '—'}</dd>
    </div>
  )
}

function DemoNote() {
  return (
    <div className="demo-note">
      <span className="demo-dot" />
      <span>Alpha workspace · synthetic data</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Navigation shells
// ---------------------------------------------------------------------------

const NAV = {
  staff: [
    { label: 'Daily work', items: [
      { to: '/staff/inbox', label: 'Inbox', badge: '6' },
      { to: '/staff/front-desk/booking', label: 'Booking queue' },
      { to: '/staff/front-desk/promises', label: 'Promises' },
    ] },
    { label: 'Patient care', items: [
      { to: '/staff/patients/p-1042/timeline', label: 'Patient timeline' },
      { to: '/staff/problem-reports/r-88/triage', label: 'Report triage' },
      { to: '/staff/appointments/a-771/chair', label: 'Chairside capture' },
      { to: '/staff/appointments/a-771/brief', label: 'Visit brief' },
    ] },
    { label: 'Operations', items: [
      { to: '/staff/operations/huddle', label: 'Daily huddle' },
      { to: '/staff/operations/loop-report', label: 'Loop report' },
      { to: '/staff/operations/alert-budget', label: 'Alert budget' },
      { to: '/staff/imports/pms', label: 'PMS import' },
    ] },
  ],
  admin: [
    { label: 'Governance', items: [
      { to: '/admin/workforce', label: 'Workforce' },
      { to: '/admin/proxy-and-consent', label: 'Proxy & consent' },
      { to: '/admin/rules', label: 'Routing rules' },
      { to: '/admin/content', label: 'Content library' },
    ] },
    { label: 'Practice', items: [
      { to: '/admin/practice-readiness', label: 'Practice readiness' },
      { to: '/admin/support-grants', label: 'Support grants' },
      { to: '/admin/audit-and-access', label: 'Audit & access' },
      { to: '/admin/record-exports', label: 'Record exports' },
    ] },
  ],
  family: [
    { label: 'Your care', items: [
      { to: '/family/home', label: 'Home' },
      { to: '/family/patients/p-1042/today', label: 'Today' },
      { to: '/family/patients/p-1042/timeline', label: 'Timeline' },
      { to: '/family/patients/p-1042/report-problem', label: 'Report a problem' },
      { to: '/family/patients/p-1042/digest', label: 'Weekly digest' },
      { to: '/family/access-and-sharing', label: 'Access & sharing' },
    ] },
  ],
}

const MODE_META = {
  staff: { label: 'Practice workspace', short: 'Staff', role: 'Practice member' },
  admin: { label: 'Administration', short: 'Admin', role: 'Practice manager' },
  family: { label: 'Family access', short: 'Family', role: 'Verified proxy' },
}

function Shell({ mode }) {
  const meta = MODE_META[mode]
  return (
    <div className="app-shell">
      <aside className="side-nav">
        <Link to="/" className="side-brand">
          <span className="brand-mark">W</span>
          <span className="brand-name">WZDM <em>LiveRecord</em></span>
        </Link>
        <div className="side-context">
          <span className="side-context-label">{meta.label}</span>
          <span className="side-context-value">WZDM Orthodontics</span>
        </div>
        <nav className="side-links">
          {NAV[mode].map((group) => (
            <div className="nav-group" key={group.label}>
              <p className="nav-label">{group.label}</p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => cn('nav-link', isActive && 'is-active')}
                >
                  <span>{item.label}</span>
                  {item.badge && <span className="nav-badge">{item.badge}</span>}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="side-foot">
          <DemoNote />
          <Link to="/safe-route" className="side-safe">Safe route & emergency contact</Link>
        </div>
      </aside>
      <div className="workspace">
        <header className="top-bar">
          <div className="top-crumbs">
            <span>{meta.short}</span><span className="crumb-sep">/</span><span>Workspace</span>
          </div>
          <div className="top-tools">
            <label className="top-search">
              <span aria-hidden="true">⌕</span>
              <input placeholder="Search records…" aria-label="Search" />
              <kbd>⌘K</kbd>
            </label>
            <div className="top-user">
              <span className="avatar" aria-hidden="true">DR</span>
              <span className="top-user-meta"><strong>{meta.role}</strong><small>Signed in</small></span>
            </div>
          </div>
        </header>
        <main className="main-content"><Outlet /></main>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Public pages
// ---------------------------------------------------------------------------

function LandingPage() {
  const inboxRows = [
    { who: 'Bond check · A. Mehta', meta: 'Due today', tone: 'due', label: 'Due today' },
    { who: 'Debond loop · R. Okafor', meta: 'In 2 days', tone: 'active', label: 'Scheduled' },
    { who: 'Problem report · J. Santos', meta: 'Needs triage', tone: 'urgent', label: 'Urgent' },
  ]
  return (
    <div className="landing">
      <header className="landing-nav">
        <Link to="/" className="landing-brand"><span className="brand-mark">W</span> WZDM <em>LiveRecord</em></Link>
        <nav>
          <a href="#capabilities">Capabilities</a>
          <a href="#workflow">How it works</a>
          <Link to="/safe-route">Safe route</Link>
          <Link to="/sign-in" className="btn btn-primary btn-sm">Sign in</Link>
        </nav>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Practice-wide care coordination</p>
            <h1><span className="hero-line">Every patient.</span><span className="hero-line">Every loop.</span><span className="hero-line">One accountable record.</span></h1>
            <p className="hero-sub">
              WZDM LiveRecord turns daily orthodontic work into role-based inboxes,
              deterministic care loops and an append-only clinical timeline — with
              human review at every decision that matters.
            </p>
            <div className="hero-actions">
              <Link to="/sign-in" className="btn btn-primary">Enter workspace</Link>
              <Link to="/safe-route" className="btn btn-quiet">View safe route</Link>
            </div>
            <p className="hero-fine">Invite-only access. No public registration.</p>
          </div>
          <div className="hero-visual" aria-label="Preview of the staff inbox">
            <div className="preview-chrome">
              <span /><span /><span />
              <small>staff / inbox</small>
            </div>
            <div className="preview-body">
              <div className="preview-title"><strong>Today's inbox</strong><Pill tone="due">7 open</Pill></div>
              {inboxRows.map((r) => (
                <div className="preview-row" key={r.who}>
                  <span className="preview-line" />
                  <div><strong>{r.who}</strong><small>{r.meta}</small></div>
                  <Pill tone={r.tone}>{r.label}</Pill>
                </div>
              ))}
              <div className="preview-foot">Acknowledged work stays assigned to a named owner.</div>
            </div>
          </div>
        </section>

        <section className="capabilities" id="capabilities">
          <div className="section-intro">
            <p className="eyebrow">The system</p>
            <h2>Built around what the practice actually does each day</h2>
          </div>
          <div className="capability-grid">
            <article className="capability feature">
              <span className="cap-index">01</span>
              <h3>Role-based inboxes</h3>
              <p>Cards arrive with an owner, a due date and a safe instruction set. Acknowledgement is explicit — never implied by delivery.</p>
            </article>
            <article className="capability">
              <span className="cap-index">02</span>
              <h3>Deterministic care loops</h3>
              <p>Version-controlled rules fire the right card at the right time. Escalations follow approved calendars, quiet hours and alert budgets.</p>
            </article>
            <article className="capability">
              <span className="cap-index">03</span>
              <h3>Source-preserving timeline</h3>
              <p>Every event keeps its origin and freshness. Corrections append; nothing is silently rewritten.</p>
            </article>
            <article className="capability wide">
              <span className="cap-index">04</span>
              <h3>Human review where it counts</h3>
              <p>Urgency is assigned by a person. Content, rules and doctor sign-offs are approved by named roles before they reach a patient.</p>
            </article>
          </div>
        </section>

        <section className="workflow" id="workflow">
          <div className="section-intro">
            <p className="eyebrow">Daily rhythm</p>
            <h2>From morning huddle to end-of-day report</h2>
          </div>
          <ol className="workflow-steps">
            <li><span>01</span><strong>Huddle</strong><p>Open work, overdue loops and capacity reviewed together.</p></li>
            <li><span>02</span><strong>Chairside</strong><p>Approved capture at the exact appointment, with traceable sources.</p></li>
            <li><span>03</span><strong>Brief & sign-off</strong><p>Doctor reviews events since the last visit and signs the snapshot.</p></li>
            <li><span>04</span><strong>Close & report</strong><p>Cards close with typed results; loops roll into the end-of-day report.</p></li>
          </ol>
        </section>
      </main>

      <footer className="landing-footer">
        <div><strong>WZDM LiveRecord</strong><span>Alpha · synthetic data</span></div>
        <nav>
          <Link to="/safe-route">Safe route</Link>
          <Link to="/access-blocked">Access help</Link>
          <Link to="/service-unavailable">Service status</Link>
        </nav>
      </footer>
    </div>
  )
}

function AuthLayout({ title, intro, children, foot }) {
  return (
    <div className="auth-page">
      <div className="auth-grid">
        <div className="auth-panel">
          <Link to="/" className="auth-brand"><span className="brand-mark">W</span> WZDM <em>LiveRecord</em></Link>
          <div className="auth-card">
            <p className="eyebrow">Account access</p>
            <h1>{title}</h1>
            <p className="form-hint">{intro}</p>
            {children}
            {foot && <div className="auth-switch">{foot}</div>}
          </div>
        </div>
        <aside className="auth-aside">
          <div className="auth-aside-inner">
            <p className="eyebrow">Before you continue</p>
            <h2>Safety stays in the practice.</h2>
            <p>Emergency messages never enter this system. If a patient is in danger, follow the approved practice emergency route.</p>
            <Link to="/safe-route" className="aside-link">Read the safe route →</Link>
            <div className="aside-rule" />
            <p className="aside-small">Access is invited and role-scoped. Accounts do not grant authority by themselves.</p>
          </div>
        </aside>
      </div>
    </div>
  )
}

function SignInPage() {
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function onSubmit(data) {
    setError(''); setLoading(true)
    try {
      const body = await api.post('/v1/sessions', data)
      localStorage.setItem('wzdm_session', JSON.stringify(body))
      navigate('/staff/inbox')
    } catch (e) {
      setError(e.message || 'Sign-in failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout
      title="Sign in"
      intro="Use the session identifier and password issued to you by the practice."
      foot={<><span>No access yet?</span> <Link to="/activate-account">Activate an invitation</Link></>}
    >
      <form onSubmit={formSubmit(onSubmit)} className="stack-form">
        <Field label="Session identifier" name="session" placeholder="Your invited email or SSO identifier" autoComplete="username" required />
        <Field label="Password" name="password" type="password" placeholder="Your password" autoComplete="current-password" required />
        {error && <p className="form-error" role="alert">{error}</p>}
        <Button type="submit" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</Button>
      </form>
      <div className="auth-secondary">
        <Link to="/recover-account">Recover access</Link>
        <Link to="/select-practice">Switch practice</Link>
      </div>
    </AuthLayout>
  )
}

function ActivatePage() {
  const [msg, setMsg] = useState('')
  async function onSubmit(data) {
    try {
      const body = await api.post('/v1/family/invitations', data)
      setMsg(`Invitation created · ${body.invitation_id || 'accepted for review'}`)
    } catch (e) { setMsg(e.message || 'Could not complete activation') }
  }
  return (
    <AuthLayout
      title="Activate your invitation"
      intro="A single-use invitation verifies identity. It does not grant authority on its own."
      foot={<><span>Already have access?</span> <Link to="/sign-in">Sign in</Link></>}
    >
      <form onSubmit={formSubmit(onSubmit)} className="stack-form">
        <Field label="Invitation code" name="invitation_code" placeholder="From your invitation message" required />
        <Field label="Full name" name="full_name" placeholder="As it appears on your invitation" required />
        <Field label="Password" name="password" type="password" placeholder="Choose a password" required />
        {msg && <p className="form-success" role="status">{msg}</p>}
        <Button type="submit">Activate account</Button>
      </form>
    </AuthLayout>
  )
}

function RecoverPage() {
  const [msg, setMsg] = useState('')
  function onSubmit(data) { setMsg(`Recovery request accepted for ${data.email}. The practice will review it.`) }
  return (
    <AuthLayout
      title="Recover access"
      intro="Family access is recovered through the practice. Staff recovery follows your identity provider."
      foot={<Link to="/sign-in">Back to sign in</Link>}
    >
      <form onSubmit={formSubmit(onSubmit)} className="stack-form">
        <Field label="Email" name="email" type="email" placeholder="Your invited email address" required />
        <Field label="Reason" name="reason" placeholder="Briefly describe why access is needed" />
        {msg && <p className="form-success" role="status">{msg}</p>}
        <Button type="submit">Request recovery</Button>
      </form>
    </AuthLayout>
  )
}

function SelectPracticePage() {
  const practices = [
    { id: 'wzdm-01', name: 'WZDM Orthodontics — Main', detail: 'Active membership · Practice member' },
    { id: 'wzdm-02', name: 'WZDM Orthodontics — West', detail: 'Active membership · Assistant' },
  ]
  const [selected, setSelected] = useState('wzdm-01')
  const navigate = useNavigate()
  return (
    <AuthLayout title="Select a practice" intro="Choose the practice context for this session."
      foot={<Link to="/sign-in">Back to sign in</Link>}>
      <div className="choice-list">
        {practices.map((p) => (
          <button key={p.id} className={cn('choice', selected === p.id && 'is-selected')}
            onClick={() => setSelected(p.id)} type="button">
            <strong>{p.name}</strong><small>{p.detail}</small>
          </button>
        ))}
      </div>
      <Button className="full-width" onClick={() => navigate('/staff/inbox')}>Continue</Button>
    </AuthLayout>
  )
}

function SafeRoutePage() {
  return (
    <div className="status-page">
      <div className="status-card">
        <p className="eyebrow">Public information</p>
        <h1>Safe route & emergency contact</h1>
        <p className="status-lead">This page stays available even when the record system is offline.</p>
        <Panel title="During practice hours">
          <dl className="kv-grid">
            <KeyValue label="Practice phone" value="(555) 010-2200" />
            <KeyValue label="Emergency text" value="(555) 010-2211" />
            <KeyValue label="Monitoring hours" value="Mon–Fri, 08:00–18:00" />
          </dl>
        </Panel>
        <Panel title="Outside monitoring hours">
          <p className="muted">For urgent dental or medical concerns, contact your local emergency service or emergency department. Do not wait for a reply through this system.</p>
        </Panel>
        <p className="status-foot"><Link to="/">Return home</Link></p>
      </div>
    </div>
  )
}

function StatusPage({ title, lead }) {
  return (
    <div className="status-page">
      <div className="status-card">
        <p className="eyebrow">Service state</p>
        <h1>{title}</h1>
        <p className="status-lead">{lead}</p>
        <Panel title="What you can do now">
          <p className="muted">Your clinical record is safe. No action is needed from you while the service recovers. For urgent care, use the approved emergency route.</p>
        </Panel>
        <p className="status-foot"><Link to="/safe-route">Open safe route</Link> · <Link to="/">Return home</Link></p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Demo data
// ---------------------------------------------------------------------------

const CARDS = [
  { id: 'c-301', title: 'Bond check', patient: 'A. Mehta', role: 'Assistant', due: 'Today', state: 'active', tone: 'due' },
  { id: 'c-302', title: 'Debond loop', patient: 'R. Okafor', role: 'Doctor', due: 'In 2 days', state: 'open', tone: 'active' },
  { id: 'c-303', title: 'Problem report triage', patient: 'J. Santos', role: 'Doctor', due: 'Today', state: 'open', tone: 'urgent' },
  { id: 'c-304', title: 'Retainer fit', patient: 'M. Iyer', role: 'Assistant', due: 'Tomorrow', state: 'acknowledged', tone: 'info' },
  { id: 'c-305', title: 'Visit brief sign-off', patient: 'T. Nguyen', role: 'Doctor', due: 'Today', state: 'active', tone: 'due' },
  { id: 'c-306', title: 'Photo request', patient: 'L. Park', role: 'Front desk', due: 'In 3 days', state: 'open', tone: 'neutral' },
]

const TIMELINE = [
  { id: 'e-1', date: '18 Nov 2026', type: 'Visit', title: 'Adjustment appointment', source: 'PMS import', freshness: 'Verified', tone: 'success' },
  { id: 'e-2', date: '14 Nov 2026', type: 'Card', title: 'Bond check completed', source: 'Staff entry', freshness: 'Verified', tone: 'active' },
  { id: 'e-3', date: '09 Nov 2026', type: 'Report', title: 'Patient-reported discomfort', source: 'Family submission', freshness: 'Triage complete', tone: 'done' },
  { id: 'e-4', date: '02 Nov 2026', type: 'Import', title: 'PMS reconciliation', source: 'Daily import', freshness: 'Matched', tone: 'neutral' },
]

// ---------------------------------------------------------------------------
// Staff pages
// ---------------------------------------------------------------------------

function StaffInbox() {
  const [filter, setFilter] = useState('all')
  const live = useApiData('/v1/cards', null)
  const cards = Array.isArray(live) && live.length ? live : CARDS
  const visible = filter === 'all' ? cards : cards.filter((c) => c.state === filter)
  const dueOrder = { Today: 0, Tomorrow: 1, 'In 2 days': 2, 'In 3 days': 3 }
  const inScope = filter === 'due' ? cards.filter((c) => c.due === 'Today') : visible
  const sorted = [...inScope].sort((a, b) => (dueOrder[a.due] ?? 9) - (dueOrder[b.due] ?? 9))
  const stateTone = { open: 'open', active: 'active', acknowledged: 'neutral' }
  const priority = { urgent: 'Urgent', due: 'Due now', active: 'Scheduled', info: 'Routine', neutral: 'Routine' }
  const priorityTone = (t) => t === 'urgent' ? 'urgent' : t === 'due' ? 'due' : t === 'active' ? 'active' : 'neutral'
  return (
    <>
      <PageHeader eyebrow="Daily work" title="Inbox"
        description="Work assigned to your role. Acknowledgement is explicit and owned."
        actions={<Button variant="quiet" onClick={() => window.print()}>Print list</Button>} />
      <div className="filter-bar">
        {['all', 'due', 'open', 'acknowledged', 'active'].map((f) => (
          <button key={f} className={cn('filter-chip', filter === f && 'is-active')} onClick={() => setFilter(f)} type="button">
            {f === 'all' ? 'All work' : f === 'due' ? 'Due today' : f[0].toUpperCase() + f.slice(1)}
            <span>{f === 'all' ? cards.length : f === 'due' ? cards.filter((c) => c.due === 'Today').length : cards.filter((c) => c.state === f).length}</span>
          </button>
        ))}
      </div>
      <Panel title="Assigned cards" subtitle={`${sorted.length} item${sorted.length === 1 ? '' : 's'} in view · sorted by due date`}>
        <DataTable columns={[
          { key: 'title', label: 'Card', render: (r) => <div className="cell-title"><strong>{r.title}</strong><small>{r.id}</small></div> },
          { key: 'state', label: 'State', render: (r) => <Pill tone={stateTone[r.state] || 'neutral'}>{r.state.charAt(0).toUpperCase() + r.state.slice(1)}</Pill> },
          { key: 'patient', label: 'Patient' },
          { key: 'role', label: 'Owner' },
          { key: 'due', label: 'Due', render: (r) => <span className={cn('due-cell', r.due === 'Today' && 'is-today')}>{r.due}</span> },
          { key: 'priority', label: 'Priority', render: (r) => <Pill tone={priorityTone(r.tone)}>{priority[r.tone] || 'Routine'}</Pill> },
          { key: 'actions', label: 'Actions', render: (r) => (
            <div className="row-actions">
              <Button size="sm" variant="quiet">View</Button>
              {r.state === 'acknowledged'
                ? <span className="ack-done">Acknowledged ✓</span>
                : <Button size="sm">Acknowledge</Button>}
            </div>
          ) },
        ]} rows={sorted} />
      </Panel>
    </>
  )
}

function PatientTimeline({ family = false }) {
  const { patientId } = useParams()
  const rows = useApiData(`/v1/patients/${patientId || 'p-1042'}/timeline`, TIMELINE)
  const events = Array.isArray(rows) && rows.length ? rows : TIMELINE
  return (
    <>
      <PageHeader eyebrow={family ? 'Family access · scoped' : 'Patient care'} title="Timeline"
        description="Source-preserving events. Corrections are appended, never rewritten."
        actions={<Button variant="quiet">Export view</Button>} />
      <div className="patient-strip">
        <div><span className="strip-label">Patient</span><strong>{patientId || 'p-1042'}</strong></div>
        <div><span className="strip-label">Scope</span><strong>{family ? 'Linked guardian' : 'Treatment team'}</strong></div>
        <div><span className="strip-label">Freshness</span><Pill tone="success">Verified</Pill></div>
      </div>
      <Panel title="Event ledger">
        <ol className="timeline">
          {events.map((e) => (
            <li key={e.id}>
              <div className="timeline-date">{e.date}</div>
              <div className="timeline-node" />
              <div className="timeline-body">
                <div className="timeline-top"><strong>{e.title}</strong><Pill tone={e.tone || 'info'}>{e.type}</Pill></div>
                <p className="timeline-source">Source: {e.source} · {e.freshness}</p>
              </div>
            </li>
          ))}
        </ol>
      </Panel>
    </>
  )
}

function TodayPage() {
  const tasks = [
    { id: 't-1', title: 'Morning check-in', meta: 'Due today · 09:00', state: 'Pending', tone: 'due' },
    { id: 't-2', title: 'Confirm next appointment', meta: 'Due today · 16:00', state: 'Open', tone: 'info' },
    { id: 't-3', title: 'Retainer care instructions', meta: 'Available now', state: 'Ready', tone: 'success' },
  ]
  return (
    <>
      <PageHeader eyebrow="Family access" title="Today"
        description="Your permitted tasks and approved instructions for today." />
      <Panel title="Today's tasks">
        <div className="task-list">
          {tasks.map((t) => (
            <div className="task-row" key={t.id}>
              <span className="task-check" aria-hidden="true" />
              <div><strong>{t.title}</strong><p>{t.meta}</p></div>
              <Pill tone={t.tone}>{t.state}</Pill>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Approved instructions" subtitle="Issued by the practice for your current phase">
        <p className="muted">Keep the area clean and gentle. Contact the practice through the safe route if something feels wrong — urgency is never decided by you.</p>
      </Panel>
    </>
  )
}

function FamilyHome() {
  return (
    <>
      <PageHeader eyebrow="Family access" title="Home"
        description="Your current patient context, permitted actions and upcoming visits." />
      <Panel title="Your patient">
        <dl className="kv-grid">
          <KeyValue label="Patient" value="Aarav Mehta" />
          <KeyValue label="Phase" value="In treatment" />
          <KeyValue label="Access scope" value="Guardian · active" />
          <KeyValue label="Next visit" value="25 Nov 2026, 10:30" />
        </dl>
      </Panel>
      <Panel title="Permitted next actions">
        <div className="action-grid">
          <Link to="/family/patients/p-1042/today" className="action-tile"><strong>Today</strong><span>Tasks and check-ins</span></Link>
          <Link to="/family/patients/p-1042/timeline" className="action-tile"><strong>Timeline</strong><span>Care history</span></Link>
          <Link to="/family/patients/p-1042/report-problem" className="action-tile"><strong>Report a problem</strong><span>Structured, no urgency question</span></Link>
          <Link to="/safe-route" className="action-tile"><strong>Safe route</strong><span>Contact and emergencies</span></Link>
        </div>
      </Panel>
    </>
  )
}

function ReportProblemPage() {
  const [msg, setMsg] = useState('')
  const { patientId } = useParams()
  async function onSubmit(data) {
    try {
      const body = await api.post(`/v1/patients/${patientId || 'p-1042'}/problem-reports`, data)
      setMsg(`Report submitted · ${body.report_id || 'received'}`)
    } catch (e) { setMsg(e.message || 'Could not submit report') }
  }
  return (
    <>
      <PageHeader eyebrow="Family access" title="Report a problem"
        description="Describe what you noticed. The practice decides urgency — there is no urgency question here." />
      <Panel title="Structured report">
        <form onSubmit={formSubmit(onSubmit)} className="stack-form narrow">
          <Field label="Subject" name="title" placeholder="What is the concern?" required />
          <Field label="Description" name="description">
            <textarea name="description" rows="6" placeholder="What did you notice? When did it start?" required />
          </Field>
          <Field label="Photo (optional)" name="photo">
            <input type="file" name="photo" accept="image/*" />
          </Field>
          {msg && <p className="form-success" role="status">{msg}</p>}
          <Button type="submit">Submit report</Button>
        </form>
      </Panel>
      <Panel title="Safe route remains available">
        <p className="muted">If this is urgent, do not wait for a reply. <Link to="/safe-route">Use the emergency route</Link>.</p>
      </Panel>
    </>
  )
}

function DigestPage() {
  return (
    <>
      <PageHeader eyebrow="Family access" title="Weekly digest"
        description="An approved, parent-visible summary of the last week." />
      <Panel title="Week of 17 November 2026">
        <dl className="kv-grid">
          <KeyValue label="Visits" value="1 completed" />
          <KeyValue label="Cards closed" value="3" />
          <KeyValue label="Open items" value="1 · Bond check" />
          <KeyValue label="Approved by" value="Dr. Vale" />
        </dl>
      </Panel>
      <Panel title="Approved summary">
        <p className="muted">Treatment is progressing as planned. One routine check remains open and is scheduled for this week. No urgent concerns were recorded.</p>
      </Panel>
    </>
  )
}

function AccessSharing() {
  const rows = [
    { id: 'pr-1', who: 'A. Mehta', relation: 'Parent / guardian', scope: 'Patient + shared', state: 'Active', tone: 'success' },
    { id: 'pr-2', who: 'S. Mehta', relation: 'Parent / guardian', scope: 'Shared only', state: 'Pending verification', tone: 'pending' },
  ]
  return (
    <>
      <PageHeader eyebrow="Family access" title="Access & sharing"
        description="Relationships, scopes, consent versions and channel preferences." />
      <Panel title="People with access">
        <DataTable columns={[
          { key: 'who', label: 'Person' }, { key: 'relation', label: 'Relationship' },
          { key: 'scope', label: 'Scope' },
          { key: 'state', label: 'Status', render: (r) => <Pill tone={r.tone}>{r.state}</Pill> },
        ]} rows={rows} />
      </Panel>
      <Panel title="Consent & channels">
        <dl className="kv-grid">
          <KeyValue label="Consent version" value="v4 · approved 12 Oct 2026" />
          <KeyValue label="Notification channel" value="Email" />
          <KeyValue label="Private scope" value="Withheld from proxy by default" />
        </dl>
      </Panel>
    </>
  )
}

function TriagePage() {
  const { reportId } = useParams()
  const [decision, setDecision] = useState('')
  return (
    <>
      <PageHeader eyebrow="Patient care · human review" title="Report triage"
        description="Urgency is assigned by a person. No machine-generated conclusion is shown."
        actions={<Pill tone="urgent">Awaiting triage</Pill>} />
      <div className="split-view">
        <Panel title="Submitted report" subtitle={`Report ${reportId || 'r-88'}`}>
          <dl className="kv-grid">
            <KeyValue label="Patient" value="Jo Santos" />
            <KeyValue label="Submitted" value="Today, 08:42" />
            <KeyValue label="Channel" value="Family form" />
          </dl>
          <h3 className="subhead">Description</h3>
          <p className="muted">Loose bracket on the upper left since yesterday evening. No swelling. Patient reports mild discomfort when chewing.</p>
          <h3 className="subhead">Source image</h3>
          <div className="image-placeholder">Photo attached · view with authorised access</div>
        </Panel>
        <Panel title="Your decision" subtitle="Recorded against your role">
          <div className="decision-options">
            {[
              { id: 'routine', label: 'Routine · next business day' },
              { id: 'priority', label: 'Priority · contact today' },
              { id: 'urgent', label: 'Urgent · immediate clinical review' },
            ].map((o) => (
              <button key={o.id} type="button"
                className={cn('choice', decision === o.id && 'is-selected')}
                onClick={() => setDecision(o.id)}>{o.label}</button>
            ))}
          </div>
          <Field label="Approved instruction" name="instruction">
            <select name="instruction" defaultValue="">
              <option value="" disabled>Select an approved instruction…</option>
              <option>Continue as directed; monitor and report changes</option>
              <option>Contact the practice using the safe route</option>
              <option>Attend an urgent clinical review</option>
            </select>
          </Field>
          <Field label="Route preview" name="route">
            <textarea name="route" rows="3" readOnly defaultValue="Patient + nominated guardian · email only" />
          </Field>
          <Button disabled={!decision}>Record triage decision</Button>
        </Panel>
      </div>
    </>
  )
}

function ChairPage() {
  return (
    <>
      <PageHeader eyebrow="Chairside" title="Capture"
        description="Exact patient and appointment context. Only approved captures are recorded."
        actions={<Pill tone="active">Appointment a-771</Pill>} />
      <div className="split-view">
        <Panel title="Appointment context">
          <dl className="kv-grid">
            <KeyValue label="Patient" value="Aarav Mehta" />
            <KeyValue label="Appointment" value="Adjustment · 10:30" />
            <KeyValue label="Clinician" value="Dr. Vale" />
            <KeyValue label="Phase" value="Active treatment" />
          </dl>
        </Panel>
        <Panel title="Approved capture">
          <form className="stack-form narrow" onSubmit={(e) => e.preventDefault()}>
            <Field label="Capture type" name="type">
              <select name="type"><option>Clinical observation</option><option>Photo</option><option>Patient statement</option></select>
            </Field>
            <Field label="Note" name="note"><textarea name="note" rows="5" placeholder="Record only approved source content" /></Field>
            <Button>Add to visit source set</Button>
          </form>
        </Panel>
      </div>
      <Panel title="Sources captured this visit">
        <DataTable columns={[
          { key: 'type', label: 'Type' }, { key: 'detail', label: 'Detail' },
          { key: 'by', label: 'Captured by' },
        ]} rows={[
          { id: 1, type: 'Photo', detail: 'Frontal, bite', by: 'S. Reed' },
          { id: 2, type: 'Observation', detail: 'Bond integrity checked', by: 'Dr. Vale' },
        ]} />
      </Panel>
    </>
  )
}

function BriefPage() {
  return (
    <>
      <PageHeader eyebrow="Doctor review" title="Visit brief"
        description="Events since the last visit, with source and freshness. Doctor signature closes the snapshot."
        actions={<Button>Sign off brief</Button>} />
      <Panel title="Since last visit">
        <DataTable columns={[
          { key: 'date', label: 'Date' }, { key: 'event', label: 'Event' },
          { key: 'source', label: 'Source' },
          { key: 'fresh', label: 'Freshness', render: (r) => <Pill tone={r.tone}>{r.fresh}</Pill> },
        ]} rows={TIMELINE.map((e) => ({
          id: e.id, date: e.date, event: e.title, source: e.source, fresh: e.freshness, tone: e.tone,
        }))} />
      </Panel>
      <Panel title="Open cards">
        <DataTable columns={[
          { key: 'title', label: 'Card' }, { key: 'owner', label: 'Owner' }, { key: 'due', label: 'Due' },
        ]} rows={CARDS.slice(0, 3).map((c) => ({ id: c.id, title: c.title, owner: c.role, due: c.due }))} />
      </Panel>
      <Panel title="Signature">
        <p className="muted">Signing freezes this exact snapshot. Later changes append a new version; they do not alter what was signed.</p>
      </Panel>
    </>
  )
}

function BookingPage() {
  const rows = [
    { id: 1, time: '09:00', patient: 'A. Mehta', reason: 'Bond check', status: 'Confirmed', tone: 'success' },
    { id: 2, time: '10:30', patient: 'R. Okafor', reason: 'Debond review', status: 'Confirmed', tone: 'success' },
    { id: 3, time: '12:00', patient: 'J. Santos', reason: 'Problem follow-up', status: 'Needs confirmation', tone: 'pending' },
    { id: 4, time: '15:30', patient: 'M. Iyer', reason: 'Retainer fit', status: 'Waiting', tone: 'info' },
  ]
  return (
    <>
      <PageHeader eyebrow="Front desk" title="Booking queue" description="Today's appointments and operational follow-up." />
      <Panel title="25 November 2026">
        <DataTable columns={[
          { key: 'time', label: 'Time' }, { key: 'patient', label: 'Patient' },
          { key: 'reason', label: 'Reason' },
          { key: 'status', label: 'Status', render: (r) => <Pill tone={r.tone}>{r.status}</Pill> },
        ]} rows={rows} />
      </Panel>
    </>
  )
}

function PromisesPage() {
  const rows = [
    { id: 1, promise: 'Call back about retainer cost', patient: 'M. Iyer', owner: 'Front desk', due: 'Today', status: 'Open', tone: 'due' },
    { id: 2, promise: 'Send approved instruction sheet', patient: 'A. Mehta', owner: 'Assistant', due: 'Tomorrow', status: 'In progress', tone: 'active' },
    { id: 3, promise: 'Confirm appointment time', patient: 'T. Nguyen', owner: 'Front desk', due: 'Done', status: 'Closed', tone: 'done' },
  ]
  return (
    <>
      <PageHeader eyebrow="Front desk" title="Promises" description="What the practice committed to, with owner, deadline and result." />
      <Panel title="Promise tracker">
        <DataTable columns={[
          { key: 'promise', label: 'Promise' }, { key: 'patient', label: 'Patient' },
          { key: 'owner', label: 'Owner' }, { key: 'due', label: 'Due' },
          { key: 'status', label: 'Status', render: (r) => <Pill tone={r.tone}>{r.status}</Pill> },
        ]} rows={rows} />
      </Panel>
    </>
  )
}

function HuddlePage() {
  return (
    <>
      <PageHeader eyebrow="Operations" title="Daily huddle" description="Practice-local preparation and open-work view." />
      <Panel title="Open work at a glance">
        <div className="metric-row">
          <div><span>Open cards</span><strong>7</strong><small>2 due today</small></div>
          <div><span>Overdue loops</span><strong>1</strong><small>Needs owner</small></div>
          <div><span>Reports to triage</span><strong>1</strong><small>Doctor review</small></div>
          <div><span>Alert budget</span><strong>68%</strong><small>Within limit</small></div>
        </div>
      </Panel>
      <div className="split-view">
        <Panel title="Focus today">
          <ul className="bullet-list">
            <li>Confirm the open bond check before the 10:30 appointment.</li>
            <li>Assign an owner to the overdue debond loop.</li>
            <li>Doctor triage pending on one family report.</li>
          </ul>
        </Panel>
        <Panel title="Capacity">
          <dl className="kv-grid">
            <KeyValue label="Chair time" value="6 of 8 slots booked" />
            <KeyValue label="On call" value="Dr. Vale" />
            <KeyValue label="Coverage gap" value="None" />
          </dl>
        </Panel>
      </div>
    </>
  )
}

function LoopReportPage() {
  const rows = [
    { id: 1, loop: 'Debond', open: 3, overdue: 1, closed: 12, owner: 'Dr. Vale', tone: 'due' },
    { id: 2, loop: 'Bond check', open: 4, overdue: 0, closed: 21, owner: 'S. Reed', tone: 'active' },
    { id: 3, loop: 'Retainer', open: 2, overdue: 0, closed: 9, owner: 'S. Reed', tone: 'info' },
  ]
  return (
    <>
      <PageHeader eyebrow="Operations" title="Loop report" description="Open, overdue and closed loops by owner." />
      <Panel title="Loop status">
        <DataTable columns={[
          { key: 'loop', label: 'Loop' }, { key: 'open', label: 'Open' },
          { key: 'overdue', label: 'Overdue' }, { key: 'closed', label: 'Closed' },
          { key: 'owner', label: 'Owner' },
          { key: 'state', label: 'State', render: (r) => <Pill tone={r.tone}>{r.overdue ? 'Attention' : 'Healthy'}</Pill> },
        ]} rows={rows} />
      </Panel>
    </>
  )
}

function AlertBudgetPage() {
  return (
    <>
      <PageHeader eyebrow="Operations" title="Alert budget"
        description="Alert load, dismissals and safety-bypass review." />
      <Panel title="Current period">
        <div className="metric-row">
          <div><span>Alerts sent</span><strong>147</strong><small>of 220 budget</small></div>
          <div><span>Dismissed</span><strong>12</strong><small>8% of sent</small></div>
          <div><span>Safety bypasses</span><strong>0</strong><small>No review required</small></div>
        </div>
      </Panel>
      <Panel title="Dismissal review">
        <DataTable columns={[
          { key: 'alert', label: 'Alert' }, { key: 'by', label: 'Dismissed by' }, { key: 'reason', label: 'Reason' },
        ]} rows={[
          { id: 1, alert: 'Debond reminder', by: 'Dr. Vale', reason: 'Handled in clinic' },
          { id: 2, alert: 'Photo request', by: 'S. Reed', reason: 'Patient already supplied' },
        ]} />
      </Panel>
    </>
  )
}

function ImportsPage() {
  const rows = [
    { id: 'imp-1', file: 'pms_export_2026-11-25.csv', status: 'Dry run complete', tone: 'info', rows: 412 },
    { id: 'imp-2', file: 'pms_export_2026-11-24.csv', status: 'Committed', tone: 'success', rows: 398 },
    { id: 'imp-3', file: 'pms_export_2026-11-23.csv', status: 'Quarantined', tone: 'blocked', rows: 0 },
  ]
  return (
    <>
      <PageHeader eyebrow="Operations" title="PMS import"
        description="Register, dry run, reconcile and commit daily practice exports." />
      <Panel title="Register an import">
        <div className="inline-form">
          <input type="file" accept=".csv" aria-label="CSV file" />
          <Button variant="quiet">Dry run</Button>
          <Button>Register import</Button>
        </div>
      </Panel>
      <Panel title="Import history">
        <DataTable columns={[
          { key: 'file', label: 'File' }, { key: 'rows', label: 'Rows' },
          { key: 'status', label: 'Status', render: (r) => <Pill tone={r.tone}>{r.status}</Pill> },
          { key: 'id', label: 'ID' },
        ]} rows={rows} />
      </Panel>
    </>
  )
}

function ImportDetailPage() {
  const { importId } = useParams()
  return (
    <>
      <PageHeader eyebrow="Operations · import" title={`Import ${importId || 'imp-1'}`}
        description="Errors, match review, reconciliation and correction plan." />
      <Panel title="Reconciliation">
        <dl className="kv-grid">
          <KeyValue label="Rows received" value="412" />
          <KeyValue label="Matched" value="406" />
          <KeyValue label="Needs review" value="4" />
          <KeyValue label="Rejected" value="2" />
        </dl>
      </Panel>
      <Panel title="Rows needing review">
        <DataTable columns={[
          { key: 'row', label: 'Row' }, { key: 'issue', label: 'Issue' }, { key: 'action', label: 'Required action' },
        ]} rows={[
          { id: 1, row: '118', issue: 'Ambiguous patient match', action: 'Confirm identity' },
          { id: 2, row: '204', issue: 'Date outside window', action: 'Check source' },
          { id: 3, row: '331', issue: 'Missing field', action: 'Correct in PMS' },
          { id: 4, row: '402', issue: 'Duplicate reference', action: 'Mark as duplicate' },
        ]} />
      </Panel>
    </>
  )
}

// ---------------------------------------------------------------------------
// Admin pages
// ---------------------------------------------------------------------------

function WorkforcePage() {
  const rows = [
    { id: 1, name: 'Dr. Vale', role: 'Orthodontist', training: 'Current', state: 'Active', tone: 'success' },
    { id: 2, name: 'S. Reed', role: 'Assistant', training: 'Current', state: 'Active', tone: 'success' },
    { id: 3, name: 'K. Brookes', role: 'Front desk', training: 'Pending', state: 'Invited', tone: 'pending' },
    { id: 4, name: 'M. Hall', role: 'Manager', training: 'Current', state: 'Deactivated', tone: 'neutral' },
  ]
  return (
    <>
      <PageHeader eyebrow="Administration" title="Workforce"
        description="Invitations, memberships, roles, training state and deactivation."
        actions={<Button>Invite staff</Button>} />
      <Panel title="People">
        <DataTable columns={[
          { key: 'name', label: 'Name' }, { key: 'role', label: 'Role' },
          { key: 'training', label: 'Training' },
          { key: 'state', label: 'Status', render: (r) => <Pill tone={r.tone}>{r.state}</Pill> },
        ]} rows={rows} />
      </Panel>
    </>
  )
}

function ProxyConsentPage() {
  return (
    <>
      <PageHeader eyebrow="Administration" title="Proxy & consent"
        description="Verified relationships, purpose-scoped consent and blocked-case review." />
      <Panel title="Verification queue">
        <DataTable columns={[
          { key: 'name', label: 'Requester' }, { key: 'patient', label: 'Patient' },
          { key: 'scope', label: 'Requested scope' }, { key: 'state', label: 'State' },
        ]} rows={[
          { id: 1, name: 'S. Mehta', patient: 'A. Mehta', scope: 'Shared only', state: 'Pending verification' },
          { id: 2, name: 'D. Okafor', patient: 'R. Okafor', scope: 'Patient + shared', state: 'Approved' },
        ]} />
      </Panel>
      <Panel title="Consent versions">
        <dl className="kv-grid">
          <KeyValue label="Current consent" value="v4 · approved 12 Oct 2026" />
          <KeyValue label="Assent" value="v2 · approved 12 Oct 2026" />
          <KeyValue label="Withdrawals" value="0 in current period" />
        </dl>
      </Panel>
    </>
  )
}

function RulesPage() {
  const rows = [
    { id: 1, name: 'Debond loop', version: 'v7', state: 'Active', approver: 'Dr. Vale', tone: 'success' },
    { id: 2, name: 'Bond check', version: 'v5', state: 'Active', approver: 'Dr. Vale', tone: 'success' },
    { id: 3, name: 'Retainer follow-up', version: 'v2-draft', state: 'Draft', approver: '—', tone: 'draft' },
  ]
  return (
    <>
      <PageHeader eyebrow="Administration" title="Routing rules"
        description="Draft, compare, submit, approve and activate deterministic rule versions."
        actions={<Button>New draft</Button>} />
      <Panel title="Rule versions">
        <DataTable columns={[
          { key: 'name', label: 'Rule' }, { key: 'version', label: 'Version' },
          { key: 'approver', label: 'Approved by' },
          { key: 'state', label: 'State', render: (r) => <Pill tone={r.tone}>{r.state}</Pill> },
        ]} rows={rows} />
      </Panel>
      <Panel title="Change control">
        <p className="muted">A rule cannot be activated by its author. Approval, tests and a documented effective date are required before activation.</p>
      </Panel>
    </>
  )
}

function ContentPage() {
  const rows = [
    { id: 1, title: 'Retainer care', version: 'v3', state: 'Active', approver: 'Dr. Vale', tone: 'success' },
    { id: 2, title: 'After adjustment', version: 'v4', state: 'In review', approver: 'Pending', tone: 'pending' },
    { id: 3, title: 'Emergency guidance', version: 'v2', state: 'Withdrawn', approver: 'Safety withdrawal', tone: 'blocked' },
  ]
  return (
    <>
      <PageHeader eyebrow="Administration" title="Content library"
        description="Exact-version review, approval, activation and safety withdrawal."
        actions={<Button>New content item</Button>} />
      <Panel title="Inventory">
        <DataTable columns={[
          { key: 'title', label: 'Item' }, { key: 'version', label: 'Version' },
          { key: 'approver', label: 'Approver' },
          { key: 'state', label: 'State', render: (r) => <Pill tone={r.tone}>{r.state}</Pill> },
        ]} rows={rows} />
      </Panel>
    </>
  )
}

function ReadinessPage() {
  const gates = [
    { id: 'G1', label: 'Foundation & decisions', state: 'Complete', tone: 'success' },
    { id: 'G2', label: 'Data model & import', state: 'Complete', tone: 'success' },
    { id: 'G3', label: 'Role inboxes & loops', state: 'In progress', tone: 'active' },
    { id: 'G4', label: 'Patient & family access', state: 'Pending', tone: 'pending' },
    { id: 'G5', label: 'Assurance & security', state: 'Pending', tone: 'pending' },
    { id: 'G6', label: 'Pilot readiness', state: 'Not started', tone: 'neutral' },
  ]
  return (
    <>
      <PageHeader eyebrow="Administration" title="Practice readiness"
        description="Configuration, calendars, routing, budgets and gate status." />
      <Panel title="Gate status">
        <div className="gate-grid">
          {gates.map((g) => (
            <div className="gate" key={g.id}>
              <span className="gate-id">{g.id}</span>
              <strong>{g.label}</strong>
              <Pill tone={g.tone}>{g.state}</Pill>
            </div>
          ))}
        </div>
      </Panel>
      <Panel title="Practice configuration">
        <dl className="kv-grid">
          <KeyValue label="Phone" value="(555) 010-2200" />
          <KeyValue label="Emergency text" value="Configured" />
          <KeyValue label="Calendars" value="Practice + on-call" />
          <KeyValue label="Alert budget" value="220 per period" />
        </dl>
      </Panel>
    </>
  )
}

function SupportGrantsPage() {
  return (
    <>
      <PageHeader eyebrow="Administration" title="Support grants"
        description="Ticketed, scoped, approved and expiring support access. No standing access." />
      <Panel title="Active grants">
        <DataTable columns={[
          { key: 'ticket', label: 'Ticket' }, { key: 'scope', label: 'Scope' },
          { key: 'expires', label: 'Expires' }, { key: 'state', label: 'State' },
        ]} rows={[
          { id: 1, ticket: 'SUP-221', scope: 'Read-only, one patient', expires: 'Today 18:00', state: 'Active' },
          { id: 2, ticket: 'SUP-219', scope: 'Import diagnostics', expires: 'Expired', state: 'Closed' },
        ]} />
      </Panel>
    </>
  )
}

function AuditPage() {
  return (
    <>
      <PageHeader eyebrow="Administration" title="Audit & access"
        description="Restricted disclosure report and investigation view." />
      <Panel title="Recent access events">
        <DataTable columns={[
          { key: 'time', label: 'When' }, { key: 'actor', label: 'Actor' },
          { key: 'action', label: 'Action' }, { key: 'scope', label: 'Scope' },
        ]} rows={[
          { id: 1, time: 'Today 09:12', actor: 'S. Reed', action: 'Timeline viewed', scope: 'Patient p-1042' },
          { id: 2, time: 'Today 08:40', actor: 'Dr. Vale', action: 'Report triaged', scope: 'Report r-88' },
          { id: 3, time: 'Yesterday 17:05', actor: 'System', action: 'Import committed', scope: 'imp-2' },
        ]} />
      </Panel>
    </>
  )
}

function ExportsPage() {
  return (
    <>
      <PageHeader eyebrow="Administration" title="Record exports"
        description="Approved support and records workflow. Not a self-service dependency." />
      <Panel title="Export requests">
        <DataTable columns={[
          { key: 'id', label: 'Request' }, { key: 'reason', label: 'Reason' },
          { key: 'reviewer', label: 'Reviewer' }, { key: 'state', label: 'State' },
        ]} rows={[
          { id: 'exp-12', reason: 'Records disclosure', reviewer: 'Privacy lead', state: 'Approved' },
          { id: 'exp-11', reason: 'Support diagnostics', reviewer: 'Practice manager', state: 'In review' },
        ]} />
      </Panel>
    </>
  )
}

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/sign-in" element={<SignInPage />} />
          <Route path="/activate-account" element={<ActivatePage />} />
          <Route path="/recover-account" element={<RecoverPage />} />
          <Route path="/select-practice" element={<SelectPracticePage />} />
          <Route path="/safe-route" element={<SafeRoutePage />} />
          <Route path="/access-blocked" element={<StatusPage title="Access blocked" lead="This account does not have permission for that view." />} />
          <Route path="/service-unavailable" element={<StatusPage title="Service unavailable" lead="The record system is restarting. Your data is safe." />} />

          <Route path="/staff" element={<Shell mode="staff" />}>
            <Route index element={<Navigate to="inbox" replace />} />
            <Route path="inbox" element={<StaffInbox />} />
            <Route path="patients/:patientId/timeline" element={<PatientTimeline />} />
            <Route path="problem-reports/:reportId/triage" element={<TriagePage />} />
            <Route path="appointments/:appointmentId/chair" element={<ChairPage />} />
            <Route path="appointments/:appointmentId/brief" element={<BriefPage />} />
            <Route path="front-desk/booking" element={<BookingPage />} />
            <Route path="front-desk/promises" element={<PromisesPage />} />
            <Route path="operations/huddle" element={<HuddlePage />} />
            <Route path="operations/loop-report" element={<LoopReportPage />} />
            <Route path="operations/alert-budget" element={<AlertBudgetPage />} />
            <Route path="imports/pms" element={<ImportsPage />} />
            <Route path="imports/pms/:importId" element={<ImportDetailPage />} />
          </Route>

          <Route path="/family" element={<Shell mode="family" />}>
            <Route index element={<Navigate to="home" replace />} />
            <Route path="home" element={<FamilyHome />} />
            <Route path="patients/:patientId/today" element={<TodayPage />} />
            <Route path="patients/:patientId/timeline" element={<PatientTimeline family />} />
            <Route path="patients/:patientId/report-problem" element={<ReportProblemPage />} />
            <Route path="patients/:patientId/digest" element={<DigestPage />} />
            <Route path="access-and-sharing" element={<AccessSharing />} />
          </Route>

          <Route path="/admin" element={<Shell mode="admin" />}>
            <Route index element={<Navigate to="workforce" replace />} />
            <Route path="workforce" element={<WorkforcePage />} />
            <Route path="proxy-and-consent" element={<ProxyConsentPage />} />
            <Route path="rules" element={<RulesPage />} />
            <Route path="content" element={<ContentPage />} />
            <Route path="practice-readiness" element={<ReadinessPage />} />
            <Route path="support-grants" element={<SupportGrantsPage />} />
            <Route path="audit-and-access" element={<AuditPage />} />
            <Route path="record-exports" element={<ExportsPage />} />
          </Route>

          {/* Legacy aliases */}
          <Route path="/invite" element={<Navigate to="/activate-account" replace />} />
          <Route path="/app/*" element={<Navigate to="/staff/inbox" replace />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
