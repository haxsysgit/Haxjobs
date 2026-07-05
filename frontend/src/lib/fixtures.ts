import { fixtureMode } from "./fixtureMode"
export { fixtureMode }

export interface FixtureJob {
  id: number
  title: string
  company: string
  location: string
  source_url: string
  jd_text?: string
  status: string
  fit_score: number
  level: number
  level_name: string
  fit_verdict: string
  role_family: string
  recommended_cv_variant: string
  strongest_matches: string[]
  major_gaps: string[]
  pack_status: string | null
  discovered_at: string
}

export const sampleJobs: FixtureJob[] = [
  {
    id: 1,
    title: "Backend Engineer",
    company: "Stripe",
    location: "London, UK",
    source_url: "https://stripe.com/jobs",
    status: "evaluated",
    fit_score: 87,
    level: 1,
    level_name: "Standard",
    fit_verdict: "STRONG_FIT",
    role_family: "backend_python",
    recommended_cv_variant: "backend_python",
    strongest_matches: ["FastAPI", "PostgreSQL", "distributed systems"],
    major_gaps: ["Kubernetes depth not proven"],
    pack_status: "generated",
    discovered_at: new Date(Date.now() - 600_000).toISOString(),
  },
  {
    id: 2,
    title: "Full Stack Engineer",
    company: "Vercel",
    location: "Remote (US)",
    source_url: "https://vercel.com/careers",
    status: "evaluated",
    fit_score: 74,
    level: 2,
    level_name: "Good",
    fit_verdict: "GOOD_FIT",
    role_family: "full_stack",
    recommended_cv_variant: "full_stack",
    strongest_matches: ["React", "Python", "TypeScript"],
    major_gaps: ["Edge runtime experience limited"],
    pack_status: "generated",
    discovered_at: new Date(Date.now() - 1_200_000).toISOString(),
  },
  {
    id: 3,
    title: "AI/ML Engineer",
    company: "Anthropic",
    location: "San Francisco, CA",
    source_url: "https://anthropic.com/careers",
    status: "evaluated",
    fit_score: 62,
    level: 3,
    level_name: "Fair",
    fit_verdict: "POSSIBLE",
    role_family: "ai_ml",
    recommended_cv_variant: "ai_ml",
    strongest_matches: ["LLM experience", "Python", "RAG pipelines"],
    major_gaps: ["No published ML research", "Limited PyTorch"],
    pack_status: null,
    discovered_at: new Date(Date.now() - 3_600_000).toISOString(),
  },
  {
    id: 4,
    title: "Waiter / Server",
    company: "The Wolseley",
    location: "London, UK",
    source_url: "https://wolseley.com/careers",
    status: "discovered",
    fit_score: 0,
    level: 0,
    level_name: "",
    fit_verdict: "",
    role_family: "waiter",
    recommended_cv_variant: "waiter",
    strongest_matches: [],
    major_gaps: [],
    pack_status: null,
    discovered_at: new Date(Date.now() - 7_200_000).toISOString(),
  },
  {
    id: 5,
    title: "Senior Backend Developer",
    company: "Monzo",
    location: "London, UK",
    source_url: "https://monzo.com/careers",
    status: "evaluated",
    fit_score: 82,
    level: 1,
    level_name: "Standard",
    fit_verdict: "STRONG_FIT",
    role_family: "backend_python",
    recommended_cv_variant: "backend_python",
    strongest_matches: ["Python", "FastAPI", "finance domain"],
    major_gaps: ["Less experience with Go"],
    pack_status: "generated",
    discovered_at: new Date(Date.now() - 86_400_000).toISOString(),
  },
  {
    id: 6,
    title: "Waiter / Front of House",
    company: "Dishoom",
    location: "London, UK",
    source_url: "https://dishoom.com/careers",
    status: "discovered",
    fit_score: 0,
    level: 0,
    level_name: "",
    fit_verdict: "",
    role_family: "waiter",
    recommended_cv_variant: "waiter",
    strongest_matches: [],
    major_gaps: [],
    pack_status: null,
    discovered_at: new Date(Date.now() - 172_800_000).toISOString(),
  },
]

/** ponytail: roles derived from sample data — in production they come from profile. */
export const sampleRoles = [
  { id: "backend_python", displayName: "Backend Developer", count: 2 },
  { id: "full_stack", displayName: "Full Stack Engineer", count: 1 },
  { id: "ai_ml", displayName: "AI/ML Engineer", count: 1 },
  { id: "waiter", displayName: "Waiter", count: 2 },
]

export function getFixtureJobs(): FixtureJob[] {
  return sampleJobs
}

export function getFixtureJobsByRole(roleId: string): FixtureJob[] {
  return sampleJobs.filter((j) => j.role_family === roleId)
}

export function getFixtureRoles() {
  return sampleRoles
}
