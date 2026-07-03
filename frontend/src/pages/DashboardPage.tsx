import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Spinner } from "@/components/ui/spinner"
import { cn } from "@/lib/utils"

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
    const timer = window.setInterval(() => refreshStatus().catch(() => undefined), 1500)
    return () => window.clearInterval(timer)
  }, [status?.running])

  const running = Boolean(status?.running || loading)
  const scrapers = status?.scrapers?.length ? status.scrapers : [
    { name: "greenhouse", status: "pending", found: 0, matched: 0, new: 0, errors: 0, message: "" },
    { name: "ashby", status: "pending", found: 0, matched: 0, new: 0, errors: 0, message: "" },
    { name: "lever", status: "pending", found: 0, matched: 0, new: 0, errors: 0, message: "" },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-heading font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">Start a discovery run and watch each scraper report back.</p>
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
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle>Discovery</CardTitle>
              <CardDescription>Greenhouse, Ashby, and Lever run one by one. Accepted jobs are promoted into the main queue.</CardDescription>
            </div>
            <Button onClick={runDiscovery} disabled={running}>
              {running ? <Spinner className="mr-2 size-4" /> : null}
              {running ? "Running" : "Discover jobs"}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat label="Found" value={status?.found ?? 0} />
            <Stat label="New" value={status?.new ?? 0} />
            <Stat label="Promoted" value={status?.promoted ?? 0} />
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            {scrapers.map((scraper) => <ScraperCard key={scraper.name} scraper={scraper} />)}
          </div>

          {status?.errors?.length ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              {status.errors.slice(0, 4).map((item) => <p key={item}>{item}</p>)}
            </div>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {status?.finished_at ? <p className="text-sm text-muted-foreground">Last run finished.</p> : null}
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

function ScraperCard({ scraper }: { scraper: ScraperStatus }) {
  const running = scraper.status === "running"
  return (
    <div className="rounded-xl border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="font-medium capitalize">{scraper.name}</h3>
        <span className={cn(
          "rounded-full px-2 py-0.5 text-xs font-medium",
          scraper.status === "done" && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
          scraper.status === "running" && "bg-primary/10 text-primary",
          scraper.status === "error" && "bg-destructive/10 text-destructive",
          scraper.status === "pending" && "bg-muted text-muted-foreground",
        )}>
          {running ? "running" : scraper.status}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <MiniStat label="Found" value={scraper.found} />
        <MiniStat label="Matched" value={scraper.matched} />
        <MiniStat label="New" value={scraper.new} />
        <MiniStat label="Errors" value={scraper.errors} />
      </div>
      {scraper.message ? <p className="mt-3 text-xs text-destructive">{scraper.message}</p> : null}
    </div>
  )
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-muted/30 p-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-semibold">{value}</p>
    </div>
  )
}
