/**
 * HaxJobs Mark — "The Caret"
 *
 * Hybrid: Opus 4.6's hexagonal shield container with Opus 4.8's
 * upward-chevron H and pulsing agent-eye node.
 *
 * - Hexagonal shield = protection, systematic precision (4.6)
 * - Two-pillar H with chevron crossbar = the "^" of Hax, rising
 *   trajectory, signal-lock for an agent always watching (4.8)
 * - Pulsing node at apex = agent's eye / status dot (4.8)
 * - Pulse ring animation when live (4.8)
 */

interface HaxJobsMarkProps {
  size?: number
  variant?: "color" | "light" | "dark"
  className?: string
  live?: boolean
  glow?: boolean
}

const GREEN = "oklch(0.67 0.17 153.85)"
const GREEN_BRIGHT = "oklch(0.78 0.16 153.85)"
const GREEN_DEEP = "oklch(0.55 0.14 153.85)"

const CUTOUT = {
  color: "oklch(0.13 0.02 153.85)",
  light: "#ffffff",
  dark: "oklch(0.13 0.02 153.85)",
}

const SHIELD_FILL = {
  color: undefined as string | undefined, // gradient via url()
  light: "oklch(0.18 0.03 153.85)",
  dark: "oklch(0.92 0.02 153.85)",
}

export function HaxJobsMark({
  size = 36,
  variant = "color",
  className = "",
  live = false,
  glow = false,
}: HaxJobsMarkProps) {
  const uid = `hax-${size}-${variant}`

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
          <stop offset="0%" stopColor={GREEN_BRIGHT} />
          <stop offset="100%" stopColor={GREEN_DEEP} />
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

      {/* Hexagonal shield — from 4.6 */}
      <path
        d="M 24 2 L 42 12 C 44.5 13.2 46 15.8 46 18.5 L 46 29.5 C 46 32.2 44.5 34.8 42 36 L 24 46 L 6 36 C 3.5 34.8 2 32.2 2 29.5 L 2 18.5 C 2 15.8 3.5 13.2 6 12 Z"
        fill={variant === "color" ? `url(#${uid}-grad)` : SHIELD_FILL[variant]}
        filter={glow && variant === "color" ? `url(#${uid}-glow)` : undefined}
      />

      {/* Left pillar — from 4.8's structure */}
      <rect
        x="14"
        y="16"
        width="7"
        height="22"
        rx="3.5"
        fill={CUTOUT[variant]}
      />

      {/* Right pillar — from 4.8's structure */}
      <rect
        x="27"
        y="16"
        width="7"
        height="22"
        rx="3.5"
        fill={CUTOUT[variant]}
      />

      {/* Upward-chevron crossbar — the "^" of Hax, the rising trajectory */}
      <path
        d="M 14 33 L 24 20 L 34 33 L 34 28 L 24 15 L 14 28 Z"
        fill={CUTOUT[variant]}
      />

      {/* Agent-eye node at chevron apex — from 4.8 */}
      <circle
        cx="24"
        cy="9"
        r="3.5"
        fill={GREEN}
      >
        {live && (
          <animate
            attributeName="opacity"
            values="1;0.35;1"
            dur="1.8s"
            repeatCount="indefinite"
          />
        )}
      </circle>

      {/* Pulse ring — from 4.8 */}
      {live && (
        <circle
          cx="24"
          cy="9"
          r="3.5"
          fill="none"
          stroke={GREEN}
          strokeWidth="1.5"
          opacity="0.6"
        >
          <animate
            attributeName="r"
            values="3.5;9;3.5"
            dur="1.8s"
            repeatCount="indefinite"
          />
          <animate
            attributeName="opacity"
            values="0.6;0;0.6"
            dur="1.8s"
            repeatCount="indefinite"
          />
        </circle>
      )}
    </svg>
  )
}
