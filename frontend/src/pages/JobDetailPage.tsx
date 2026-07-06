/** Job detail page with fit, decisions, timeline, and jd text. */
import { useParams, Link } from "react-router-dom"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { ArrowLeft, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { EmptyState } from "@/components/app/EmptyState"
import { AgentMessage } from "@/components/app/AgentMessage"
import { IconFit, IconArena } from "@/components/icons"
import { JobFitPanel } from "@/components/jobs/JobFitPanel"
import { JobDecisionBar } from "@/components/jobs/JobDecisionBar"
import { JobStatusTimeline } from "@/components/jobs/JobStatusTimeline"
import { getJob, evaluateJob, recordDecision } from "@/lib/jobs"
import type { JobDetail, Decision } from "@/lib/jobs"
import { roleDisplayName } from "@/lib/roles"
import { decisionCopy } from "@/lib/decisionCopy"
import { fireApplyConfetti } from "@/hooks/useConfetti"
import { toast } from "sonner"
import { useState } from "react"

export function JobDetailPage() {
  const { roleId, jobId } = useParams<{ roleId?: string; jobId: string }>()
  const id = Number(jobId)
  const displayName = roleId ? roleDisplayName(roleId) : null
  const queryClient = useQueryClient()
  const [evaluating, setEvaluating] = useState(false)

  const { data: job, isLoading, isError } = useQuery<JobDetail>({
    queryKey: ["job", id],
    queryFn: () => getJob(id),
    staleTime: 30_000,
    retry: false,
  })

  async function handleEvaluate() {
    setEvaluating(true)
    try {
      const result = await evaluateJob(id)
      if (result.ok) {
        toast.success(`Evaluated: ${result.fit_score}% - ${result.fit_verdict}`)
        queryClient.invalidateQueries({ queryKey: ["job", id] })
        queryClient.invalidateQueries({ queryKey: ["jobs"] })
      } else {
        toast.error(result.error || "Evaluation failed")
      }
    } catch (e: any) {
      toast.error(e.message || "Evaluation failed")
    } finally {
      setEvaluating(false)
    }
  }

  async function handleDecide(decision: Decision) {
    try {
      const result = await recordDecision(id, decision)
      if (result.ok) {
        toast.success(decisionCopy[decision])
        if (decision === "apply") {
          fireApplyConfetti()
        }
        queryClient.invalidateQueries({ queryKey: ["job", id] })
        queryClient.invalidateQueries({ queryKey: ["jobs"] })
      } else {
        toast.error(result.error || "Decision failed")
      }
    } catch (e: any) {
      toast.error(e.message || "Decision failed")
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-48" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-4">
            <Skeleton className="h-40" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-32" />
            <Skeleton className="h-24" />
          </div>
        </div>
      </div>
    )
  }

  if (isError || !job) {
    return (
      <EmptyState
        icon={<IconArena />}
        title="Job not found"
        description="This job may have been removed or the link is broken."
        action={<Link to="/jobs"><Button variant="outline">Back to Job Arena</Button></Link>}
      />
    )
  }

  const latestDecision = job.decisions?.length > 0 ? job.decisions[job.decisions.length - 1] : null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Back link */}
      <div className="flex items-center gap-2">
        <Link
          to={roleId ? `/jobs/${roleId}` : "/jobs"}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="size-3" />
          {displayName ? `${displayName}` : "Job Arena"}
        </Link>
      </div>

      {/* Header */}
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-heading font-semibold">{job.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {job.company}{job.location ? ` · ${job.location}` : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {job.fit_score != null && (
              <div className="rounded-lg bg-primary/10 px-3 py-1.5 text-center">
                <div className="text-lg font-bold">{job.fit_score}%</div>
                <div className="text-[10px] text-muted-foreground">{job.fit_verdict}</div>
              </div>
            )}
            {job.source_url && (
              <a href={job.source_url} target="_blank" rel="noopener noreferrer">
                <Button variant="ghost" size="icon" className="size-8">
                  <ExternalLink className="size-4" />
                </Button>
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left column: job description */}
        <div className="lg:col-span-2 space-y-4">
          {/* Agent message summary */}
          {job.summary && (
            <AgentMessage
              icon={<IconFit />}
              title="Agent Brief"
              subtitle={job.summary}
              variant="highlight"
            />
          )}

          {/* JD text */}
          <div className="rounded-xl border bg-card p-5">
            <h2 className="font-medium text-sm mb-3">Job Description</h2>
            {/* ponytail: no rich HTML rendering, raw text for v1 */}
            <div className="text-sm text-muted-foreground whitespace-pre-wrap max-h-96 overflow-y-auto">
              {job.jd_text || <span className="italic text-muted-foreground/60">No description available.</span>}
            </div>
          </div>
        </div>

        {/* Right column: panels */}
        <div className="space-y-4">
          <JobFitPanel
            evaluation={job.evaluation}
            onEvaluate={handleEvaluate}
            evaluating={evaluating}
          />

          <JobDecisionBar
            onDecide={handleDecide}
            currentDecision={latestDecision?.decision || job.status}
          />

          <JobStatusTimeline
            status={job.status}
            discoveredAt={job.discovered_at}
            evaluatedAt={job.evaluated_at}
            packStatus={job.pack_status}
            currentDecision={latestDecision?.decision || null}
          />
        </div>
      </div>
    </motion.div>
  )
}
