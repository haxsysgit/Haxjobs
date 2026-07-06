import { Link, useParams } from "react-router-dom"
import { ArrowUpRight, BriefcaseBusiness, MapPin, Settings, Sparkles, UserRound } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button, buttonVariants } from "@/components/ui/button"
import { useRoles } from "@/hooks/useRoles"
import { roleDisplayName } from "@/lib/roles"
import { Skeleton } from "@/components/ui/skeleton"

const fallbackSkills: Record<string, string[]> = {
  backend_python: ["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "Redis"],
  full_stack: ["React", "TypeScript", "Python", "PostgreSQL"],
  ai_ml: ["Python", "LLMs", "Prompt engineering", "RAG"],
  waiter: ["Customer service", "POS systems", "Team coordination"],
}

const personaUse = [
  "Discovery filters stay role-aware.",
  "Evaluation prompts score against this target.",
  "Pack wording borrows the right proof points.",
]

function skillsFor(roleId: string) {
  return fallbackSkills[roleId] || ["Profile signals", "Role fit", "Evidence matching"]
}

function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-2xl border bg-background/70 px-4 py-3">
      <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-heading text-xl">{value}</p>
    </div>
  )
}

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

  const skillCount = new Set(roles.flatMap((role) => skillsFor(role.id))).size

  return (
    <div className="space-y-6">
      <PageHeader title="You" description="Your profile split into role-specific personas." />

      <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/10 via-card to-card">
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Persona core</p>
            <CardTitle className="mt-1 font-heading text-2xl">One profile, many attack angles.</CardTitle>
            <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
              HaxJobs uses these read-only personas to keep discovery, scoring, and packs focused per role.
              The chips below are current persona signals, not final truth.
            </p>
          </div>
          <Link to="/you/profile" className={buttonVariants({ variant: "outline" })}>
            Raw profile
          </Link>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatPill label="Active personas" value={roles.length} />
            <StatPill label="Skill signals" value={skillCount} />
            <StatPill label="Profile mode" value="Lenient" />
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {roles.map((role) => (
          <Link key={role.id} to={`/you/${role.id}`}>
            <Card className="group h-full overflow-hidden transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <UserRound className="size-5 text-primary" />
                  {role.displayName}
                  <ArrowUpRight className="ml-auto size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  {skillsFor(role.id).slice(0, 4).map((skill) => (
                    <span key={skill} className="rounded-full bg-primary/10 px-2 py-1 text-[11px] text-primary">
                      {skill}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">Discovery, fit scoring, and pack voice for this role.</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}

export function YouPersonaPage() {
  const { roleId = "" } = useParams<{ roleId: string }>()
  const displayName = roleDisplayName(roleId)
  const skills = skillsFor(roleId)

  return (
    <div className="space-y-6">
      <PageHeader
        title={displayName}
        kicker="You / Persona"
        description="A read-only role lens for discovery, evaluation, and packs. Editing lands later."
        action={
          <Link to={`/jobs/${roleId}`} className={buttonVariants({ variant: "outline" })}>
            Open Job Arena
          </Link>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <Card className="overflow-hidden">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 font-heading text-2xl">
              <BriefcaseBusiness className="size-5 text-primary" />
              {displayName} persona
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <section>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Skills in play</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <span key={skill} className="rounded-full border bg-background px-3 py-1 text-xs">
                    {skill}
                  </span>
                ))}
              </div>
            </section>
            <section className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border bg-muted/30 p-4">
                <MapPin className="mb-2 size-4 text-primary" />
                <p className="text-sm font-medium">Target locations</p>
                <p className="mt-1 text-xs text-muted-foreground">London, Remote, and profile-configured locations.</p>
              </div>
              <div className="rounded-2xl border bg-muted/30 p-4">
                <Sparkles className="mb-2 size-4 text-primary" />
                <p className="text-sm font-medium">Work modes</p>
                <p className="mt-1 text-xs text-muted-foreground">Remote, hybrid, onsite where your profile allows it.</p>
              </div>
            </section>
            <p className="rounded-2xl border border-dashed bg-background p-4 text-xs text-muted-foreground">
              Editing is intentionally off here. This page shows how HaxJobs currently thinks about the role while the profile editor waits for the later profile plan.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">How I use this persona</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {personaUse.map((item) => (
              <div key={item} className="flex gap-3 rounded-xl border bg-background/70 p-3 text-sm">
                <span className="mt-1 size-2 rounded-full bg-primary" />
                <span>{item}</span>
              </div>
            ))}
            <Button variant="ghost" className="w-full" disabled>
              Editing arrives in the profile pass
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

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
