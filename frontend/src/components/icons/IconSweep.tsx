import { motion } from "framer-motion"
import type { IconProps } from "./types"

/** Recon sweep — radar arc with optional spin animation. */
export function IconSweep({ size = 24, animate = false, ...props }: IconProps & { animate?: boolean }) {
  const svg = (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <circle cx="12" cy="12" r="9" opacity="0.3" />
      <circle cx="12" cy="12" r="5" opacity="0.5" />
      <circle cx="12" cy="12" r="2" />
      <path d="M12 3a9 9 0 0 1 9 9" />
      <line x1="12" y1="3" x2="12" y2="12" />
    </svg>
  )

  if (!animate) return svg

  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
      style={{ width: size, height: size }}
    >
      {svg}
    </motion.div>
  )
}
