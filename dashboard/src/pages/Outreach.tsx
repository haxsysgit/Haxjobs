import { useState, useEffect } from 'react'
import { Send, CheckCircle, X, FileText, ExternalLink } from '../components/Icons'

interface OutreachJob {
  id: number
  title: string
  company: string
  location: string
  sourceUrl: string
  fitScore: number
  fitVerdict: string
  levelName: string
  summary: string
  outreachStatus: string
  packStatus: string
  packDir: string
  roleFamily: string
  recommendedCvVariant: string
  draftCount: number
  approvedCount: number
  sentCount: number
  contactCount: number
}

interface OutreachDraft {
  id: number
  jobId: number
  contactId: number | null
  subject: string
  messageText: string
  status: string
  sentAt: string | null
  createdAt: string
  jobTitle: string
  jobCompany: string
  outreachStatus: string
  packDir: string
  packStatus: string
  fitScore: number
  fitVerdict: string
  contactName: string
  contactTitle: string
}

const API = '/api'

async function fetchJSON(url: string, options?: RequestInit) {
  const r = await fetch(url, options)
  return r.json()
}

export function Outreach() {
  const [jobs, setJobs] = useState<OutreachJob[]>([])
  const [drafts, setDrafts] = useState<OutreachDraft[]>([])
  const [selectedJob, setSelectedJob] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState('')

  const load = async () => {
    try {
      const [j, d] = await Promise.all([
        fetchJSON(`${API}/outreach/jobs`),
        fetchJSON(`${API}/outreach/drafts`),
      ])
      setJobs(j)
      setDrafts(d)
    } catch { /* offline */ }
    setLoading(false)
  }

  // Fetch-on-mount — no external system to subscribe to
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { load() }, [])

  const handleApprove = async (draftId: number) => {
    setActionMsg('')
    try {
      const r = await fetchJSON(`${API}/outreach/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft_id: draftId }),
      })
      if (r.ok) {
        setActionMsg(`Draft #${draftId} approved`)
        load()
      } else {
        setActionMsg(`Error: ${r.error}`)
      }
    } catch {
      setActionMsg('Network error')
    }
  }

  const handleReject = async (draftId: number) => {
    setActionMsg('')
    try {
      const r = await fetchJSON(`${API}/outreach/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draft_id: draftId, reason: 'Rejected from dashboard' }),
      })
      if (r.ok) {
        setActionMsg(`Draft #${draftId} rejected`)
        load()
      } else {
        setActionMsg(`Error: ${r.error}`)
      }
    } catch {
      setActionMsg('Network error')
    }
  }

  const draftCount = drafts.filter(d => d.status === 'draft').length
  const approvedCount = drafts.filter(d => d.status === 'approved').length
  const rejectedCount = drafts.filter(d => d.status === 'rejected').length

  const filteredDrafts = selectedJob
    ? drafts.filter(d => d.jobId === selectedJob)
    : drafts.filter(d => d.status === 'draft')

  if (loading) {
    return <div className="empty"><h3>Loading...</h3></div>
  }

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <Send size={18} style={{ color: 'var(--warning)', marginBottom: 2 }} />
          <span className="stat-label">Pending Review</span>
          <span className="stat-value">{draftCount}</span>
          <span className="stat-change">Awaiting your approval</span>
        </div>
        <div className="stat-card">
          <CheckCircle size={18} style={{ color: 'var(--success)', marginBottom: 2 }} />
          <span className="stat-label">Approved</span>
          <span className="stat-value">{approvedCount}</span>
          <span className="stat-change">Ready to send</span>
        </div>
        <div className="stat-card">
          <X size={18} style={{ color: 'var(--muted)', marginBottom: 2 }} />
          <span className="stat-label">Rejected</span>
          <span className="stat-value">{rejectedCount}</span>
          <span className="stat-change">Skipped drafts</span>
        </div>
      </div>

      {actionMsg && (
        <div style={{
          padding: '8px 12px', margin: '0 0 12px 0', borderRadius: 6,
          background: actionMsg.includes('Error') ? 'var(--danger-bg)' : 'var(--success-bg)',
          color: actionMsg.includes('Error') ? 'var(--danger)' : 'var(--success)',
          fontSize: 12,
        }}>
          {actionMsg}
        </div>
      )}

      {/* Job filter tabs */}
      {jobs.length > 0 && (
        <div style={{ marginBottom: 16, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <button
            className={`btn ${!selectedJob ? 'btn-primary' : 'btn-ghost'} btn-sm`}
            onClick={() => setSelectedJob(null)}
          >
            All Drafts ({draftCount})
          </button>
          {jobs.map(j => (
            <button
              key={j.id}
              className={`btn ${selectedJob === j.id ? 'btn-primary' : 'btn-ghost'} btn-sm`}
              onClick={() => setSelectedJob(j.id)}
            >
              {j.company} · {j.fitScore}% ({j.draftCount})
            </button>
          ))}
        </div>
      )}

      {/* Selected job detail */}
      {selectedJob && (() => {
        const job = jobs.find(j => j.id === selectedJob)
        if (!job) return null
        return (
          <div className="card" style={{ marginBottom: 16, background: 'var(--surface)', border: '1px solid var(--grid)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
              <div>
                <h3 style={{ margin: '0 0 4px 0', fontSize: 15 }}>{job.title}</h3>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                  {job.company} · {job.location} · {job.fitScore}% fit · {job.levelName}
                </p>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                {job.packDir && (
                  <a
                    href={`/api/pack-detail?dir=${encodeURIComponent(job.packDir)}`}
                    className="btn btn-ghost btn-sm"
                    target="_blank" rel="noopener"
                    style={{ textDecoration: 'none' }}
                  >
                    <FileText size={12} /> Pack
                  </a>
                )}
                {job.sourceUrl && (
                  <a href={job.sourceUrl} className="btn btn-ghost btn-sm" target="_blank" rel="noopener" style={{ textDecoration: 'none' }}>
                    <ExternalLink size={12} /> JD
                  </a>
                )}
              </div>
            </div>
            {job.summary && <p style={{ fontSize: 12, color: 'var(--body)', margin: '4px 0 0 0' }}>{job.summary}</p>}
          </div>
        )
      })()}

      {/* Drafts list */}
      {filteredDrafts.length === 0 ? (
        <div className="empty">
          <Send size={32} />
          <h3>No outreach drafts yet</h3>
          <p>When high-fit jobs are evaluated, Archilles will draft outreach messages here for your review.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {filteredDrafts.map(draft => (
            <div key={draft.id} className="card" style={{
              background: 'var(--surface)',
              border: draft.status === 'approved' ? '1px solid var(--success)' :
                     draft.status === 'rejected' ? '1px solid var(--danger)' :
                     '1px solid var(--grid)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: 'var(--muted)', fontWeight: 500 }}>
                      {draft.jobTitle?.slice(0, 40)} at {draft.jobCompany}
                    </span>
                    <span style={{
                      fontSize: 10, padding: '1px 6px', borderRadius: 4,
                      background: draft.fitScore >= 80 ? 'var(--success-bg)' : 'var(--warning-bg)',
                      color: draft.fitScore >= 80 ? 'var(--success)' : 'var(--warning)',
                    }}>
                      {draft.fitScore}%
                    </span>
                  </div>
                  <h4 style={{ margin: '0 0 2px 0', fontSize: 13, color: 'var(--heading)' }}>
                    {draft.subject}
                  </h4>
                  {draft.contactName && (
                    <span style={{ fontSize: 11, color: 'var(--accent)' }}>
                      To: {draft.contactName} · {draft.contactTitle}
                    </span>
                  )}
                  <span style={{
                    fontSize: 10, padding: '1px 6px', borderRadius: 4, marginLeft: 8,
                    background: draft.status === 'approved' ? 'var(--success-bg)' :
                               draft.status === 'rejected' ? 'var(--danger-bg)' :
                               draft.status === 'sent' ? 'var(--accent-bg)' :
                               'var(--muted-bg)',
                    color: draft.status === 'approved' ? 'var(--success)' :
                           draft.status === 'rejected' ? 'var(--danger)' :
                           draft.status === 'sent' ? 'var(--accent)' :
                           'var(--muted)',
                  }}>
                    {draft.status}
                  </span>
                </div>
              </div>

              <pre style={{
                background: 'var(--bg)', padding: '12px 14px', borderRadius: 6,
                fontSize: 12, lineHeight: 1.6, color: 'var(--body)',
                whiteSpace: 'pre-wrap', margin: '8px 0', fontFamily: 'inherit',
              }}>
                {draft.messageText}
              </pre>

              {draft.status === 'draft' && (
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleApprove(draft.id)}
                  >
                    <CheckCircle size={14} /> Approve
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => handleReject(draft.id)}
                    style={{ color: 'var(--danger)' }}
                  >
                    <X size={14} /> Reject
                  </button>
                </div>
              )}

              {draft.packDir && (
                <div style={{ marginTop: 8, fontSize: 11, color: 'var(--muted)' }}>
                  Pack:{' '}
                  <a
                    href={`/api/pack-detail?dir=${encodeURIComponent(draft.packDir)}`}
                    target="_blank" rel="noopener"
                    style={{ color: 'var(--accent)' }}
                  >
                    {draft.packDir}
                  </a>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
