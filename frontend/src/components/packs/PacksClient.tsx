"use client";

import { useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Package,
  FileText,
  Download,
  ChevronDown,
  ChevronUp,
  Loader2,
  MessagesSquare,
} from "lucide-react";
import { HaxJobsMark } from "../brand/HaxJobsMark";
import { TrackDot } from "../agent/primitives";
import { Button } from "../ui/button";
import type { PackView } from "../../lib/opusTypes";
import { cn } from "../../lib/utils";

export function PacksClient({ packs }: { packs: PackView[] }) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="sticky top-0 z-10 border-b border-border bg-bg-elev/95 px-6 py-4 backdrop-blur">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-heading text-2xl text-text">Packs</h1>
            <p className="text-sm text-text-muted">
              Application packs Hax built. CV variant, cover letter, prep notes.
            </p>
          </div>
          <Link
            to="/workspace"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-bold text-primary-foreground hover:bg-primary-strong"
          >
            <MessagesSquare size={16} /> Ask Hax for a pack
          </Link>
        </div>
      </div>

      <div className="mx-auto max-w-4xl space-y-3 px-6 py-6">
        {packs.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-surface p-10 text-center">
            <HaxJobsMark size={48} />
            <p className="text-sm text-text-muted">
              No packs yet. Tell Hax to build one for your best match.
            </p>
          </div>
        ) : (
          packs.map((p, i) => <PackItem key={p.id} pack={p} index={i} />)
        )}
      </div>
    </div>
  );
}

function PackItem({ pack, index }: { pack: PackView; index: number }) {
  const [open, setOpen] = useState(index === 0);
  const generating = pack.status === "generating";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
      className="rounded-2xl border border-border bg-surface p-4"
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "flex h-11 w-11 items-center justify-center rounded-xl",
            generating ? "bg-warn/15 text-warn" : "bg-primary-soft text-primary",
          )}
        >
          {generating ? (
            <Loader2 size={20} className="animate-spin" />
          ) : (
            <Package size={20} />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {pack.job && <TrackDot track={pack.job.track} />}
            <h3 className="truncate font-heading text-base text-text">{pack.title}</h3>
          </div>
          <p className="text-[11px] text-text-faint">
            {generating
              ? "Hax is assembling this pack…"
              : `${pack.files.length} files · ready`}
          </p>
        </div>
        <span
          className={cn(
            "rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide",
            generating ? "bg-warn/15 text-warn" : "bg-primary-soft text-primary",
          )}
        >
          {pack.status}
        </span>
        <button
          onClick={() => setOpen((v) => !v)}
          className="rounded-md p-1.5 text-text-muted hover:bg-surface-hover hover:text-text"
        >
          {open ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
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
              {pack.files.map((f) => (
                <div
                  key={f.name}
                  className="flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2"
                >
                  <FileText size={15} className="shrink-0 text-primary" />
                  <span className="min-w-0 flex-1 truncate text-xs text-text">{f.name}</span>
                  <span className="text-[10px] text-text-faint">{f.size}</span>
                  <button
                    disabled={generating}
                    className="rounded p-1 text-text-muted hover:text-primary disabled:opacity-40"
                  >
                    <Download size={14} />
                  </button>
                </div>
              ))}
            </div>
            {!generating && (
              <div className="mt-3 flex gap-2">
                <Button size="sm" variant="secondary">
                  <Download size={14} /> Download all
                </Button>
                <Link to="/workspace">
                  <Button size="sm" variant="ghost">
                    Request a revision
                  </Button>
                </Link>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
