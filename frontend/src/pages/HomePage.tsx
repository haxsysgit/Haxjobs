import { motion } from "framer-motion"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { AgentBriefingCard } from "@/components/home/AgentBriefingCard"
import { HomeMetricGrid } from "@/components/home/HomeMetricGrid"
import { LiveAgentFeedPanel } from "@/components/home/LiveAgentFeedPanel"
import { QuickStatsRow } from "@/components/home/QuickStatsRow"
import { apiGet } from "@/lib/api"
import { PageHeader } from "@/components/app/PageHeader"
import { fixtureMode, getFixtureJobs } from "@/lib/fixtures"
import {
  buildHomeFeedEvents,
  type DiscoveryStatus,
  type HomeDecisionRow,
  type HomeJobRow,
} from "@/lib/homeSummary"

interface OnboardingStatus {
  stage?: string
}

export function HomePage() {
  const { data: onboard } = useQuery<OnboardingStatus>({
    queryKey: ["onboarding-status"],
    queryFn: () => apiGet<OnboardingStatus>("/onboarding/status"),
    retry: false,
    staleTime: 30_000,
  })

  const discoveryQ = useQuery<DiscoveryStatus>({
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

  if (onboard && onboard.stage !== "complete") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6"
      >
        <PageHeader title="Home" description="Agent activity feed" />
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <h2 className="text-xl font-heading font-semibold">Welcome to HaxJobs.</h2>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Let's build your profile first so I can start finding jobs that fit you.
          </p>
          <Link to="/onboarding" className="mt-6">
            <Button size="lg">Build My Profile</Button>
          </Link>
        </div>
      </motion.div>
    )
  }

  const jobs = fixtureMode ? getFixtureJobs() : jobsQ.data?.jobs || []
  const events = buildHomeFeedEvents({
    discovery: discoveryQ.data,
    jobs,
    decisions: decisionsQ.data?.decisions,
    fixtureMode,
  })

  return (
    <div className="gap-6 space-y-6 lg:grid lg:grid-cols-[minmax(0,1.45fr)_minmax(360px,0.9fr)] lg:space-y-0">
      <section className="min-w-0 space-y-5">
        <AgentBriefingCard />
        <HomeMetricGrid discovery={discoveryQ.data} jobs={jobs} />
        <QuickStatsRow jobs={jobs} events={events} />
      </section>
      <aside className="min-w-0 lg:sticky lg:top-6 lg:max-h-[calc(100vh-7rem)]">
        <LiveAgentFeedPanel eventCount={events.length} />
      </aside>
    </div>
  )
}
