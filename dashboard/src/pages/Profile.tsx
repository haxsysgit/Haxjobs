import { useState, useEffect } from 'react'
import { api, type ProfileData } from '../data/api'

export function Profile({ data }: { data: ProfileData | null }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState('')
  const [headline, setHeadline] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data?.name && !name) setName(data.name)
    if (data?.headline && !headline) setHeadline(data.headline)
  }, [data])

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.saveProfile(name, headline)
      setSaved(true)
      setEditing(false)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Failed to save profile:', err)
    }
    setSaving(false)
  }

  const d = data ?? { name: '', headline: '', email: '', location: '', visa: '', university: '', preferred_roles: [], preferred_locations: [], preferred_work_modes: [], salary_preference: '', skills: [], fact_count: 0, platform_count: 0, saved_answer_count: 0 }

  return (
    <div className="profile-grid">
      <div className="card" style={{ gridColumn: '1 / -1' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--muted)', margin: 0 }}>Profile Identity</h3>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {saved && <span style={{ fontSize: 12, color: 'var(--success)' }}>Saved</span>}
            {editing ? (
              <>
                <button className="btn btn-sm" onClick={() => setEditing(false)}>Cancel</button>
                <button className="btn btn-sm btn-primary" onClick={handleSave} disabled={saving}>
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </>
            ) : (
              <button className="btn btn-sm" onClick={() => setEditing(true)}>Edit</button>
            )}
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 14 }}>
          <div className="profile-field">
            <label>Full Name</label>
            {editing ? (
              <input value={name} onChange={e => setName(e.target.value)} />
            ) : (
              <p style={{ fontSize: 14, fontWeight: 600 }}>{d.name || 'Not set'}</p>
            )}
          </div>
          <div className="profile-field" style={{ gridColumn: '2 / -1' }}>
            <label>Headline</label>
            {editing ? (
              <input value={headline} onChange={e => setHeadline(e.target.value)} />
            ) : (
              <p style={{ fontSize: 14 }}>{d.headline || 'Not set'}</p>
            )}
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginTop: 14 }}>
          <div className="profile-field">
            <label>Email</label>
            <p style={{ fontSize: 13, color: 'var(--muted)' }}>{d.email || 'Not set'}</p>
          </div>
          <div className="profile-field">
            <label>Location</label>
            <p style={{ fontSize: 13, color: 'var(--muted)' }}>{d.location || 'Not set'}</p>
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--muted)', marginBottom: 12 }}>Skills ({d.skills.length})</h3>
        <div className="tag-group">
          {d.skills.map(s => <span key={s} className="tag tag-skill">{s}</span>)}
          {d.skills.length === 0 && <p style={{ fontSize: 12, color: 'var(--muted)' }}>No skills loaded from profile</p>}
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--muted)', marginBottom: 12 }}>Work Authorization</h3>
        <p style={{ fontSize: 13 }}>{d.visa || 'Not configured'}</p>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--muted)', marginBottom: 12 }}>Preferred Roles</h3>
        <div className="tag-group">
          {d.preferred_roles.map(r => <span key={r} className="tag tag-skill">{r}</span>)}
          {d.preferred_roles.length === 0 && <p style={{ fontSize: 12, color: 'var(--muted)' }}>No preferred roles set</p>}
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--muted)', marginBottom: 12 }}>Preferred Locations</h3>
        <div className="tag-group">
          {d.preferred_locations.map(l => <span key={l} className="tag tag-skill">{l}</span>)}
          {d.preferred_locations.length === 0 && <p style={{ fontSize: 12, color: 'var(--muted)' }}>No locations set</p>}
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.4px', color: 'var(--muted)', marginBottom: 12 }}>Stats</h3>
        <div style={{ fontSize: 13 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
            <span style={{ color: 'var(--muted)' }}>Profile facts</span>
            <span>{d.fact_count}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
            <span style={{ color: 'var(--muted)' }}>Platform accounts</span>
            <span>{d.platform_count}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
            <span style={{ color: 'var(--muted)' }}>Saved answers</span>
            <span>{d.saved_answer_count}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
