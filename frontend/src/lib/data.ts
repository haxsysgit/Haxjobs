// Synthetic HaxJobs data. Used as dev fixtures.

import type { Verdict, Confidence, DecisionKind, MessageKind } from "./opusTypes";

export type { Verdict, Confidence, DecisionKind, MessageKind };

export interface SeedJob {
  slug: string;
  company: string;
  role: string;
  location: string;
  remote: string;
  source: "greenhouse" | "ashby" | "lever";
  salary: string;
  postedAt: string;
  track: "backend" | "fullstack" | "aiml" | "platform";
  stack: string[];
  jd: string;
  evaluation: {
    score: number;
    verdict: Verdict;
    confidence: Confidence;
    confidenceNote?: string;
    summary: string;
    matches: string[];
    gaps: string[];
    suggestedAction: DecisionKind;
  };
}

export const SEED_JOBS: SeedJob[] = [
  {
    slug: "monzo-backend-engineer",
    company: "Monzo",
    role: "Backend Engineer",
    location: "London, UK",
    remote: "hybrid",
    source: "greenhouse",
    salary: "£85k–£110k",
    postedAt: "2h ago",
    track: "backend",
    stack: ["Python", "PostgreSQL", "Kafka", "gRPC"],
    jd: "We're scaling our core banking platform and need backend engineers who love clean service boundaries. You'll own Python microservices backed by PostgreSQL, ship to millions of customers, and work closely with product. We care about testing, observability, and shipping small. Kafka experience is a plus but not required.",
    evaluation: {
      score: 78,
      verdict: "STRONG FIT",
      confidence: "high",
      confidenceNote: "JD is detailed and stack lines up cleanly.",
      summary:
        "Strong match. They want Python and Postgres, which is exactly your stack. Kafka is a nice-to-have you can pick up fast.",
      matches: ["Python", "PostgreSQL", "Microservices", "Testing culture"],
      gaps: ["Kafka (nice-to-have)", "Fintech domain"],
      suggestedAction: "apply",
    },
  },
  {
    slug: "stripe-backend-engineer",
    company: "Stripe",
    role: "Backend Engineer, Payments",
    location: "Remote (EU)",
    remote: "remote",
    source: "greenhouse",
    salary: "£120k–£150k",
    postedAt: "5h ago",
    track: "backend",
    stack: ["Ruby", "Go", "PostgreSQL", "Kafka"],
    jd: "Join Payments infra. You'll build the systems that move billions. Primarily Ruby and Go. Deep distributed systems experience expected. This team ships high-reliability services with strict SLAs.",
    evaluation: {
      score: 67,
      verdict: "GOOD FIT",
      confidence: "medium",
      confidenceNote: "Stack overlap is partial — Ruby is not in your profile.",
      summary:
        "Better brand, weaker stack fit. They lead with Ruby and Go. Your Python transfers but you'd be ramping. Worth it if you want the name.",
      matches: ["PostgreSQL", "Distributed systems", "Go (basic)"],
      gaps: ["Ruby (primary)", "Billing-scale infra"],
      suggestedAction: "save",
    },
  },
  {
    slug: "linear-fullstack-engineer",
    company: "Linear",
    role: "Full Stack Engineer",
    location: "Remote (Global)",
    remote: "remote",
    source: "ashby",
    salary: "$140k–$180k",
    postedAt: "1d ago",
    track: "fullstack",
    stack: ["TypeScript", "React", "Node.js", "PostgreSQL"],
    jd: "Build the fastest project management tool on the planet. Full stack TypeScript, React on the front, Node and Postgres on the back. Obsessive about performance and craft. Small team, high ownership.",
    evaluation: {
      score: 91,
      verdict: "STRONG FIT",
      confidence: "high",
      confidenceNote: "Every core requirement maps to something you've shipped.",
      summary:
        "This is the one. TypeScript, React, Node, Postgres — your whole stack. Small team, high ownership. Build the pack and let's move.",
      matches: ["TypeScript", "React", "Node.js", "PostgreSQL", "Performance focus"],
      gaps: ["Timezone overlap with US"],
      suggestedAction: "apply",
    },
  },
  {
    slug: "vercel-platform-engineer",
    company: "Vercel",
    role: "Platform Engineer",
    location: "Remote (EU)",
    remote: "remote",
    source: "ashby",
    salary: "$150k–$190k",
    postedAt: "1d ago",
    track: "platform",
    stack: ["Go", "Kubernetes", "TypeScript", "AWS"],
    jd: "Own the infra behind the frontend cloud. Go and Kubernetes heavy. You'll build the systems that deploy millions of projects. Strong ops and reliability background needed.",
    evaluation: {
      score: 62,
      verdict: "WEAK FIT",
      confidence: "low",
      confidenceNote: "JD was vague on day-to-day. Infra depth is unclear from your profile.",
      summary:
        "Platform-heavy and Go-first. Your Kubernetes is light. Interesting company but you'd be stretching. Low confidence — the JD is thin.",
      matches: ["TypeScript", "AWS (basic)"],
      gaps: ["Go (primary)", "Kubernetes depth", "On-call infra"],
      suggestedAction: "skip",
    },
  },
  {
    slug: "anthropic-aiml-engineer",
    company: "Anthropic",
    role: "AI/ML Engineer, Product",
    location: "London, UK",
    remote: "hybrid",
    source: "greenhouse",
    salary: "£130k–£170k",
    postedAt: "2d ago",
    track: "aiml",
    stack: ["Python", "PyTorch", "FastAPI", "PostgreSQL"],
    jd: "Bring models into products. Python, FastAPI, some PyTorch. You don't need to be a researcher — you need to ship reliable ML-backed features. Strong engineering fundamentals matter more than a PhD.",
    evaluation: {
      score: 74,
      verdict: "GOOD FIT",
      confidence: "high",
      confidenceNote: "They explicitly want engineers, not researchers.",
      summary:
        "Product ML, not research. Python and FastAPI are yours. PyTorch is light but they said fundamentals beat a PhD. Solid shot.",
      matches: ["Python", "FastAPI", "PostgreSQL", "Product engineering"],
      gaps: ["PyTorch depth", "ML eval experience"],
      suggestedAction: "apply",
    },
  },
  {
    slug: "shopify-backend-engineer",
    company: "Shopify",
    role: "Senior Backend Engineer",
    location: "Remote (Global)",
    remote: "remote",
    source: "lever",
    salary: "$150k–$200k",
    postedAt: "3d ago",
    track: "backend",
    stack: ["Ruby", "Rails", "MySQL", "Kafka"],
    jd: "Senior role on commerce platform. Rails monolith at massive scale. 8+ years expected. Deep Ruby and Rails required.",
    evaluation: {
      score: 42,
      verdict: "SKIP",
      confidence: "high",
      confidenceNote: "Seniority and language both mismatch.",
      summary:
        "Rails monolith, 8+ years, deep Ruby. That's not you right now. Skipping this one unless you say otherwise.",
      matches: ["Backend at scale"],
      gaps: ["Ruby/Rails (primary)", "8+ years required", "MySQL"],
      suggestedAction: "skip",
    },
  },
  {
    slug: "notion-fullstack-engineer",
    company: "Notion",
    role: "Full Stack Engineer",
    location: "Dublin, IE",
    remote: "hybrid",
    source: "lever",
    salary: "€110k–€140k",
    postedAt: "3d ago",
    track: "fullstack",
    stack: ["TypeScript", "React", "Node.js", "PostgreSQL"],
    jd: "Work across the stack on collaborative editing. TypeScript everywhere, React front end, Node services, Postgres. Care about UX detail and offline-first sync.",
    evaluation: {
      score: 83,
      verdict: "STRONG FIT",
      confidence: "high",
      confidenceNote: "Clean stack overlap and relocation is optional.",
      summary:
        "Great fit. Full stack TypeScript, React, Node, Postgres. Hybrid Dublin but they take remote in EU. Suggested: build pack.",
      matches: ["TypeScript", "React", "Node.js", "PostgreSQL"],
      gaps: ["CRDT / sync internals"],
      suggestedAction: "apply",
    },
  },
  {
    slug: "figma-fullstack-engineer",
    company: "Figma",
    role: "Full Stack Engineer, Growth",
    location: "London, UK",
    remote: "hybrid",
    source: "ashby",
    salary: "£100k–£130k",
    postedAt: "4d ago",
    track: "fullstack",
    stack: ["TypeScript", "React", "Ruby", "PostgreSQL"],
    jd: "Growth team. Fast experiments, TypeScript and React front end, Ruby services on the back. You'll run A/B tests and ship weekly.",
    evaluation: {
      score: 55,
      verdict: "WEAK FIT",
      confidence: "medium",
      confidenceNote: "Front end fits, backend is Ruby.",
      summary:
        "Front end is all yours, but the backend is Ruby again. Growth work is fast and fun. Middling fit — save it as a maybe.",
      matches: ["TypeScript", "React", "PostgreSQL", "Experimentation"],
      gaps: ["Ruby services", "Growth/marketing analytics"],
      suggestedAction: "maybe",
    },
  },
];

