import { HaxJobsMark } from "./HaxJobsMark"
import { cn } from "@/lib/utils"

/**
 * HaxJobs full lockup — mark + wordmark + tagline.
 * Designed for the sidebar top (260px wide, dark background).
 *
 * "Hax" in Lato Black 900 (agent personality, weight, confidence)
 * "Jobs" in Lato Light 300 (the domain, secondary)
 * Tagline: tracked uppercase, understated
 */

interface HaxJobsLockupProps {
  markSize?: number
  variant?: "color" | "light" | "dark"
  showTagline?: boolean
  className?: string
  animated?: boolean
}

export function HaxJobsLockup({
  markSize = 36,
  variant = "color",
  showTagline = true,
  className = "",
  animated = false,
}: HaxJobsLockupProps) {
  const textColor =
    variant === "light"
      ? "oklch(0.20 0.02 153.85)"
      : "oklch(0.92 0.02 153.85)"
  const taglineColor =
    variant === "light"
      ? "oklch(0.50 0.03 153.85)"
      : "oklch(0.50 0.02 153.85)"

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <HaxJobsMark
        size={markSize}
        variant={variant}
        animated={animated}
      />
      <div className="flex flex-col" style={{ fontFamily: "'Lato', sans-serif" }}>
        <div className="flex items-baseline">
          <span
            style={{
              color: "oklch(0.67 0.17 153.85)",
              fontSize: `${markSize * 0.58}px`,
              fontWeight: 900,
              letterSpacing: "-0.03em",
              lineHeight: 1,
            }}
          >
            Hax
          </span>
          <span
            style={{
              color: textColor,
              fontSize: `${markSize * 0.58}px`,
              fontWeight: 300,
              letterSpacing: "-0.03em",
              lineHeight: 1,
            }}
          >
            Jobs
          </span>
        </div>
        {showTagline && (
          <span
            style={{
              color: taglineColor,
              fontSize: `${Math.max(markSize * 0.22, 8)}px`,
              fontWeight: 400,
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              lineHeight: 1,
              marginTop: `${markSize * 0.1}px`,
            }}
          >
            your own job-search agent
          </span>
        )}
      </div>
    </div>
  )
}
