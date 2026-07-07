"use client";

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Search,
  ArrowUpRight,
  Briefcase,
  CheckCircle2,
  Send,
  Package,
  Brain,
  MessagesSquare,
  Radar,
  Inbox,
  Sparkles,
} from "lucide-react";
import { HaxJobsMark } from "../brand/HaxJobsMark";
import { ScoreRing, VerdictBadge, TrackDot } from "../agent/primitives";
import type { JobView, MessageView, MemoryView, StatsView } from "../../lib/opusTypes";
import { cn } from "../../lib/utils";

export function DashboardClient({
  jobs,
  stats,
  memory,
  recent,
}: {
  jobs: JobView[];
  stats: StatsView;
  memory: MemoryView[];
  recent: MessageView[];
}) {
  const [q, setQ] = useState("");

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const evaluated = jobs.filter((j) => j.evaluation);
    if (!needle) return evaluated;
    return evaluated.filter(
      (j) =>
        j.company.toLowerCase().includes(needle) ||
        j.role.toLowerCase().includes(needle) ||
        j.stack.some((s) => s.toLowerCase().includes(needle)),
    );
  }, [jobs, q]);

  const needsDecision = jobs
    .filter((j) => j.evaluation && !j.decision)
    .sort((a, b) => (b.evaluation!.score ?? 0) - (a.evaluation!.score ?? 0));

  return (
    <div className="h-full overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 z-10 border-b border-border bg-bg-elev/95 px-6 py-4 backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="font-heading text-2xl text-text">Dashboard</h1>
            <p className="text-sm text-text-muted">
              Everything Hax has been up to, at a glance.
            </p>
          </div>
          <Link
            to="/workspace"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground transition-colors hover:bg-primary-strong"
          >
            <MessagesSquare size={16} /> Open Workspace
          </Link>
        </div>
        <div className="mt-3 flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2">
          <Search size={16} className="text-text-faint" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search jobs, companies, stacks…"
            className="flex-1 bg-transparent text-sm text-text outline-none placeholder:text-text-faint"
          />
        </div>
      </div>

      <div className="mx-auto max-w-6xl space-y-6 px-6 py-6">
        {/* Agent status banner */}
        <div className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-4">
          <div className="relative">
            <HaxJobsMark size={48} animated glow />
          </div>
          <div className="flex-1">
            <p className="text-sm text-text">
              <b className="font-bold">Hax</b> is online. Evaluated{" "}
              <b>{stats.evaluated}</b> roles this cycle,{" "}
              <b>{stats.strongFits}</b> strong fits are open.
            </p>
            <p className="text-[11px] text-primary flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-primary status-pulse" />
              Recon idle — last sweep ran overnight
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard icon={Briefcase} label="Jobs this cycle" value={stats.jobsThisCycle} />
          <StatCard icon={CheckCircle2} label="Evaluated" value={stats.evaluated} />
          <StatCard icon={Send} label="Applied" value={stats.applied} accent />
          <StatCard icon={Package} label="Packs ready" value={stats.packsReady} />
        </div>

        {/* Alerts */}
        {(stats.needsDecision > 0 || stats.packsReady > 0) && (
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {stats.needsDecision > 0 && (
              <AlertRow
                tone="warn"
                icon={Inbox}
                title={`${stats.needsDecision} jobs need your decision`}
                sub="Hax has an opinion on each. Go clear the queue."
                to="/workspace"
                cta="Review"
              />
            )}
            <AlertRow
              tone="primary"
              icon={Radar}
              title="Run a fresh recon sweep"
              sub="No new matches since Tuesday. Want Hax to look again?"
              to="/workspace"
              cta="Sweep"
            />
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Jobs list */}
          <div className="lg:col-span-2 space-y-3">
            <SectionTitle
              icon={Briefcase}
              title={q ? `Results for \u201c${q}\u201d` : "Needs your decision"}
              hint={`${(q ? filtered : needsDecision).length} roles`}
            />
            {(q ? filtered : needsDecision).length === 0 ? (
              <EmptyState
                text={
                  q
                    ? "No matches. Try a company or a stack like \u201cPostgres\u201d."
                    : "Inbox zero. Nothing waiting on you."
                }
              />
            ) : (
              (q ? filtered : needsDecision).map((j, i) => (
                <JobRow key={j.id} job={j} index={i} />
              ))
            )}
          </div>

          {/* Right column */}
          <div className="space-y-6">
            <div>
              <SectionTitle icon={Sparkles} title="Recent activity" />
              <div className="space-y-2 rounded-2xl border border-border bg-surface p-3">
                {recent.length === 0 ? (
                  <p className="text-xs text-text-faint">No activity yet.</p>
                ) : (
                  recent.map((m) => <ActivityRow key={m.id} message={m} />)
                )}
                <Link
                  to="/workspace"
                  className="mt-1 flex items-center justify-center gap-1 rounded-lg py-1.5 text-xs font-medium text-primary hover:underline"
                >
                  Open full conversation <ArrowUpRight size={13} />
                </Link>
              </div>
            </div>

            <div>
              <SectionTitle icon={Brain} title="What Hax has learned" />
              <div className="space-y-2 rounded-2xl border border-border bg-surface p-3">
                {memory.map((m) => (
                  <div
                    key={m.id}
                    className="rounded-lg border border-border-soft bg-surface-2 p-2.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="rounded bg-primary-soft px-1.5 py-0.5 text-[10px] font-bold text-primary">
                        {m.tag}
                      </span>
                      <span className="text-[10px] text-text-faint">×{m.weight}</span>
                    </div>
                    <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
                      {m.note}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: typeof Briefcase;
  label: string;
  value: number;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div
        className={cn(
          "flex h-8 w-8 items-center justify-center rounded-lg",
          accent ? "bg-primary text-primary-foreground" : "bg-primary-soft text-primary",
        )}
      >
        <Icon size={16} />
      </div>
      <div className="mt-3 font-heading text-2xl text-text">{value}</div>
      <div className="text-[11px] text-text-faint">{label}</div>
    </div>
  );
}

function AlertRow({
  tone,
  icon: Icon,
  title,
  sub,
  to,
  cta,
}: {
  tone: "warn" | "primary";
  icon: typeof Inbox;
  title: string;
  sub: string;
  to: string;
  cta: string;
}) {
  return (
    <Link
      to={to}
      className={cn(
        "flex items-center gap-3 rounded-2xl border p-3 transition-colors",
        tone === "warn"
          ? "border-warn/30 bg-warn/10 hover:bg-warn/15"
          : "border-primary/25 bg-primary-soft hover:bg-primary/15",
      )}
    >
      <span
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
          tone === "warn" ? "bg-warn/20 text-warn" : "bg-primary/20 text-primary",
        )}
      >
        <Icon size={17} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-text">{title}</p>
        <p className="truncate text-[11px] text-text-muted">{sub}</p>
      </div>
      <span
        className={cn(
          "rounded-lg px-3 py-1.5 text-xs font-bold",
          tone === "warn" ? "bg-warn/20 text-warn" : "bg-primary text-primary-foreground",
        )}
      >
        {cta}
      </span>
    </Link>
  );
}

function JobRow({ job, index }: { job: JobView; index: number }) {
  const e = job.evaluation!;
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
    >
      <Link
        to="/workspace"
        className="flex items-center gap-4 rounded-2xl border border-border bg-surface p-3 transition-colors hover:border-primary/40 hover:bg-surface-hover"
      >
        <ScoreRing score={e.score} size={52} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <TrackDot track={job.track} />
            <span className="font-heading text-sm text-text">{job.company}</span>
            <VerdictBadge verdict={e.verdict} />
          </div>
          <p className="truncate text-xs text-text-muted">{job.role}</p>
          <p className="truncate text-[11px] text-text-faint">{e.summary}</p>
        </div>
        {job.decision ? (
          <span className="shrink-0 rounded-full bg-surface-2 px-2 py-1 text-[10px] font-bold uppercase text-text-muted">
            {job.decision.decision}
          </span>
        ) : (
          <ArrowUpRight size={16} className="shrink-0 text-text-faint" />
        )}
      </Link>
    </motion.div>
  );
}

