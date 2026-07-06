import { Heart, Plug, Cpu } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"

interface PrefRowProps {
  label: string
  icon: React.ReactNode
  value: string
}

function PrefRow({ label, icon, value }: PrefRowProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground">
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[13px] text-muted-foreground">{label}</div>
      </div>
      <span className="shrink-0 text-[13.5px] font-medium text-foreground">{value}</span>
    </div>
  )
}

export function SettingsPreferencesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Preferences"
        kicker="Config"
        description="Search radius, profile depth, notification tone. The dials."
      />

      <div className="space-y-3">
        <PrefRow
          label="Search radius"
          icon={<Heart size={15} />}
          value="London + Remote"
        />
        <PrefRow
          label="Profile depth"
          icon={<Cpu size={15} />}
          value="Lenient"
        />
        <PrefRow
          label="Minimum score"
          icon={<Plug size={15} />}
          value="55%"
        />
      </div>

      <p className="text-xs text-muted-foreground">
        These are preview rows. They do not write profile data or change backend settings yet.
      </p>
    </div>
  )
}
