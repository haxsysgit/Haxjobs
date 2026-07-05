import type { IconProps } from "./types"

/** HaxJobs agent mascot — small fox/cat silhouette. */
export function IconAgent({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M12 2L4 8l3 12h10l3-12z" />
      <circle cx="10" cy="10" r="1.5" fill="currentColor" stroke="none" />
      <circle cx="14" cy="10" r="1.5" fill="currentColor" stroke="none" />
      <path d="M9 15c1 .5 2 .5 3 0s2-.5 3 0" />
    </svg>
  )
}
