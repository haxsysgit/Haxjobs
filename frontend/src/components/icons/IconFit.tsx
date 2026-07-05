import type { IconProps } from "./types"

/** Fit evaluation — target with checkmark. */
export function IconFit({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" opacity="0.6" />
      <circle cx="12" cy="12" r="1" fill="currentColor" />
      <path d="M9 12l2 2 4-4" opacity="0.5" />
    </svg>
  )
}
