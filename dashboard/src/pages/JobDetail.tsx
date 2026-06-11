import { ChevronLeft, ExternalLink, AlertCircle, CheckCircle, Clock } from '../components/Icons'
import type { Job } from '../data/api'

export function JobDetailPage({ job, onBack }: { job: Job; onBack: () => void }) {
  const isEvaluated = (job.status === 'evaluated' || job.status === 'completed') && job.fitScore > 0
  const isSkipped = job.status === 'skipped'
  const isPending = job.status === 'pending'
  const isApproved = job.status === 'approved'

  return (
    <div>
      <button className="btn btn-ghost" onClick={onBack} style={{ marginBottom: 20 }}>
        <ChevronLeft size={14} /> Back to Pipeline
      </button>

      <div className="detail-grid">
        <div className="detail-main">
          <h2>{job.title}</h2>
          <div className="detail-meta">
            <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{job.company}</span>
            <span>·</span>
            <span>{job.location}</span>
            <span>·</span>
            <span className={`badge ${isApproved ? 'badge-strong' : isSkipped ? 'badge-skip' : 'badge-neutral'}`} style={{ fontSize: 10 }}>
              {job.status}
            </span>
            {job.applicationUrl && (
              <>
                <span>·</span>
                <a href={job.applicationUrl} target="_blank" rel="noopener" className="btn btn-sm"
                  style={{ textDecoration: 'none' }}>
                  <ExternalLink size={12} /> Apply
                </a>
              </>
            )}
          </div>

          {/* Skipped jobs — show skip reason prominently */}
          {isSkipped && (
            <div className="detail-section" style={{ borderLeft: '3px solid var(--danger)', paddingLeft: 14 }}>
              <h3 style={{ color: 'var(--danger)' }}>Skipped</h3>
              <p style={{ fontSize: 14, lineHeight: 1.65 }}>{(job as any).skipReason || 'No reason recorded'}</p>
            </div>
          )}

          {/* Approved jobs — show approval note */}
          {isApproved && (
            <div className="detail-section" style={{ borderLeft: '3px solid var(--success)', paddingLeft: 14 }}>
              <h3 style={{ color: 'var(--success)' }}>Manually Approved</h3>
              <p style={{ fontSize: 14 }}>This job was manually approved and is ready for pack generation. It bypassed automatic evaluation.</p>
            </div>
          )}

          {/* Pending jobs — show that it's awaiting evaluation */}
          {isPending && (
            <div className="detail-section" style={{ borderLeft: '3px solid var(--warning)', paddingLeft: 14 }}>
              <h3 style={{ color: 'var(--warning)' }}>Pending Evaluation</h3>
              <p style={{ fontSize: 14 }}>This job is in the queue waiting for Hermes to evaluate it. The pipeline processes one job every 30 minutes.</p>
            </div>
          )}

          {/* Evaluated jobs — show fit details */}
          {isEvaluated && (
            <>
              <div className="detail-section">
                <h3>Fit Summary</h3>
                <p style={{ fontSize: 14, lineHeight: 1.65 }}>{job.summary}</p>
              </div>

              <div className="detail-section">
                <h3>Strongest Matches</h3>
                <ul>
                  {job.strongestMatches.map((m, i) => (
                    <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                      <CheckCircle size={14} style={{ color: 'var(--success)', flexShrink: 0, marginTop: 3 }} />
                      {m}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="detail-section">
                <h3>Major Gaps</h3>
                <ul>
                  {job.majorGaps.map((g, i) => (
                    <li key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                      <AlertCircle size={14} style={{ color: 'var(--warning)', flexShrink: 0, marginTop: 3 }} />
                      {g}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {/* Application Pack section — only for evaluated and approved jobs */}
          {(isEvaluated || isApproved) && (
            <div className="detail-section">
              <h3>Application Pack</h3>
              {job.packDir ? (
                <div className="card" style={{ padding: '12px 16px' }}>
                  <p style={{ fontSize: 13, margin: 0 }}>Pack location: <code style={{ fontSize: 11, wordBreak: 'break-all' }}>{job.packDir}</code></p>
                </div>
              ) : (
                <div className="card" style={{ padding: '12px 16px' }}>
                  <p style={{ fontSize: 13, color: 'var(--muted)', margin: 0 }}>No application pack generated yet. Packs are generated for jobs scoring 60%+ or manually approved jobs.</p>
                </div>
              )}
            </div>
          )}
        </div>

        <aside>
          {/* Score — only for evaluated jobs */}
          {isEvaluated && (
            <div className="sidebar-card">
              <h4>Fit Score</h4>
              <div className="score" style={{ fontSize: 32 }}>{job.fitScore}%</div>
              <span className={`badge ${job.level === 1 ? 'badge-strong' : job.level === 2 ? 'badge-good' : 'badge-weak'}`}
                style={{ marginTop: 8 }}>
                Level {job.level} · {job.levelName}
              </span>
            </div>
          )}

          {/* Status card for non-evaluated */}
          {!isEvaluated && (
            <div className="sidebar-card">
              <h4>Status</h4>
              <span className={`badge ${isApproved ? 'badge-strong' : isSkipped ? 'badge-skip' : 'badge-neutral'}`}
                style={{ fontSize: 14 }}>
                {job.status}
              </span>
              {isApproved && <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>Ready for pack generation</p>}
              {isSkipped && <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>Use Unskip or Approve to override</p>}
              {isPending && <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 8 }}>Awaiting evaluation</p>}
            </div>
          )}

          {job.sponsorshipRisk && (
            <div className="sidebar-card">
              <h4>Sponsorship Risk</h4>
              <span className={`badge ${job.sponsorshipRisk === 'low' ? 'badge-strong' : job.sponsorshipRisk === 'medium' ? 'badge-weak' : 'badge-skip'}`}>
                {job.sponsorshipRisk}
              </span>
            </div>
          )}

          <div className="sidebar-card">
            <h4>Timeline</h4>
            <div style={{ fontSize: 12, color: 'var(--muted)', display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Clock size={12} />
                Received: {new Date(job.receivedAt).toLocaleDateString()}
              </div>
              {job.processedAt && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <CheckCircle size={12} style={{ color: 'var(--success)' }} />
                  Processed: {new Date(job.processedAt).toLocaleDateString()}
                </div>
              )}
            </div>
          </div>

          {job.packDir && (
            <div className="sidebar-card">
              <h4>Pack Location</h4>
              <code style={{ fontSize: 11, wordBreak: 'break-all', color: 'var(--muted)' }}>
                {job.packDir}
              </code>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