export const SCRAPERS = [
  { id: "greenhouse", name: "Greenhouse", found: 20, added: 5, errors: 0 },
  { id: "ashby", name: "Ashby", found: 18, added: 4, errors: 0 },
  { id: "lever", name: "Lever", found: 9, added: 3, errors: 1 },
] as const;

export const DECISION_TAGS = [
  "wrong stack",
  "too senior",
  "too junior",
  "relocation required",
  "salary too low",
  "bad vibes",
  "great match",
  "strong brand",
];

export interface SeedMemory {
  tag: string;
  note: string;
  weight: number;
}

export const SEED_MEMORY: SeedMemory[] = [
  { tag: "relocation required", note: "You usually skip relocation-heavy roles.", weight: 3 },
  { tag: "wrong stack", note: "You pass on Ruby/Rails-first backends.", weight: 4 },
  { tag: "great match", note: "You move fast on TypeScript + Postgres full stack roles.", weight: 5 },
];

export interface SeedPack {
  jobSlug: string;
  title: string;
  status: "ready" | "generating" | "draft";
  files: { name: string; kind: string; size: string }[];
}

export const SEED_PACKS: SeedPack[] = [
  {
    jobSlug: "linear-fullstack-engineer",
    title: "Linear — Full Stack Engineer",
    status: "ready",
    files: [
      { name: "CV (fullstack_ts variant).pdf", kind: "cv", size: "184 KB" },
      { name: "Cover letter.pdf", kind: "letter", size: "72 KB" },
      { name: "Interview prep notes.md", kind: "notes", size: "14 KB" },
    ],
  },
  {
    jobSlug: "monzo-backend-engineer",
    title: "Monzo — Backend Engineer",
    status: "ready",
    files: [
      { name: "CV (backend_python variant).pdf", kind: "cv", size: "179 KB" },
      { name: "Cover letter.pdf", kind: "letter", size: "68 KB" },
      { name: "Interview prep notes.md", kind: "notes", size: "12 KB" },
    ],
  },
  {
    jobSlug: "anthropic-aiml-engineer",
    title: "Anthropic — AI/ML Engineer",
    status: "generating",
    files: [
      { name: "CV (aiml_python variant).pdf", kind: "cv", size: "—" },
      { name: "Cover letter.pdf", kind: "letter", size: "—" },
    ],
  },
];

