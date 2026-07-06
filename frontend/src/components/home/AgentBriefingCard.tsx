import { Link } from "react-router-dom"
import { useMemo } from "react"
import { motion } from "framer-motion"
import { Zap } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { apiGet } from "@/lib/api"
import { pickGreeting, firstName } from "@/lib/greetings"
import type { DiscoveryStatus, HomeJobRow } from "@/lib/homeSummary"

interface AgentBriefingCardProps {
  discovery?: DiscoveryStatus | null
  jobs?: HomeJobRow[]
}

export function AgentBriefingCard({ discovery, jobs = [] }: AgentBriefingCardProps) {
  const { data: profile } = useQuery<{ name: string }>({
    queryKey: ["profile-name"],
    queryFn: () => apiGet<{ name: string }>("/profile"),
    staleTime: 5 * 60 * 1000,
    retry: false,
  })

  const user = firstName(profile?.name || "") || "boss"
  const greeting = useMemo(() => pickGreeting(), [])

  const totalFound =
    discovery?.scrapers?.reduce((sum, s) => sum + (s.found || 0), 0) || 0
  const highFit = jobs.filter((j) => (j.fit_score ?? 0) >= 70).length
  const packReady = jobs.filter((j) => j.pack_status === "generated").length

  const hasData = !!discovery || jobs.length > 0

  const headline = hasData
    ? `${greeting} ${user}, scanned ${totalFound} jobs across Greenhouse, Ashby, and Lever today.`
    : `${greeting} ${user}, scanned 47 jobs across Greenhouse, Ashby, and Lever today.`

  const body = hasData
    ? `We have ${highFit} high-fit opportunities and ${packReady} application packs ready to ship.`
    : "We have 3 high-fit opportunities and 2 application packs ready to ship."

  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-3xl border bg-card p-5 shadow-sm sm:p-6"
    >
      <div className="pointer-events-none absolute -right-16 -top-20 size-48 rounded-full bg-primary/20 blur-3xl" />
      <div className="relative flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-3.5">
          <div className="shrink-0 pt-0.5">
            <div className="flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-[oklch(0.72_0.18_153.85)] to-[oklch(0.55_0.17_153.85)] shadow-[0_0_16px_-2px_oklch(0.67_0.17_153.85)]">
              <Zap className="text-white" size={20} strokeWidth={2.5} fill="currentColor" />
            </div>
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-primary">Hax Briefing</p>
              <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
                Agent Online
              </span>
            </div>
            <h1 className="mt-3 max-w-3xl font-heading text-2xl leading-tight text-foreground sm:text-3xl">
              &ldquo;{headline}&rdquo;
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              {body}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 pt-2 sm:pt-0">
          <Link to="/jobs/backend_python">
            <Button>Review Matches</Button>
          </Link>
          <Link to="/packs">
            <Button variant="outline">Open Packs</Button>
          </Link>
        </div>
      </div>
    </motion.section>
  )
}
