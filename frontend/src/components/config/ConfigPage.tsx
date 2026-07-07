"use client";

import { useState } from "react";
import { toast } from "sonner";
import {
  Cpu,
  Check,
  Settings2,
  Sun,
  Moon,
  Sliders,
  Plus,
} from "lucide-react";
import { Button } from "../ui/button";
import { useTheme } from "../../hooks/useTheme";
import { cn } from "../../lib/utils";

const PROVIDERS = [
  { id: "deepseek", name: "DeepSeek", model: "deepseek-chat", status: "connected", note: "Hax's default brain" },
  { id: "openai", name: "OpenAI", model: "gpt-4o", status: "connected", note: "Fallback for evals" },
  { id: "anthropic", name: "Anthropic", model: "claude-sonnet", status: "idle", note: "Not configured" },
  { id: "custom", name: "Custom endpoint", model: "—", status: "idle", note: "Bring your own" },
];

export function ConfigPage() {
  const { theme, toggle } = useTheme();
  const [active, setActive] = useState("deepseek");
  const [depth, setDepth] = useState(70);
  const [autoRecon, setAutoRecon] = useState(true);
  const [proactive, setProactive] = useState(true);

  return (
    <div className="h-full overflow-y-auto">
      <div className="sticky top-0 z-10 border-b border-border bg-bg-elev/95 px-6 py-4 backdrop-blur">
        <h1 className="font-heading text-2xl text-text">Config</h1>
        <p className="text-sm text-text-muted">Configure Hax&apos;s brain and how it works for you.</p>
      </div>

      <div className="mx-auto max-w-3xl space-y-8 px-6 py-6">
        {/* Providers */}
        <section>
          <SectionHead icon={Cpu} title="AI providers" sub="The model powering Hax's evaluations." />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {PROVIDERS.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setActive(p.id);
                  toast.success(`Hax now runs on ${p.name}.`);
                }}
                className={cn(
                  "flex items-start gap-3 rounded-2xl border p-4 text-left transition-colors",
                  active === p.id
                    ? "border-primary bg-primary-soft"
                    : "border-border bg-surface hover:border-primary/40",
                )}
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-2 text-primary">
                  <Cpu size={17} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-text">{p.name}</span>
                    {active === p.id && (
                      <span className="rounded-full bg-primary px-1.5 py-0.5 text-[9px] font-bold text-primary-foreground">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-text-faint">{p.model}</p>
                  <p className="mt-1 text-[11px] text-text-muted">{p.note}</p>
                </div>
                <StatusBadge status={p.status} />
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" className="mt-3">
            <Plus size={14} /> Add provider
          </Button>
        </section>

        {/* Preferences */}
        <section>
          <SectionHead icon={Settings2} title="Preferences" sub="How Hax behaves day to day." />
          <div className="space-y-3 rounded-2xl border border-border bg-surface p-4">
            <ToggleRow
              label="Proactive mode"
              sub="Hax surfaces roles before you ask."
              on={proactive}
              onToggle={() => setProactive((v) => !v)}
            />
            <ToggleRow
              label="Auto recon each morning"
              sub="Runs a quiet sweep overnight."
              on={autoRecon}
              onToggle={() => setAutoRecon((v) => !v)}
            />
            <div className="flex items-center justify-between border-t border-border-soft pt-3">
              <div>
                <p className="text-sm font-bold text-text flex items-center gap-2">
                  {theme === "dark" ? <Moon size={15} /> : <Sun size={15} />} Theme
                </p>
                <p className="text-[11px] text-text-muted">Currently {theme} mode.</p>
              </div>
              <Button variant="secondary" size="sm" onClick={toggle}>
                Switch to {theme === "dark" ? "light" : "dark"}
              </Button>
            </div>
          </div>
        </section>

        {/* Profile depth */}
        <section>
          <SectionHead icon={Sliders} title="Profile depth" sub="How aggressively Hax tailors packs." />
          <div className="rounded-2xl border border-border bg-surface p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-text">Tailoring intensity</span>
              <span className="font-heading text-lg text-primary">{depth}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="mt-2 w-full accent-[var(--primary)]"
            />
            <p className="mt-1 text-[11px] text-text-faint">
              {depth < 40
                ? "Light touch — generic packs, faster output."
                : depth < 75
                  ? "Balanced — solid tailoring per role."
                  : "Deep — Hax rewrites hard for every JD."}
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const connected = status === "connected";
  return (
    <span
      className={cn(
        "flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold",
        connected ? "bg-primary-soft text-primary" : "bg-surface-2 text-text-faint",
      )}
    >
      {connected ? <Check size={10} /> : null}
      {connected ? "connected" : "idle"}
    </span>
  );
}

function SectionHead({
  icon: Icon,
  title,
  sub,
}: {
  icon: typeof Cpu;
  title: string;
  sub: string;
}) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <Icon size={16} className="text-primary" />
      <div>
        <h2 className="text-sm font-bold text-text">{title}</h2>
        <p className="text-[11px] text-text-faint">{sub}</p>
      </div>
    </div>
  );
}

function ToggleRow({
  label,
  sub,
  on,
  onToggle,
}: {
  label: string;
  sub: string;
  on: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-bold text-text">{label}</p>
        <p className="text-[11px] text-text-muted">{sub}</p>
      </div>
      <button
        onClick={onToggle}
        className={cn(
          "relative h-6 w-11 rounded-full transition-colors",
          on ? "bg-primary" : "bg-surface-hover",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform",
            on ? "translate-x-[22px]" : "translate-x-0.5",
          )}
        />
      </button>
    </div>
  );
}
