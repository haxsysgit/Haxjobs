// API client for HaxJobs Pipeline API v2.0
// Uses pipeline_db backend with server-side favorites and saved jobs.
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? `http://${window.location.hostname}:8800`
  : ''

export interface Job {
  id: string
  company: string
  title: string
  location: string
  source: string
  fitScore: number
  level: number
  levelName: string
  status: string
  skipReason: string
  strongestMatches: string[]
  majorGaps: string[]
  sponsorshipRisk: string
  summary: string
  applicationUrl: string
  packDir: string
  receivedAt: string
  processedAt: string | null
  isFavorite: boolean
  isSaved: boolean
  isApproved?: boolean
  isUnskipped?: boolean
  // Extended fields
  jdText?: string
  outreachStatus?: string
}

export interface Pack {
  dir: string
  name: string
  files: string[]
  count: number
}

export interface DiscoveryStatus {
  total_companies: string
  lever_count: number
  ashby_count: number
  greenhouse_count: number
  cron_jobs: number
  last_pipeline_run: string | null
}

export interface ProfileData {
  name: string
  headline: string
  email: string
  location: string
  visa: string
  university: string
  experience_levels: string[]
  preferred_roles: string[]
  preferred_locations: string[]
  preferred_work_modes: string[]
  salary_preference: string
  skills: string[]
  fact_count: number
  platform_count: number
  saved_answer_count: number
}

export interface PipelineStats {
  total_jobs: number
  pending: number
  evaluated: number
  skipped: number
  strong_fit: number
  good_fit: number
  favorites: number
  saved: number
  activity_24h: number
}

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export const api = {
  // Jobs
  getJobs: (status?: string) => {
    const qs = status ? `?status=${status}` : ''
    return fetchAPI<Job[]>(`/api/jobs${qs}`)
  },

  // Packs
  getPacks: () => fetchAPI<Pack[]>('/api/packs'),

  // Stats
  getStats: () => fetchAPI<PipelineStats>('/api/stats'),
  getStatus: () => fetchAPI<any>('/api/status'),

  // Discovery
  getDiscovery: () => fetchAPI<DiscoveryStatus>('/api/discovery'),

  // Profile
  getProfile: () => fetchAPI<ProfileData>('/api/profile'),

  // Activity
  getActivity: () => fetchAPI<any[]>('/api/activity'),

  // Favorites (server-side, persistent)
  getFavorites: () => fetchAPI<Job[]>('/api/favorites'),
  addFavorite: (jobId: string) =>
    fetchAPI<any>('/api/favorites', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),
  removeFavorite: (jobId: string) =>
    fetchAPI<any>('/api/favorites/remove', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),

  // Saved Jobs (server-side, persistent)
  getSavedJobs: () => fetchAPI<any[]>('/api/saved-jobs'),
  saveJob: (jobId: string, notes?: string) =>
    fetchAPI<any>('/api/saved-jobs', { method: 'POST', body: JSON.stringify({ job_id: jobId, notes }) }),
  unsaveJob: (jobId: string) =>
    fetchAPI<any>('/api/saved-jobs/remove', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),

  // Pipeline actions
  triggerPipeline: () => fetchAPI<any>('/api/trigger', { method: 'POST', body: '{}' }),
  queueIntake: (data: { jd_text: string; source?: string; company?: string; title?: string; url?: string }) =>
    fetchAPI<any>('/api/queue', { method: 'POST', body: JSON.stringify(data) }),

  // Unskip & Approve
  unskipJob: (jobId: string, reason?: string, addToWhitelist?: boolean) =>
    fetchAPI<any>('/api/jobs/unskip', { method: 'POST', body: JSON.stringify({ job_id: jobId, reason, add_to_whitelist: addToWhitelist }) }),
  approveJob: (jobId: string, reason?: string, addToWhitelist?: boolean) =>
    fetchAPI<any>('/api/jobs/approve', { method: 'POST', body: JSON.stringify({ job_id: jobId, reason, add_to_whitelist: addToWhitelist }) }),

  // Whitelist
  getWhitelist: () => fetchAPI<any[]>('/api/whitelist'),
  addWhitelist: (data: { pattern_type: string; pattern_value: string; reason?: string; source_job_id?: number }) =>
    fetchAPI<any>('/api/whitelist', { method: 'POST', body: JSON.stringify(data) }),
  removeWhitelist: (id: number) =>
    fetchAPI<any>('/api/whitelist/remove', { method: 'POST', body: JSON.stringify({ id }) }),

  // Auto-apply
  toggleAutoApply: (jobId: string) =>
    fetchAPI<any>('/api/jobs/auto-apply', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),

  // Profile
  saveProfile: (name: string, headline: string) =>
    fetchAPI<any>('/api/profile/save', { method: 'POST', body: JSON.stringify({ name, headline }) }),
}
