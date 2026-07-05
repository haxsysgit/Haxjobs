import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface PageHeaderProps {
  title: string
  kicker?: string
  description?: string
  action?: ReactNode
  className?: string
}

export function PageHeader({ title, kicker, description, action, className }: PageHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div className="space-y-0.5">
        {kicker && (
          <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            {kicker}
          </p>
        )}
        <h1 className="text-2xl font-heading font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action && <div className="flex-shrink-0">{action}</div>}
    </div>
  )
}
