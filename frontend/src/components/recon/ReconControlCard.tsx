import { Link } from "react-router-dom"
import { Button, buttonVariants } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { RadarSweep } from "@/components/recon/RadarSweep"

interface ReconControlCardProps {
  running: boolean
  onStart: () => void | Promise<void>
}

export function ReconControlCard({ running, onStart }: ReconControlCardProps) {
  return (
    <section className="relative overflow-hidden rounded-3xl border bg-card p-5 shadow-sm sm:p-6">
      <div className="pointer-events-none absolute -right-16 -top-16 size-44 rounded-full bg-primary/10 blur-3xl" />
      <div className="relative flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <RadarSweep running={running} />
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-primary">Recon control</p>
            <h2 className="mt-1 font-heading text-2xl leading-tight">Ready to sweep.</h2>
            <p className="mt-2 max-w-xl text-sm text-muted-foreground">
              I'll hit Greenhouse, Ashby, and Lever in parallel. Usually done in ~40 seconds.
            </p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button onClick={onStart} disabled={running}>
            {running ? <><Spinner className="mr-2 size-4" /> Sweeping...</> : "Start Recon Sweep"}
          </Button>
          <Link to="/settings/preferences" className={buttonVariants({ variant: "outline" })}>
            Configure sources
          </Link>
        </div>
      </div>
    </section>
  )
}
