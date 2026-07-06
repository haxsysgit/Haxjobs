import { useQuery } from "@tanstack/react-query"
import { KeyRound, ServerCog } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { apiGet } from "@/lib/api"
import { SetupPage } from "./SetupPage"

interface SetupStatus {
  configured: boolean
  provider: string | null
  presets: { key: string; name: string; models: string[] }[]
}

function ProviderTile({ name, detail, status }: { name: string; detail: string; status: string }) {
  return (
    <div className="rounded-2xl border bg-background/70 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{name}</p>
          <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
        </div>
        <Badge variant={status === "Active" ? "default" : "secondary"}>{status}</Badge>
      </div>
    </div>
  )
}

export function SettingsProvidersPage() {
  const { data } = useQuery<SetupStatus>({
    queryKey: ["setup-status"],
    queryFn: () => apiGet<SetupStatus>("/setup/status"),
    retry: false,
    staleTime: 30_000,
  })

  const configuredProvider = data?.provider || "deepseek"

  return (
    <div className="space-y-6">
      <PageHeader title="Providers" kicker="Control Room" description="Pick the model brain. Keep the real setup flow below." />

      <Card className="overflow-hidden border-primary/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-heading text-2xl">
            <ServerCog className="size-5 text-primary" />
            Provider overview
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <ProviderTile
            name="DeepSeek"
            detail="Best default for HaxJobs evaluation and pack work."
            status={data?.configured && configuredProvider === "deepseek" ? "Active" : "Ready"}
          />
          <ProviderTile
            name="OpenAI"
            detail="Useful backup if configured through setup."
            status={data?.configured && configuredProvider === "openai" ? "Active" : "Needs key"}
          />
          <ProviderTile
            name="Custom"
            detail="Bring your own compatible endpoint."
            status={data?.configured && configuredProvider === "custom" ? "Active" : "Optional"}
          />
        </CardContent>
      </Card>

      <div className="rounded-3xl border bg-card p-4 shadow-sm">
        <div className="mb-4 flex items-center gap-2 text-sm text-muted-foreground">
          <KeyRound className="size-4 text-primary" />
          Actual key saving stays in the existing setup form.
        </div>
        <SetupPage />
      </div>
    </div>
  )
}
