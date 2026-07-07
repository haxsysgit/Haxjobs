import type { IconProps } from "./types"

/** Pack — briefcase with sparkle. */
export function IconPack({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <rect x="4" y="8" width="16" height="12" rx="2" />
      <path d="M8 8V5a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v3" />
      <path d="M12 14v.01" opacity="0.5" />
      <path d="M10 12l2 2 2-2" />
      <circle cx="12" cy="2" r="1" fill="currentColor" opacity="0.6" />
    </svg>
  )
}
