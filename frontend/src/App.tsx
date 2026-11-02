import { useEffect, useState } from 'react'
import { buildScoutingUrl, formatMetric, formatPercentage, nextSortDirection, type ProfileKey, type ScoutingSearchFilters, type SortMetric } from './scouting-helpers.mjs'

type SearchFilters = ScoutingSearchFilters
type ScoutingPlayer = {
  player_id: number; player_name: string; country_name: string | null; team_names: string[]; appearances: number
  minutes_played: number; role_minutes: number; role_share_pct: number | null; metrics: Record<SortMetric, number | null>
}
type ScoutingMetricDefinition = { key: SortMetric; label: string; unit: string; definition: string }
type ScoutingProfileSummary = {
  profile_key: ProfileKey; profile_name: string; profile_description: string; role_group: string
  role_label: string; position_ids: number[]; default_sort: SortMetric; metric_definitions: ScoutingMetricDefinition[]
}
type ScoutingResponse = {
  profile_key: ProfileKey; profile_name: string; profile_description: string; role_label: string
  scope: { competition_id: number; competition_name: string; season_id: number; season_name: string; source_commit: string; historical_note: string }
  filters: SearchFilters; metric_definitions: ScoutingMetricDefinition[]; result_count: number; results: ScoutingPlayer[]
}
type SearchState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'success'; data: ScoutingResponse }
type LocalAiStatus = { state: 'ready' | 'runtime_missing' | 'model_missing' | 'remote_disallowed'; model: string; base_url: string; installed_models: string[]; detail: string }
type FilterInterpretationResult = { status: 'ready' | 'clarify' | 'unsupported'; message: string; proposed_filters: SearchFilters | null }
type InterpretationState = { status: 'loading' } | { status: 'error'; message: string } | { status: 'success'; data: FilterInterpretationResult }
type ReportClaim = { category: 'strength' | 'watchpoint' | 'context'; metric_key: string; label: string; statement: string; player_value: number; unit: string; peer_median: number; peer_percentile: number; peer_count: number; definition: string; competition: string; season: string; source_commit: string }
type PlayerReport = { player: ScoutingPlayer; profile_key: ProfileKey; profile_name: string; role_label: string; scope: ScoutingResponse['scope']; peer_count: number; selected_by: 'ollama' | 'rule_based'; draft_note: string; claims: ReportClaim[] }
type ReportState = { status: 'loading'; player_id: number } | { status: 'error'; message: string } | { status: 'success'; data: PlayerReport }

const defaultFilters: SearchFilters = {
  profile: 'ball_progressing_midfielder', min_minutes: 450, min_role_share_pct: 50,
  sort_by: 'progressive_passes_completed_per90', sort_direction: 'desc', limit: 25,
}

