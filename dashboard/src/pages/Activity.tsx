import { useState, useEffect } from 'react'
import { api } from '../data/api'
import { Clock, Zap, Globe } from '../components/Icons'

export function Activity({ connected }: { connected: boolean }) {
  const [log, setLog] = useState<string[]>([])

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getActivity()
        setLog(data.map((l: any) => l.message || '').filter(Boolean))
      } catch { /* offline */ }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="activity-feed">
      <div className="section-header">
        <h3>Pipeline Log</h3>
        <span style={{ fontSize: 12, color: 'var(--muted)' }}>Recent pipeline activity from Archilles</span>
      </div>

      {!connected && (
        <div className="empty">
          <Globe size={24} />
          <h3>API not connected</h3>
          <p>Start the pipeline API server on Archilles to see live activity.</p>
        </div>
      )}

      {connected && log.length === 0 && (
        <div className="empty">
          <Clock size={24} />
          <h3>No activity yet</h3>
          <p>Pipeline log will show here after Archilles processes jobs.</p>
        </div>
      )}

      {log.map((entry, i) => (
        <div key={i} className="activity-item">
          <div className="activity-icon"><Zap size={14} /></div>
          <div className="activity-body">
            <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--muted)' }}>
              {entry.length > 180 ? entry.slice(0, 180) + '...' : entry}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
