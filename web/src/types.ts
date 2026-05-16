export type AnalysisMode = "safe" | "stretch" | "interview" | "ideal";

export interface FitSummary {
  score: number;
  label: string;
  matched_requirements: number;
  total_requirements: number;
  summary: string;
}

export interface JDRequirement {
  id: string;
  text: string;
  section: string;
  importance: "required" | "nice_to_have";
  category: string;
  keywords: string[];
}

export interface JDAnalysis {
  role_title: string;
  section_titles: string[];
  requirements: JDRequirement[];
  recruiter_concerns: string[];
  required_skills: string[];
  desirable_skills: string[];
}

export interface EvidenceItem {
  id: string;
  category: string;
  source_section: string;
  evidence: string;
  keywords: string[];
}

export interface EvidenceMatch {
  requirement_id: string;
  requirement_text: string;
  section: string;
  importance: "required" | "nice_to_have";
  match_label:
    | "Strong Match"
    | "Partial Match"
    | "Transferable Match"
    | "Weak Match"
    | "Gap";
  claim_label:
    | "Confirmed"
    | "Inferred"
    | "Needs User Confirmation"
    | "Stretch Wording"
    | "Unsafe Claim";
  supporting_evidence: string[];
  suggested_safe_wording: string;
  risk_warning: string | null;
}

export interface FollowUpQuestion {
  requirement_id: string;
  requirement_text: string;
  question: string;
  reason: string;
  priority: "high" | "medium" | "low";
}

export interface AnalysisMetadata {
  mode: AnalysisMode;
  source: "upload" | "demo";
  cv_label: string;
  jd_label: string;
}

export interface AnalysisResponse {
  ok: boolean;
  metadata: AnalysisMetadata;
  fit_summary: FitSummary;
  jd_analysis: JDAnalysis;
  candidate_evidence: EvidenceItem[];
  evidence_map: EvidenceMatch[];
  follow_up_questions: FollowUpQuestion[];
  warnings: string[];
  markdown_report: string;
}

export interface HealthResponse {
  ok: boolean;
  llm_configured: boolean;
}

export interface DemoFixtureOption {
  id: string;
  label: string;
}

export interface DemoOptionsResponse {
  cv_fixtures: DemoFixtureOption[];
  jd_fixtures: DemoFixtureOption[];
  default_cv_fixture: string;
  default_jd_fixture: string;
  modes: AnalysisMode[];
}
