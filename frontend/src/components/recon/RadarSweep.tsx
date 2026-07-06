import { cn } from "@/lib/utils"

interface RadarSweepProps {
  running?: boolean
  className?: string
}

export function RadarSweep({ running, className }: RadarSweepProps) {
  return (
    <div
      className={cn(
        "relative grid size-24 place-items-center overflow-hidden rounded-full border border-primary/30 bg-primary/5 shadow-[0_0_40px_oklch(0.67_0.17_153.85/0.16)] md:size-30",
        className
      )}
      aria-hidden="true"
    >
      <div className="absolute inset-3 rounded-full border border-primary/20" />
      <div className="absolute inset-7 rounded-full border border-primary/15" />
      <div className="absolute left-1/2 top-0 h-full w-px -translate-x-1/2 bg-primary/10" />
      <div className="absolute left-0 top-1/2 h-px w-full -translate-y-1/2 bg-primary/10" />
      <div
        className={cn(
          "radar-sweep absolute inset-0 rounded-full bg-[conic-gradient(from_0deg,transparent_0deg,oklch(0.67_0.17_153.85/0.34)_55deg,transparent_95deg)]",
          running && "radar-sweep-fast"
        )}
      />
      <span className="absolute left-[62%] top-[28%] size-2 rounded-full bg-primary shadow-[0_0_14px_oklch(0.67_0.17_153.85/0.75)]" />
      <span className="absolute left-[35%] top-[58%] size-1.5 rounded-full bg-primary/80" />
      <span className="absolute left-[70%] top-[70%] size-1.5 rounded-full bg-primary/70" />
      <span className="relative size-2.5 rounded-full bg-primary" />
    </div>
  )
}
