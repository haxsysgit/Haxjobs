import { Link, useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { AgentMessage } from "@/components/app/AgentMessage"
import { EmptyState } from "@/components/app/EmptyState"
import { PageHeader } from "@/components/app/PageHeader"
import { IconArena, IconFit } from "@/components/icons"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { apiGet } from "@/lib/api"
import { fixtureMode, getFixtureJobsByRole, type FixtureJob } from "@/lib/fixtures"
import { useRoles } from "@/hooks/useRoles"
import { roleDisplayName } from "@/lib/roles"
import { Swords } from "lucide-react"

// Job Arena index — role picker
export function JobsPage() {
  const { roles, isLoading } = useRoles()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Job Arena" description="Pick a role to see matching jobs" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border p-6">
              <Skeleton className="mb-2 h-5 w-32" />
              <Skeleton className="h-3 w-20" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Job Arena" description="Pick a role to see matching jobs" />
      {roles.length === 0 ? (
        <EmptyState
          icon={<Swords />}
          title="No roles configured yet"
          description="Set up your profile first, then I'll find jobs for each role."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {roles.map((role) => (
            <Link key={role.id} to={`/jobs/${role.id}`}>
              <div className="group rounded-xl border bg-card p-6 transition-all hover:border-primary/30 hover:shadow-sm">
                <h3 className="font-medium">{role.displayName}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {role.id.replace(/_/g, " ")}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

// Role-specific job list
export function JobsRolePage() {
  const { roleId } = useParams<{ roleId: string }>()
  const displayName = roleDisplayName(roleId || "")

  const { data: jobsData, isLoading } = useQuery<{ jobs: any[] }>({
    queryKey: ["jobs", "role", roleId],
    queryFn: () => apiGet(`/jobs?role_family=${roleId}&limit=20`),
    enabled: !fixtureMode && !!roleId,
    staleTime: 30_000,
    retry: false,
  })

  // Fixture mode
  const fixtureJobs: FixtureJob[] = fixtureMode && roleId ? getFixtureJobsByRole(roleId) : []

  const jobs = fixtureMode ? fixtureJobs : (jobsData?.jobs || [])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title={displayName} kicker="Job Arena" />
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="flex items-center gap-3 rounded-xl border p-4">
              <Skeleton className="size-10 rounded-full" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={displayName}
        kicker="Job Arena"
        description={`${jobs.length} jobs found`}
      />

      {jobs.length === 0 ? (
        <EmptyState
          icon={<IconArena />}
          title="No jobs yet"
          description="I haven't found jobs matching this role yet. Start a recon sweep."
          action={
            <Link to="/discovery">
              <Button>Go to Recon</Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {jobs.map((job: any) => (
            <AgentMessage
              key={job.id}
              icon={<IconFit />}
              title={`${job.company} — ${job.title}`}
              subtitle={
                job.fit_score
                  ? `Score ${job.fit_score} · Level ${job.level} · ${job.fit_verdict}`
                  : `Awaiting evaluation`
              }
              timestamp={job.discovered_at ? timeAgo(job.discovered_at) : undefined}
              status={job.fit_score ? "success" : "idle"}
              variant="compact"
              actions={
                <Link to={`/jobs/${roleId}/${job.id}`}>
                  <Button variant="ghost" size="sm" className="text-xs">Detail</Button>
                </Link>
              }
            >
              <div className="flex flex-wrap gap-2 text-xs">
                {job.strongest_matches?.map((m: string) => (
                  <Badge key={m} variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/10 dark:text-emerald-400">{m}</Badge>
                ))}
                {job.major_gaps?.map((g: string) => (
                  <Badge key={g} variant="outline" className="bg-amber-500/10 text-amber-600 dark:bg-amber-400/10 dark:text-amber-400">{g}</Badge>
                ))}
              </div>
            </AgentMessage>
          ))}
        </div>
      )}
    </div>
  )
}

function timeAgo(iso: string): string {
  if (!iso) return ""
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}
