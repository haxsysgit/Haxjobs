import { useState, type ReactNode } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { ChevronDown, Zap } from "lucide-react"
import { TypingIndicator } from "./TypingIndicator"

export interface AgentMessageProps {
  icon: ReactNode
  title: string
  subtitle?: string
  timestamp?: string
  status?: "success" | "running" | "error" | "idle"
  children?: ReactNode
  actions?: ReactNode
  variant?: "default" | "compact" | "highlight"
  animated?: boolean
  direction?: "left" | "right"
}

const toneBorder: Record<string, string> = {
  success: "border-l-[oklch(0.67_0.17_153.85)] bg-[oklch(0.97_0.02_153.85)]/60 dark:border-l-[oklch(0.55_0.15_153.85)] dark:bg-[oklch(0.18_0.03_153.85)]/60",
  running: "border-l-[oklch(0.75_0.16_65)] bg-[oklch(0.97_0.03_65)]/60 dark:border-l-[oklch(0.6_0.14_65)] dark:bg-[oklch(0.18_0.03_65)]/60",
  error: "border-l-red-400 bg-red-50/60 dark:border-l-red-500 dark:bg-red-950/30",
  idle: "border-l-border bg-card",
}

const runPulse = "animate-pulse border-l-[oklch(0.75_0.16_65)] bg-[oklch(0.97_0.03_65)]/60 dark:border-l-[oklch(0.6_0.14_65)] dark:bg-[oklch(0.18_0.03_65)]/60"

export function AgentMessage({
  icon,
  title,
  subtitle,
  timestamp,
  status = "idle",
  children,
  actions,
  variant = "default",
  animated = true,
  direction = "left",
}: AgentMessageProps) {
  const [expanded, setExpanded] = useState(false)
  const compact = variant === "compact"
  const isAgent = direction === "left"
  const isRunning = status === "running"
  const borderClass = isRunning ? runPulse : toneBorder[status] || toneBorder.idle

  const bubble = (
    <motion.div
      initial={animated ? { opacity: 0, y: 12 } : undefined}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "group flex gap-3",
        isAgent ? "flex-row" : "flex-row-reverse"
      )}
    >
      {/* Agent avatar — left side only */}
      {isAgent && (
        <div className="shrink-0 pt-0.5">
          <div className={cn("flex items-center justify-center rounded-full bg-gradient-to-br from-[oklch(0.72_0.18_153.85)] to-[oklch(0.55_0.17_153.85)] shadow-[0_0_12px_-2px_oklch(0.67_0.17_153.85)]", compact ? "size-7" : "size-8")}>
            <Zap className="text-white" size={compact ? 14 : 16} strokeWidth={2.5} fill="currentColor" />
          </div>
        </div>
      )}

      {/* Bubble */}
      <div className="min-w-0 flex-1">
        {/* Header */}
        <div className={cn("mb-1 flex items-baseline gap-2", isAgent ? "flex-row" : "flex-row-reverse")}>
          <span className={cn("font-semibold text-foreground", compact ? "text-xs" : "text-[13px]")}>
            {isAgent ? "Hax" : "You"}
          </span>
          {timestamp && (
            <span className="text-[11px] text-muted-foreground">{timestamp}</span>
          )}
        </div>

        {/* Bubble body */}
        <div
          className={cn(
            "relative rounded-2xl border p-4 shadow-sm transition-colors",
            isAgent ? "rounded-tl-md border-l-2" : "rounded-tr-md",
            compact ? "p-3" : "p-4",
            variant === "highlight" && "border-primary/30",
            borderClass
          )}
        >
          {/* Inner content: icon + text area + expand chevron */}
          <div className={cn("flex items-start", isRunning && "gap-3")}>
            {isRunning ? (
              <div className="flex items-center gap-3">
                <div className={cn("flex-shrink-0 rounded-full p-1.5", toneBorder.running || "bg-amber-500/15")}>
                  <div className="[&>svg]:size-4">{icon}</div>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>{title}</span>
                  <TypingIndicator />
                </div>
              </div>
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => children && setExpanded(!expanded)}
                  aria-expanded={children ? expanded : undefined}
                  className="flex min-w-0 flex-1 items-start gap-3 text-left"
                >
                  {/* Status icon */}
                  <div className={cn(
                    "flex-shrink-0 rounded-full p-1.5",
                    status === "success" && "bg-emerald-500/15 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-400",
                    status === "error" && "bg-red-500/15 text-red-600 dark:bg-red-400/15 dark:text-red-400",
                    status === "idle" && "bg-muted text-muted-foreground"
                  )}>
                    <div className="[&>svg]:size-4">{icon}</div>
                  </div>

                  {/* Text */}
                  <div className="min-w-0 flex-1">
                    <p className={cn("font-medium leading-snug text-foreground", compact ? "text-xs" : "text-sm")}>
                      {title}
                    </p>
                    {(subtitle || timestamp) && (
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        {subtitle && <span>{subtitle}</span>}
                      </div>
                    )}
                  </div>

                  {children && (
                    <ChevronDown
                      className={cn(
                        "size-4 flex-shrink-0 text-muted-foreground transition-transform duration-200",
                        expanded && "rotate-180"
                      )}
                    />
                  )}
                </button>

                {actions && (
                  <div className="flex flex-shrink-0 items-center gap-2">
                    {actions}
                  </div>
                )}
              </>
            )}
          </div>

          {/* Expandable children */}
          <AnimatePresence initial={false}>
            {expanded && children && (
              <motion.div
                key="content"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <div className="mt-3 border-t pt-3">
                  {children}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  )

  return bubble
}
