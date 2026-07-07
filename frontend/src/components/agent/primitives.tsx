"use client";

import { cn, scoreColor, verdictColor } from "../../lib/utils";
import { Check, X, TrendingUp, TrendingDown } from "lucide-react";

export function ScoreRing({ score, size = 64 }: { score: number; size?: number }) {
  const stroke = 6;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (score / 100) * c;
  const color = scoreColor(score);
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="var(--surface-hover)"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 0.9s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-heading text-lg leading-none" style={{ color }}>
          {score}
        </span>
        <span className="text-[9px] font-bold uppercase tracking-wide text-text-faint">fit</span>
      </div>
    </div>
  );
}

export function VerdictBadge({ verdict }: { verdict: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wide",
        verdictColor(verdict),
      )}
    >
      {verdict}
    </span>
  );
}

export function ConfidenceTag({ confidence, note }: { confidence: string; note?: string | null }) {
  const label =
    confidence === "high"
      ? "high confidence"
      : confidence === "medium"
        ? "medium confidence"
        : "low confidence";
  const color =
    confidence === "high"
      ? "text-primary"
      : confidence === "medium"
        ? "text-info"
        : "text-warn";
  return (
    <span className={cn("text-[11px] font-medium", color)} title={note ?? undefined}>
      {label}
      {confidence === "low" && note ? " — JD was vague" : ""}
    </span>
  );
}

export function Pill({
  children,
  tone = "match",
}: {
  children: React.ReactNode;
  tone?: "match" | "gap";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium",
        tone === "match"
          ? "border-primary/25 bg-primary-soft text-primary"
          : "border-border bg-surface-2 text-text-muted",
      )}
    >
      {tone === "match" ? (
        <Check size={11} className="shrink-0" />
      ) : (
        <X size={11} className="shrink-0" />
      )}
      {children}
    </span>
  );
}

export function TrendPill({ value, up }: { value: string; up?: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[11px] font-bold",
        up ? "text-primary" : "text-text-muted",
      )}
    >
      {up ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
      {value}
    </span>
  );
}

export function TrackDot({ track }: { track: string }) {
  const color =
    track === "backend"
      ? "var(--primary)"
      : track === "fullstack"
        ? "var(--info)"
        : track === "aiml"
          ? "var(--warn)"
          : "var(--text-faint)";
  return <span className="h-2 w-2 rounded-full" style={{ background: color }} />;
}
