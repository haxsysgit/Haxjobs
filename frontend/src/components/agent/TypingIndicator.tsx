"use client";

import { motion } from "framer-motion";
import { HaxJobsMark } from "../brand/HaxJobsMark";

export function TypingIndicator({ label = "Hax is working" }: { label?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-3 px-4 py-1.5"
    >
      <HaxJobsMark size={38} animated />
      <div className="flex items-center gap-2 rounded-2xl rounded-bl-sm border border-border bg-surface px-4 py-3">
        <div className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-primary"
              style={{ animation: `typing-bounce 1.2s ease-in-out ${i * 0.15}s infinite` }}
            />
          ))}
        </div>
        <span className="text-xs text-text-faint">{label}</span>
      </div>
    </motion.div>
  );
}
