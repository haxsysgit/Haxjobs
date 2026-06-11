import { useState, useEffect } from 'react'
import { api, type Pack } from '../data/api'
import { FileText, Globe } from '../components/Icons'

export function PacksPage({ connected }: { connected: boolean }) {
  const [packs, setPacks] = useState<Pack[]>([])

  useEffect(() => {
    if (!connected) return
    api.getPacks().then(setPacks).catch(() => {})
  }, [connected])

  return (
    <div>
      <div className="section-header">
        <h3>Application Packs</h3>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>Generated CVs, cover letters, and Q&A — sorted newest first</span>
      </div>

      {!connected && (
        <div className="empty">
          <Globe size={24} />
          <h3>API not connected</h3>
        </div>
      )}

      {connected && packs.length === 0 && (
        <div className="empty">
          <FileText size={24} />
          <h3>No packs generated yet</h3>
          <p>Packs are generated for jobs scoring 60%+ or manually approved jobs.</p>
        </div>
      )}

      <div style={{ display: 'grid', gap: 10 }}>
        {packs.map(pack => (
          <div key={pack.dir} className="card" style={{ padding: '14px 16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h3 style={{ fontSize: 14, marginBottom: 4 }}>{pack.name.replace(/_/g, ' ')}</h3>
                <p style={{ fontSize: 12, color: 'var(--muted)', margin: 0 }}>
                  {pack.count} file{pack.count !== 1 ? 's' : ''}
                </p>
              </div>
              <span className="badge badge-good" style={{ fontSize: 10 }}>
                {pack.count} PDF{pack.count !== 1 ? 's' : ''}
              </span>
            </div>
            <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {pack.files.filter(f => f.endsWith('.pdf')).map(f => (
                <span key={f} className="tag tag-skill" style={{ fontSize: 11 }}>
                  <FileText size={12} /> {f.replace('Arinze_Elenasulu_', '').replace('.pdf', '').replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
