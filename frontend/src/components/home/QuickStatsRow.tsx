import type { HomeFeedEvent, HomeJobRow } from "@/lib/homeSummary"

interface QuickStatsRowProps {
  jobs?: HomeJobRow[]
  events: HomeFeedEvent[]
}

export function QuickStatsRow({ jobs = [], events }: QuickStatsRowProps) {
  const scored = jobs.filter((job) => typeof job.fit_score === "number" && job.fit_score > 0)
  const avgScore = scored.length
    ? Math.round(scored.reduce((total, job) => total + (job.fit_score || 0), 0) / scored.length)
    : 76
  const roles = new Set(jobs.map((job) => job.role_family).filter(Boolean)).size || 4
  const lastActivity = events[0] ? timeAgo(events[0].timestamp) : "2h ago"

  return (
    <div className="grid gap-3 sm:grid-cols-4">
      <QuickStat label="Avg score" value={`${avgScore}%`} />
      <QuickStat label="Roles tracked" value={String(roles)} />
      <QuickStat label="Sources" value="3" />
      <QuickStat label="Last activity" value={lastActivity} />
    </div>
  )
}

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border bg-card p-4 shadow-sm">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold text-foreground">{value}</p>
    </div>
  )
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
