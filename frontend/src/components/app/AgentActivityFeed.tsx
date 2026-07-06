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
import { fixtureMode } from "@/lib/fixtures"
import {
  buildHomeFeedEvents,
  type DiscoveryStatus,
  type HomeDecisionRow,
  type HomeFeedEvent,
  type HomeJobRow,
} from "@/lib/homeSummary"

interface AgentActivityFeedProps {
  variant?: "default" | "compact"
  maxEvents?: number
  hideHeader?: boolean
}

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

export function AgentActivityFeed({
  variant = "default",
  maxEvents = 30,
  hideHeader = false,
}: AgentActivityFeedProps) {
  const ds = useQuery<DiscoveryStatus>({
    queryKey: ["discovery-status"],
    queryFn: () => apiGet<DiscoveryStatus>("/discovery/status"),
    enabled: !fixtureMode,
    refetchInterval: (q) => (q.state.data?.running ? 5_000 : 60_000),
    retry: false,
  })

  const jobsQ = useQuery<{ jobs: HomeJobRow[] }>({
    queryKey: ["jobs", "evaluated"],
    queryFn: () => apiGet<{ jobs: HomeJobRow[] }>("/jobs?status=evaluated&limit=20"),
    enabled: !fixtureMode,
    staleTime: 30_000,
    retry: false,
  })

  const decisionsQ = useQuery<{ decisions: HomeDecisionRow[] }>({
    queryKey: ["decisions"],
    queryFn: () => apiGet<{ decisions: HomeDecisionRow[] }>("/decisions?limit=20"),
    enabled: !fixtureMode,
    staleTime: 30_000,
    retry: false,
  })

  const events = buildHomeFeedEvents({
    discovery: ds.data,
    jobs: jobsQ.data?.jobs,
    decisions: decisionsQ.data?.decisions,
    fixtureMode,
  })

  const isLoading = ds.isLoading || jobsQ.isLoading || decisionsQ.isLoading
  const hasError = ds.isError || jobsQ.isError || decisionsQ.isError
  const compact = variant === "compact"

  if (isLoading) {
    return (
      <div className={compact ? "space-y-3" : "space-y-4"}>
        {!hideHeader && <PageHeader title="Home" description="Agent activity feed" />}
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

  if (hasError) {
    return (
      <div className={compact ? "space-y-3" : "space-y-6"}>
        {!hideHeader && <PageHeader title="Home" description="Agent activity feed" />}
        <AgentMessage
          icon={<IconSweep />}
          title="I hit a snag loading your feed. The backend might be waking up. Try refreshing."
          status="error"
          variant={compact ? "compact" : "default"}
        />
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className={compact ? "space-y-3" : "space-y-6"}>
        {!hideHeader && <PageHeader title="Home" description="Agent activity feed" />}
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

  return (
    <div className={compact ? "space-y-3" : "space-y-6"}>
      {!hideHeader && <PageHeader title="Home" description="Agent activity feed" />}
      <AnimatePresence initial={false}>
        {events.slice(0, maxEvents).map((event) => (
          <AgentMessage
            key={event.id}
            icon={<EventIcon event={event} />}
            title={eventTitle(event)}
            subtitle={eventSubtitle(event)}
            timestamp={timeAgo(event.timestamp)}
            status={eventStatus(event)}
            actions={<EventActions event={event} />}
            variant={compact ? "compact" : "default"}
          >
            <EventBody event={event} />
          </AgentMessage>
        ))}
      </AnimatePresence>
    </div>
  )
}

function EventIcon({ event }: { event: HomeFeedEvent }) {
  switch (event.type) {
    case "discovery":
      return event.data.running ? <IconSweep animate /> : <IconRecon />
    case "evaluation":
      return <IconFit />
    case "pack":
      return <IconPack />
    case "decision":
      return <IconDecision />
  }
}

function eventTitle(event: HomeFeedEvent): string {
  switch (event.type) {
    case "discovery": {
      if (event.data.running) return "I'm running a recon sweep right now."
      const total = event.data.scrapers?.reduce((s, x) => s + (x.found || 0), 0) || 0
      const newC = event.data.scrapers?.reduce((s, x) => s + (x.new || 0), 0) || 0
      return `I completed a recon sweep. ${total} jobs found, ${newC} new.`
    }
    case "evaluation":
      return `Scored ${event.data.company}: ${event.data.title}: ${event.data.fit_score}% fit.`
    case "pack":
      return `Application pack ready for ${event.data.company} ${event.data.title}.`
    case "decision":
      return decisionTitle(event.data.decision, event.data.job_company || event.data.job_title || "this job")
  }
}

function decisionTitle(decision: string, target: string): string {
  const copy: Record<string, string> = {
    apply: `You applied to ${target}. Nice, this one gets a real shot.`,
    maybe: `You parked ${target} in maybe.`,
    save: `You saved ${target} for a second look.`,
    skip: `You skipped ${target}. Precious mortal attention preserved.`,
    reject: `You rejected ${target}. Clean exit, no drama.`,
  }
  return copy[decision] || `You marked ${target} as ${decision}.`
}

function eventSubtitle(event: HomeFeedEvent): string {
  switch (event.type) {
    case "discovery":
      return event.data.scrapers?.map((s) => `${s.name}: ${s.status}`).join(", ") || ""
    case "evaluation":
      return `Level ${event.data.level ?? event.data.fit_level} · ${event.data.fit_verdict}`
    case "pack":
      return "CV, cover letter, interview prep inside."
    case "decision":
      return event.data.reason || ""
  }
}

function eventStatus(event: HomeFeedEvent): "success" | "running" | "error" | "idle" {
  switch (event.type) {
    case "discovery":
      return event.data.running ? "running" : event.data.scrapers?.some((s) => s.status === "error") ? "error" : "success"
    case "evaluation":
    case "pack":
    case "decision":
      return "success"
  }
}

function EventActions({ event }: { event: HomeFeedEvent }) {
  switch (event.type) {
    case "discovery":
      return (
        <Link to="/discovery">
          <Button variant="ghost" size="sm" className="text-xs">View</Button>
        </Link>
      )
    case "evaluation":
      return (
        <Link to={`/jobs/detail/${event.data.id}`}>
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

function EventBody({ event }: { event: HomeFeedEvent }) {
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
