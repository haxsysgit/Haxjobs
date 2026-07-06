import type { ReactNode } from "react"

interface PreferenceRowProps {
  icon: ReactNode
  label: string
  value: string
  note: string
}

export function PreferenceRow({ icon, label, value, note }: PreferenceRowProps) {
  return (
    <div className="flex gap-3 rounded-2xl border bg-background/70 p-4">
      <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="mt-1 font-heading text-xl">{value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{note}</p>
      </div>
    </div>
  )
}
