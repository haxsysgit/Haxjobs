import { useState, type ReactNode } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import { ChevronDown } from "lucide-react"

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
}

const statusColors: Record<string, string> = {
  success: "bg-emerald-500/15 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-400",
  running: "bg-amber-500/15 text-amber-600 dark:bg-amber-400/15 dark:text-amber-400",
  error: "bg-red-500/15 text-red-600 dark:bg-red-400/15 dark:text-red-400",
  idle: "bg-muted text-muted-foreground",
}

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
}: AgentMessageProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <motion.div
      initial={animated ? { opacity: 0, y: 16 } : undefined}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        "group rounded-xl border bg-card transition-all duration-200",
        variant === "compact" && "rounded-lg",
        variant === "highlight" && "border-primary/30 shadow-sm",
        expanded && "shadow-sm"
      )}
    >
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex w-full items-start gap-3 text-left",
          variant === "default" && "p-4",
          variant === "compact" && "p-3",
          variant === "highlight" && "p-5"
        )}
      >
        {/* Icon */}
        <div
          className={cn(
            "flex-shrink-0 rounded-full p-2",
            statusColors[status],
            status === "running" && "animate-pulse"
          )}
        >
          <div className="[&>svg]:size-5">{icon}</div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium leading-snug text-foreground">{title}</p>
          {(subtitle || timestamp) && (
            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              {subtitle && <span>{subtitle}</span>}
              {timestamp && (
                <>
                  {subtitle && <span aria-hidden="true">·</span>}
                  <span>{timestamp}</span>
                </>
              )}
            </div>
          )}
        </div>

        {/* Actions + chevron */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {actions}
          {children && (
            <ChevronDown
              className={cn(
                "size-4 text-muted-foreground transition-transform duration-200",
                expanded && "rotate-180"
              )}
            />
          )}
        </div>
      </button>

      {/* Expandable content */}
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
            <div
              className={cn(
                "border-t px-4 pb-4 pt-3",
                variant === "compact" && "px-3 pb-3 pt-2"
              )}
            >
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
