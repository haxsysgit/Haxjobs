/** Decision buttons for Apply / Maybe / Save / Skip / Reject. */
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Decision } from "@/lib/jobs"

interface Props {
  onDecide: (decision: Decision, reason?: string) => Promise<void>
  currentDecision?: string | null
  disabled?: boolean
}

const DECISIONS: { value: Decision; label: string; variant: "default" | "secondary" | "outline" | "ghost" }[] = [
  { value: "apply", label: "Apply", variant: "default" },
  { value: "maybe", label: "Maybe", variant: "secondary" },
  { value: "save", label: "Save", variant: "outline" },
  { value: "skip", label: "Skip", variant: "ghost" },
  { value: "reject", label: "Reject", variant: "ghost" },
]

export function JobDecisionBar({ onDecide, currentDecision, disabled }: Props) {
  const [loading, setLoading] = useState<Decision | null>(null)

  async function handleDecision(d: Decision) {
    setLoading(d)
    try {
      await onDecide(d)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="rounded-xl border bg-card p-5 space-y-3">
      <h3 className="font-medium text-sm">Your Call</h3>
      <div className="flex flex-wrap gap-2">
        {DECISIONS.map((d) => (
          <Button
            key={d.value}
            variant={d.variant}
            size="sm"
            disabled={disabled || loading !== null}
            onClick={() => handleDecision(d.value)}
            className={cn(
              "text-xs",
              currentDecision === d.value && "ring-2 ring-primary"
            )}
          >
            {loading === d.value ? "…" : d.label}
          </Button>
        ))}
      </div>
    </div>
  )
}
