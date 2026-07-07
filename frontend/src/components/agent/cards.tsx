"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronDown,
  ChevronUp,
  MapPin,
  Banknote,
  FileText,
  Download,
  FolderOpen,
  CheckCircle2,
  XCircle,
  Bookmark,
  HelpCircle,
  Radar,
  ExternalLink,
  Sparkles,
  Package,
  Send,
} from "lucide-react";
import { Button } from "../ui/button";
import {
  ScoreRing,
  VerdictBadge,
  ConfidenceTag,
  Pill,
  TrendPill,
  TrackDot,
} from "./primitives";
import { DecisionReasons } from "./DecisionReasons";
import { useAgentActions } from "./context";
import type { JobView } from "../../lib/opusTypes";
import { cn } from "../../lib/utils";

const ACTION_META: Record<
  string,
  { label: string; icon: typeof CheckCircle2; variant: "primary" | "subtle" | "outline" | "danger" }
> = {
  apply: { label: "Apply", icon: Send, variant: "primary" },
  maybe: { label: "Maybe", icon: HelpCircle, variant: "subtle" },
  save: { label: "Save", icon: Bookmark, variant: "subtle" },
  skip: { label: "Skip", icon: XCircle, variant: "outline" },
  reject: { label: "Reject", icon: XCircle, variant: "danger" },
};

/* ---------- Evaluation card ---------- */
export function EvaluationCard({ job }: { job: JobView }) {
  const { decide, buildPack } = useAgentActions();
  const [expanded, setExpanded] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const e = job.evaluation;
  if (!e) return null;

  const suggested = e.suggestedAction;
  const secondary = (["apply", "save", "skip", "reject"] as const).filter(
    (a) => a !== suggested,
  );

  return (
    <Bubble>
      <div className="flex items-start gap-4">
        <ScoreRing score={e.score} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <TrackDot track={job.track} />
            <h4 className="font-heading text-base leading-tight text-text">
              {job.company}
            </h4>
            <VerdictBadge verdict={e.verdict} />
          </div>
          <p className="mt-0.5 text-sm text-text-muted">{job.role}</p>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-text-faint">
            <span className="flex items-center gap-1">
              <MapPin size={11} /> {job.location}
            </span>
            {job.salary && (
              <span className="flex items-center gap-1">
                <Banknote size={11} /> {job.salary}
              </span>
            )}
            <span className="uppercase">{job.source}</span>
            <ConfidenceTag confidence={e.confidence} note={e.confidenceNote} />
          </div>
        </div>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-text">{e.summary}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {e.matches.map((m) => (
          <Pill key={m} tone="match">
            {m}
          </Pill>
        ))}
        {e.gaps.map((g) => (
          <Pill key={g} tone="gap">
            {g}
          </Pill>
        ))}
      </div>

      <button
        onClick={() => setExpanded((v) => !v)}
        className="mt-3 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
      >
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        {expanded ? "Hide" : "Inspect"} JD & evidence
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 rounded-lg border border-border bg-surface-2 p-3">
              <div className="mb-2 flex flex-wrap gap-1.5">
                {job.stack.map((s) => (
                  <span
                    key={s}
                    className="rounded bg-surface px-1.5 py-0.5 text-[10px] font-medium text-text-muted"
                  >
                    {s}
                  </span>
                ))}
              </div>
              <p className="text-xs leading-relaxed text-text-muted">{job.jd}</p>
              <a
                href="#"
                onClick={(ev) => ev.preventDefault()}
                className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline"
              >
                <ExternalLink size={11} /> Open source posting ({job.source})
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {job.decision ? (
        <div className="mt-3 flex items-center gap-2 rounded-lg border border-primary/25 bg-primary-soft px-3 py-2 text-xs font-medium text-primary">
          <CheckCircle2 size={14} /> You marked this{" "}
          <b className="font-bold">{job.decision.decision}</b>
          {job.decision.reason ? ` (${job.decision.reason})` : ""}
        </div>
      ) : (
        <>
          <p className="mt-3 mb-1.5 flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide text-primary">
            <Sparkles size={12} /> Hax suggests: {ACTION_META[suggested]?.label}
          </p>
          <div className="flex flex-wrap gap-2">
            <PrimaryAction
              action={suggested}
              onClick={() => {
                if (suggested === "apply" || suggested === "maybe") {
                  setPending(suggested);
                } else decide(job, suggested, null);
              }}
            />
            {suggested !== "save" && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => buildPack(job)}
              >
                <Package size={14} /> Build pack
              </Button>
            )}
            {secondary.map((a) => {
              const meta = ACTION_META[a];
              const Icon = meta.icon;
              return (
                <Button
                  key={a}
                  variant="ghost"
                  size="sm"
                  onClick={() => setPending(a)}
                >
                  <Icon size={14} /> {meta.label}
                </Button>
              );
            })}
          </div>
          <AnimatePresence>
            {pending && (
              <DecisionReasons
                decision={pending}
                onConfirm={(reason) => {
                  decide(job, pending, reason);
                  setPending(null);
                }}
                onCancel={() => setPending(null)}
              />
            )}
          </AnimatePresence>
        </>
      )}
    </Bubble>
  );
}