export interface SeedDecision {
  jobSlug: string;
  decision: DecisionKind;
  reason: string | null;
}

export const SEED_DECISIONS: SeedDecision[] = [
  { jobSlug: "shopify-backend-engineer", decision: "skip", reason: "wrong stack" },
  { jobSlug: "vercel-platform-engineer", decision: "skip", reason: "wrong stack" },
  { jobSlug: "monzo-backend-engineer", decision: "save", reason: null },
];

export function seedMessages() {
  return [
    {
      author: "hax",
      kind: "text" as const,
      pinned: false,
      payload: {
        text: "Morning. Ran a quiet sweep overnight. 47 roles crawled, 12 new, 3 actually worth your time. Want the rundown?",
        suggestions: ["Show the 3", "Run a fresh sweep", "What did you skip?"],
      },
    },
    {
      author: "hax",
      kind: "discovery" as const,
      pinned: false,
      payload: {
        status: "complete",
        headline: "Sweep complete. 47 found, 12 new, 3 worth your time.",
        scrapers: SCRAPERS,
      },
    },
    {
      author: "hax",
      kind: "evaluation" as const,
      pinned: false,
      payload: { jobSlug: "linear-fullstack-engineer" },
    },
  ];
}

export const HAX_QUICK_ACTIONS = [
  { label: "Run recon sweep", trigger: "scan for new roles", icon: "radar" },
  { label: "Show jobs needing a decision", trigger: "what needs my decision", icon: "inbox" },
  { label: "Build a pack", trigger: "build a pack for my best match", icon: "package" },
  { label: "Compare top matches", trigger: "compare my top 2 matches", icon: "gitcompare" },
] as const;
