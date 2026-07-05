/** Filter chips for job list — status + role_family. */
import { cn } from "@/lib/utils"

interface Props {
  activeStatus: string | null
  onStatusChange: (status: string | null) => void
}

const STATUSES: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "evaluated", label: "Evaluated" },
  { value: "applied", label: "Applied" },
  { value: "maybe", label: "Maybe" },
  { value: "saved", label: "Saved" },
  { value: "skipped", label: "Skipped" },
  { value: "rejected", label: "Rejected" },
]

export function JobListFilters({ activeStatus, onStatusChange }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {STATUSES.map((s) => (
        <button
          key={s.value}
          type="button"
          onClick={() => onStatusChange(s.value || null)}
          className={cn(
            "rounded-full px-3 py-1 text-xs font-medium transition-colors",
            (activeStatus || "") === s.value
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          )}
        >
          {s.label}
        </button>
      ))}
    </div>
  )
}
