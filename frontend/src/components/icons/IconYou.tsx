import type { IconProps } from "./types"

/** You — user silhouette with aura. */
export function IconYou({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 4-7 8-7s8 3 8 7" />
      <circle cx="12" cy="12" r="9" opacity="0.2" />
    </svg>
  )
}
