import { IconFit, IconPack, IconRecon, IconYou } from "@/components/icons"
import { DashboardCard } from "./DashboardCard"
import type { DiscoveryStatus, HomeJobRow } from "@/lib/homeSummary"

interface HomeMetricGridProps {
  discovery?: DiscoveryStatus
  jobs?: HomeJobRow[]
}

const fallbackScrapers = [
  { name: "Greenhouse", found: 20, new: 5 },
  { name: "Ashby", found: 18, new: 4 },
  { name: "Lever", found: 9, new: 3 },
]

const fallbackMatches = [
  { company: "Monzo", score: 85, level: 1 },
  { company: "Stripe", score: 78, level: 1 },
]

const fallbackPacks = ["Monzo", "Stripe"]
const fallbackRoles = ["Backend", "Full Stack", "AI/ML", "Waiter"]

export function HomeMetricGrid({ discovery, jobs = [] }: HomeMetricGridProps) {
  const scrapers = discovery?.scrapers?.length ? discovery.scrapers : fallbackScrapers
  const totalFound = sum(scrapers.map((s) => s.found || 0))
  const totalNew = sum(scrapers.map((s) => s.new || 0))
  const topMatches = jobs
    .filter((job) => typeof job.fit_score === "number" && job.fit_score > 0)
    .sort((a, b) => (b.fit_score || 0) - (a.fit_score || 0))
    .slice(0, 2)
  const matchRows = topMatches.length
    ? topMatches.map((job) => ({
        company: job.company,
        score: job.fit_score || 0,
        level: job.level ?? job.fit_level ?? 0,
      }))
    : fallbackMatches
  const strongCount = topMatches.filter((job) => (job.fit_score || 0) >= 75).length || 2
  const packJobs = jobs.filter((job) => job.pack_status === "generated").slice(0, 2)
  const packRows = packJobs.length ? packJobs.map((job) => job.company) : fallbackPacks
  const roleNames = roleLabels(jobs)

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <DashboardCard
        icon={<IconRecon />}
        title="Recon & Discovery"
        subtitle={`${scrapers.length || 3} scrapers active · ${totalFound || 47} jobs found`}
        href="/discovery"
        accent="green"
      >
        <div className="grid grid-cols-3 gap-2 text-center">
          {scrapers.slice(0, 3).map((scraper) => (
            <div key={scraper.name} className="rounded-xl border bg-background/60 p-2">
              <p className="truncate text-[11px] font-medium text-muted-foreground">{scraper.name}</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{scraper.found || 0}</p>
              <p className="text-[11px] text-primary">+{scraper.new || 0} new</p>
            </div>
          ))}
        </div>
        <p className="mt-3 rounded-xl border bg-background/50 p-3 text-xs text-muted-foreground">
          {discovery?.running
            ? "Sweep in motion. The scrapers are out hunting."
            : totalNew
              ? `Last sweep ran 2h ago. ${totalNew} new roles flagged.`
              : "Last sweep ran 2h ago. 12 new roles flagged."}
        </p>
      </DashboardCard>

      <DashboardCard
        icon={<IconFit />}
        title="Top Scored Matches"
        subtitle={`${strongCount} Strong Fit roles evaluated`}
        href="/jobs/backend_python"
        accent="blue"
      >
        <div className="space-y-2">
          {matchRows.map((match) => (
            <div key={match.company} className="flex items-center justify-between rounded-xl border bg-background/60 p-3">
              <span className="text-sm font-medium">{match.company}</span>
              <span className="text-xs text-muted-foreground">{match.score}% · L{match.level || 1}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs font-medium text-primary">Explore 5 Evaluated Roles</p>
      </DashboardCard>

      <DashboardCard
        icon={<IconPack />}
        title="Ready Packs"
        subtitle={`${packRows.length || 2} application packs generated`}
        href="/packs"
        accent="purple"
      >
        <div className="space-y-2">
          {packRows.map((company) => (
            <div key={company} className="rounded-xl border bg-background/60 p-3">
              <p className="text-sm font-medium">{company}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {['CV', 'Cover', 'Prep'].map((file) => (
                  <span key={file} className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] text-primary">
                    {file}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
        <p className="mt-3 text-xs font-medium text-primary">Manage & Download Packs</p>
      </DashboardCard>

      <DashboardCard
        icon={<IconYou />}
        title="You & Personas"
        subtitle={`${roleNames.length || 4} personas configured · DeepSeek AI`}
        href="/you"
        accent="orange"
      >
        <div className="rounded-xl border bg-background/60 p-3">
          <p className="text-xs text-muted-foreground">Active target persona</p>
          <p className="mt-1 text-sm font-semibold">{roleNames[0] || "Backend"}</p>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {(roleNames.length ? roleNames : fallbackRoles).slice(0, 4).map((role) => (
            <span key={role} className="rounded-full border px-2 py-1 text-[11px] text-muted-foreground">
              {role}
            </span>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted-foreground">Model: DeepSeek v4 Flash · Configure</p>
      </DashboardCard>
    </div>
  )
}

function sum(values: number[]): number {
  return values.reduce((total, value) => total + value, 0)
}

function roleLabels(jobs: HomeJobRow[]): string[] {
  const roles = Array.from(new Set(jobs.map((job) => job.role_family).filter(Boolean))) as string[]
  return roles.map(formatRoleLabel)
}

function formatRoleLabel(role: string): string {
  const known: Record<string, string> = {
    ai_ml: "AI/ML",
    backend_python: "Backend Python",
    full_stack: "Full Stack",
  }
  return known[role] || role.split("_").map(formatRolePart).join(" ")
}

function formatRolePart(part: string): string {
  return part.toUpperCase() === part ? part : part.charAt(0).toUpperCase() + part.slice(1)
}
