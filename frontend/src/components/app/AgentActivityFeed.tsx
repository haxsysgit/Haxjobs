import { useQuery } from "@tanstack/react-query"
import { AnimatePresence } from "framer-motion"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { AgentMessage } from "./AgentMessage"
import { EmptyState } from "./EmptyState"
import { PageHeader } from "./PageHeader"
import { IconRecon, IconFit, IconPack, IconDecision, IconSweep } from "@/components/icons"
import { apiGet } from "@/lib/api"
import { fixtureMode, getFixtureJobs, type FixtureJob } from "@/lib/fixtures"

/* ── Types ──────────────────────────────────────────────────────────────── */

interface DiscoveryStatus {
  status: string
  scrapers?: { name: string; status: string; found?: number; new?: number; errors?: string[] }[]
  started_at?: string
}

interface JobRow {
  id: number
  title: string
  company: string
  status: string
  fit_score?: number
  level?: number
  fit_verdict?: string
  pack_status?: string | null
  evaluated_at?: string
  pack_generated_at?: string
}

interface DecisionRow {
  job_id: number
  decision: string
  reason?: string
  created_at: string
  job_title?: string
  job_company?: string
}

type FeedEvent =
  | { type: "discovery"; id: string; timestamp: string; data: DiscoveryStatus }
  | { type: "evaluation"; id: string; timestamp: string; data: JobRow }
  | { type: "pack"; id: string; timestamp: string; data: JobRow }
  | { type: "decision"; id: string; timestamp: string; data: DecisionRow }

/* ── Helpers ────────────────────────────────────────────────────────────── */

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

/* ── Feed component ─────────────────────────────────────────────────────── */

