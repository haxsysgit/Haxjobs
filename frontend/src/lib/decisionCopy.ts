import type { Decision } from "@/lib/jobs"

export const decisionCopy: Record<Decision, string> = {
  apply: "Applied. I also marked this one as worth a human follow-up.",
  maybe: "Parked in maybe. Not a yes, not a no, just suspiciously possible.",
  save: "Saved. This one gets a second look when your caffeine is back.",
  skip: "Skipped. We do not owe every job post our precious mortal attention.",
  reject: "Rejected. Clean exit, no drama.",
}
