"use client";

import { useState, type ReactNode } from "react";
import { motion } from "framer-motion";

import { ThumbsUp, ThumbsDown, RotateCcw } from "lucide-react";
import { HaxJobsMark } from "../brand/HaxJobsMark";
import { cn } from "../../lib/utils";
import { toast } from "sonner";

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000)
  if (seconds < 60) return "just now"
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return minutes + "m ago"
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return hours + "h ago"
  const days = Math.floor(hours / 24)
  if (days < 30) return days + "d ago"
  return Math.floor(days / 30) + "mo ago"
}

interface Props {
  author: "hax" | "user";
  createdAt: string;
  active?: boolean;
  children: ReactNode;
  showFeedback?: boolean;
}

export function MessageShell({ author, createdAt, active, children, showFeedback = true }: Props) {
  const [reaction, setReaction] = useState<"up" | "down" | null>(null);

  let time = "";
  try {
    time = timeAgo(new Date(createdAt));
  } catch {
    time = "";
  }

  if (author === "user") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        className="flex justify-end px-4 py-1.5"
      >
        <div className="max-w-[78%]">
          <div className="rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm">
            {children}
          </div>
          <div className="mt-0.5 pr-1 text-right text-[10px] text-text-faint">{time}</div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      className="group flex gap-3 px-4 py-1.5"
    >
      <div className="relative mt-0.5 shrink-0">
        <HaxJobsMark size={38} animated={active} />
        <span
          className={cn(
            "absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-bg",
            active ? "status-pulse bg-warn" : "bg-primary",
          )}
        />
      </div>

      <div className="min-w-0 max-w-[82%] flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="text-sm font-bold text-text">Hax</span>
          <span className="rounded bg-primary-soft px-1.5 py-px text-[9px] font-bold uppercase tracking-wide text-primary">
            agent
          </span>
          <span className="text-[10px] text-text-faint">{time}</span>
        </div>

        <div className="relative">
          {children}

          {showFeedback && (
            <div className="mt-1 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
              <FeedbackBtn
                active={reaction === "up"}
                onClick={() => {
                  setReaction("up");
                  toast.success("Noted. I'll surface more like this.");
                }}
              >
                <ThumbsUp size={13} />
              </FeedbackBtn>
              <FeedbackBtn
                active={reaction === "down"}
                onClick={() => {
                  setReaction("down");
                  toast("Got it. Dialing that down.");
                }}
              >
                <ThumbsDown size={13} />
              </FeedbackBtn>
              <FeedbackBtn onClick={() => toast("Re-running that for you.")}>
                <RotateCcw size={13} />
              </FeedbackBtn>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function FeedbackBtn({
  children,
  onClick,
  active,
}: {
  children: ReactNode;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-md border border-border bg-surface p-1 text-text-muted transition-colors hover:text-text hover:border-primary/40",
        active && "border-primary/50 bg-primary-soft text-primary",
      )}
    >
      {children}
    </button>
  );
}
