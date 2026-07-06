import type { ReactNode } from "react"
import { Link } from "react-router-dom"
import { Bot, KeyRound, SlidersHorizontal } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function ControlCard({
  to,
  icon,
  title,
  subtitle,
  detail,
}: {
  to: string
  icon: ReactNode
  title: string
  subtitle: string
  detail: string
}) {
  return (
    <Link to={to}>
      <Card className="group h-full overflow-hidden transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md">
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="grid size-10 place-items-center rounded-2xl bg-primary/10 text-primary">
              {icon}
            </div>
            <div>
              <CardTitle className="font-heading text-xl">{title}</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="rounded-2xl border bg-background/70 p-3 text-sm text-muted-foreground">{detail}</p>
        </CardContent>
      </Card>
    </Link>
  )
}

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Control Room" description="Providers, defaults, and the knobs that steer the agent." />
      <div className="grid gap-4 lg:grid-cols-2">
        <ControlCard
          to="/settings/providers"
          icon={<KeyRound className="size-5" />}
          title="Providers"
          subtitle="DeepSeek primary, custom providers welcome"
          detail="Model access lives here. Configure keys and choose the brain HaxJobs uses for heavier calls."
        />
        <ControlCard
          to="/settings/preferences"
          icon={<SlidersHorizontal className="size-5" />}
          title="Preferences"
          subtitle="Search defaults and profile depth"
          detail="Keep the hunt pointed at the right locations, work modes, and score thresholds."
        />
      </div>
      <Card className="border-dashed bg-muted/20">
        <CardContent className="flex items-center gap-3 p-4 text-sm text-muted-foreground">
          <Bot className="size-5 text-primary" />
          Keep it honest: this room shows real setup flows or read-only previews. No fake switches.
        </CardContent>
      </Card>
    </div>
  )
}
