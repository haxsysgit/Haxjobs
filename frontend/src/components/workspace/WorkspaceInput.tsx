"use client";

import { useState } from "react";
import {
  Radar,
  Inbox,
  Package,
  GitCompare,
  Send,
  Zap,
  Plus,
} from "lucide-react";
import { Button } from "../ui/button";
import { cn } from "../../lib/utils";

const QUICK = [
  { label: "Run recon sweep", trigger: "scan for new roles", icon: Radar },
  { label: "Needs my decision", trigger: "what needs my decision", icon: Inbox },
  { label: "Build best pack", trigger: "build a pack for my best match", icon: Package },
  { label: "Compare top 2", trigger: "compare my top 2 matches", icon: GitCompare },
];

const SUGGESTIONS = [
  "scan for backend jobs",
  "recon greenhouse only",
  "evaluate the newest role",
  "what did you skip today?",
  "show me strong fits",
];

export function WorkspaceInput({
  onSend,
  busy,
}: {
  onSend: (text: string) => void;
  busy: boolean;
}) {
  const [value, setValue] = useState("");
  const [showSug, setShowSug] = useState(false);

  const send = (text: string) => {
    const t = text.trim();
    if (!t || busy) return;
    onSend(t);
    setValue("");
    setShowSug(false);
  };

  return (
    <div className="border-t border-border bg-bg-elev px-4 py-3">
      <div className="mb-2 flex flex-wrap gap-1.5">
        {QUICK.map((q) => {
          const Icon = q.icon;
          return (
            <button
              key={q.label}
              disabled={busy}
              onClick={() => send(q.trigger)}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1.5 text-xs font-medium text-text-muted transition-colors hover:border-primary/40 hover:text-text disabled:opacity-50"
            >
              <Icon size={13} className="text-primary" />
              {q.label}
            </button>
          );
        })}
      </div>

      <div className="relative">
        {showSug && value.length === 0 && (
          <div className="absolute bottom-full mb-2 w-full rounded-lg border border-border bg-surface p-1.5 shadow-lg">
            <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-text-faint">
              Try telling Hax
            </p>
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onMouseDown={(e) => {
                  e.preventDefault();
                  send(s);
                }}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-text-muted hover:bg-surface-hover hover:text-text"
              >
                <Zap size={13} className="text-primary" />
                {s}
              </button>
            ))}
          </div>
        )}

        <div
          className={cn(
            "flex items-end gap-2 rounded-xl border bg-surface px-3 py-2 transition-colors",
            "border-border focus-within:border-primary/50",
          )}
        >
          <button className="mb-0.5 rounded-md p-1 text-text-muted hover:text-text">
            <Plus size={18} />
          </button>
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onFocus={() => setShowSug(true)}
            onBlur={() => setTimeout(() => setShowSug(false), 120)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(value);
              }
            }}
            rows={1}
            placeholder="Tell Hax what to do — try “scan for backend jobs”"
            className="max-h-32 flex-1 resize-none bg-transparent py-1.5 text-sm text-text outline-none placeholder:text-text-faint"
          />
          <Button
            size="icon"
            className="mb-0.5"
            disabled={busy || !value.trim()}
            onClick={() => send(value)}
            aria-label="Send"
          >
            <Send size={16} />
          </Button>
        </div>
      </div>
      <p className="mt-1.5 px-1 text-[10px] text-text-faint">
        Hax leads with an opinion. Pick an action or type a task — this isn&apos;t a chatbot.
      </p>
    </div>
  );
}
