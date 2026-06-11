import { useState } from 'react'
import { api, type DiscoveryStatus } from '../data/api'

export function Discovery({ data, connected }: { data: DiscoveryStatus | null; connected: boolean }) {
  const d = data ?? { total_companies: '...', lever_count: 0, ashby_count: 0, greenhouse_count: 0, cron_jobs: 0, last_pipeline_run: null }
  const [showAdd, setShowAdd] = useState(false)
  const [newCompany, setNewCompany] = useState({ name: '', url: '', platform: 'lever' })

  const handleAdd = async () => {
    if (!newCompany.name.trim()) return
    try {
      await api.queueIntake({
        jd_text: `Manual company watch: ${newCompany.name}. Career page: ${newCompany.url}. Platform: ${newCompany.platform}.`,
        source: 'manual_discovery',
        company: newCompany.name,
        title: `Watch: ${newCompany.name} Career Page`,
        url: newCompany.url,
      })
      setNewCompany({ name: '', url: '', platform: 'lever' })
      setShowAdd(false)
    } catch { /* will refresh on next poll */ }
  }

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Companies Tracked</span>
          <span className="stat-value">{d.total_companies}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Cron Jobs</span>
          <span className="stat-value">{d.cron_jobs}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">ATS Platforms</span>
          <span className="stat-value">3</span>
          <span className="stat-change">{d.lever_count}L · {d.ashby_count}A · {d.greenhouse_count}G</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Status</span>
          <span className="stat-value" style={{ fontSize: 16 }}>{connected ? 'Connected' : 'Offline'}</span>
        </div>
      </div>

      {/* Add Company */}
      <div className="section-header">
        <h3>Add Company to Watch</h3>
        <button className="btn btn-sm btn-primary" onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? 'Cancel' : '+ Add Company'}
        </button>
      </div>
      {showAdd && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 10, alignItems: 'end' }}>
            <div className="profile-field" style={{ marginBottom: 0 }}>
              <label>Company Name</label>
              <input placeholder="e.g. Stripe" value={newCompany.name}
                onChange={e => setNewCompany({ ...newCompany, name: e.target.value })} />
            </div>
            <div className="profile-field" style={{ marginBottom: 0 }}>
              <label>Career Page URL</label>
              <input placeholder="https://jobs.lever.co/stripe" value={newCompany.url}
                onChange={e => setNewCompany({ ...newCompany, url: e.target.value })} />
            </div>
            <div className="profile-field" style={{ marginBottom: 0 }}>
              <label>Platform</label>
              <select value={newCompany.platform}
                onChange={e => setNewCompany({ ...newCompany, platform: e.target.value })}
                style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', fontSize: 13, fontFamily: 'var(--font)', background: 'white' }}>
                <option value="lever">Lever</option>
                <option value="ashby">Ashby</option>
                <option value="greenhouse">Greenhouse</option>
                <option value="workday">Workday</option>
                <option value="other">Other / Unknown</option>
              </select>
            </div>
            <button className="btn btn-primary" onClick={handleAdd}>Add</button>
          </div>
        </div>
      )}

      {/* Scraper Schedule */}
      <div className="section-header" style={{ marginTop: 10 }}>
        <h3>Active Scrapers</h3>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
        {[
          { name: 'Lever Scraper', schedule: 'Every 2 days', count: d.lever_count, status: 'active', detail: `${d.lever_count} companies` },
          { name: 'Ashby Scraper', schedule: 'Every 2 days', count: d.ashby_count, status: 'active', detail: `${d.ashby_count} companies` },
          { name: 'Greenhouse Scraper', schedule: 'Every 2 days', count: d.greenhouse_count, status: 'active', detail: `${d.greenhouse_count} companies` },
          { name: 'HN Who Is Hiring', schedule: '1st of month', count: '-', status: 'active', detail: 'Monthly thread' },
          { name: 'Reed Discovery', schedule: 'Weekly', count: '-', status: 'paused', detail: 'Company discovery only' },
          { name: 'Mongoose Jobs', schedule: 'Weekly', count: '-', status: 'planned', detail: 'Coming next' },
        ].map(s => (
          <div key={s.name} className="card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ marginBottom: 2, fontSize: 13 }}>{s.name}</h3>
              <span className={`badge ${s.status === 'active' ? 'badge-strong' : s.status === 'paused' ? 'badge-weak' : 'badge-neutral'}`}
                style={{ fontSize: 10 }}>{s.status}</span>
            </div>
            <p className="job-card-meta">{s.schedule} · {s.detail}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