export function AgentActivityFeed() {
  const ds = useQuery<DiscoveryStatus>({
    queryKey: ["discovery-status"],
    queryFn: () => apiGet<DiscoveryStatus>("/discovery/status"),
    enabled: !fixtureMode,
    refetchInterval: (q) => (q.state.data?.status === "running" ? 5_000 : 60_000),
    retry: false,
  })

  const jobsQ = useQuery<{ jobs: JobRow[] }>({
    queryKey: ["jobs", "evaluated"],
    queryFn: () => apiGet<{ jobs: JobRow[] }>("/jobs?status=evaluated&limit=20"),
    enabled: !fixtureMode,
    staleTime: 30_000,
    retry: false,
  })

  const decisionsQ = useQuery<{ decisions: DecisionRow[] }>({
    queryKey: ["decisions"],
    queryFn: () => apiGet<{ decisions: DecisionRow[] }>("/decisions?limit=20"),
    enabled: !fixtureMode,
    staleTime: 30_000,
    retry: false,
  })

  // Build feed events
  const events: FeedEvent[] = []

  if (fixtureMode) {
    // ponytail: fixture data for dev
    const now = new Date()
    events.push({
      type: "discovery",
      id: "discovery-fixture",
      timestamp: new Date(now.getTime() - 300_000).toISOString(),
      data: {
        status: "completed",
        scrapers: [{ name: "Greenhouse", status: "done", found: 12, new: 3 }],
        started_at: new Date(now.getTime() - 600_000).toISOString(),
      },
    })
    for (const j of getFixtureJobs().filter((j: FixtureJob) => j.fit_score > 0)) {
      events.push({
        type: "evaluation",
        id: `fixture-eval-${j.id}`,
        timestamp: j.discovered_at,
        data: {
          id: j.id,
          title: j.title,
          company: j.company,
          status: "evaluated",
          fit_score: j.fit_score,
          level: j.level,
          fit_verdict: j.fit_verdict,
          evaluated_at: j.discovered_at,
          pack_status: j.pack_status,
        },
      })
    }
  } else {
    if (ds.data && ds.data.status === "running") {
      events.push({
        type: "discovery",
        id: "discovery-running",
        timestamp: ds.data.started_at || new Date().toISOString(),
        data: ds.data,
      })
    }
    if (jobsQ.data?.jobs) {
      for (const j of jobsQ.data.jobs) {
        if (j.evaluated_at && j.fit_score) {
          events.push({ type: "evaluation", id: `eval-${j.id}`, timestamp: j.evaluated_at, data: j })
        }
        if (j.pack_generated_at && j.pack_status === "generated") {
          events.push({ type: "pack", id: `pack-${j.id}`, timestamp: j.pack_generated_at, data: j })
        }
      }
    }
    if (decisionsQ.data?.decisions) {
      for (const d of decisionsQ.data.decisions) {
        events.push({
          type: "decision",
          id: `dec-${d.job_id}-${d.created_at}`,
          timestamp: d.created_at,
          data: d,
        })
      }
    }
  }

  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  const isLoading = ds.isLoading || jobsQ.isLoading || decisionsQ.isLoading
  const hasError = ds.isError || jobsQ.isError || decisionsQ.isError

  /* ── Loading state ──────────────────────────────────────────────────── */
  if (isLoading) {
    return (
      <div className="space-y-4">
        <PageHeader title="Home" description="Agent activity feed" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-3 rounded-xl border p-4">
            <Skeleton className="size-10 rounded-full" />
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  /* ── Error state ────────────────────────────────────────────────────── */
  if (hasError) {
    return (
      <div className="space-y-6">
        <PageHeader title="Home" description="Agent activity feed" />
        <AgentMessage
          icon={<IconSweep />}
          title="I hit a snag loading your feed. The backend might be waking up. Try refreshing."
          status="error"
        />
      </div>
    )
  }

  /* ── Empty state ────────────────────────────────────────────────────── */
  if (events.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader title="Home" description="Agent activity feed" />
        <EmptyState
          icon={<IconRecon />}
          title="I'm ready to work."
          description="Start a recon sweep and I'll find jobs for you."
          action={
            <Link to="/discovery">
              <Button>Start Recon</Button>
            </Link>
          }
        />
      </div>
    )
  }

  /* ── Feed ───────────────────────────────────────────────────────────── */
  return (
    <div className="space-y-6">
      <PageHeader title="Home" description="Agent activity feed" />
      <AnimatePresence initial={false}>
        {events.slice(0, 30).map((event) => (
          <AgentMessage
            key={event.id}
            icon={<EventIcon event={event} />}
            title={eventTitle(event)}
            subtitle={eventSubtitle(event)}
            timestamp={timeAgo(event.timestamp)}
            status={eventStatus(event)}
            actions={<EventActions event={event} />}
          >
            <EventBody event={event} />
          </AgentMessage>
        ))}
      </AnimatePresence>
    </div>
  )
}

/* ── Event helpers (return plain strings for AgentMessage props) ────────── */

function EventIcon({ event }: { event: FeedEvent }) {
  switch (event.type) {
    case "discovery":
      return event.data.status === "running" ? <IconSweep animate /> : <IconRecon />
    case "evaluation":
      return <IconFit />
    case "pack":
      return <IconPack />
    case "decision":
      return <IconDecision />
  }
}

function eventTitle(event: FeedEvent): string {
  switch (event.type) {
    case "discovery": {
      if (event.data.status === "running") return "I'm running a recon sweep right now."
      const total = event.data.scrapers?.reduce((s, x) => s + (x.found || 0), 0) || 0
      const newC = event.data.scrapers?.reduce((s, x) => s + (x.new || 0), 0) || 0
      return `I completed a recon sweep. ${total} jobs found, ${newC} new.`
    }
    case "evaluation":
      return `Scored ${event.data.company} — ${event.data.title}: ${event.data.fit_score}% fit.`
    case "pack":
      return `Application pack ready for ${event.data.company} ${event.data.title}.`
    case "decision":
      return `You ${event.data.decision}d ${event.data.job_company || "a job"}.`
  }
}

function eventSubtitle(event: FeedEvent): string {
  switch (event.type) {
    case "discovery":
      return event.data.scrapers?.map((s) => `${s.name}: ${s.status}`).join(", ") || ""
    case "evaluation":
      return `Level ${event.data.level} · ${event.data.fit_verdict}`
    case "pack":
      return "CV, cover letter, interview prep inside."
    case "decision":
      return event.data.reason || ""
  }
}

function eventStatus(event: FeedEvent): "success" | "running" | "error" | "idle" {
  switch (event.type) {
    case "discovery":
      return event.data.status === "running" ? "running" : event.data.status === "error" ? "error" : "success"
    case "evaluation":
    case "pack":
    case "decision":
      return "success"
  }
}

function EventActions({ event }: { event: FeedEvent }) {
  switch (event.type) {
    case "discovery":
      return (
        <Link to="/discovery">
          <Button variant="ghost" size="sm" className="text-xs">View</Button>
        </Link>
      )
    case "evaluation":
      return (
        <Link to={`/jobs/${event.data.id}`}>
          <Button variant="ghost" size="sm" className="text-xs">Review</Button>
        </Link>
      )
    case "pack":
      return (
        <Link to="/packs">
          <Button variant="ghost" size="sm" className="text-xs">Open Pack</Button>
        </Link>
      )
    case "decision":
      return null
  }
}

function EventBody({ event }: { event: FeedEvent }) {
  switch (event.type) {
    case "discovery":
      return (
        <div className="space-y-2 text-sm">
          {event.data.scrapers?.map((s) => (
            <div key={s.name} className="flex items-center justify-between">
              <span>{s.name}</span>
              <span className="text-muted-foreground">{s.found || 0} found · {s.new || 0} new</span>
            </div>
          ))}
        </div>
      )
    case "evaluation":
      return (
        <div className="space-y-1 text-sm">
          <p><strong>Score:</strong> {event.data.fit_score}/100</p>
          <p><strong>Verdict:</strong> {event.data.fit_verdict}</p>
        </div>
      )
    default:
      return null
  }
}
