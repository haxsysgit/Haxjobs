"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";

import { toast } from "sonner";
import confetti from "canvas-confetti";
import { AgentActionsContext } from "../agent/context";
import { MessageRenderer } from "../agent/MessageRenderer";
import { TypingIndicator } from "../agent/TypingIndicator";
import { WorkspaceInput } from "./WorkspaceInput";
import { PinnedBriefings } from "./PinnedBriefings";
import { HaxJobsMark } from "../brand/HaxJobsMark";
import type { JobView, MessageView, StatsView } from "../../lib/opusTypes";
import {
  interpret,
  comparePayload,
  packFilesFor,
  CONFIRM_TEXT,
} from "../../lib/brain";

let tempId = -1;

export function WorkspaceClient({
  initialMessages,
  initialJobs,
  initialStats,
  trackFilter,
}: {
  initialMessages: MessageView[];
  initialJobs: JobView[];
  initialStats: StatsView;
  trackFilter?: string;
}) {
  const [messages, setMessages] = useState<MessageView[]>(initialMessages);
  const [jobs, setJobs] = useState<JobView[]>(initialJobs);
  const [typing, setTyping] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const stats = useMemo<StatsView>(() => {
    const decided = jobs.filter((j) => j.decision);
    return {
      ...initialStats,
      applied: decided.filter((j) => j.decision?.decision === "apply").length,
      saved: decided.filter((j) => j.decision?.decision === "save").length,
      needsDecision: jobs.filter((j) => j.evaluation && !j.decision).length,
      strongFits: jobs.filter(
        (j) => j.evaluation?.verdict === "STRONG FIT" && !j.decision,
      ).length,
    };
  }, [jobs, initialStats]);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, []);
  useEffect(() => {
    scrollToBottom();
  }, [messages, typing, scrollToBottom]);

  const jobBySlug = useCallback(
    (slug: string) => jobs.find((j) => j.slug === slug),
    [jobs],
  );

  const persist = useCallback(
    async (author: string, kind: string, payload: Record<string, unknown>) => {
      const res = await fetch("/api/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ author, kind, payload }),
      });
      const data = (await res.json()) as { message: MessageView };
      return data.message;
    },
    [],
  );

  const pushLocal = useCallback((m: MessageView) => {
    setMessages((prev) => [...prev, m]);
  }, []);

  const say = useCallback(
    async (author: string, kind: string, payload: Record<string, unknown>) => {
      const local: MessageView = {
        id: tempId--,
        author,
        kind,
        payload,
        pinned: false,
        createdAt: new Date().toISOString(),
      };
      pushLocal(local);
      persist(author, kind, payload).catch(() => {});
    },
    [persist, pushLocal],
  );

  const respond = useCallback(
    async (text: string) => {
      const intent = interpret(text);
      const evalJobs = jobs.filter((j) => j.evaluation);

      const withTyping = async (label: string, ms: number, run: () => Promise<void>) => {
        setTyping(label);
        setBusy(true);
        await new Promise((r) => setTimeout(r, ms));
        setTyping(null);
        await run();
        setBusy(false);
      };

      switch (intent.type) {
        case "recon":
          await withTyping(
            intent.target ? `Sweeping ${intent.target}…` : "Running recon sweep…",
            1400,
            async () => {
              const res = await fetch("/api/discovery/run", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ target: intent.target }),
              });
              const data = (await res.json()) as { message: MessageView };
              pushLocal(data.message);
            },
          );
          break;
        case "needs": {
          const needs = jobs.filter((j) => j.evaluation && !j.decision).slice(0, 3);
          await withTyping("Pulling your open decisions…", 900, async () => {
            if (needs.length === 0) {
              await say("hax", "text", {
                text: "Nothing waiting on you right now. Inbox zero. Want me to sweep for more?",
                suggestions: ["Run a fresh sweep", "Show strong fits"],
              });
            } else {
              await say("hax", "text", {
                text: `${needs.length} roles waiting on your call. Top of the pile first.`,
              });
              for (const j of needs) {
                await say("hax", "evaluation", { jobSlug: j.slug });
              }
            }
          });
          break;
        }
        case "strong": {
          const strong = evalJobs
            .filter((j) => (j.evaluation?.score ?? 0) >= 74 && !j.decision)
            .slice(0, 3);
          await withTyping("Ranking your best fits…", 900, async () => {
            await say("hax", "text", {
              text:
                strong.length > 0
                  ? `Here are your strongest live matches. I'd move on the top one today.`
                  : "No strong fits open right now. Recon's been quiet — want me to sweep?",
              suggestions: strong.length === 0 ? ["Run a fresh sweep"] : undefined,
            });
            for (const j of strong) await say("hax", "evaluation", { jobSlug: j.slug });
          });
          break;
        }
        case "pack": {
          const best = evalJobs
            .filter((j) => !j.decision || j.decision.decision !== "reject")
            .sort((a, b) => (b.evaluation!.score ?? 0) - (a.evaluation!.score ?? 0))[0];
          await withTyping("Assembling your pack…", 1500, async () => {
            if (!best) {
              await say("hax", "text", { text: "No evaluated roles to pack yet." });
              return;
            }
            await say("hax", "text", {
              text: `Built a pack for ${best.company}. CV tuned to their stack, cover letter, and prep notes.`,
            });
            await say("hax", "pack", {
              title: `${best.company} — ${best.role}`,
              status: "ready",
              files: packFilesFor(best),
            });
          });
          break;
        }
        case "compare": {
          const top = evalJobs
            .filter((j) => !j.decision)
            .sort((a, b) => (b.evaluation!.score ?? 0) - (a.evaluation!.score ?? 0))
            .slice(0, 3);
          await withTyping("Lining them up…", 1000, async () => {
            if (top.length < 2) {
              await say("hax", "text", {
                text: "Need at least two open evaluated roles to compare. Run a sweep first.",
              });
              return;
            }
            await say("hax", "compare", comparePayload(top));
          });
          break;
        }
        case "skipped": {
          const skipped = jobs.filter((j) => j.decision?.decision === "skip");
          await withTyping("Checking what I filtered…", 800, async () => {
            const list = skipped.map((j) => `${j.company} (${j.decision?.reason ?? "no fit"})`);
            await say("hax", "text", {
              text:
                skipped.length > 0
                  ? `Skipped ${skipped.length} so far: ${list.join(", ")}. You usually pass on Ruby-first backends, so I buried those fast.`
                  : "Haven't skipped anything yet this cycle.",
            });
          });
          break;
        }
        default:
          await withTyping("Thinking…", 700, async () => {
            await say("hax", "text", {
              text: "Not sure what you're after there. Here's what I can do right now:",
              suggestions: [
                "scan for new roles",
                "what needs my decision",
                "build a pack",
                "compare my top 2",
              ],
            });
          });
      }
    },
    [jobs, pushLocal, say],
  );

  const trigger = useCallback(
    (text: string) => {
      const userMsg: MessageView = {
        id: tempId--,
        author: "user",
        kind: "text",
        payload: { text },
        pinned: false,
        createdAt: new Date().toISOString(),
      };
      pushLocal(userMsg);
      persist("user", "text", { text }).catch(() => {});
      respond(text);
    },
    [persist, pushLocal, respond],
  );

  const decide = useCallback(
    (job: JobView, decision: string, reason: string | null) => {
      setJobs((prev) =>
        prev.map((j) =>
          j.id === job.id
            ? { ...j, decision: { decision, reason, createdAt: new Date().toISOString() } }
            : j,
        ),
      );
      const company = job.company;
      const text = (CONFIRM_TEXT[decision] ?? ((c: string) => `Recorded ${c}.`))(company);
      const temp: MessageView = {
        id: tempId--,
        author: "hax",
        kind: "decision",
        payload: { decision, reason, company, role: job.role, text },
        pinned: false,
        createdAt: new Date().toISOString(),
      };
      pushLocal(temp);

      if (decision === "apply") {
        confetti({
          particleCount: 70,
          spread: 65,
          origin: { y: 0.7 },
          colors: ["#1db954", "#3ecf8e", "#ffffff"],
        });
      }

      let undone = false;
      const timer = setTimeout(() => {
        if (undone) return;
        fetch("/api/decisions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ jobId: job.id, decision, reason }),
        }).catch(() => {});
      }, 4200);

      toast(text, {
        action: {
          label: "Undo",
          onClick: () => {
            undone = true;
            clearTimeout(timer);
            setJobs((prev) =>
              prev.map((j) => (j.id === job.id ? { ...j, decision: null } : j)),
            );
            setMessages((prev) => prev.filter((m) => m.id !== temp.id));
            toast.success("Undone. Back to pending.");
          },
        },
        duration: 4000,
      });
    },
    [pushLocal],
  );

  const runRecon = useCallback((target?: string) => trigger(target ? `recon ${target}` : "scan for new roles"), [trigger]);
  const buildPack = useCallback(
    (job: JobView) => {
      trigger(`build a pack for ${job.company}`);
    },
    [trigger],
  );
  const compare = useCallback((slugs: string[]) => {
    void slugs;
    trigger("compare my top 2 matches");
  }, [trigger]);

  const visibleMessages = useMemo(() => {
    if (!trackFilter) return messages;
    return messages.filter((m) => {
      if (m.kind !== "evaluation") return true;
      const j = jobBySlug(m.payload.jobSlug as string);
      return !j || j.track === trackFilter;
    });
  }, [messages, trackFilter, jobBySlug]);

  const grouped = groupByDay(visibleMessages);

  return (
    <AgentActionsContext.Provider
      value={{ jobs, jobBySlug, decide, runRecon, buildPack, trigger, compare, busy }}
    >
      <div className="flex h-full flex-col">
        <WorkspaceHeader trackFilter={trackFilter} />
        <PinnedBriefings stats={stats} onTrigger={trigger} />
        <div ref={scrollRef} className="chat-canvas flex-1 overflow-y-auto py-4">
          {grouped.map((group) => (
            <div key={group.label}>
              <DayDivider label={group.label} />
              {group.items.map((m) => (
                <MessageRenderer key={m.id} message={m} />
              ))}
            </div>
          ))}
          <AnimatePresence>{typing && <TypingIndicator label={typing} />}</AnimatePresence>
          <div className="h-2" />
        </div>
        <WorkspaceInput onSend={trigger} busy={busy} />
      </div>
    </AgentActionsContext.Provider>
  );
}

