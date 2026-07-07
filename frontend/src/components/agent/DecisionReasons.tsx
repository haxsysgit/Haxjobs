"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { DECISION_TAGS } from "../../lib/data";
import { Button } from "../ui/button";
import { cn } from "../../lib/utils";

export function DecisionReasons({
  decision,
  onConfirm,
  onCancel,
}: {
  decision: string;
  onConfirm: (reason: string | null) => void;
  onCancel: () => void;
}) {
  const [custom, setCustom] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="mt-3 overflow-hidden rounded-lg border border-border bg-surface-2 p-3"
    >
      <p className="mb-2 text-xs font-bold text-text">
        Quick — why {decision}? Helps me learn your taste.
      </p>
      <div className="flex flex-wrap gap-1.5">
        {DECISION_TAGS.map((tag) => (
          <button
            key={tag}
            onClick={() => setSelected(tag === selected ? null : tag)}
            className={cn(
              "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
              selected === tag
                ? "border-primary bg-primary-soft text-primary"
                : "border-border bg-surface text-text-muted hover:text-text hover:border-primary/40",
            )}
          >
            {tag}
          </button>
        ))}
      </div>
      <input
        value={custom}
        onChange={(e) => {
          setCustom(e.target.value);
          setSelected(null);
        }}
        placeholder="or type your own reason…"
        className="mt-2 w-full rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-text outline-none placeholder:text-text-faint focus:border-primary/50"
      />
      <div className="mt-2 flex justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={() => onConfirm(custom.trim() || selected || null)}
        >
          Confirm
        </Button>
      </div>
    </motion.div>
  );
}
