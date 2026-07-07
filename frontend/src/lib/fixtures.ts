import { SEED_JOBS, SEED_PACKS, SEED_MEMORY, SEED_DECISIONS, seedMessages } from "./data"
import type { JobView, PackView, MemoryView, MessageView, StatsView } from "./opusTypes"

let idCounter = 1

export function getJobs(): JobView[] {
  const decBySlug = new Map(SEED_DECISIONS.map(d => [d.jobSlug, d]))
  return SEED_JOBS.map(j => ({
    id: idCounter++,
    ...j,
    salary: j.salary,
    decision: decBySlug.has(j.slug)
      ? { decision: decBySlug.get(j.slug)!.decision, reason: decBySlug.get(j.slug)!.reason, createdAt: new Date().toISOString() }
      : null,
  }))
}

export function getPacks(): PackView[] {
  const jobs = getJobs()
  const jobBySlug = new Map(jobs.map(j => [j.slug, j]))
  return SEED_PACKS.map((p, i) => ({
    id: i + 1,
    title: p.title,
    status: p.status,
    files: p.files,
    createdAt: new Date().toISOString(),
    job: jobBySlug.get(p.jobSlug)
      ? { slug: p.jobSlug, company: jobBySlug.get(p.jobSlug)!.company, role: jobBySlug.get(p.jobSlug)!.role, track: jobBySlug.get(p.jobSlug)!.track }
      : null,
  }))
}

export function getMemory(): MemoryView[] {
  return SEED_MEMORY.map((m, i) => ({ id: i + 1, ...m }))
}

export function getMessages(): MessageView[] {
  return seedMessages().map((m, i) => ({
    id: i + 1,
    author: m.author,
    kind: m.kind,
    payload: m.payload,
    pinned: m.pinned,
    createdAt: new Date(Date.now() - (seedMessages().length - i) * 3600000).toISOString(),
  }))
}

export function getStats(): StatsView {
  const jobs = getJobs()
  const decided = jobs.filter(j => j.decision)
  const packs = getPacks()
  return {
    jobsThisCycle: jobs.length,
    evaluated: jobs.filter(j => j.evaluation).length,
    applied: decided.filter(j => j.decision?.decision === "apply").length,
    saved: decided.filter(j => j.decision?.decision === "save").length,
    packsReady: packs.filter(p => p.status === "ready").length,
    needsDecision: jobs.filter(j => j.evaluation && !j.decision).length,
    strongFits: jobs.filter(j => j.evaluation?.verdict === "STRONG FIT" && !j.decision).length,
  }
}
