import { useEffect, useState } from 'react'
import { buildScoutingUrl, formatPercentage, formatRate, nextSortDirection, type ScoutingSearchFilters, type SortMetric, type SortDirection } from './scouting-helpers.mjs'

type SearchFilters = ScoutingSearchFilters
type ScoutingPlayer = {
  player_id: number; player_name: string; country_name: string | null; team_names: string[]; appearances: number
  minutes_played: number; central_midfield_minutes: number; central_midfield_share_pct: number | null
  passes_attempted: number; passes_completed: number; overall_pass_completion_pct: number | null
  progressive_passes_attempted: number; progressive_passes_attempted_per90: number | null
  progressive_passes_completed: number; progressive_passes_completed_per90: number | null
  progressive_pass_completion_pct: number | null; progressive_carries: number; progressive_carries_per90: number | null
}
type ScoutingMetricDefinition = { key: SortMetric; label: string; unit: string; definition: string }
type ScoutingResponse = {
  profile_key: string; profile_name: string; profile_description: string
  scope: { competition_id: number; competition_name: string; season_id: number; season_name: string; source_commit: string; historical_note: string }
  filters: SearchFilters; metric_definitions: ScoutingMetricDefinition[]; result_count: number; results: ScoutingPlayer[]
}
type SearchState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'success'; data: ScoutingResponse }

const defaultFilters: SearchFilters = {
  profile: 'ball_progressing_midfielder', min_minutes: 450, min_central_share_pct: 50,
  sort_by: 'progressive_passes_completed_per90', sort_direction: 'desc', limit: 25,
}

const fallbackMetricLabels: Record<SortMetric, string> = {
  progressive_passes_attempted_per90: 'Progressive passes attempted / 90',
  progressive_passes_completed_per90: 'Progressive passes completed / 90',
  progressive_pass_completion_pct: 'Progressive pass completion (%)',
  progressive_carries_per90: 'Progressive carries / 90',
  overall_pass_completion_pct: 'Overall pass completion (%)',
}

const metricColumns: { key: SortMetric; value: (player: ScoutingPlayer) => number | null; format: (value: number | null) => string }[] = [
  { key: 'progressive_passes_attempted_per90', value: (player) => player.progressive_passes_attempted_per90, format: formatRate },
  { key: 'progressive_passes_completed_per90', value: (player) => player.progressive_passes_completed_per90, format: formatRate },
  { key: 'progressive_pass_completion_pct', value: (player) => player.progressive_pass_completion_pct, format: formatPercentage },
  { key: 'progressive_carries_per90', value: (player) => player.progressive_carries_per90, format: formatRate },
  { key: 'overall_pass_completion_pct', value: (player) => player.overall_pass_completion_pct, format: formatPercentage },
]

function metricLabel(definitions: ScoutingMetricDefinition[], key: SortMetric) {
  const definition = definitions.find((item) => item.key === key)
  const label = definition?.label ?? fallbackMetricLabels[key]
  return definition?.unit === 'percent' ? `${label} (%)` : label
}

function describeApiError(body: unknown, status: number) {
  if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') return body.detail
  return `The shortlist request failed (HTTP ${status}). Check that the API and database are running, then try again.`
}

