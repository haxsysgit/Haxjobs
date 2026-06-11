export function Settings() {
  return (
    <div>
      <div className="section-header">
        <h3>Pipeline Settings</h3>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 12 }}>
        <div className="card">
          <h3>Notification Preferences</h3>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>Where and how Archilles notifies you</p>
          <div style={{ fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Email for 80%+ jobs</span>
              <span className="badge badge-strong">ON</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Telegram for 60-79%</span>
              <span className="badge badge-strong">ON</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Outreach drafts</span>
              <span className="badge badge-strong">ON</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
              <span>Daily job report</span>
              <span className="badge badge-good">6pm</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Pipeline Schedule</h3>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>How often Archilles runs each phase</p>
          <div style={{ fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Discovery scrapers</span>
              <span style={{ color: 'var(--muted)' }}>Daily / 2 days</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Pipeline evaluation</span>
              <span style={{ color: 'var(--muted)' }}>Every 3 hours</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Email intake check</span>
              <span style={{ color: 'var(--muted)' }}>Every 30 min</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
              <span>Company career pages</span>
              <span style={{ color: 'var(--muted)' }}>Every 2 days</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>Data & Storage</h3>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 10 }}>Pipeline state and pack management</p>
          <div style={{ fontSize: 13 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Intake retention</span>
              <span style={{ color: 'var(--muted)' }}>Keep all (audit trail)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--grid)' }}>
              <span>Pack storage</span>
              <span style={{ color: 'var(--muted)' }}>~/job-pipeline/packs/</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0' }}>
              <span>API + Dashboard</span>
              <span style={{ color: 'var(--muted)' }}>Port 8800</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3>About</h3>
          <p style={{ fontSize: 13, marginBottom: 8 }}>
            Archilles Job Pipeline v1.0
          </p>
          <p style={{ fontSize: 12, color: 'var(--muted)' }}>
            Built on Hermes Agent. Discovery scrapers + evaluation pipeline + dashboard.
            95+ companies tracked across Lever, Ashby, and Greenhouse ATS platforms.
          </p>
          <p style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
            Dashboard: React + TypeScript + Vite<br />
            API: Python stdlib http.server<br />
            Pipeline: Bash + Python + Hermes skills + system crontab
          </p>
        </div>
      </div>
    </div>
  )
}
