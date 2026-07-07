"use client";

import { AlertCircle, Package, Send, Radar } from "lucide-react";
import type { StatsView } from "../../lib/opusTypes";
import { cn } from "../../lib/utils";

export function PinnedBriefings({
  stats,
  onTrigger,
}: {
  stats: StatsView;
  onTrigger: (text: string) => void;
}) {
  const items = [
    stats.needsDecision > 0 && {
      icon: AlertCircle,
      tone: "warn",
      label: `${stats.needsDecision} jobs need review`,
      trigger: "what needs my decision",
    },
    stats.packsReady > 0 && {
      icon: Package,
      tone: "primary",
      label: `${stats.packsReady} packs ready`,
      trigger: "build a pack for my best match",
    },
    stats.strongFits > 0 && {
      icon: Send,
      tone: "primary",
      label: `${stats.strongFits} worth sending today`,
      trigger: "show me strong fits",
    },
    {
      icon: Radar,
      tone: "muted",
      label: "Recon quiet since Tuesday",
      trigger: "run a fresh sweep",
    },
  ].filter(Boolean) as {
    icon: typeof AlertCircle;
    tone: string;
    label: string;
    trigger: string;
  }[];

  return (
    <div className="flex gap-2 overflow-x-auto border-b border-border bg-bg-elev px-4 py-2.5">
      <span className="flex shrink-0 items-center text-[10px] font-bold uppercase tracking-widest text-text-faint">
        Hax pinned
      </span>
      {items.map((it) => {
        const Icon = it.icon;
        return (
          <button
            key={it.label}
            onClick={() => onTrigger(it.trigger)}
            className={cn(
              "flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              it.tone === "warn"
                ? "border-warn/30 bg-warn/10 text-warn hover:bg-warn/20"
                : it.tone === "primary"
                  ? "border-primary/30 bg-primary-soft text-primary hover:bg-primary/20"
                  : "border-border bg-surface text-text-muted hover:text-text",
            )}
          >
            <Icon size={13} />
            {it.label}
          </button>
        );
      })}
    </div>
  );
}
