import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"
import { PageHeader } from "@/components/app/PageHeader"
import { AgentMessage } from "@/components/app/AgentMessage"
import { IconSweep, IconRecon } from "@/components/icons"

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

export function DiscoveryPage() {
  const [status, setStatus] = useState<DiscoveryStatus | null>(null)
  const [starting, setStarting] = useState(false)

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

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recon"
        description="Run ATS scrapers to find jobs matching your profile."
        action={
          <Button onClick={start} disabled={isRunning}>
            {isRunning ? <><Spinner className="mr-2 size-4" /> Sweeping...</> : "Start Recon"}
          </Button>
        }
      />

      {/* Running state */}
      {isRunning && (
        <AgentMessage
          icon={<IconSweep animate />}
          title="I'm running a recon sweep right now. Checking scrapers for new jobs."
          status="running"
        >
          <div className="space-y-2 text-sm">
            {status?.scrapers?.map((s) => (
              <div key={s.name} className="flex items-center justify-between">
                <span>{s.name}</span>
                <span className={cn(
                  "text-xs",
                  s.status === "done" && "text-emerald-600 dark:text-emerald-400",
                  s.status === "error" && "text-red-600 dark:text-red-400",
                  s.status === "running" && "text-amber-600 dark:text-amber-400"
                )}>
                  {s.status}
                </span>
              </div>
            ))}
          </div>
        </AgentMessage>
      )}

      {/* Done state */}
      {!isRunning && status && (
        <AgentMessage
          icon={<IconRecon />}
          title={`I completed a recon sweep. ${status.found} jobs found, ${status.new} new, ${status.promoted} promoted.`}
          status="success"
          subtitle={`${status.errors?.length || 0} errors`}
        >
          <div className="space-y-3 text-sm">
            {status.scrapers?.map((s) => (
              <div key={s.name} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <p className="font-medium">{s.name}</p>
                  <p className="text-xs text-muted-foreground">{s.status}</p>
                </div>
                <div className="flex gap-3 text-xs">
                  <span>{s.found} found</span>
                  <span>{s.matched} matched</span>
                  <span>{s.new} new</span>
                  {s.errors > 0 && <span className="text-red-500">{s.errors} errors</span>}
                </div>
              </div>
            ))}
            {status.errors && status.errors.length > 0 && (
              <div>
                <p className="mb-1 text-xs font-medium text-red-500">Errors</p>
                {status.errors.slice(0, 5).map((e, i) => (
                  <p key={i} className="text-xs text-muted-foreground">{e}</p>
                ))}
              </div>
            )}
          </div>
        </AgentMessage>
      )}

      {/* Idle state */}
      {!isRunning && !status && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <IconRecon className="mb-4 size-12 text-muted-foreground/50" />
          <h3 className="text-lg font-medium">No recon runs yet</h3>
          <p className="mt-1 max-w-sm text-sm text-muted-foreground">
            Hit the button above and I'll search Greenhouse, Ashby, and Lever for you.
          </p>
        </div>
      )}
    </div>
  )
}
