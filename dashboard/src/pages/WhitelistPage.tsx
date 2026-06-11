import { useState, useEffect } from 'react'
import { api } from '../data/api'
import { X, Globe } from '../components/Icons'

interface WhitelistEntry {
  id: number
  pattern_type: string
  pattern_value: string
  reason: string
  match_count: number
  active: number
  created_at: string
}

export function Whitelist({ connected }: { connected: boolean }) {
  const [entries, setEntries] = useState<WhitelistEntry[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [newEntry, setNewEntry] = useState({ pattern_type: 'company_name', pattern_value: '', reason: '' })

  useEffect(() => {
    if (!connected) return
    api.getWhitelist().then(setEntries).catch(() => {})
  }, [connected])

  const handleAdd = async () => {
    if (!newEntry.pattern_value.trim()) return
    await api.addWhitelist({
      pattern_type: newEntry.pattern_type,
      pattern_value: newEntry.pattern_value.trim(),
      reason: newEntry.reason.trim(),
    })
    setNewEntry({ pattern_type: 'company_name', pattern_value: '', reason: '' })
    setShowAdd(false)
    const updated = await api.getWhitelist()
    setEntries(updated)
  }

  const handleRemove = async (id: number) => {
    await api.removeWhitelist(id)
    setEntries(prev => prev.filter(e => e.id !== id))
  }

  const typeLabel = (t: string) => {
    switch (t) {
      case 'company_name': return 'Company'
      case 'title_keyword': return 'Title Keyword'
      case 'company_and_title': return 'Company + Title'
      default: return t
    }
  }

  return (
    <div>
      <div className="section-header">
        <h3>Whitelist</h3>
        <button className="btn btn-sm btn-primary" onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? 'Cancel' : '+ Add Pattern'}
        </button>
      </div>
      <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 16 }}>
        Patterns the evaluator should never auto-skip. When a job matches any active pattern, it will not be skipped regardless of score.
      </p>

      {!connected && (
        <div className="empty">
          <Globe size={24} />
          <h3>API not connected</h3>
        </div>
      )}

      {showAdd && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr auto', gap: 10, alignItems: 'end' }}>
            <div className="profile-field" style={{ marginBottom: 0 }}>
              <label>Pattern Type</label>
              <select value={newEntry.pattern_type}
                onChange={e => setNewEntry({ ...newEntry, pattern_type: e.target.value })}
                style={{ width: '100%', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', fontSize: 13, fontFamily: 'var(--font)', background: 'white' }}>
                <option value="company_name">Company Name</option>
                <option value="title_keyword">Title Keyword</option>
                <option value="company_and_title">Company + Title</option>
              </select>
            </div>
            <div className="profile-field" style={{ marginBottom: 0 }}>
              <label>Pattern Value</label>
              <input placeholder={newEntry.pattern_type === 'company_and_title' ? 'company||keyword' : 'e.g. mongoose gray'}
                value={newEntry.pattern_value}
                onChange={e => setNewEntry({ ...newEntry, pattern_value: e.target.value })} />
            </div>
            <div className="profile-field" style={{ marginBottom: 0 }}>
              <label>Reason</label>
              <input placeholder="Why this should not be skipped"
                value={newEntry.reason}
                onChange={e => setNewEntry({ ...newEntry, reason: e.target.value })} />
            </div>
            <button className="btn btn-primary" onClick={handleAdd}>Add</button>
          </div>
        </div>
      )}

      {entries.length === 0 && connected && (
        <div className="empty">
          <h3>No whitelist patterns</h3>
          <p>Add patterns to prevent the evaluator from auto-skipping matching jobs.</p>
        </div>
      )}

      <div style={{ display: 'grid', gap: 8 }}>
        {entries.map(e => (
          <div key={e.id} className="card" style={{ padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <span className="badge badge-neutral" style={{ fontSize: 10 }}>{typeLabel(e.pattern_type)}</span>
                <strong style={{ fontSize: 13 }}>{e.pattern_value}</strong>
                {e.match_count > 0 && (
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>matched {e.match_count} job{e.match_count !== 1 ? 's' : ''}</span>
                )}
              </div>
              {e.reason && <p style={{ fontSize: 12, color: 'var(--muted)', margin: '4px 0 0' }}>{e.reason}</p>}
            </div>
            <button className="btn btn-sm" style={{ color: 'var(--danger)' }}
              onClick={() => handleRemove(e.id)}>
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
