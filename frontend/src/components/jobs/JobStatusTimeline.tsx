/** Simple vertical timeline showing job status progression. */
import { cn } from "@/lib/utils"

interface Props {
  status: string
  discoveredAt?: string | null
  evaluatedAt?: string | null
  packStatus?: string | null
  currentDecision?: string | null
}

interface Step {
  label: string
  done: boolean
  timestamp?: string
}

export function JobStatusTimeline({ status, discoveredAt, evaluatedAt, packStatus, currentDecision }: Props) {
  const steps: Step[] = [
    { label: "Discovered", done: true, timestamp: discoveredAt || undefined },
    {
      label: "Evaluated",
      done: status === "evaluated" || status === "applied" || status === "maybe" || status === "saved" || status === "skipped" || status === "rejected",
      timestamp: evaluatedAt || undefined,
    },
    { label: "Pack Generated", done: packStatus === "generated" },
    {
      label: currentDecision ? `Decided: ${currentDecision}` : "Decision Recorded",
      done: !!currentDecision,
    },
  ]

  return (
    <div className="rounded-xl border bg-card p-5 space-y-3">
      <h3 className="font-medium text-sm">Timeline</h3>
      <div className="space-y-0">
        {steps.map((step, i) => (
          <div key={step.label} className="flex items-start gap-3">
            {/* Connector + dot */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "size-2.5 rounded-full mt-1.5",
                  step.done ? "bg-primary" : "bg-muted-foreground/30"
                )}
              />
              {i < steps.length - 1 && (
                <div
                  className={cn(
                    "w-px flex-1 mt-1",
                    step.done && steps[i + 1]?.done ? "bg-primary/40" : "bg-muted-foreground/20"
                  )}
                  style={{ minHeight: "1rem" }}
                />
              )}
            </div>
            {/* Label */}
            <div className="pb-3">
              <p className={cn("text-xs", step.done ? "text-foreground font-medium" : "text-muted-foreground")}>
                {step.label}
              </p>
              {step.timestamp && (
                <p className="text-[10px] text-muted-foreground">{step.timestamp}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
