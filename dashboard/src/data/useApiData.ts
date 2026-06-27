import { useState, useEffect } from 'react'
import { api, type Job, type DiscoveryStatus, type ProfileData } from './api'

// ── Shared data context ──
// Moved from App.tsx to satisfy react-refresh/only-export-components

export function useApiData() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [discovery, setDiscovery] = useState<DiscoveryStatus | null>(null)
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    async function load() {
      try {
        const [j, d, p] = await Promise.all([api.getJobs(), api.getDiscovery(), api.getProfile()])
        setJobs(j); setDiscovery(d); setProfile(p); setConnected(true)
      } catch { setConnected(false) }
    }
    load()
    const interval = setInterval(load, 30000)
    return () => clearInterval(interval)
  }, [])

  const updateJob = (jobId: string, updates: Partial<Job>) => {
    setJobs(prev => prev.map(j => j.id === jobId ? { ...j, ...updates } : j))
  }

  return { jobs, discovery, profile, connected, updateJob }
}
