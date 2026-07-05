/** Job types and API functions for the HaxJobs frontend. */
import { apiGet, apiPost } from "./api"
import { fixtureMode, getFixtureJobs } from "./fixtures"
import type { FixtureJob } from "./fixtures"

/* ── Types ──────────────────────────────────────────────────────────────── */

export type JobStatus =
  | "pending"
  | "discovered"
  | "evaluated"
  | "skipped"
  | "applied"
  | "maybe"
  | "saved"
  | "rejected"

export type Decision = "apply" | "maybe" | "save" | "skip" | "reject"

export interface JobListItem {
  id: number
  title: string
  company: string | null
  location: string | null
  source_url: string | null
  jd_text: string | null
  status: string
  source: string | null
  discovered_at: string | null
  role_family: string | null
  recommended_cv_variant: string | null
  pack_status: string | null
  pack_dir: string | null
  fit_score: number | null
  fit_level: number | null
  fit_verdict: string | null
  level: number | null
  level_name: string | null
  summary: string | null
  strongest_matches: string[] | null
  major_gaps: string[] | null
  sponsorship_risk: string | null
  evaluated_at: string | null
}

export interface Evaluation {
  fit_score: number
  fit_verdict: string
  level: number
  level_name: string
  summary: string
  strongest_matches: string[]
  major_gaps: string[]
  sponsorship_risk: string
  evaluated_at: string | null
  pack_dir: string | null
}

export interface DecisionRow {
  id: number
  job_id: number
  decision: string
  reason: string
  decided_at: string
}

export interface JobDetail extends JobListItem {
  evaluation: Evaluation | null
  decisions: DecisionRow[]
}

export interface JobsListResponse {
  jobs: JobListItem[]
  total: number
}

export interface EvaluationRunResponse {
  ok: boolean
  job_id?: number
  fit_score?: number
  level?: number
  level_name?: string
  fit_verdict?: string
  strongest_matches?: string[]
  major_gaps?: string[]
  sponsorship_risk?: string
  summary?: string
  pack?: { ok: boolean; pack_dir?: string }
  code?: string
  error?: string
}

export interface DecisionResponse {
  ok: boolean
  job_id?: number
  decision?: string
  decision_id?: number
  code?: string
  error?: string
}

/* ── API functions ──────────────────────────────────────────────────────── */

export async function listJobs(params?: {
  status?: string
  role_family?: string
}): Promise<JobsListResponse> {
  if (fixtureMode) {
    const all = getFixtureJobs()
    let jobs = all
    if (params?.status) jobs = jobs.filter((j: FixtureJob) => j.status === params.status)
    if (params?.role_family) jobs = jobs.filter((j: FixtureJob) => j.role_family === params.role_family)
    return { jobs: jobs as JobListItem[], total: jobs.length }
  }
  const qs = new URLSearchParams()
  if (params?.status) qs.set("status", params.status)
  if (params?.role_family) qs.set("role_family", params.role_family)
  qs.set("limit", "100")
  return apiGet<JobsListResponse>(`/jobs?${qs.toString()}`)
}

export async function getJob(jobId: number): Promise<JobDetail> {
  if (fixtureMode) {
    const job = getFixtureJobs().find((j: FixtureJob) => j.id === jobId)
    if (!job) throw new Error("Job not found")
    return { ...job, jd_text: job.jd_text || "", evaluation: job.fit_score ? { fit_score: job.fit_score, fit_verdict: job.fit_verdict, level: job.level, level_name: job.level_name, summary: "", strongest_matches: job.strongest_matches, major_gaps: job.major_gaps, sponsorship_risk: "", evaluated_at: job.discovered_at, pack_dir: null } : null, decisions: [] } as unknown as JobDetail
  }
  return apiGet<JobDetail>(`/jobs/${jobId}`)
}

export async function evaluateJob(
  jobId: number,
  autoGeneratePack = true
): Promise<EvaluationRunResponse> {
  return apiPost<EvaluationRunResponse>(`/jobs/${jobId}/evaluate`, {
    auto_generate_pack: autoGeneratePack,
  })
}

export async function recordDecision(
  jobId: number,
  decision: Decision,
  reason?: string
): Promise<DecisionResponse> {
  return apiPost<DecisionResponse>("/decisions", {
    job_id: jobId,
    decision,
    reason: reason || "",
  })
}