function describeApiError(body: unknown, status: number) {
  if (typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string') return body.detail
  return `The shortlist request failed (HTTP ${status}). Check that the API and database are running, then try again.`
}

function ScoutingSearch() {
  const [filters, setFilters] = useState<SearchFilters>(defaultFilters)
  const [draftMinutes, setDraftMinutes] = useState(String(defaultFilters.min_minutes))
  const [draftRoleShare, setDraftRoleShare] = useState(String(defaultFilters.min_role_share_pct))
  const [profiles, setProfiles] = useState<ScoutingProfileSummary[]>([])
  const [profilesError, setProfilesError] = useState<string | null>(null)
  const [search, setSearch] = useState<SearchState>({ status: 'loading' })
  const [aiStatus, setAiStatus] = useState<LocalAiStatus | null>(null)
  const [question, setQuestion] = useState('')
  const [interpretation, setInterpretation] = useState<InterpretationState | null>(null)
  const [report, setReport] = useState<ReportState | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void fetch('/api/scouting/profiles', { signal: controller.signal })
      .then(async (response) => {
        const body: unknown = await response.json()
        if (!response.ok) throw new Error(describeApiError(body, response.status))
        setProfiles(body as ScoutingProfileSummary[])
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setProfilesError(error instanceof Error ? error.message : 'Scouting profiles could not be loaded.')
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    void fetch('/api/ai/status', { signal: controller.signal })
      .then(async (response) => {
        const body: unknown = await response.json()
        if (!response.ok) throw new Error(describeApiError(body, response.status))
        setAiStatus(body as LocalAiStatus)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setAiStatus({ state: 'runtime_missing', model: 'qwen3.5:4b', base_url: 'http://127.0.0.1:11434', installed_models: [], detail: error instanceof Error ? error.message : 'Local model status could not be checked.' })
      })
    return () => controller.abort()
  }, [])

  useEffect(() => { setReport(null) }, [filters])

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
    setFilters((current) => ({ ...current, min_minutes: minutes, min_role_share_pct: roleShare }))
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

  function changeProfile(profileKey: ProfileKey) {
    const profile = profiles.find((item) => item.profile_key === profileKey)
    if (!profile) return
    setFilters((current) => ({
      ...current,
      profile: profile.profile_key,
      sort_by: profile.default_sort,
      sort_direction: 'desc',
    }))
  }

  async function refreshAiStatus() {
    try {
      const response = await fetch('/api/ai/status')
      const body: unknown = await response.json()
      if (!response.ok) throw new Error(describeApiError(body, response.status))
      setAiStatus(body as LocalAiStatus)
    } catch (error) {
      setAiStatus({ state: 'runtime_missing', model: aiStatus?.model ?? 'qwen3.5:4b', base_url: aiStatus?.base_url ?? 'http://127.0.0.1:11434', installed_models: [], detail: error instanceof Error ? error.message : 'Local model status could not be checked.' })
    }
  }

  async function submitQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setInterpretation({ status: 'loading' })
    try {
      const response = await fetch('/api/ai/interpret', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, active_filters: filters }),
      })
      const body: unknown = await response.json()
      if (!response.ok) throw new Error(describeApiError(body, response.status))
      setInterpretation({ status: 'success', data: body as FilterInterpretationResult })
    } catch (error) {
      setInterpretation({ status: 'error', message: error instanceof Error ? error.message : 'The local model could not interpret that request.' })
      void refreshAiStatus()
    }
  }

  function applyInterpretation() {
    if (interpretation?.status !== 'success' || interpretation.data.status !== 'ready' || !interpretation.data.proposed_filters) return
    const proposed = interpretation.data.proposed_filters
    setDraftMinutes(String(proposed.min_minutes))
    setDraftRoleShare(String(proposed.min_role_share_pct))
    setFilters(proposed)
    setInterpretation(null)
  }

  async function openDossier(player: ScoutingPlayer) {
    setReport({ status: 'loading', player_id: player.player_id })
    try {
      const response = await fetch('/api/reports/player', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: player.player_id, filters }),
      })
      const body: unknown = await response.json()
      if (!response.ok) throw new Error(describeApiError(body, response.status))
      setReport({ status: 'success', data: body as PlayerReport })
    } catch (error) {
      setReport({ status: 'error', message: error instanceof Error ? error.message : 'The evidence dossier could not be built.' })
    }
  }

  const data = search.status === 'success' ? search.data : undefined
  const activeProfile = profiles.find((profile) => profile.profile_key === filters.profile)
  const metricDefinitions = data?.metric_definitions ?? activeProfile?.metric_definitions ?? []
  const sortDefinition = metricDefinitions.find((metric) => metric.key === filters.sort_by)

  return (
    <section className="scouting-search" id="shortlist" aria-labelledby="scouting-title">
      <div className="section-heading scouting-heading">
        <span className="section-number">03 / MULTI-PROFILE SCOUTING</span>
        <h2 id="scouting-title">Build the shortlist<span className="title-period">.</span></h2>
        <p>Switch between role-specific scouting lenses, then inspect the evidence and metrics that fit each role.</p>
      </div>
      <div className="scouting-workspace">
        <div className="profile-strip">
          <div><span className="summary-label">ACTIVE PROFILE / {String(profiles.length || 4).padStart(2, '0')} LENSES</span><h3>{data?.profile_name ?? activeProfile?.profile_name ?? 'Ball-progressing central midfielder'}</h3><p>{data?.profile_description ?? activeProfile?.profile_description ?? 'Compare players through role-specific evidence and transparent metrics.'}</p></div>
          <div className="scope-stamp"><span>DATA WINDOW</span><strong>{data ? `${data.scope.competition_name} / ${data.scope.season_name}` : 'PREMIER LEAGUE / 2015–16'}</strong></div>
        </div>
        <form className="filter-bar" onSubmit={applyFilters} aria-label="Shortlist filters">
          <label className="filter-field profile-field"><span>SCOUTING LENS</span><select aria-label="Scouting profile" value={filters.profile} onChange={(event) => changeProfile(event.target.value as ProfileKey)} disabled={!profiles.length}>
            {profiles.length === 0 && <option value={filters.profile}>{profilesError ? 'Profiles unavailable' : 'Loading profiles…'}</option>}
            {profiles.map((profile) => <option key={profile.profile_key} value={profile.profile_key}>{profile.profile_name}</option>)}
          </select></label>
          <label className="filter-field minutes-field"><span>MINIMUM MINUTES</span><input aria-label="Minimum minutes played" type="number" min="0" max="25000" step="1" value={draftMinutes} onChange={(event) => setDraftMinutes(event.target.value)} /></label>
          <label className="filter-field role-field"><span>MINIMUM {activeProfile?.role_label.toUpperCase() ?? 'ROLE'} SHARE <b>{draftRoleShare}%</b></span><input aria-label="Minimum role share" type="range" min="0" max="100" step="5" value={draftRoleShare} onChange={(event) => setDraftRoleShare(event.target.value)} /></label>
          <button className="apply-filters" type="submit">UPDATE SHORTLIST <span aria-hidden="true">↗</span></button>
        </form>
        <div className="ai-assist">
          <div className="ai-assist-heading">
            <div><span className="summary-label">LOCAL AI / QUESTION TO FILTERS</span><h3>Ask the scouting desk.</h3><p>Your question becomes a filter proposal. Review it before it changes the shortlist.</p></div>
            <span className={`ai-model-state ${aiStatus?.state === 'ready' ? 'available' : ''}`}><i aria-hidden="true" />{aiStatus?.state === 'ready' ? `LOCAL / ${aiStatus.model}` : aiStatus?.state === 'model_missing' ? 'MODEL NOT DOWNLOADED' : aiStatus?.state === 'remote_disallowed' ? 'ENDPOINT BLOCKED' : 'OLLAMA NOT RUNNING'}</span>
          </div>
          <form className="ai-question-form" onSubmit={submitQuestion}>
            <label className="ai-question-label" htmlFor="scout-question">SCOUT QUESTION</label>
            <textarea id="scout-question" value={question} onChange={(event) => { setQuestion(event.target.value); setInterpretation(null) }} placeholder="For example: find forwards with the highest xG per 90 after 900 minutes" maxLength={1000} />
            <div className="ai-question-actions"><span>Only the four available scouting lenses and their listed metrics are supported.</span><button className="apply-filters" type="submit" disabled={!aiStatus || aiStatus.state !== 'ready' || question.trim().length < 3 || interpretation?.status === 'loading'}>{interpretation?.status === 'loading' ? 'READING QUESTION…' : 'INTERPRET QUESTION'} <span aria-hidden="true">↗</span></button></div>
          </form>
          {aiStatus && aiStatus.state !== 'ready' && <div className="ai-setup-note"><p>{aiStatus.detail} {aiStatus.state === 'runtime_missing' ? 'Local AI is optional; manual search and evidence dossiers still work. If you choose to enable it, the starter model download is about 4 GB.' : aiStatus.state === 'model_missing' ? 'Local AI is optional; download the model only when you want question interpretation.' : 'Set the Ollama endpoint to this machine if you intend to use local AI.'}</p>{aiStatus.state !== 'remote_disallowed' && <><code>ollama pull {aiStatus.model}</code><div><a href="https://ollama.com/download" target="_blank" rel="noreferrer">GET OLLAMA <span aria-hidden="true">↗</span></a><button type="button" onClick={() => void refreshAiStatus()}>CHECK AGAIN</button></div></>}</div>}
          {interpretation?.status === 'loading' && <div className="ai-result-state" role="status">Interpreting the question with the local model…</div>}
          {interpretation?.status === 'error' && <div className="ai-result-state ai-result-error" role="alert">{interpretation.message}</div>}
          {interpretation?.status === 'success' && <div className={`interpretation-preview interpretation-${interpretation.data.status}`} role="status">
            <div><span className="step-id">{interpretation.data.status === 'ready' ? 'FILTER PROPOSAL / REVIEW BEFORE APPLYING' : interpretation.data.status === 'clarify' ? 'CLARIFICATION NEEDED' : 'OUTSIDE THIS DATASET'}</span><p>{interpretation.data.message}</p>
              {interpretation.data.proposed_filters && <dl className="proposal-filters"><div><dt>PROFILE</dt><dd>{profiles.find((item) => item.profile_key === interpretation.data.proposed_filters?.profile)?.profile_name ?? interpretation.data.proposed_filters.profile}</dd></div><div><dt>MINUTES</dt><dd>{interpretation.data.proposed_filters.min_minutes}</dd></div><div><dt>ROLE SHARE</dt><dd>{interpretation.data.proposed_filters.min_role_share_pct}%</dd></div><div><dt>RANK BY</dt><dd>{metricDefinitions.find((item) => item.key === interpretation.data.proposed_filters?.sort_by)?.label ?? interpretation.data.proposed_filters.sort_by} · {interpretation.data.proposed_filters.sort_direction}</dd></div></dl>}
            </div>
            {interpretation.data.status === 'ready' && <button type="button" className="apply-filters" onClick={applyInterpretation}>APPLY PROPOSAL <span aria-hidden="true">↗</span></button>}
          </div>}
        </div>
        <div className="shortlist-toolbar">
          <div><span className="step-id">PLAYERS SHOWN</span><strong>{data ? String(data.result_count).padStart(2, '0') : '—'}</strong></div>
          <p>Ordered by <b>{sortDefinition?.label ?? filters.sort_by}</b> · {filters.sort_direction === 'desc' ? 'highest first' : 'lowest first'}</p>
          {data && <span className="result-scope">{data.scope.competition_name} · {data.scope.season_name}</span>}
        </div>
        {search.status === 'loading' && <div className="search-state" role="status" aria-live="polite"><span className="state-pip" />Gathering season evidence for this profile…</div>}
        {search.status === 'error' && <div className="search-state search-error" role="alert"><div><strong>SHORTLIST UNAVAILABLE</strong><p>{search.message}</p></div><button type="button" className="retry-button" onClick={retry}>TRY AGAIN</button></div>}
        {data && data.results.length === 0 && <div className="search-state empty-state" role="status"><div><strong>No players meet these filters.</strong><p>Lower the minutes or {data.role_label.toLowerCase()} share threshold to widen the search.</p></div></div>}
        {data && data.results.length > 0 && (
          <div className="table-scroll" role="region" aria-label="Scouting shortlist results" tabIndex={0}>
            <table className="shortlist-table">
              <caption>{data.profile_name} — {data.scope.competition_name}, {data.scope.season_name}. Historical sample; not a current-player recommendation.</caption>
              <thead><tr>
                <th scope="col" className="player-column">PLAYER</th><th scope="col" className="club-column">CLUB</th>
                <th scope="col" aria-label="Appearances">APP</th><th scope="col" aria-label="Minutes played">MINS</th><th scope="col" aria-label={`${data.role_label} role share, percent`}>ROLE (%)</th>
                {data.metric_definitions.map((metric) => <th key={metric.key} scope="col" aria-sort={filters.sort_by === metric.key ? (filters.sort_direction === 'asc' ? 'ascending' : 'descending') : 'none'}>
                  <button type="button" className="sort-button" onClick={() => changeSort(metric.key)} title={metric.definition}>
                    {metric.label}{metric.unit === 'percent' ? ' (%)' : ''}<span aria-hidden="true">{filters.sort_by === metric.key ? (filters.sort_direction === 'asc' ? ' ↑' : ' ↓') : ' ↕'}</span>
                  </button>
                </th>)}<th scope="col">REPORT</th>
              </tr></thead>
              <tbody>{data.results.map((player, index) => (
                <tr key={player.player_id}>
                  <td className="player-cell"><span className="rank">{String(index + 1).padStart(2, '0')}</span><span><strong>{player.player_name}</strong>{player.country_name && <small>{player.country_name}</small>}</span></td>
                  <td>{player.team_names.join(' / ') || '—'}</td><td className="numeric">{player.appearances}</td><td className="numeric">{Math.round(player.minutes_played).toLocaleString('en-GB')}</td><td className="numeric">{formatPercentage(player.role_share_pct)}</td>
                  {data.metric_definitions.map((metric) => <td key={metric.key} className={`numeric ${filters.sort_by === metric.key ? 'active-metric' : ''}`}>{formatMetric(player.metrics[metric.key], metric.unit)}</td>)}
                  <td className="report-action-cell"><button type="button" className="dossier-button" onClick={() => void openDossier(player)} disabled={report?.status === 'loading'} aria-label={`Open evidence dossier for ${player.player_name}`}>{report?.status === 'loading' && report.player_id === player.player_id ? 'BUILDING…' : 'DOSSIER ↗'}</button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
        {report?.status === 'loading' && <div className="report-loading" role="status">Building the dossier from the current eligible peer group…</div>}
        {report?.status === 'error' && <div className="search-state search-error" role="alert"><div><strong>DOSSIER UNAVAILABLE</strong><p>{report.message}</p></div></div>}
        {report?.status === 'success' && <section className="report-panel" aria-labelledby="report-title">
          <div className="report-header"><div><span className="summary-label">05 / REPORTING LENS · {report.data.selected_by === 'ollama' ? 'LOCAL MODEL DRAFT' : 'EVIDENCE-ONLY DRAFT'}</span><h3 id="report-title">{report.data.player.player_name}<span className="title-period">.</span></h3><p>{report.data.profile_name} · {report.data.scope.competition_name} / {report.data.scope.season_name} · {report.data.peer_count} eligible peers</p></div><button className="report-close" type="button" onClick={() => setReport(null)} aria-label="Close dossier">CLOSE ×</button></div>
          <p className="report-note">{report.data.draft_note}</p>
          <div className="report-claims">{report.data.claims.map((claim) => <article className={`report-claim report-${claim.category}`} key={claim.metric_key}><span className="report-category">{claim.category.toUpperCase()} / {claim.peer_percentile.toFixed(1)}TH PERCENTILE</span><h4>{claim.label}</h4><p>{claim.statement}</p><details><summary>METRIC DEFINITION & SOURCE</summary><p>{claim.definition}</p><small>{claim.competition} · {claim.season} · StatsBomb revision {claim.source_commit.slice(0, 10)}</small></details></article>)}</div>
          <p className="report-footnote">A historical, role-filtered comparison within the 2015/16 open-data sample. Percentiles describe this eligible peer group only; they are not a current-player recommendation or a quality score.</p>
        </section>}
        {data && <p className="historical-note"><span aria-hidden="true">i</span>{data.scope.historical_note} Role share approximates season usage from the primary position recorded per appearance. Metrics are descriptive and do not adjust for role, team tactics or opponent strength; an em dash means a rate has no valid denominator in this sample.</p>}
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
            <div className="section-index"><span>01 / THE WORKSPACE</span><span>SPRINT 4 — LOCAL AI + REPORTING LENS</span></div>
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
            <article><span className="step-id">03 — REPORT</span><h3>Explain the decision</h3><p>Use local AI to select relevant evidence; the API supplies every value and source.</p></article>
          </div>
        </section>
      </main>
      <footer className="footer"><span>TOUCHLINE / SCOUTING INTELLIGENCE</span><span>LOCAL DATA · SPRINT 4</span></footer>
    </div>
  )
}

export default App
