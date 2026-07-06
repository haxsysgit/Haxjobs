import { Badge } from "@/components/ui/badge"

interface ProviderTileProps {
  name: string
  detail: string
  status: string
}

export function ProviderTile({ name, detail, status }: ProviderTileProps) {
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