function ScoutingSearch() {
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters)
  const [draftMinutes, setDraftMinutes] = useState(String(defaultFilters.min_minutes))
  const [draftRoleShare, setDraftRoleShare] = useState(String(defaultFilters.min_central_share_pct))
  const [search, setSearch] = useState<SearchState>({ status: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    setSearch({ status: 'loading' })
    void fetch(buildScoutingUrl(filters), { signal: controller.signal })
      .then(async (response) => {
        const body: unknown = await response.json()
        if (!response.ok) throw new Error(describeApiError(body, response.status))
        setSearch({ status: 'success', data: body as ScoutingResponse })
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setSearch({ status: 'error', message: error instanceof Error ? error.message : 'The shortlist could not be loaded.' })
      })
    return () => controller.abort()
  }, [filters])

  function applyFilters(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const minutes = Number(draftMinutes)
    const roleShare = Number(draftRoleShare)
    if (!Number.isFinite(minutes) || !Number.isFinite(roleShare)) return
    setFilters((current) => ({ ...current, min_minutes: minutes, min_central_share_pct: roleShare }))
  }

  function changeSort(key: SortMetric) {
    setFilters((current) => ({
      ...current,
      sort_by: key,
      sort_direction: nextSortDirection(current.sort_by, current.sort_direction, key),
    }))
  }

  function retry() {
    setFilters((current) => ({ ...current }))
  }

  const data = search.status === 'success' ? search.data : undefined

  return (
    <section className="scouting-search" id="shortlist" aria-labelledby="scouting-title">
      <div className="section-heading scouting-heading">
        <span className="section-number">03 / PLAYER SEARCH</span>
        <h2 id="scouting-title">Build the shortlist<span className="title-period">.</span></h2>
        <p>Find midfielders who move the ball forward, then inspect each metric separately.</p>
      </div>
      <div className="scouting-workspace">
        <div className="profile-strip">
          <div><span className="summary-label">ACTIVE PROFILE / ONE OF ONE</span><h3>{data?.profile_name ?? 'Ball-progressing central midfielder'}</h3><p>{data?.profile_description ?? 'Compare progressive passing and carrying among players used mainly in central midfield.'}</p></div>
          <div className="scope-stamp"><span>DATA WINDOW</span><strong>{data ? `${data.scope.competition_name} / ${data.scope.season_name}` : 'PREMIER LEAGUE / 2015–16'}</strong></div>
        </div>
        <form className="filter-bar" onSubmit={applyFilters} aria-label="Shortlist filters">
          <label className="filter-field minutes-field"><span>MINIMUM MINUTES</span><input aria-label="Minimum minutes played" type="number" min="0" max="25000" step="1" value={draftMinutes} onChange={(event) => setDraftMinutes(event.target.value)} /></label>
          <label className="filter-field role-field"><span>MINIMUM CENTRAL-MIDFIELD SHARE <b>{draftRoleShare}%</b></span><input aria-label="Minimum central midfield role share" type="range" min="0" max="100" step="5" value={draftRoleShare} onChange={(event) => setDraftRoleShare(event.target.value)} /></label>
          <button className="apply-filters" type="submit">UPDATE SHORTLIST <span aria-hidden="true">↗</span></button>
        </form>
        <div className="shortlist-toolbar">
          <div><span className="step-id">PLAYERS SHOWN</span><strong>{data ? String(data.result_count).padStart(2, '0') : '—'}</strong></div>
          <p>Ordered by <b>{data ? metricLabel(data.metric_definitions, filters.sort_by) : metricLabel([], filters.sort_by)}</b> · {filters.sort_direction === 'desc' ? 'highest first' : 'lowest first'}</p>
          {data && <span className="result-scope">{data.scope.competition_name} · {data.scope.season_name}</span>}
        </div>
        {search.status === 'loading' && <div className="search-state" role="status" aria-live="polite"><span className="state-pip" />Gathering season evidence for this profile…</div>}
        {search.status === 'error' && <div className="search-state search-error" role="alert"><div><strong>SHORTLIST UNAVAILABLE</strong><p>{search.message}</p></div><button type="button" className="retry-button" onClick={retry}>TRY AGAIN</button></div>}
        {data && data.results.length === 0 && <div className="search-state empty-state" role="status"><div><strong>No players meet these filters.</strong><p>Lower the minutes or central-midfield share threshold to widen the search.</p></div></div>}
        {data && data.results.length > 0 && (
          <div className="table-scroll" role="region" aria-label="Scouting shortlist results" tabIndex={0}>
            <table className="shortlist-table">
              <caption>{data.profile_name} — {data.scope.competition_name}, {data.scope.season_name}. Historical sample; not a current-player recommendation.</caption>
              <thead><tr>
                <th scope="col" className="player-column">PLAYER</th><th scope="col" className="club-column">CLUB</th>
                <th scope="col" aria-label="Appearances">APP</th><th scope="col" aria-label="Minutes played">MINS</th><th scope="col" aria-label="Central midfield minutes share, percent">CM ROLE (%)</th>
                {metricColumns.map((column) => <th key={column.key} scope="col" aria-sort={filters.sort_by === column.key ? (filters.sort_direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
                  <button type="button" className="sort-button" onClick={() => changeSort(column.key)} title={data.metric_definitions.find((item) => item.key === column.key)?.definition ?? ''}>
                    {metricLabel(data.metric_definitions, column.key)}<span aria-hidden="true">{filters.sort_by === column.key ? (filters.sort_direction === 'asc' ? ' ↑' : ' ↓') : ' ↕'}</span>
                  </button>
                </th>)}
              </tr></thead>
              <tbody>{data.results.map((player, index) => (
                <tr key={player.player_id}>
                  <td className="player-cell"><span className="rank">{String(index + 1).padStart(2, '0')}</span><span><strong>{player.player_name}</strong>{player.country_name && <small>{player.country_name}</small>}</span></td>
                  <td>{player.team_names.join(' / ') || '—'}</td><td className="numeric">{player.appearances}</td><td className="numeric">{Math.round(player.minutes_played).toLocaleString('en-GB')}</td><td className="numeric">{formatPercentage(player.central_midfield_share_pct)}</td>
                  {metricColumns.map((column) => <td key={column.key} className={`numeric ${filters.sort_by === column.key ? 'active-metric' : ''}`}>{column.format(column.value(player))}</td>)}
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
        {data && <p className="historical-note"><span aria-hidden="true">i</span>{data.scope.historical_note} Central-midfield share approximates season role from the primary position recorded per appearance. Metrics are descriptive and do not adjust for role, team tactics or opponent strength; an em dash means a rate has no valid denominator in this sample.</p>}
      </div>
    </section>
  )
}

type HealthState = 'checking' | 'ready' | 'database-down' | 'api-down'

async function checkHealth(): Promise<HealthState> {
  try {
    const response = await fetch('/api/health')
    const body = (await response.json()) as { api?: string; database?: string }
    if (response.ok && body.api === 'ok' && body.database === 'ok') return 'ready'
    if (response.status === 503 && body.api === 'ok' && body.database === 'unavailable') return 'database-down'
  } catch {
    // A failed request or invalid response means the API cannot be checked.
  }
  return 'api-down'
}

const copy: Record<HealthState, { label: string; heading: string; detail: string }> = {
  checking: { label: 'CHECKING SYSTEMS', heading: 'Establishing the connection', detail: 'Checking the API and local database.' },
  ready: { label: 'SYSTEMS ONLINE', heading: 'The scouting desk is ready', detail: 'FastAPI and PostgreSQL are connected. Your local foundation is running.' },
  'database-down': { label: 'ACTION REQUIRED', heading: 'Database connection lost', detail: 'FastAPI is running. Start PostgreSQL, then run the check again.' },
  'api-down': { label: 'ACTION REQUIRED', heading: 'API connection lost', detail: 'Start FastAPI, then run the check again. Database status cannot be confirmed.' },
}

function PitchGraphic() {
  return (
    <svg className="pitch-graphic" viewBox="0 0 560 720" role="img" aria-label="Abstract football pitch with three scouting markers and a passing route">
      <defs><pattern id="pitch-grid" width="28" height="28" patternUnits="userSpaceOnUse"><path d="M 28 0 L 0 0 0 28" fill="none" stroke="currentColor" strokeWidth="0.5" /></pattern></defs>
      <rect width="560" height="720" fill="url(#pitch-grid)" className="pitch-grid" />
      <g className="pitch-lines" fill="none" stroke="currentColor" strokeWidth="1.3">
        <rect x="54" y="45" width="452" height="630" rx="2" /><path d="M54 360h452" /><circle cx="280" cy="360" r="65" /><circle cx="280" cy="360" r="3" fill="currentColor" stroke="none" />
        <path d="M166 45v92h228V45M214 45v40h132V45M166 675v-92h228v92M214 675v-40h132v40" />
        <path d="M237 138a52 52 0 0 0 86 0M237 582a52 52 0 0 1 86 0" />
      </g>
      <path className="route-line" d="M155 522 Q193 419 280 360 T406 194" fill="none" stroke="currentColor" strokeWidth="2" strokeDasharray="5 9" />
      <g className="pitch-marker" transform="translate(155 522)"><circle r="15" /><circle r="4" /></g>
      <g className="pitch-marker" transform="translate(280 360)"><circle r="15" /><circle r="4" /></g>
      <g className="pitch-marker marker-final" transform="translate(406 194)"><circle r="15" /><circle r="4" /></g>
      <text x="98" y="561" className="pitch-label">DATA</text><text x="298" y="395" className="pitch-label">SEARCH</text><text x="425" y="178" className="pitch-label">REPORT</text>
    </svg>
  )
}

function App() {
  const [health, setHealth] = useState<HealthState>('checking')

  useEffect(() => {
    let active = true
    void checkHealth().then((result) => { if (active) setHealth(result) })
    return () => { active = false }
  }, [])

  function refresh() {
    setHealth('checking')
    void checkHealth().then(setHealth)
  }

  const apiStatus = health === 'api-down' ? 'Unavailable' : health === 'checking' ? 'Checking' : 'Connected'
  const databaseStatus = health === 'ready' ? 'Connected' : health === 'database-down' ? 'Unavailable' : health === 'checking' ? 'Checking' : 'Unknown'

  return (
    <div className="app-shell">
      <header className="masthead">
        <div className="identity"><div className="identity-mark" aria-hidden="true"><span /><span /><span /></div><div className="identity-text"><strong>TOUCHLINE</strong><span>SCOUTING INTELLIGENCE</span></div></div>
        <div className="masthead-right"><span className="edition">THE LOCAL DESK <b>/ 001</b></span><span className={`top-status top-status-${health}`}><i aria-hidden="true" />{copy[health].label}</span></div>
      </header>
      <main>
        <section className="console" aria-labelledby="page-title">
          <div className="console-copy">
            <div className="section-index"><span>01 / THE WORKSPACE</span><span>SPRINT 2 — PLAYER SEARCH</span></div>
            <p className="kicker">FOOTBALL / EVIDENCE / DECISIONS</p>
            <h1 id="page-title">THE<br /><em>SCOUTING</em><br />DESK<span className="title-period">.</span></h1>
            <p className="console-intro">A sharper view of the game starts with trustworthy data. This is the local base for player search, comparison and evidence-backed reports.</p>
            <a className="status-link" href="#readiness-title">VIEW SYSTEM STATUS <span aria-hidden="true">↓</span></a>
          </div>
          <div className="pitch-panel"><PitchGraphic /><div className="pitch-corner">FIG. 01 <span>THE PATH FROM DATA TO DECISION</span></div></div>
        </section>
        <section className="readiness" aria-labelledby="readiness-title">
          <div className="section-heading"><span className="section-number">02 / SYSTEM READINESS</span><h2 id="readiness-title">Live from your machine<span className="title-period">.</span></h2></div>
          <div className={`readiness-panel readiness-${health}`}>
            <div className="readiness-summary" role="status" aria-live="polite"><div className="summary-signal" aria-hidden="true"><span /></div><div><span className="summary-label">{copy[health].label}</span><h3>{copy[health].heading}</h3><p>{copy[health].detail}</p></div></div>
            <div className="service-list" aria-label="Service details">
              <div className="service-row"><span className="service-number">01</span><span className="service-name">FASTAPI<small>APPLICATION SERVICE</small></span><span className={`service-state ${apiStatus.toLowerCase()}`}>{apiStatus}</span></div>
              <div className="service-row"><span className="service-number">02</span><span className="service-name">POSTGRESQL<small>SCOUTING DATABASE</small></span><span className={`service-state ${databaseStatus.toLowerCase()}`}>{databaseStatus}</span></div>
            </div>
            <button className="check-button" type="button" onClick={refresh} disabled={health === 'checking'}><span aria-hidden="true">↗</span> RUN SYSTEM CHECK</button>
          </div>
        </section>
        <ScoutingSearch />
        <section className="pipeline" aria-labelledby="pipeline-title">
          <div className="section-heading"><span className="section-number">04 / THE PIPELINE</span><h2 id="pipeline-title">From signal to shortlist.</h2></div>
          <div className="pipeline-steps">
            <article><span className="step-id">01 — SOURCE</span><h3>Trusted match data</h3><p>Record where every event and metric came from.</p></article>
            <article><span className="step-id">02 — SEARCH</span><h3>Clear player comparisons</h3><p>Filter candidates and see the evidence side by side.</p></article>
            <article><span className="step-id">03 — REPORT</span><h3>Explain the decision</h3><p>Use a local model to draft grounded scouting notes.</p></article>
          </div>
        </section>
      </main>
      <footer className="footer"><span>TOUCHLINE / SCOUTING INTELLIGENCE</span><span>LOCAL DATA · SPRINT 2</span></footer>
    </div>
  )
}

export default App
