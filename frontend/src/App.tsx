import { useEffect, useState } from 'react'

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
            <div className="section-index"><span>01 / THE WORKSPACE</span><span>SPRINT 0 — FOUNDATION</span></div>
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
        <section className="pipeline" aria-labelledby="pipeline-title">
          <div className="section-heading"><span className="section-number">03 / THE PIPELINE</span><h2 id="pipeline-title">From signal to shortlist.</h2></div>
          <div className="pipeline-steps">
            <article><span className="step-id">01 — SOURCE</span><h3>Trusted match data</h3><p>Record where every event and metric came from.</p></article>
            <article><span className="step-id">02 — SEARCH</span><h3>Clear player comparisons</h3><p>Filter candidates and see the evidence side by side.</p></article>
            <article><span className="step-id">03 — REPORT</span><h3>Explain the decision</h3><p>Use a local model to draft grounded scouting notes.</p></article>
          </div>
        </section>
      </main>
      <footer className="footer"><span>TOUCHLINE / SCOUTING INTELLIGENCE</span><span>LOCAL FOUNDATION · SPRINT 0</span></footer>
    </div>
  )
}

export default App
