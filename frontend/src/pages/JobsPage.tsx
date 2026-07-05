import { Link, useParams } from "react-router-dom"
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { PageHeader } from "@/components/app/PageHeader"
import { EmptyState } from "@/components/app/EmptyState"
import { IconArena } from "@/components/icons"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { JobCard } from "@/components/jobs/JobCard"
import { JobListFilters } from "@/components/jobs/JobListFilters"
import { listJobs } from "@/lib/jobs"
import type { JobListItem } from "@/lib/jobs"
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
  const [activeStatus, setActiveStatus] = useState<string | null>(null)

  const { data: jobsData, isLoading } = useQuery<{ jobs: JobListItem[]; total: number }>({
    queryKey: ["jobs", "role", roleId, activeStatus],
    queryFn: () => listJobs({ role_family: roleId, status: activeStatus || undefined }),
    enabled: !!roleId,
    staleTime: 30_000,
    retry: false,
  })

  const jobs = jobsData?.jobs || []

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

      <JobListFilters activeStatus={activeStatus} onStatusChange={setActiveStatus} />

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
          {jobs.map((job, i) => (
            <JobCard key={job.id} job={job} index={i} roleId={roleId} />
          ))}
        </div>
      )}
    </div>
  )
}
