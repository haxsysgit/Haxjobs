import { useNavigate } from 'react-router-dom'
import { Layers, Activity as ActivityIcon, Globe, User, Zap, AlertCircle, Send } from '../components/Icons'
import type { Job, DiscoveryStatus } from '../data/api'
import { api } from '../data/api'

export function Dashboard({ jobs, discovery, connected }: {
  jobs: Job[]
  discovery: DiscoveryStatus | null
  connected: boolean
}) {
  const navigate = useNavigate()
  const topJobs = [...jobs].sort((a, b) => b.fitScore - a.fitScore).slice(0, 4)
  const packCount = jobs.filter(j => j.status === 'completed').length

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <Layers size={18} style={{ color: 'var(--accent)', marginBottom: 2 }} />
          <span className="stat-label">Active Jobs</span>
          <span className="stat-value">{jobs.length}</span>
          <span className="stat-change">{packCount} packs ready</span>
        </div>
        <div className="stat-card">
          <Zap size={18} style={{ color: 'var(--success)', marginBottom: 2 }} />
          <span className="stat-label">Companies</span>
          <span className="stat-value">{discovery?.total_companies ?? '...'}</span>
          <span className="stat-change">{discovery?.lever_count ?? 0}L · {discovery?.ashby_count ?? 0}A · {discovery?.greenhouse_count ?? 0}G</span>
        </div>
        <div className="stat-card">
          <ActivityIcon size={18} style={{ color: 'var(--warning)', marginBottom: 2 }} />
          <span className="stat-label">Cron Jobs</span>
          <span className="stat-value">{discovery?.cron_jobs ?? '...'}</span>
        </div>
        <div className="stat-card">
          <AlertCircle size={18} style={{ color: connected ? 'var(--success)' : 'var(--danger)', marginBottom: 2 }} />
          <span className="stat-label">Status</span>
          <span className="stat-value" style={{ fontSize: 16 }}>{connected ? 'Connected' : 'Offline'}</span>
          <span className="stat-change">{connected ? 'API live' : 'Check Archilles'}</span>
        </div>
      </div>

      <div className="section-header">
        <h3>{topJobs.length ? 'Top Matches' : 'No jobs yet'}</h3>
        {jobs.length > 0 && <button className="btn btn-sm" onClick={() => navigate('/jobs')}>View All</button>}
      </div>
      <div className="pipeline-grid">
        {topJobs.map(job => (
          <div key={job.id} className="card job-card" onClick={() => navigate(`/jobs/${job.id}`)}>
            <div className="job-card-header">
              <div>
                <h3>{job.title}</h3>
                <p className="job-card-meta">{job.company} · {job.location}</p>
              </div>
              <span className={`badge ${job.fitScore >= 80 ? 'badge-strong' : job.fitScore >= 60 ? 'badge-good' : 'badge-weak'}`}>
                {job.fitScore >= 80 ? 'Strong' : job.fitScore >= 60 ? 'Good' : 'Weak'}
              </span>
            </div>
            <div className="job-card-score">
              <span className="score">{job.fitScore}%</span>
              <span className="score-label">fit</span>
            </div>
          </div>
        ))}
        {topJobs.length === 0 && (
          <div className="empty" style={{ gridColumn: '1 / -1' }}>
            <Zap size={24} />
            <h3>No jobs evaluated yet</h3>
            <p>Queue a job via Telegram, email, or the Pipeline view.</p>
          </div>
        )}
      </div>

      <div className="section-header" style={{ marginTop: 28 }}>
        <h3>Quick Actions</h3>
      </div>
      <div className="quick-actions">
        <button className="btn" onClick={() => navigate('/jobs')}>
          <Layers size={14} /> View Pipeline
        </button>
        <button className="btn" onClick={async () => {
          try { await api.triggerPipeline(); alert('Pipeline triggered — evaluating next pending job') }
          catch { alert('Failed to trigger pipeline') }
        }}>
          <Send size={14} /> Evaluate Next Job
        </button>
        <button className="btn" onClick={() => navigate('/profile')}>
          <User size={14} /> Edit Profile
        </button>
        <button className="btn" onClick={() => navigate('/discovery')}>
          <Globe size={14} /> Manage Companies
        </button>
        <button className="btn" onClick={() => navigate('/activity')}>
          <ActivityIcon size={14} /> Activity Log
        </button>
      </div>
    </div>
  )
}
