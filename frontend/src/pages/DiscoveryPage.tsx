import { useEffect, useRef, useState } from "react"
import { Radio } from "lucide-react"
import { cn } from "@/lib/utils"
import { ReconControlCard } from "@/components/recon/ReconControlCard"
import { fireSweepCompleteConfetti } from "@/hooks/useConfetti"

interface ScraperStatus {
  name: string
  status: "pending" | "running" | "done" | "error" | string
  found: number
  matched: number
  new: number
  errors: number
  message: string
}

interface DiscoveryStatus {
  running: boolean
  run_id: string
  found: number
  new: number
  promoted: number
  errors: string[]
  scrapers: ScraperStatus[]
  finished_at: string
}

export default function DiscoveryPage() {
  const [status, setStatus] = useState<DiscoveryStatus | null>(null)
  const [starting, setStarting] = useState(false)
  const wasRunning = useRef(false)

  async function fetchStatus() {
    try {
      const res = await fetch("/api/discovery/status")
      if (res.ok) setStatus(await res.json())
    } catch { /* ignore */ }
  }

  async function start() {
    setStarting(true)
    try {
      await fetch("/api/discovery/run", { method: "POST" })
      await fetchStatus()
    } catch { /* ignore */ }
    setStarting(false)
  }

  useEffect(() => {
    fetchStatus()
    const timer = setInterval(fetchStatus, 3000)
    return () => clearInterval(timer)
  }, [])

  const isRunning = status?.running || starting

  useEffect(() => {
    if (wasRunning.current && !isRunning && status) {
      fireSweepCompleteConfetti()
    }
    wasRunning.current = Boolean(isRunning)
  }, [isRunning, status])

  return (
    <div className="h-full overflow-y-auto">
      {/* Opus-style page header */}
      <div className="sticky top-0 z-10 border-b border-border bg-bg-elev/95 px-6 py-4 backdrop-blur">
        <div>
          <h1 className="font-heading text-2xl text-text">Recon</h1>
          <p className="text-sm text-text-muted">
            Watch the scrapers and launch new sweeps.
          </p>
        </div>
      </div>

      <div className="mx-auto max-w-4xl space-y-4 px-6 py-6">
        <ReconControlCard running={Boolean(isRunning)} onStart={start} />

        {/* Running state */}
        {isRunning && (
          <div className="rounded-2xl border border-primary/20 bg-primary-soft p-4">
            <div className="mb-2 flex items-center gap-2">
              <div className="flex h-2 w-2 rounded-full bg-primary animate-pulse" />
              <p className="text-sm font-medium text-text">Sweeping in progress...</p>
            </div>
            <div className="space-y-1.5 text-sm">
              {status?.scrapers?.map((s) => (
                <div key={s.name} className="flex items-center justify-between">
                  <span>{s.name}</span>
                  <span className={cn(
                    "text-xs font-medium",
                    s.status === "done" && "text-primary",
                    s.status === "error" && "text-danger",
                    s.status === "running" && "text-warn"
                  )}>
                    {s.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Done state */}
        {!isRunning && status && (
          <div className="rounded-2xl border border-border bg-surface p-4">
            <div className="mb-3 flex items-center gap-2">
              <Radio size={18} className="text-primary" />
              <p className="text-sm font-medium text-text">
                Sweep complete. {status.found} jobs found, {status.new} new, {status.promoted} promoted.
              </p>
            </div>
            <div className="space-y-2">
              {status.scrapers?.map((s) => (
                <div key={s.name} className="flex items-center justify-between rounded-lg border border-border bg-surface-2 px-3 py-2">
                  <div>
                    <p className="text-sm font-medium text-text">{s.name}</p>
                    <p className="text-[11px] text-text-faint">{s.status}</p>
                  </div>
                  <div className="flex gap-3 text-xs text-text-muted">
                    <span>{s.found} found</span>
                    <span>{s.matched} matched</span>
                    <span className="text-primary font-medium">{s.new} new</span>
                    {s.errors > 0 && <span className="text-danger">{s.errors} errors</span>}
                  </div>
                </div>
              ))}
            </div>
            {status.errors && status.errors.length > 0 && (
              <div className="mt-3 rounded-lg border border-danger/30 bg-danger/10 p-2">
                <p className="mb-1 text-xs font-medium text-danger">Errors</p>
                {status.errors.slice(0, 5).map((e, i) => (
                  <p key={i} className="text-xs text-text-muted">{e}</p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Idle state */}
        {!isRunning && !status && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Radio size={48} className="mb-4 text-text-faint" />
            <h3 className="text-lg font-medium text-text">No recon runs yet</h3>
            <p className="mt-1 max-w-sm text-sm text-text-muted">
              Hit the button above and I'll search Greenhouse, Ashby, and Lever for you.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
