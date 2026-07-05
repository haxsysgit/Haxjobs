import type { IconProps } from "./types"

/** Decision — thumbs up with star. */
export function IconDecision({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M7 10v8a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1h3z" />
      <path d="M14 13V5a2 2 0 0 0-2-2l-3 10v8h8.6a2 2 0 0 0 2-1.6l1.2-6a2 2 0 0 0-2-2.4H14z" />
      <path d="M17 15l-1 3" opacity="0.5" />
      <path d="M12 22v.01" opacity="0.3" />
    </svg>
  )
}
