/* ponytail: API type definitions for backend job endpoints. */
export type Decision = "apply" | "maybe" | "save" | "skip" | "reject"

export interface JobListItem {
  id: number
  company: string
  title: string
  location: string
  fit_score: number
  fit_verdict: string
  level: number
  level_name: string
  strongest_matches: string[]
  major_gaps: string[]
  sponsorship_risk: string
}

export interface Evaluation {
  fit_score: number
  fit_verdict: string
  level: number
  level_name: string
  strongest_matches: string[]
  major_gaps: string[]
  sponsorship_risk: string
}

export type DecisionRow = { id: number; job_id: number; decision: Decision; created_at: string }

export interface JobDetail extends JobListItem {
  description: string
  evaluations: Evaluation[]
  decisions: DecisionRow[]
}

interface JobsListResponse { jobs: JobListItem[] }
interface EvaluationRunResponse extends Evaluation {}

async function apiGet<T>(url: string): Promise<T> {
  const res = await fetch(`/api${url}`)
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}
async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status}`)
  return res.json()
}

export async function listJobs(params?: Record<string, string>): Promise<JobListItem[]> {
  const qs = new URLSearchParams(params)
  return (await apiGet<JobsListResponse>(`/jobs?${qs.toString()}`)).jobs
}
export async function getJob(jobId: number): Promise<JobDetail> {
  return apiGet<JobDetail>(`/jobs/${jobId}`)
}
export async function evaluateJob(jobId: number): Promise<EvaluationRunResponse> {
  return apiPost<EvaluationRunResponse>(`/jobs/${jobId}/evaluate`, { job_id: jobId })
}
export async function recordDecision(jobId: number, decision: Decision, reason?: string): Promise<DecisionRow> {
  return apiPost<DecisionRow>("/decisions", { job_id: jobId, decision, reason })
}
