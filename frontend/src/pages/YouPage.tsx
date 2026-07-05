import { Link, useParams } from "react-router-dom"
import { PageHeader } from "@/components/app/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { useRoles } from "@/hooks/useRoles"
import { roleDisplayName } from "@/lib/roles"
import { Skeleton } from "@/components/ui/skeleton"
import { UserRound, Settings } from "lucide-react"

export function YouPage() {
  const { roles, isLoading } = useRoles()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader title="You" description="Your career personas" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2].map((i) => (
            <div key={i} className="rounded-xl border p-6">
              <Skeleton className="mb-2 h-5 w-32" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title="You" description="Your career personas" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {roles.map((role) => (
          <Link key={role.id} to={`/you/${role.id}`}>
            <Card className="transition-all hover:border-primary/30 hover:shadow-sm">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <UserRound className="size-5 text-muted-foreground" />
                  {role.displayName}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">Persona config</p>
              </CardContent>
            </Card>
          </Link>
        ))}
        <Link to="/you/profile">
          <Card className="transition-all hover:border-primary/30 hover:shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Settings className="size-5 text-muted-foreground" />
                Profile
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">Raw profile data</p>
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  )
}

// Per-role persona (shell)
export function YouPersonaPage() {
  const { roleId } = useParams<{ roleId: string }>()
  const displayName = roleDisplayName(roleId || "")

  return (
    <div className="space-y-6">
      <PageHeader title={displayName} kicker="You / Persona" description="This is your career persona. Full editing lands after the jobs loop works." />
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          <UserRound className="mx-auto mb-3 size-10 text-muted-foreground/50" />
          <p>Persona editing for {displayName} is coming after the jobs loop is complete.</p>
          <p className="mt-1 text-xs">HaxJobs uses this persona to judge roles and tailor packs.</p>
        </CardContent>
      </Card>
    </div>
  )
}

// Raw profile (shell)
export function YouProfilePage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Profile" kicker="You / Profile" description="This is the memory core HaxJobs uses to judge roles." />
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          <Settings className="mx-auto mb-3 size-10 text-muted-foreground/50" />
          <p>Full profile editing lands after the jobs loop works.</p>
          <p className="mt-1 text-xs">For now, update your profile through onboarding or the profile API.</p>
        </CardContent>
      </Card>
    </div>
  )
}
