import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Star } from '../components/Icons'
import { api, type Job } from '../data/api'

interface Props {
  jobs: Job[]
  onUnskip: (j: Job) => void
  onApprove: (j: Job) => void
  connected: boolean
}

function JobCard({ job, onToggleFav, onToggleAuto, onGeneratePack, onReviewPack }: {
  job: Job
  onToggleFav: (j: Job) => void
  onToggleAuto?: (j: Job) => void
  onGeneratePack?: (j: Job) => void
  onReviewPack?: (j: Job, action: 'approve' | 'reject' | 'changes') => void
}) {
  const navigate = useNavigate()
  return (
    <div className="card job-card" onClick={() => navigate(`/jobs/${job.id}`)}>
      <div className="job-card-topline">
        <div className="job-card-title-block">
          <h3>{job.title}</h3>
          <p className="job-card-meta">{job.company} · {job.location || 'Location TBD'}</p>
        </div>
        <div className="job-card-actions">
          {job.fitScore > 0 && (
            <span className={`badge job-score-badge ${job.fitScore >= 80 ? 'badge-strong' : job.fitScore >= 60 ? 'badge-good' : 'badge-weak'}`}>
              {job.fitScore}%
            </span>
          )}
          {onToggleAuto && (
            <button className={`btn-bookmark btn-auto${job.isAutoApply ? ' bookmarked' : ''}`}
              onClick={e => { e.stopPropagation(); onToggleAuto(job) }}
              title="Toggle assisted apply intent">
              Auto
            </button>
          )}
          <button className={`btn-bookmark${job.isFavorite ? ' bookmarked' : ''}`}
            onClick={e => { e.stopPropagation(); onToggleFav(job) }}
            title="Toggle favorite">
            <Star size={14} fill={job.isFavorite ? 'currentColor' : 'none'} />
          </button>
        </div>
      </div>
      {job.strongestMatches && job.strongestMatches.length > 0 && (
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
          {job.strongestMatches.slice(0, 2).join(' · ')}
        </div>
      )}
      <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <span className="badge badge-neutral" style={{ fontSize: 10 }}>{job.source}</span>
        {job.recommendedCvVariant && job.recommendedCvVariant !== 'unknown' && (
          <span className="badge badge-good" style={{ fontSize: 10 }}>CV: {job.recommendedCvVariant.replaceAll('_', ' ')}</span>
        )}
        {job.sourceQuality && job.sourceQuality !== 'unknown' && (
          <span className="badge badge-neutral" style={{ fontSize: 10 }}>{job.sourceQuality}</span>
        )}
        <span className="badge badge-neutral" style={{ fontSize: 10 }}>{job.status}</span>
        {job.isSaved && <span className="badge badge-good" style={{ fontSize: 10 }}>Saved</span>}
        {job.isApproved && <span className="badge badge-strong" style={{ fontSize: 10 }}>Approved</span>}
        {job.packStatus && job.packStatus !== 'none' && (
          <span className="badge badge-good" style={{ fontSize: 10 }}>Pack: {job.packStatus.replaceAll('_', ' ')}</span>
        )}
      </div>
      {(onGeneratePack || onReviewPack) && (
        <div className="job-pack-actions">
          {onGeneratePack && (!job.packStatus || job.packStatus === 'none') && job.fitScore >= 50 && (
            <button className="btn btn-sm" onClick={e => { e.stopPropagation(); onGeneratePack(job) }}>
              Generate Pack
            </button>
          )}
          {onReviewPack && job.packStatus === 'generated' && (
            <>
              <button className="btn btn-sm btn-primary" onClick={e => { e.stopPropagation(); onReviewPack(job, 'approve') }}>
                Approve Pack
              </button>
              <button className="btn btn-sm" onClick={e => { e.stopPropagation(); onReviewPack(job, 'changes') }}>
                Changes
              </button>
              <button className="btn btn-sm" onClick={e => { e.stopPropagation(); onReviewPack(job, 'reject') }}>
                Reject
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export function Evaluated({ jobs, onToggleFav, onToggleAuto, onGeneratePack, onReviewPack }: {
  jobs: Job[]
  onToggleFav: (j: Job) => void
  onToggleAuto: (j: Job) => void
  onGeneratePack: (j: Job) => void
  onReviewPack: (j: Job, action: 'approve' | 'reject' | 'changes') => void
}) {
  return (
    <div className="pipeline-grid">
      {jobs.map(j => <JobCard key={j.id} job={j} onToggleFav={onToggleFav} onToggleAuto={onToggleAuto} onGeneratePack={onGeneratePack} onReviewPack={onReviewPack} />)}
      {jobs.length === 0 && <div className="empty" style={{ gridColumn: '1 / -1' }}><h3>No evaluated jobs</h3><p>Jobs with fit scores appear here after Hermes evaluates them.</p></div>}
    </div>
  )
}

export function PendingList({ jobs }: { jobs: Job[] }) {
  const navigate = useNavigate()
  return (
    <div className="pipeline-grid">
      {jobs.map(j => (
        <div key={j.id} className="card job-card" onClick={() => navigate(`/jobs/${j.id}`)} style={{ opacity: 0.7 }}>
          <h3 style={{ fontSize: 13 }}>{j.title}</h3>
          <p style={{ fontSize: 12, color: 'var(--muted)' }}>{j.company}</p>
          <span className="badge badge-neutral" style={{ fontSize: 10, marginTop: 6 }}>{j.source}</span>
        </div>
      ))}
      {jobs.length === 0 && <div className="empty" style={{ gridColumn: '1 / -1' }}><h3>No pending jobs</h3><p>Newly discovered jobs wait here for evaluation.</p></div>}
    </div>
  )
}

export function FilteredList({ jobs, onUnskip, onApprove, onToggleFav }: {
  jobs: Job[]
  onUnskip: (j: Job) => void
  onApprove: (j: Job) => void
  onToggleFav: (j: Job) => void
}) {
  const navigate = useNavigate()
  return (
    <div className="pipeline-grid">
      {jobs.map(j => {
        const reason = j.skipReason || j.status
        return (
          <div key={j.id} className="card" style={{ opacity: 0.55, cursor: 'pointer', position: 'relative' }}
            onClick={() => navigate(`/jobs/${j.id}`)}>
            <button className={`btn-bookmark${j.isFavorite ? ' bookmarked' : ''}`}
              style={{ position: 'absolute', top: 8, right: 8 }}
              onClick={e => { e.stopPropagation(); onToggleFav(j) }}>
              <Star size={14} fill={j.isFavorite ? 'currentColor' : 'none'} />
            </button>
            <h3 style={{ fontSize: 12 }}>{j.title}</h3>
            <p style={{ fontSize: 11, color: 'var(--muted)', margin: '2px 0' }}>{j.company}</p>
            <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
              <span className="badge badge-skip" style={{ fontSize: 10 }}>{reason}</span>
              <span className="badge badge-neutral" style={{ fontSize: 10 }}>{j.source}</span>
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
              <button className="btn btn-sm" style={{ flex: 1 }}
                onClick={e => { e.stopPropagation(); onUnskip(j) }}>
                Unskip
              </button>
              <button className="btn btn-sm btn-primary" style={{ flex: 1 }}
                onClick={e => { e.stopPropagation(); onApprove(j) }}>
                Approve
              </button>
            </div>
          </div>
        )
      })}
      {jobs.length === 0 && <div className="empty" style={{ gridColumn: '1 / -1' }}><h3>No filtered jobs</h3><p>Jobs that don't require attention are listed here.</p></div>}
    </div>
  )
}

export function Pipeline({ jobs, onUnskip, onApprove, connected }: Props) {
  const [subView, setSubView] = useState<'evaluated' | 'pending' | 'favorites' | 'filtered'>('evaluated')
  const [favJobs, setFavJobs] = useState<Job[]>([])
  const [search, setSearch] = useState('')
  const [packStatusById, setPackStatusById] = useState<Record<string, string>>({})

  // Derive autoApplyById from jobs — no separate state needed
  const autoApplyById: Record<string, boolean> = {}
  jobs.forEach(job => {
    if (job.isAutoApply !== undefined) autoApplyById[job.id] = job.isAutoApply
  })

  useEffect(() => {
    if (!connected) return
    api.getFavorites()
      .then(favs => setFavJobs(favs))
      .catch(() => {})
  }, [connected, jobs])

  const searchLower = search.toLowerCase()
  const hydrateJob = (j: Job): Job => ({
    ...j,
    isAutoApply: autoApplyById[j.id] ?? j.isAutoApply ?? false,
    packStatus: packStatusById[j.id] ?? j.packStatus,
  })
  const visibleJobs = jobs.map(hydrateJob)
  const visibleFavJobs = favJobs.map(hydrateJob)
  const filterSearch = (j: Job) =>
    !search || j.title.toLowerCase().includes(searchLower) || j.company.toLowerCase().includes(searchLower)

  const evaluated = visibleJobs.filter(j => (j.status === 'evaluated' || j.status === 'completed') && j.fitScore > 0 && filterSearch(j))
  const pending = visibleJobs.filter(j => j.status === 'pending' && filterSearch(j))
  const filtered = visibleJobs.filter(j => j.status === 'skipped' && filterSearch(j))

  const tabs = [
    { key: 'evaluated' as const, label: 'Evaluated', count: jobs.filter(j => (j.status === 'evaluated' || j.status === 'completed') && j.fitScore > 0).length },
    { key: 'pending' as const, label: 'Pending', count: jobs.filter(j => j.status === 'pending').length },
    { key: 'favorites' as const, label: 'Favorites', count: favJobs.length },
    { key: 'filtered' as const, label: 'Filtered', count: jobs.filter(j => j.status === 'skipped').length },
  ]

  const handleToggleFav = async (job: Job) => {
    try {
      if (job.isFavorite) {
        await api.removeFavorite(job.id)
      } else {
        await api.addFavorite(job.id)
      }
      const favs = await api.getFavorites()
      setFavJobs(favs)
    } catch (err) {
      console.error('Failed to toggle favorite:', err)
    }
  }

  const handleToggleAuto = async (job: Job) => {
    try {
      const result = await api.toggleAutoApply(job.id)
      setFavJobs(prev => prev.map(j => j.id === job.id ? { ...j, isAutoApply: Boolean(result.auto_apply) } : j))
    } catch (err) {
      console.error('Failed to toggle auto-apply:', err)
    }
  }

  const handleGeneratePack = async (job: Job) => {
    try {
      const result = await api.generatePack(job.id)
      if (result.ok) {
        setPackStatusById(prev => ({ ...prev, [job.id]: 'generated' }))
      }
    } catch (err) {
      console.error('Failed to generate pack:', err)
    }
  }

  const handleReviewPack = async (job: Job, action: 'approve' | 'reject' | 'changes') => {
    try {
      const notes = action === 'approve' ? 'Approved from dashboard' : `Marked ${action} from dashboard`
      const result = await api.reviewPack(job.id, action, notes)
      if (result.ok && result.pack_status) {
        const packStatus: string = result.pack_status
        setPackStatusById(prev => ({ ...prev, [job.id]: packStatus }))
      }
    } catch (err) {
      console.error('Failed to review pack:', err)
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14, alignItems: 'center' }}>
        <div className="sub-nav" style={{ marginBottom: 0, flex: 1 }}>
          {tabs.map(t => (
            <a key={t.key} href="#" className={subView === t.key ? 'active' : ''}
              onClick={e => { e.preventDefault(); setSubView(t.key); setSearch('') }}>
              {t.label} <span className="sub-nav-badge">{t.count}</span>
            </a>
          ))}
        </div>
        <input
          type="text"
          placeholder="Search company or title..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            padding: '6px 12px',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            fontSize: 13,
            fontFamily: 'var(--font)',
            background: 'white',
            width: 220,
          }}
        />
      </div>

      {subView === 'evaluated' && <Evaluated jobs={evaluated} onToggleFav={handleToggleFav} onToggleAuto={handleToggleAuto} onGeneratePack={handleGeneratePack} onReviewPack={handleReviewPack} />}
      {subView === 'pending' && <PendingList jobs={pending} />}
      {subView === 'favorites' && <Evaluated jobs={visibleFavJobs} onToggleFav={handleToggleFav} onToggleAuto={handleToggleAuto} onGeneratePack={handleGeneratePack} onReviewPack={handleReviewPack} />}
      {subView === 'filtered' && <FilteredList jobs={filtered} onUnskip={onUnskip} onApprove={onApprove} onToggleFav={handleToggleFav} />}
    </div>
  )
}
