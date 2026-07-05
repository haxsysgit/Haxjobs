import { useQuery } from "@tanstack/react-query"
import { AgentMessage } from "@/components/app/AgentMessage"
import { EmptyState } from "@/components/app/EmptyState"
import { PageHeader } from "@/components/app/PageHeader"
import { IconPack } from "@/components/icons"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { apiGet } from "@/lib/api"
import { fixtureMode, getFixtureJobs, type FixtureJob } from "@/lib/fixtures"

interface PackJob {
  id: number
  title: string
  company: string
  pack_status: string
  pack_dir?: string
}

export function PacksPage() {
  const { data, isLoading } = useQuery<{ jobs: PackJob[] }>({
    queryKey: ["jobs", "packs"],
    queryFn: () => apiGet("/jobs?pack_status=generated&limit=20"),
    enabled: !fixtureMode,
    staleTime: 30_000,
    retry: false,
  })

  const fixturePacks: FixtureJob[] = fixtureMode
    ? getFixtureJobs().filter((j: FixtureJob) => j.pack_status === "generated")
    : []

  const packs = fixtureMode ? fixturePacks : (data?.jobs || [])

  return (
    <div className="space-y-6">
      <PageHeader title="Packs" description="Application packs generated for your best-match roles." />

      {isLoading ? (
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
      ) : packs.length === 0 ? (
        <EmptyState
          icon={<IconPack />}
          title="No packs yet"
          description="When I find a strong match for your profile, I'll generate an application pack here."
        />
      ) : (
        <div className="space-y-3">
          {packs.map((pack: any) => (
            <AgentMessage
              key={pack.id}
              icon={<IconPack />}
              title={`Pack ready: ${pack.company} — ${pack.title}`}
              subtitle="CV, cover letter, interview prep"
              status="success"
              variant="compact"
              actions={
                <Button variant="ghost" size="sm" className="text-xs">Open</Button>
              }
            />
          ))}
        </div>
      )}
    </div>
  )
}
