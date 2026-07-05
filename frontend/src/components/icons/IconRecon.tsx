import type { IconProps } from "./types"

/** Recon — radar/satellite dish. */
export function IconRecon({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="2" />
      <path d="M12 2a10 10 0 0 1 10 10" opacity="0.6" />
      <path d="M12 6a6 6 0 0 1 6 6" opacity="0.8" />
      <path d="M5 19a10 10 0 0 1 0-14" />
      <path d="M19 5a10 10 0 0 1 0 14" />
    </svg>
  )
}
