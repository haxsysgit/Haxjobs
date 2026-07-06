import { type ReactNode } from "react"
import { motion } from "framer-motion"
import { Link } from "react-router-dom"
import { ArrowUpRight } from "lucide-react"
import { cn } from "@/lib/utils"

interface DashboardCardProps {
  icon: ReactNode
  title: string
  subtitle: string
  href: string
  accent?: "green" | "blue" | "purple" | "orange"
  children: ReactNode
}

const accentStyles = {
  green: "from-[oklch(0.72_0.18_153.85)] to-[oklch(0.55_0.17_153.85)] shadow-[oklch(0.67_0.17_153.85)]",
  blue: "from-[oklch(0.7_0.15_255)] to-[oklch(0.5_0.15_255)] shadow-[oklch(0.62_0.17_255)]",
  purple: "from-[oklch(0.65_0.2_290)] to-[oklch(0.5_0.18_290)] shadow-[oklch(0.6_0.18_290)]",
  orange: "from-[oklch(0.7_0.18_65)] to-[oklch(0.55_0.16_65)] shadow-[oklch(0.65_0.17_65)]",
}

export function DashboardCard({
  icon,
  title,
  subtitle,
  href,
  accent = "green",
  children,
}: DashboardCardProps) {
  const accentClass = accentStyles[accent]

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -2 }}
      transition={{ duration: 0.2 }}
      className="group relative overflow-hidden rounded-2xl border bg-card shadow-sm transition-shadow hover:shadow-md"
    >
      <div
        className={cn(
          "pointer-events-none absolute -right-12 -top-12 size-32 rounded-full bg-gradient-to-br opacity-0 blur-2xl transition-opacity group-hover:opacity-20",
          accentClass
        )}
      />
      <Link to={href} className="block h-full p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div
              className={cn(
                "flex size-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-lg [&>svg]:size-5",
                accentClass
              )}
            >
              {icon}
            </div>
            <div className="min-w-0">
              <h3 className="font-heading text-lg leading-tight text-foreground">{title}</h3>
              <p className="text-[12.5px] text-muted-foreground">{subtitle}</p>
            </div>
          </div>
          <ArrowUpRight className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
        </div>
        <div className="mt-4">{children}</div>
      </Link>
    </motion.div>
  )
}
