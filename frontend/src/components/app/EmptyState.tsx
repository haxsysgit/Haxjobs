import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  variant?: "default" | "compact"
}

export function EmptyState({ icon, title, description, action, variant = "default" }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center",
        variant === "default" && "py-16",
        variant === "compact" && "py-8"
      )}
    >
      {icon && (
        <div className="mb-4 rounded-full bg-muted p-3 text-muted-foreground [&>svg]:size-8">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium">{title}</h3>
      {description && (
        <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}
