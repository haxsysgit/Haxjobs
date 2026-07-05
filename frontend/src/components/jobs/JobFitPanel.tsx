/** Fit evaluation panel shown on job detail page. */
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { IconFit } from "@/components/icons"
import type { Evaluation } from "@/lib/jobs"

interface Props {
  evaluation: Evaluation | null
  onEvaluate: () => void
  evaluating: boolean
}

export function JobFitPanel({ evaluation, onEvaluate, evaluating }: Props) {
  if (!evaluation) {
    return (
      <div className="rounded-xl border bg-card p-5 space-y-3">
        <h3 className="font-medium text-sm">Fit Signal</h3>
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          <IconFit />
          <div>
            <p className="text-sm font-medium">No fit signal yet.</p>
            <p className="text-xs text-muted-foreground mt-1">
              Run evaluation to get the intel brief.
            </p>
          </div>
          <Button onClick={onEvaluate} disabled={evaluating} size="sm">
            {evaluating ? "Evaluating…" : "Evaluate Fit"}
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border bg-card p-5 space-y-4">
      <h3 className="font-medium text-sm">Fit Signal</h3>

      <div className="flex items-center gap-4">
        <div className="text-3xl font-bold tracking-tight">{evaluation.fit_score}%</div>
        <div>
          <p className="font-medium text-sm">{evaluation.fit_verdict}</p>
          <p className="text-xs text-muted-foreground">Level {evaluation.level} · {evaluation.level_name}</p>
        </div>
      </div>

      {evaluation.summary && (
        <p className="text-sm text-muted-foreground">{evaluation.summary}</p>
      )}

      {evaluation.strongest_matches && evaluation.strongest_matches.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-1.5">Strongest Matches</p>
          <div className="flex flex-wrap gap-1.5">
            {evaluation.strongest_matches.map((m) => (
              <Badge key={m} variant="outline" className="bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/10 dark:text-emerald-400">
                {m}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {evaluation.major_gaps && evaluation.major_gaps.length > 0 && (
        <div>
          <p className="text-xs font-medium mb-1.5">Major Gaps</p>
          <div className="flex flex-wrap gap-1.5">
            {evaluation.major_gaps.map((g) => (
              <Badge key={g} variant="outline" className="bg-amber-500/10 text-amber-600 dark:bg-amber-400/10 dark:text-amber-400">
                {g}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {evaluation.sponsorship_risk && (
        <div>
          <p className="text-xs font-medium mb-1">Sponsorship Risk</p>
          <p className="text-xs text-muted-foreground">{evaluation.sponsorship_risk}</p>
        </div>
      )}

      <Button onClick={onEvaluate} disabled={evaluating} variant="outline" size="sm" className="w-full">
        {evaluating ? "Evaluating…" : "Re-evaluate"}
      </Button>
    </div>
  )
}
