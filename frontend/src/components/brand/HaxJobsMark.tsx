/**
 * HaxJobs Mark — "The Scanner"
 *
 * From Claude Opus 4.6, unchanged.
 *
 * An angular hexagonal shield enclosing a negative-space "H" glyph.
 * The crossbar extends past the right pillar into a sharp point —
 * the scan-head, the cursor, the agent always moving forward.
 * The left crossbar end is a flat cut — grounded, you the user.
 *
 * At 16px favicon size, it reads as a compact angular glyph.
 */

interface HaxJobsMarkProps {
  size?: number
  variant?: "color" | "light" | "dark"
  className?: string
  animated?: boolean
  glow?: boolean
}

const COLORS = {
  color: {
    primary: "oklch(0.67 0.17 153.85)",
    secondary: "oklch(0.55 0.14 153.85)",
    bright: "oklch(0.78 0.16 153.85)",
  },
  light: {
    primary: "oklch(0.18 0.03 153.85)",
    secondary: "oklch(0.25 0.03 153.85)",
    bright: "oklch(0.30 0.04 153.85)",
  },
  dark: {
    primary: "oklch(0.92 0.02 153.85)",
    secondary: "oklch(0.82 0.02 153.85)",
    bright: "oklch(0.97 0.01 153.85)",
  },
}

export function HaxJobsMark({
  size = 36,
  variant = "color",
  className = "",
  animated = false,
  glow = false,
}: HaxJobsMarkProps) {
  const c = COLORS[variant]
  const uid = `haxmark-${size}-${variant}`

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      role="img"
      aria-label="HaxJobs logo mark"
    >
      <defs>
        <linearGradient id={`${uid}-grad`} x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor={c.bright} />
          <stop offset="100%" stopColor={c.secondary} />
        </linearGradient>
        {glow && variant === "color" && (
          <filter id={`${uid}-glow`}>
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        )}
      </defs>

      {/* Hexagonal shield */}
      <path
        d="M 24 2 L 42 12 C 44.5 13.2 46 15.8 46 18.5 L 46 29.5 C 46 32.2 44.5 34.8 42 36 L 24 46 L 6 36 C 3.5 34.8 2 32.2 2 29.5 L 2 18.5 C 2 15.8 3.5 13.2 6 12 Z"
        fill={variant === "color" ? `url(#${uid}-grad)` : c.primary}
        filter={glow && variant === "color" ? `url(#${uid}-glow)` : undefined}
      />

      {/* H glyph — negative space carve */}
      <path
        d="M 13 12 L 19 12 L 19 20.5 L 29 20.5 L 29 12 L 35 12 L 35 36 L 29 36 L 29 27.5 L 19 27.5 L 19 36 L 13 36 Z"
        fill={variant === "dark" ? "oklch(0.13 0.02 153.85)" : variant === "color" ? "oklch(0.13 0.02 153.85)" : "#ffffff"}
      />

      {/* Scan tip — arrow extending from crossbar past right pillar */}
      <path
        d="M 35 21.5 L 40 24 L 35 26.5 Z"
        fill={variant === "dark" ? "oklch(0.13 0.02 153.85)" : variant === "color" ? "oklch(0.13 0.02 153.85)" : "#ffffff"}
      />

      {/* Left block — flat scanner base, grounding */}
      <rect
        x="8" y="21.5" width="5" height="5" rx="0.5"
        fill={variant === "dark" ? "oklch(0.13 0.02 153.85)" : variant === "color" ? "oklch(0.13 0.02 153.85)" : "#ffffff"}
      />

      {/* Animated scan line */}
      {animated && (
        <line x1="8" y1="24" x2="40" y2="24" stroke={c.bright} strokeWidth="1" opacity="0.6">
          <animate
            attributeName="y1" values="14;34;14" dur="3s" repeatCount="indefinite"
            calcMode="spline" keySplines="0.4 0 0.2 1;0.4 0 0.2 1"
          />
          <animate
            attributeName="y2" values="14;34;14" dur="3s" repeatCount="indefinite"
            calcMode="spline" keySplines="0.4 0 0.2 1;0.4 0 0.2 1"
          />
          <animate
            attributeName="opacity" values="0.2;0.8;0.2" dur="3s" repeatCount="indefinite"
          />
        </line>
      )}
    </svg>
  )
}
