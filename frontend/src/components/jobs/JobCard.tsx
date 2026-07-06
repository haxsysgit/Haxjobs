/** Compact job card for the job list. */
import { Link } from "react-router-dom"
import { motion } from "framer-motion"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { JobListItem } from "@/lib/jobs"

interface Props {
  job: JobListItem
  index?: number
  roleId?: string
}

const verdictColors: Record<string, string> = {
  STRONG_FIT: "bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/10 dark:text-emerald-400",
  GOOD_FIT: "bg-blue-500/10 text-blue-600 dark:bg-blue-400/10 dark:text-blue-400",
  POSSIBLE: "bg-amber-500/10 text-amber-600 dark:bg-amber-400/10 dark:text-amber-400",
}

const levelColors: Record<string, string> = {
  "1": "bg-emerald-500/15 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-400",
  "2": "bg-blue-500/15 text-blue-600 dark:bg-blue-400/15 dark:text-blue-400",
  "3": "bg-amber-500/15 text-amber-600 dark:bg-amber-400/15 dark:text-amber-400",
  "4": "bg-red-500/15 text-red-600 dark:bg-red-400/15 dark:text-red-400",
}

export function JobCard({ job, index = 0, roleId }: Props) {
  const href = roleId ? `/jobs/${roleId}/${job.id}` : `/jobs/${job.id}`

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ y: -2 }}
    >
      <Link to={href} className="block">
        <div className="group flex items-start gap-4 rounded-xl border bg-card p-4 transition-all hover:border-primary/35 hover:shadow-md hover:shadow-primary/5">
          <div className="flex-1 min-w-0">
            {job.fit_score != null && (
              <p className="mb-1 text-xs font-semibold text-primary">
                Yo, scored {job.company || "this one"} at {job.fit_score}%.
              </p>
            )}
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-sm truncate">{job.title}</h3>
              {job.fit_score != null && (
                <span
                  className={cn(
                    "rounded-md px-1.5 py-0.5 text-[10px] font-semibold",
                    verdictColors[job.fit_verdict || ""] || "bg-muted text-muted-foreground"
                  )}
                >
                  {job.fit_score}% {job.fit_verdict}
                </span>
              )}
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {job.company}{job.location ? ` · ${job.location}` : ""}
            </p>
            {job.strongest_matches && job.strongest_matches.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {job.strongest_matches.slice(0, 3).map((m) => (
                  <Badge key={m} variant="outline" className="text-[10px] py-0">
                    {m}
                  </Badge>
                ))}
              </div>
            )}
          </div>
          {job.level != null && (
            <div className={cn("rounded-lg px-2 py-1 text-[11px] font-bold", levelColors[String(job.level)] || "bg-muted")}>
              L{job.level}
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  )
}
