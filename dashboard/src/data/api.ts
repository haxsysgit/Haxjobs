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
  sourceQuality?: string
  roleFamily?: string
  roleFamilyConfidence?: number
  recommendedCvVariant?: string
  packStatus?: string
  packReviewStatus?: string
  packReviewNotes?: string
  packReviewedAt?: string
  outreachStatus?: string
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
  isAutoApply?: boolean
  // Extended fields
  jdText?: string
}

// ── Response types for API calls ──

export interface ApiResult {
  ok: boolean
  error?: string
}

export interface PackGenerateResult extends ApiResult {
  pack_dir?: string
}

export interface PackReviewResult extends ApiResult {
  pack_status?: string
}

export interface AutoApplyResult extends ApiResult {
  auto_apply: boolean
}

export interface StatusResult {
  pipeline_status: string
}

export interface ActivityEntry {
  message: string
}

export interface WhitelistEntry {
  id: number
  pattern_type: string
  pattern_value: string
  reason?: string
  source_job_id?: number
  match_count?: number
  active?: number
  created_at?: string
}

export interface Pack {
  dir: string
  name: string
  files: string[]
  count: number
}

export interface PackDetail {
  ok: boolean
  packDir: string
  metadata: Record<string, unknown>
  files: Record<string, string>
  error?: string
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
  getJobs: (status?: string, offset?: number, limit?: number) => {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (offset !== undefined) params.set('offset', String(offset))
    if (limit !== undefined) params.set('limit', String(limit))
    const qs = params.toString()
    return fetchAPI<Job[]>(`/api/jobs${qs ? '?' + qs : ''}`)
  },

  // Packs
  getPacks: () => fetchAPI<Pack[]>('/api/packs'),
  getPackDetail: (packDir: string) => fetchAPI<PackDetail>(`/api/pack-detail?dir=${encodeURIComponent(packDir)}`),
  generatePack: (jobId: string) =>
    fetchAPI<PackGenerateResult>('/api/jobs/generate-pack', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),
  reviewPack: (jobId: string, action: 'approve' | 'reject' | 'changes', notes?: string) =>
    fetchAPI<PackReviewResult>('/api/jobs/review-pack', { method: 'POST', body: JSON.stringify({ job_id: jobId, action, notes }) }),

  // Stats
  getStats: () => fetchAPI<PipelineStats>('/api/stats'),
  getStatus: () => fetchAPI<StatusResult>('/api/status'),

  // Discovery
  getDiscovery: () => fetchAPI<DiscoveryStatus>('/api/discovery'),

  // Profile
  getProfile: () => fetchAPI<ProfileData>('/api/profile'),

  // Activity
  getActivity: () => fetchAPI<ActivityEntry[]>('/api/activity'),

  // Favorites (server-side, persistent)
  getFavorites: () => fetchAPI<Job[]>('/api/favorites'),
  addFavorite: (jobId: string) =>
    fetchAPI<ApiResult>('/api/favorites', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),
  removeFavorite: (jobId: string) =>
    fetchAPI<ApiResult>('/api/favorites/remove', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),

  // Saved Jobs (server-side, persistent)
  getSavedJobs: () => fetchAPI<Job[]>('/api/saved-jobs'),
  saveJob: (jobId: string, notes?: string) =>
    fetchAPI<ApiResult>('/api/saved-jobs', { method: 'POST', body: JSON.stringify({ job_id: jobId, notes }) }),
  unsaveJob: (jobId: string) =>
    fetchAPI<ApiResult>('/api/saved-jobs/remove', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),

  // Pipeline actions
  triggerPipeline: () => fetchAPI<ApiResult>('/api/trigger', { method: 'POST', body: '{}' }),
  queueIntake: (data: { jd_text: string; source?: string; company?: string; title?: string; url?: string }) =>
    fetchAPI<ApiResult>('/api/queue', { method: 'POST', body: JSON.stringify(data) }),

  // Unskip & Approve
  unskipJob: (jobId: string, reason?: string, addToWhitelist?: boolean) =>
    fetchAPI<ApiResult>('/api/jobs/unskip', { method: 'POST', body: JSON.stringify({ job_id: jobId, reason, add_to_whitelist: addToWhitelist }) }),
  approveJob: (jobId: string, reason?: string, addToWhitelist?: boolean) =>
    fetchAPI<ApiResult>('/api/jobs/approve', { method: 'POST', body: JSON.stringify({ job_id: jobId, reason, add_to_whitelist: addToWhitelist }) }),

  // Whitelist
  getWhitelist: () => fetchAPI<WhitelistEntry[]>('/api/whitelist'),
  addWhitelist: (data: { pattern_type: string; pattern_value: string; reason?: string; source_job_id?: number }) =>
    fetchAPI<ApiResult>('/api/whitelist', { method: 'POST', body: JSON.stringify(data) }),
  removeWhitelist: (id: number) =>
    fetchAPI<ApiResult>('/api/whitelist/remove', { method: 'POST', body: JSON.stringify({ id }) }),

  // Auto-apply
  toggleAutoApply: (jobId: string) =>
    fetchAPI<AutoApplyResult>('/api/jobs/auto-apply', { method: 'POST', body: JSON.stringify({ job_id: jobId }) }),

  // Profile
  saveProfile: (name: string, headline: string) =>
    fetchAPI<ApiResult>('/api/profile/save', { method: 'POST', body: JSON.stringify({ name, headline }) }),
}
