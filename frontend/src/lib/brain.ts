import type { JobView } from "./opusTypes"

export const CONFIRM_TEXT: Record<string, (c: string) => string> = {
  apply: (c) => `Applied to ${c}. I flagged this one for follow-up in 4 days.`,
  maybe: (c) => `Marked ${c} as a maybe. Keeping it near the top so it doesn't get buried.`,
  save: (c) => `Saved ${c}. Pack's ready whenever you want to pull the trigger.`,
  skip: (c) => `Skipped ${c}. Noted why so I don't waste your time with the same thing.`,
  reject: (c) => `Rejected ${c}. Won't surface anything like it again.`,
};

export function packFilesFor(job: JobView) {
  const variant =
    job.track === "backend"
      ? "backend_python"
      : job.track === "fullstack"
        ? "fullstack_ts"
        : job.track === "aiml"
          ? "aiml_python"
          : "platform";
  return [
    { name: `CV (${variant} variant).pdf`, kind: "cv", size: "182 KB" },
    { name: "Cover letter.pdf", kind: "letter", size: "70 KB" },
    { name: "Interview prep notes.md", kind: "notes", size: "13 KB" },
  ];
}

export function comparePayload(jobs: JobView[]) {
  const withEval = jobs.filter((j) => j.evaluation);
  const sorted = [...withEval].sort(
    (a, b) => (b.evaluation!.score ?? 0) - (a.evaluation!.score ?? 0),
  );
  const notes: Record<string, string> = {};
  sorted.forEach((j, i) => {
    if (i === 0) notes[j.slug] = "Best overall fit. Move on this first.";
    else if (i === 1) notes[j.slug] = "Strong brand, slightly weaker stack fit.";
    else notes[j.slug] = "Safe backup — decent match, lower urgency.";
  });
  const names = sorted.map((j) => j.company);
  const verdict =
    sorted.length >= 2
      ? `${names[0]} is your easiest win. ${names[1]} is the safer brand play. Your call — I'd start with ${names[0]}.`
      : "Not enough evaluated roles to compare yet. Run a sweep first.";
  return { slugs: sorted.map((j) => j.slug), verdict, notes };
}

export type Intent =
  | { type: "recon"; target?: string }
  | { type: "needs" }
  | { type: "pack" }
  | { type: "compare" }
  | { type: "strong" }
  | { type: "skipped" }
  | { type: "unknown" };

export function interpret(text: string): Intent {
  const t = text.toLowerCase();
  if (/(scan|recon|sweep|crawl|discover)/.test(t)) {
    const target = ["greenhouse", "ashby", "lever"].find((s) => t.includes(s));
    return { type: "recon", target };
  }
  if (/(decision|needs? my|review|to review|pending)/.test(t)) return { type: "needs" };
  if (/(pack|cv|cover letter|apply pack|generate)/.test(t)) return { type: "pack" };
  if (/(compare|versus|vs\b|side by side|top 2|top two)/.test(t)) return { type: "compare" };
  if (/(strong fit|best|matches|new match|good fit|show.*roles?|show.*jobs?)/.test(t))
    return { type: "strong" };
  if (/(skip|skipped|passed|reject)/.test(t)) return { type: "skipped" };
  return { type: "unknown" };
}
