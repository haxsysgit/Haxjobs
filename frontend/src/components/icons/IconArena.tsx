import type { IconProps } from "./types"

/** Job Arena — crossed swords. */
export function IconArena({ size = 24, ...props }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M14 2v6l4 4" />
      <path d="M10 2v6l-4 4" />
      <path d="M12 12v10" />
      <path d="M8 16h8" />
    </svg>
  )
}
