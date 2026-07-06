import { useQuery } from "@tanstack/react-query"
import { Cpu, KeyRound, Plug } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"
import { apiGet } from "@/lib/api"
import { cn } from "@/lib/utils"
import { SetupPage } from "./SetupPage"

interface SetupStatus {
  configured: boolean
  provider: string | null
  presets: { key: string; name: string; models: string[] }[]
}

interface ProviderRowProps {
  name: string
  icon: React.ReactNode
  status: "active" | "configured" | "missing-key"
  meta: string
}

function ProviderRow({ name, icon, status, meta }: ProviderRowProps) {
  const badge =
    status === "active"
      ? {
          label: "Active",
          cls: "bg-[oklch(0.92_0.06_153.85)] text-[oklch(0.35_0.08_153.85)] dark:bg-[oklch(0.28_0.06_153.85)] dark:text-[oklch(0.85_0.14_153.85)]",
        }
      : status === "configured"
        ? {
            label: "Configured",
            cls: "bg-[oklch(0.93_0.05_255)] text-[oklch(0.35_0.08_255)] dark:bg-[oklch(0.28_0.05_255)] dark:text-[oklch(0.85_0.14_255)]",
          }
        : {
            label: "Needs key",
            cls: "bg-[oklch(0.94_0.05_65)] text-[oklch(0.4_0.1_65)] dark:bg-[oklch(0.28_0.05_65)] dark:text-[oklch(0.85_0.14_65)]",
          }

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[14px] font-semibold text-foreground">{name}</div>
        <div className="text-[12px] text-muted-foreground">{meta}</div>
      </div>
      <span className={cn("rounded-md px-2 py-0.5 text-[10px] font-bold tracking-wider", badge.cls)}>
        {badge.label}
      </span>
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
      <PageHeader
        title="Providers"
        kicker="Config"
        description="AI providers, models, and keys. Who's thinking for me today."
      />

      <div className="space-y-3">
        <ProviderRow
          name="DeepSeek v4 Flash"
          icon={<Cpu size={15} />}
          status={data?.configured && configuredProvider === "deepseek" ? "active" : "configured"}
          meta="Default · 1.2M tokens used"
        />
        <ProviderRow
          name="OpenAI"
          icon={<Plug size={15} />}
          status={data?.configured && configuredProvider === "openai" ? "active" : "missing-key"}
          meta={data?.configured && configuredProvider === "openai" ? "Backup · fallback chain" : "Add API key to enable"}
        />
        <ProviderRow
          name="Custom endpoint"
          icon={<KeyRound size={15} />}
          status={data?.configured && configuredProvider === "custom" ? "active" : "missing-key"}
          meta={data?.configured && configuredProvider === "custom" ? "Active · custom base URL" : "Add API key to enable"}
        />
      </div>

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
