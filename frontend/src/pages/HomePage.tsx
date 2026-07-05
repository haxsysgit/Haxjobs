import { motion } from "framer-motion"
import { AgentActivityFeed } from "@/components/app/AgentActivityFeed"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { apiGet } from "@/lib/api"
import { PageHeader } from "@/components/app/PageHeader"

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

  // If no profile, show onboarding prompt
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

  return <AgentActivityFeed />
}
