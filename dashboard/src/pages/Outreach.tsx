import { useState, useEffect } from 'react'
import { Send, Mail, Clock } from '../components/Icons'
import { api, type Job } from '../data/api'

export function Outreach() {
  const [jobs, setJobs] = useState<Job[]>([])

  useEffect(() => {
    async function load() {
      try {
        const all = await api.getJobs()
        setJobs(all.filter(j => j.fitScore >= 60))
      } catch { /* offline */ }
    }
    load()
  }, [])

  const outreachReady = jobs.filter(j => (j as any).outreach_status === 'draft_ready')
  const outreachPending = jobs.filter(j => (j as any).outreach_status === 'pending')
  const eligible = jobs.filter(j => j.fitScore >= 80 && !(j as any).outreach_status)

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <Send size={18} style={{ color: 'var(--success)', marginBottom: 2 }} />
          <span className="stat-label">Drafts Ready</span>
          <span className="stat-value">{outreachReady.length}</span>
          <span className="stat-change">Ready for review</span>
        </div>
        <div className="stat-card">
          <Clock size={18} style={{ color: 'var(--warning)', marginBottom: 2 }} />
          <span className="stat-label">Pending Search</span>
          <span className="stat-value">{outreachPending.length}</span>
          <span className="stat-change">Finding contacts</span>
        </div>
        <div className="stat-card">
          <Mail size={18} style={{ color: 'var(--accent)', marginBottom: 2 }} />
          <span className="stat-label">Eligible (80%+)</span>
          <span className="stat-value">{eligible.length}</span>
          <span className="stat-change">Outreach not yet queued</span>
        </div>
      </div>

      <div className="section-header">
        <h3>Drafts Ready for Review</h3>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>Approve or edit before sending</span>
      </div>

      {outreachReady.length === 0 && outreachPending.length === 0 ? (
        <div className="empty">
          <Send size={32} />
          <h3>No outreach drafts yet</h3>
          <p>When a job scores 80%+ and passes all filters, Archilles will find the hiring team and draft an intro email here for your review.</p>
          <div style={{ marginTop: 16, fontSize: 13, color: 'var(--body)', textAlign: 'left', maxWidth: 500, margin: '16px auto 0' }}>
            <strong>How it works:</strong>
            <ol style={{ marginTop: 8, paddingLeft: 20 }}>
              <li style={{ marginBottom: 6 }}>Job scores 80%+ fit → marked for outreach</li>
              <li style={{ marginBottom: 6 }}>Archilles searches for engineering leads at the company</li>
              <li style={{ marginBottom: 6 }}>Drafts a short intro email in your voice</li>
              <li style={{ marginBottom: 6 }}>You review here, tweak if needed, then send</li>
            </ol>
          </div>
        </div>
      ) : (
        <div className="pipeline-grid">
          {[...outreachReady, ...outreachPending].map(job => (
            <div key={job.id} className="card" style={{ cursor: 'default' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <h3 style={{ marginBottom: 2 }}>{job.title}</h3>
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>{job.company}</p>
                </div>
                <span className={`badge ${(job as any).outreach_status === 'draft_ready' ? 'badge-strong' : 'badge-weak'}`} style={{ fontSize: 10 }}>
                  {(job as any).outreach_status === 'draft_ready' ? 'Ready' : 'Searching'}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 8 }}>
                <span className="score" style={{ fontSize: 22 }}>{job.fitScore}%</span>
                <span className="score-label">fit</span>
              </div>
              <div style={{ marginTop: 10, display: 'flex', gap: 6 }}>
                {(job as any).outreach_status === 'draft_ready' ? (
                  <button className="btn btn-primary btn-sm">
                    <Mail size={12} /> Review Draft
                  </button>
                ) : (
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>Contact search in progress...</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