function PrimaryAction({ action, onClick }: { action: string; onClick: () => void }) {
  const meta = ACTION_META[action] ?? ACTION_META.save;
  const Icon = meta.icon;
  return (
    <Button variant="default" size="sm" onClick={onClick}>
      <Icon size={14} /> {meta.label}
    </Button>
  );
}

/* ---------- Discovery card ---------- */
export function DiscoveryCard({ payload }: { payload: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const { trigger } = useAgentActions();
  const scrapers =
    (payload.scrapers as { name: string; found: number; added: number; errors: number }[]) ?? [];
  const headline = (payload.headline as string) ?? "Sweep complete.";
  const status = (payload.status as string) ?? "complete";

  return (
    <Bubble>
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide",
            status === "sweeping"
              ? "bg-warn/15 text-warn"
              : "bg-primary-soft text-primary",
          )}
        >
          <Radar size={12} className={status === "sweeping" ? "animate-spin" : ""} />
          {status === "sweeping" ? "sweeping" : "recon complete"}
        </span>
      </div>
      <p className="mt-2 text-sm font-medium text-text">{headline}</p>

      <button
        onClick={() => setOpen((v) => !v)}
        className="mt-2 flex items-center gap-1 text-xs font-medium text-primary hover:underline"
      >
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        Per-scraper breakdown
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-3">
              {scrapers.map((s) => (
                <div
                  key={s.name}
                  className="rounded-lg border border-border bg-surface-2 p-2.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-text">{s.name}</span>
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        s.errors > 0 ? "bg-warn" : "bg-primary",
                      )}
                    />
                  </div>
                  <div className="mt-1.5 flex items-center gap-3">
                    <span className="text-[11px] text-text-faint">{s.found} found</span>
                    <TrendPill value={`+${s.added}`} up />
                  </div>
                  {s.errors > 0 && (
                    <p className="mt-1 text-[10px] text-warn">{s.errors} error</p>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={() => trigger("show me the new matches")}>
          Review new matches
        </Button>
        <Button variant="ghost" size="sm" onClick={() => trigger("run a fresh sweep")}>
          Sweep again
        </Button>
      </div>
    </Bubble>
  );
}

/* ---------- Pack card ---------- */
export function PackCard({ payload }: { payload: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const title = (payload.title as string) ?? "Application pack";
  const files =
    (payload.files as { name: string; kind: string; size: string }[]) ?? [];
  const status = (payload.status as string) ?? "ready";

  return (
    <Bubble>
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
          <Package size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="truncate font-heading text-base text-text">{title}</h4>
          <p className="text-[11px] text-text-faint">
            {status === "generating"
              ? "Assembling files…"
              : `${files.length} files ready`}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => setOpen((v) => !v)}>
          <FolderOpen size={14} /> {open ? "Close" : "Open pack"}
        </Button>
      </div>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-3 space-y-1.5">
              {files.map((f) => (
                <div
                  key={f.name}
                  className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2"
                >
                  <FileText size={15} className="shrink-0 text-primary" />
                  <span className="min-w-0 flex-1 truncate text-xs text-text">
                    {f.name}
                  </span>
                  <span className="text-[10px] text-text-faint">{f.size}</span>
                  <button className="rounded p-1 text-text-muted hover:text-primary">
                    <Download size={14} />
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Bubble>
  );
}

/* ---------- Decision confirmation card ---------- */
export function DecisionCard({ payload }: { payload: Record<string, unknown> }) {
  const decision = (payload.decision as string) ?? "save";
  const text = (payload.text as string) ?? "Decision recorded.";
  const applied = decision === "apply";
  const rejected = decision === "reject" || decision === "skip";
  const Icon = applied ? CheckCircle2 : rejected ? XCircle : Bookmark;
  const color = applied
    ? "text-primary"
    : rejected
      ? "text-text-muted"
      : "text-info";
  return (
    <div className="inline-flex items-center gap-2 rounded-2xl rounded-bl-sm border border-border bg-surface px-4 py-2.5 text-sm">
      <Icon size={16} className={cn("shrink-0", color)} />
      <span className="text-text">{text}</span>
    </div>
  );
}

/* ---------- Alert card ---------- */
export function AlertCard({ payload }: { payload: Record<string, unknown> }) {
  const { trigger } = useAgentActions();
  const text = (payload.text as string) ?? "";
  const action = (payload.action as string) ?? "Review";
  const triggerText = (payload.trigger as string) ?? "review";
  return (
    <Bubble className="border-l-2 border-l-warn">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-warn/15 text-warn">
          <Sparkles size={13} />
        </span>
        <div className="flex-1">
          <p className="text-sm text-text">{text}</p>
          <Button
            size="sm"
            variant="ghost"
            className="mt-2"
            onClick={() => trigger(triggerText)}
          >
            {action}
          </Button>
        </div>
      </div>
    </Bubble>
  );
}

/* ---------- Text card with suggestion chips ---------- */
export function TextCard({ payload }: { payload: Record<string, unknown> }) {
  const { trigger } = useAgentActions();
  const text = (payload.text as string) ?? "";
  const suggestions = (payload.suggestions as string[]) ?? [];
  return (
    <div className="max-w-full">
      <div className="rounded-2xl rounded-bl-sm border border-border bg-surface px-4 py-2.5 text-sm leading-relaxed text-text">
        {text}
      </div>
      {suggestions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => trigger(s)}
              className="rounded-full border border-primary/30 bg-primary-soft px-3 py-1 text-[11px] font-medium text-primary transition-colors hover:bg-primary/20"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---------- Compare card ---------- */
export function CompareCard({ payload }: { payload: Record<string, unknown> }) {
  const { jobBySlug, decide } = useAgentActions();
  const slugs = (payload.slugs as string[]) ?? [];
  const verdict = (payload.verdict as string) ?? "";
  const jobs = slugs.map((s) => jobBySlug(s)).filter(Boolean) as JobView[];

  return (
    <Bubble>
      <p className="mb-3 text-sm font-medium text-text">{verdict}</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        {jobs.map((j) => {
          const e = j.evaluation!;
          return (
            <div key={j.slug} className="rounded-lg border border-border bg-surface-2 p-3">
              <div className="flex items-center justify-between">
                <span className="font-heading text-sm text-text">{j.company}</span>
                <ScoreRing score={e.score} size={40} />
              </div>
              <p className="mt-0.5 text-[11px] text-text-muted">{j.role}</p>
              <div className="mt-2">
                <VerdictBadge verdict={e.verdict} />
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-text-faint">
                {(payload.notes as Record<string, string>)?.[j.slug] ?? e.summary}
              </p>
              <Button
                size="sm"
                variant="ghost"
                className="mt-2 w-full"
                onClick={() => decide(j, e.suggestedAction, null)}
              >
                {ACTION_META[e.suggestedAction]?.label ?? "Save"}
              </Button>
            </div>
          );
        })}
      </div>
    </Bubble>
  );
}

/* ---------- Shared bubble wrapper ---------- */
export function Bubble({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl rounded-bl-sm border border-border bg-surface p-4 shadow-sm",
        className,
      )}
    >
      {children}
    </div>
  );
}
