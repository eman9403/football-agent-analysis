import { useEffect, useState } from 'react'

type HealthState = 'checking' | 'ready' | 'database-down' | 'api-down'

async function checkHealth(): Promise<HealthState> {
  try {
    const response = await fetch('/api/health')
    const body = (await response.json()) as { api?: string; database?: string }

    if (response.ok && body.api === 'ok' && body.database === 'ok') return 'ready'
    if (response.status === 503 && body.api === 'ok' && body.database === 'unavailable') {
      return 'database-down'
    }
  } catch {
    // A failed request or invalid response means the API cannot be checked.
  }

  return 'api-down'
}

const copy: Record<HealthState, { heading: string; detail: string }> = {
  checking: {
    heading: 'Checking your local services',
    detail: 'Connecting the workbench to the API and database.',
  },
  ready: {
    heading: 'Your workspace is ready',
    detail: 'The API can reach PostgreSQL. The foundation is running.',
  },
  'database-down': {
    heading: 'PostgreSQL needs attention',
    detail: 'The API is running, but it cannot reach the local database. Start PostgreSQL and check again.',
  },
  'api-down': {
    heading: 'The API is unavailable',
    detail: 'Start the FastAPI service, then check the connection again.',
  },
}

function App() {
  const [health, setHealth] = useState<HealthState>('checking')

  useEffect(() => {
    let active = true
    void checkHealth().then((result) => {
      if (active) setHealth(result)
    })
    return () => {
      active = false
    }
  }, [])

  function refresh() {
    setHealth('checking')
    void checkHealth().then(setHealth)
  }

  const apiStatus = health === 'api-down' ? 'Unavailable' : health === 'checking' ? 'Checking' : 'Connected'
  const databaseStatus =
    health === 'ready' ? 'Connected' : health === 'database-down' ? 'Unavailable' : health === 'checking' ? 'Checking' : 'Unknown'

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Workbench information">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">FA</div>
          <div>
            <strong>Football Agent</strong>
            <span>Scouting workbench</span>
          </div>
        </div>
        <div className="sidebar-bottom">
          <span className="sidebar-label">CURRENT PHASE</span>
          <strong>Sprint 0 · Foundation</strong>
          <p>Building the reliable local base for player analysis.</p>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <span>Workspace / Overview</span>
          <span className="environment-tag"><span className="environment-dot" /> Local environment</span>
        </header>

        <div className="content">
          <div className="intro">
            <p className="eyebrow">SCOUTING PLATFORM · SETUP</p>
            <h1>Good scouting starts with a solid foundation.</h1>
            <p className="intro-copy">Your local workbench will bring player data, explainable search, and AI-assisted reports together. First, make sure the core services are connected.</p>
          </div>

          <section className="status-card" aria-labelledby="status-title">
            <div className="status-card-header">
              <div>
                <p className="eyebrow">SYSTEM CHECK</p>
                <h2 id="status-title">Connection status</h2>
              </div>
              <button type="button" onClick={refresh} disabled={health === 'checking'}>Check again</button>
            </div>

            <div className={`health-message health-${health}`} role="status" aria-live="polite">
              <span className="health-icon" aria-hidden="true" />
              <div>
                <strong>{copy[health].heading}</strong>
                <p>{copy[health].detail}</p>
              </div>
            </div>

            <div className="service-list" aria-label="Service details">
              <div className="service-row">
                <div><span className="service-symbol">A</span><span><strong>FastAPI</strong><small>Local application service</small></span></div>
                <span className={`service-state ${apiStatus.toLowerCase()}`}>{apiStatus}</span>
              </div>
              <div className="service-row">
                <div><span className="service-symbol">P</span><span><strong>PostgreSQL</strong><small>Local scouting database</small></span></div>
                <span className={`service-state ${databaseStatus.toLowerCase()}`}>{databaseStatus}</span>
              </div>
            </div>
          </section>

          <section className="next-section" aria-labelledby="next-title">
            <div>
              <p className="eyebrow">WHAT COMES NEXT</p>
              <h2 id="next-title">From connection to insight</h2>
            </div>
            <div className="next-grid">
              <article><span>01</span><h3>Load trusted data</h3><p>Bring in a small, documented sample of open football events.</p></article>
              <article><span>02</span><h3>Compare players</h3><p>Filter candidates with clear metrics and source context.</p></article>
              <article><span>03</span><h3>Explain the evidence</h3><p>Use a local model to draft reports grounded in the returned data.</p></article>
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
