import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"

interface DiscoveryStatus {
  running: boolean
  run_id: string
  found: number
  new: number
  promoted: number
  errors: string[]
  finished_at: string
}

export function DashboardPage() {
  const [status, setStatus] = useState<DiscoveryStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  async function refreshStatus() {
    const response = await fetch("/api/discovery/status")
    if (response.ok) setStatus(await response.json())
  }

  async function runDiscovery() {
    setError("")
    setLoading(true)
    try {
      const response = await fetch("/api/discovery/run", { method: "POST" })
      if (!response.ok) throw new Error("Could not start discovery")
      await refreshStatus()
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Could not start discovery")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshStatus().catch(() => undefined)
  }, [])

  useEffect(() => {
    if (!status?.running) return
    const timer = window.setInterval(() => refreshStatus().catch(() => undefined), 2000)
    return () => window.clearInterval(timer)
  }, [status?.running])

  const running = Boolean(status?.running || loading)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-heading font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Start a discovery run, then review what HaxJobs found.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Welcome to HaxJobs</CardTitle>
          <CardDescription>Your personal job search platform.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Discover jobs, evaluate fit, generate application packs, and track every application.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Discovery</CardTitle>
          <CardDescription>Run the configured ATS scrapers and promote matching jobs into the pipeline.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Found" value={status?.found ?? 0} />
            <Stat label="New" value={status?.new ?? 0} />
            <Stat label="Promoted" value={status?.promoted ?? 0} />
          </div>

          {status?.errors?.length ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {status.errors.slice(0, 3).map((item) => <p key={item}>{item}</p>)}
            </div>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <div className="flex items-center gap-3">
            <Button onClick={runDiscovery} disabled={running}>
              {running ? <Spinner className="mr-2 size-4" /> : null}
              {running ? "Discovery running" : "Discover jobs"}
            </Button>
            {status?.finished_at ? <span className="text-sm text-muted-foreground">Last run finished.</span> : null}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-muted/20 p-3">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  )
}
