import { Link } from "react-router-dom"
import { IconFit, IconPack, IconRecon, IconYou } from "@/components/icons"
import { DashboardCard } from "./DashboardCard"
import type { DiscoveryStatus, HomeJobRow } from "@/lib/homeSummary"
import {
  ArrowUpRight,
  FileText,
  Download,
  Cpu,
  Sparkles,
  CheckCircle2,
} from "lucide-react"

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
  { company: "Monzo", score: 85, level: 1, title: "Python Backend Developer" },
  { company: "Stripe", score: 78, level: 1, title: "Backend Engineer" },
]

const fallbackPacks = [
  { company: "Monzo", title: "Python Developer", files: ["cv_review.md", "cover_letter.md", "field_answers.md"] },
  { company: "Stripe", title: "Backend Engineer", files: ["cv_review.md", "cover_letter.md"] },
]

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
        title: job.title,
      }))
    : fallbackMatches
  const strongCount = topMatches.filter((job) => (job.fit_score || 0) >= 75).length || 2
  const packJobs = jobs.filter((job) => job.pack_status === "generated").slice(0, 2)
  const packRows = packJobs.length
    ? packJobs.map((job) => ({
        company: job.company,
        title: job.title,
        files: ["cv_review.md", "cover_letter.md", "field_answers.md"],
      }))
    : fallbackPacks
  const roleNames = roleLabels(jobs)
  const activeRole = roleNames[0] || "Backend"

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {/* Recon & Discovery */}
      <DashboardCard
        icon={<IconRecon />}
        title="Recon & Discovery"
        subtitle={`${scrapers.length || 3} scrapers active · ${totalFound || 47} jobs found`}
        href="/discovery"
        accent="green"
      >
        <div className="grid grid-cols-3 gap-2 text-center">
          {scrapers.slice(0, 3).map((scraper) => (
            <div key={scraper.name} className="rounded-xl border border-border/80 bg-background/60 p-2.5">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {scraper.name}
              </p>
              <p className="mt-1 font-heading text-xl text-foreground">{scraper.found || 0}</p>
              <p className="text-[11px] text-[oklch(0.5_0.1_153.85)] dark:text-[oklch(0.78_0.15_153.85)]">
                +{scraper.new || 0} new
              </p>
            </div>
          ))}
        </div>
        <div className="mt-3 rounded-xl border border-border/60 bg-secondary/50 p-3 text-xs text-muted-foreground">
          {discovery?.running ? (
            <div className="flex items-center gap-2">
              <span className="inline-flex h-2 w-2 rounded-full bg-[oklch(0.75_0.17_65)] animate-pulse" />
              <span>Sweeping Greenhouse & Ashby feeds…</span>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <span>Last sweep ran 2h ago. {totalNew || 12} new roles flagged.</span>
              <span className="inline-flex h-2 w-2 rounded-full bg-[oklch(0.67_0.17_153.85)] animate-pulse" />
            </div>
          )}
        </div>
        <Link
          to="/discovery"
          className="group mt-4 flex items-center justify-between rounded-lg bg-[oklch(0.67_0.17_153.85)] px-3 py-2 text-[13px] font-semibold text-[oklch(0.06_0.02_153.85)] transition-colors hover:bg-[oklch(0.72_0.17_153.85)]"
        >
          <span>Quick Recon Sweep</span>
          <ArrowUpRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </DashboardCard>

      {/* Top Scored Matches */}
      <DashboardCard
        icon={<IconFit />}
        title="Top Scored Matches"
        subtitle={`${strongCount} Strong Fit roles evaluated`}
        href="/jobs/backend_python"
        accent="blue"
      >
        <div className="space-y-2.5">
          {matchRows.map((match) => (
            <div
              key={match.company}
              className="flex items-center justify-between rounded-xl border border-border/80 bg-background/60 p-3 transition-colors hover:bg-secondary/40"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                {/* Score mini-ring */}
                <div className="relative size-10 shrink-0">
                  <svg width={40} height={40} className="-rotate-90">
                    <circle cx={20} cy={20} r={16} stroke="var(--border)" strokeWidth={3} fill="none" />
                    <circle
                      cx={20} cy={20} r={16}
                      stroke="oklch(0.67 0.17 153.85)"
                      strokeWidth={3}
                      fill="none"
                      strokeLinecap="round"
                      strokeDasharray={2 * Math.PI * 16}
                      strokeDashoffset={2 * Math.PI * 16 * (1 - match.score / 100)}
                      className="transition-all duration-700"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-[10px] font-bold leading-none text-foreground">{match.score}</span>
                  </div>
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate text-[13px] font-bold text-foreground">{match.company}</span>
                    <span className="shrink-0 rounded bg-[oklch(0.9_0.04_153.85)] px-1 text-[9px] font-bold text-[oklch(0.35_0.08_153.85)] dark:bg-[oklch(0.25_0.04_153.85)] dark:text-[oklch(0.82_0.1_153.85)]">
                      L{match.level || 1}
                    </span>
                  </div>
                  <p className="truncate text-[11px] text-muted-foreground">{match.title}</p>
                </div>
              </div>
              <Link
                to={`/jobs/detail/${match.company.toLowerCase()}`}
                className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1 text-[11px] font-medium text-foreground transition-colors hover:bg-secondary"
              >
                Review <ArrowUpRight className="size-3" />
              </Link>
            </div>
          ))}
        </div>
        <Link
          to="/jobs/backend_python"
          className="group mt-4 flex items-center justify-between rounded-lg bg-secondary px-3 py-2 text-[13px] font-semibold text-secondary-foreground transition-colors hover:bg-secondary/80"
        >
          <span>Explore {strongCount} Evaluated Roles</span>
          <ArrowUpRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </DashboardCard>

      {/* Ready Packs */}
      <DashboardCard
        icon={<IconPack />}
        title="Ready Packs"
        subtitle={`${packRows.length || 2} application packs generated`}
        href="/packs"
        accent="purple"
      >
        <div className="space-y-2.5">
          {packRows.map((pack) => (
            <div key={pack.company} className="rounded-xl border border-border/80 bg-background/60 p-3">
              <div className="flex items-center justify-between">
                <div className="font-heading text-sm font-bold text-foreground truncate">
                  {pack.company} — {pack.title}
                </div>
                <span className="text-[10px] text-muted-foreground">ready</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(pack.files || []).slice(0, 4).map((file) => (
                  <span
                    key={file}
                    className="inline-flex items-center gap-1 rounded-full bg-[oklch(0.92_0.05_255)] px-2 py-0.5 text-[10px] font-medium text-[oklch(0.35_0.08_255)] dark:bg-[oklch(0.25_0.05_255)] dark:text-[oklch(0.82_0.12_255)]"
                  >
                    <FileText size={10} />
                    {file}
                  </span>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-2">
                <button className="inline-flex w-full items-center justify-center gap-1 rounded-lg bg-secondary px-2.5 py-1 text-[11px] font-medium text-secondary-foreground transition-colors hover:bg-secondary/80">
                  <Download size={12} /> Open {pack.company} Pack
                </button>
              </div>
            </div>
          ))}
        </div>
        <Link
          to="/packs"
          className="group mt-4 flex items-center justify-between rounded-lg bg-secondary px-3 py-2 text-[13px] font-semibold text-secondary-foreground transition-colors hover:bg-secondary/80"
        >
          <span>Manage &amp; Download Packs</span>
          <ArrowUpRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
      </DashboardCard>

      {/* You & Personas */}
      <DashboardCard
        icon={<IconYou />}
        title="You &amp; Personas"
        subtitle={`${roleNames.length || 4} personas configured · DeepSeek AI`}
        href="/you"
        accent="orange"
      >
        <div className="rounded-xl border border-border/80 bg-background/60 p-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Active Target Persona
              </span>
              <div className="mt-1 flex items-center gap-1.5">
                <Sparkles size={12} className="text-[oklch(0.6_0.15_153.85)]" />
                <span className="text-[13px] font-bold text-foreground">{activeRole}</span>
              </div>
            </div>
            <Link
              to={`/you/${roleIds(jobs)[0] || "backend_python"}`}
              className="inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground hover:text-primary transition-colors"
            >
              Edit <ArrowUpRight size={11} />
            </Link>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {(roleNames.length ? roleNames : fallbackRoles).slice(0, 4).map((role) => (
            <Link
              key={role}
              to={role === activeRole ? `/you/${roleIds(jobs)[roleNames.indexOf(role)] || role.toLowerCase().replace(/\s+/g, "_")}` : "#"}
              className={
                role === activeRole
                  ? "inline-flex items-center gap-1 rounded-lg bg-[oklch(0.67_0.17_153.85)] px-2.5 py-1 text-[11px] font-bold text-[oklch(0.06_0.02_153.85)] transition-all"
                  : "inline-flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1 text-[11px] text-muted-foreground transition-all hover:bg-secondary hover:text-foreground"
              }
            >
              {role === activeRole && <CheckCircle2 size={10} />}
              {role}
            </Link>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-2 rounded-xl border border-border/80 bg-background/60 p-3">
          <Cpu size={14} className="text-muted-foreground" />
          <div>
            <div className="text-[12px] font-medium text-foreground">DeepSeek v4 Flash</div>
            <div className="text-[10px] text-muted-foreground">Active model · 1.2M tokens</div>
          </div>
        </div>
        <Link
          to="/settings/providers"
          className="group mt-4 flex items-center justify-between rounded-lg bg-secondary px-3 py-2 text-[13px] font-semibold text-secondary-foreground transition-colors hover:bg-secondary/80"
        >
          <span>Configure Providers</span>
          <ArrowUpRight className="size-3.5 transition-transform group-hover:translate-x-0.5" />
        </Link>
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

function roleIds(jobs: HomeJobRow[]): string[] {
  return Array.from(new Set(jobs.map((job) => job.role_family).filter(Boolean))) as string[]
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