function WorkspaceHeader({ trackFilter }: { trackFilter?: string }) {
  const title = trackFilter
    ? `${trackFilter[0].toUpperCase()}${trackFilter.slice(1)} hunt`
    : "Workspace";
  return (
    <div className="flex items-center gap-3 border-b border-border bg-bg-elev px-4 py-3">
      <HaxJobsMark size={34} animated />
      <div className="flex-1">
        <h1 className="font-heading text-base leading-tight text-text">{title}</h1>
        <p className="flex items-center gap-1.5 text-[11px] text-primary">
          <span className="h-1.5 w-1.5 rounded-full bg-primary status-pulse" />
          Hax is online — directing the search
        </p>
      </div>
    </div>
  );
}

function DayDivider({ label }: { label: string }) {
  return (
    <div className="my-2 flex items-center gap-3 px-4">
      <div className="h-px flex-1 bg-border" />
      <span className="rounded-full border border-border bg-surface px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-text-faint">
        {label}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}

function formatDateLabel(d: Date): string {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 86400000)
  const date = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  if (date.getTime() === today.getTime()) return 'Today'
  if (date.getTime() === yesterday.getTime()) return 'Yesterday'
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function groupByDay(messages: MessageView[]) {
  const groups: { label: string; items: MessageView[] }[] = [];
  for (const m of messages) {
    const d = new Date(m.createdAt);
    const label = formatDateLabel(d);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.items.push(m);
    else groups.push({ label, items: [m] });
  }
  return groups;
}
