import { getFixtureJobs, type FixtureJob } from "@/lib/fixtures"

export interface DiscoveryStatus {
  running: boolean
  scrapers?: { name: string; status: string; found?: number; new?: number; errors?: string[] }[]
  started_at?: string
}

export interface HomeJobRow {
  id: number
  title: string
  company: string
  status: string
  fit_score?: number | null
  fit_level?: number | null
  level?: number | null
  level_name?: string | null
  fit_verdict?: string | null
  pack_status?: string | null
  evaluated_at?: string | null
  pack_generated_at?: string | null
  discovered_at?: string | null
  role_family?: string | null
}

export interface HomeDecisionRow {
  job_id: number
  decision: string
  reason?: string
  created_at?: string
  decided_at?: string
  job_title?: string
  job_company?: string
}

export type HomeFeedEvent =
  | { type: "discovery"; id: string; timestamp: string; data: DiscoveryStatus }
  | { type: "evaluation"; id: string; timestamp: string; data: HomeJobRow }
  | { type: "pack"; id: string; timestamp: string; data: HomeJobRow }
  | { type: "decision"; id: string; timestamp: string; data: HomeDecisionRow }

export function buildHomeFeedEvents(args: {
  discovery?: DiscoveryStatus
  jobs?: HomeJobRow[]
  decisions?: HomeDecisionRow[]
  fixtureMode: boolean
}): HomeFeedEvent[] {
  const events: HomeFeedEvent[] = []

  if (args.fixtureMode) {
    const now = new Date()
    events.push({
      type: "discovery",
      id: "discovery-fixture",
      timestamp: new Date(now.getTime() - 300_000).toISOString(),
      data: {
        running: false,
        scrapers: [{ name: "Greenhouse", status: "done", found: 12, new: 3, errors: [] }],
        started_at: new Date(now.getTime() - 600_000).toISOString(),
      },
    })

    for (const j of getFixtureJobs().filter((j: FixtureJob) => j.fit_score > 0)) {
      const job: HomeJobRow = {
        id: j.id,
        title: j.title,
        company: j.company,
        status: "evaluated",
        fit_score: j.fit_score,
        level: j.level,
        level_name: j.level_name,
        fit_verdict: j.fit_verdict,
        evaluated_at: j.discovered_at,
        pack_status: j.pack_status,
        discovered_at: j.discovered_at,
        role_family: j.role_family,
      }
      events.push({
        type: "evaluation",
        id: `fixture-eval-${j.id}`,
        timestamp: j.discovered_at,
        data: job,
      })
      if (j.pack_status === "generated") {
        events.push({
          type: "pack",
          id: `fixture-pack-${j.id}`,
          timestamp: j.discovered_at,
          data: job,
        })
      }
    }
  } else {
    if (args.discovery?.running) {
      events.push({
        type: "discovery",
        id: "discovery-running",
        timestamp: args.discovery.started_at || new Date().toISOString(),
        data: args.discovery,
      })
    }

    for (const j of args.jobs || []) {
      if (j.evaluated_at && j.fit_score) {
        events.push({ type: "evaluation", id: `eval-${j.id}`, timestamp: j.evaluated_at, data: j })
      }
      if (j.pack_generated_at && j.pack_status === "generated") {
        events.push({ type: "pack", id: `pack-${j.id}`, timestamp: j.pack_generated_at, data: j })
      }
    }

    for (const d of args.decisions || []) {
      const timestamp = d.created_at || d.decided_at
      if (!timestamp) continue
      events.push({
        type: "decision",
        id: `dec-${d.job_id}-${timestamp}`,
        timestamp,
        data: d,
      })
    }
  }

  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
  return events
}