function ActivityRow({ message }: { message: MessageView }) {
  const label = describe(message);
  return (
    <div className="flex items-start gap-2 rounded-lg px-1 py-1.5">
      <div className="mt-0.5 shrink-0">
        <HaxJobsMark size={22} />
      </div>
      <p className="text-[11px] leading-relaxed text-text-muted">{label}</p>
    </div>
  );
}

function describe(m: MessageView): string {
  switch (m.kind) {
    case "discovery":
      return (m.payload.headline as string) ?? "Ran a recon sweep.";
    case "evaluation":
      return `Evaluated ${(m.payload.jobSlug as string)?.split("-")[0] ?? "a role"}.`;
    case "pack":
      return `Built a pack: ${(m.payload.title as string) ?? ""}.`;
    case "decision":
      return (m.payload.text as string) ?? "Recorded a decision.";
    default:
      return (m.payload.text as string) ?? "Sent a message.";
  }
}

function SectionTitle({
  icon: Icon,
  title,
  hint,
}: {
  icon: typeof Briefcase;
  title: string;
  hint?: string;
}) {
  return (
    <div className="mb-2 flex items-center gap-2">
      <Icon size={15} className="text-primary" />
      <h2 className="text-sm font-bold text-text">{title}</h2>
      {hint && <span className="text-[11px] text-text-faint">· {hint}</span>}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-border bg-surface p-8 text-center">
      <HaxJobsMark size={40} />
      <p className="text-sm text-text-muted">{text}</p>
    </div>
  );
}
