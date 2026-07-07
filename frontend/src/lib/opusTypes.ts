export type Verdict = "STRONG FIT" | "GOOD FIT" | "WEAK FIT" | "SKIP";
export type Confidence = "high" | "medium" | "low";
export type DecisionKind = "apply" | "maybe" | "save" | "skip" | "reject";
export type MessageKind =
  | "text"
  | "evaluation"
  | "discovery"
  | "pack"
  | "decision"
  | "alert"
  | "compare";

export interface JobView {
  id: number;
  slug: string;
  company: string;
  role: string;
  location: string;
  remote: string;
  source: string;
  salary: string | null;
  postedAt: string;
  track: string;
  stack: string[];
  jd: string;
  evaluation: {
    score: number;
    verdict: string;
    confidence: string;
    confidenceNote: string | null;
    summary: string;
    matches: string[];
    gaps: string[];
    suggestedAction: string;
  } | null;
  decision: {
    decision: string;
    reason: string | null;
    createdAt: string;
  } | null;
}

export interface MessageView {
  id: number;
  author: string;
  kind: string;
  payload: Record<string, unknown>;
  pinned: boolean;
  createdAt: string;
}

export interface PackView {
  id: number;
  title: string;
  status: string;
  files: { name: string; kind: string; size: string }[];
  createdAt: string;
  job: { slug: string; company: string; role: string; track: string } | null;
}

export interface MemoryView {
  id: number;
  tag: string;
  note: string;
  weight: number;
}

export interface StatsView {
  jobsThisCycle: number;
  evaluated: number;
  applied: number;
  saved: number;
  packsReady: number;
  needsDecision: number;
  strongFits: number;
}
