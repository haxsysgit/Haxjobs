import type { IconProps } from "./types"

/** Control Room — sliders/knobs. */
export function IconControl({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <line x1="4" y1="7" x2="10" y2="7" />
      <line x1="14" y1="7" x2="20" y2="7" />
      <circle cx="12" cy="7" r="2" />
      <line x1="4" y1="17" x2="14" y2="17" />
      <line x1="18" y1="17" x2="20" y2="17" />
      <circle cx="16" cy="17" r="2" />
    </svg>
  )
}
