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

export interface RecruiterAssessment {
  shortlist_summary: string;
  priority_requirements: string[];
  concerns: string[];
  model_tier: string;
}

export interface EvaluatorFlag {
  requirement_id: string;
  requirement_text: string;
  issue: string;
  severity: "high" | "medium" | "low";
}

export interface EvaluatorAssessment {
  fit_score: number;
  summary: string;
  weak_claims: EvaluatorFlag[];
  uncertain_claims: EvaluatorFlag[];
  model_tier: string;
}

export interface VerificationQuestion {
  requirement_id: string;
  requirement_text: string;
  question: string;
  reason: string;
  priority: "high" | "medium" | "low";
  model_tier: string;
}

export interface AspirationalPack {
  label: string;
  non_submittable: boolean;
  tailored_cv_markdown: string;
  cover_letter_markdown: string;
  interview_notes_markdown: string;
  model_tier: string;
}

export interface AnalysisResponse {
  ok: boolean;
  analysis_engine: "ai";
  metadata: AnalysisMetadata;
  fit_summary: FitSummary;
  jd_analysis: JDAnalysis;
  candidate_evidence: EvidenceItem[];
  evidence_map: EvidenceMatch[];
  follow_up_questions: FollowUpQuestion[];
  recruiter_assessment: RecruiterAssessment | null;
  evaluator_assessment: EvaluatorAssessment | null;
  verification_questions: VerificationQuestion[];
  aspirational_pack: AspirationalPack | null;
  warnings: string[];
  markdown_report: string;
}

export interface FollowUpAnswer {
  requirement_id: string;
  answer: string;
  skipped: boolean;
}

export interface UserClaimConfirmation {
  requirement_id: string;
  status: "confirmed" | "rejected" | "uncertain";
  notes: string;
}

export interface GenerationMetadata {
  mode: AnalysisMode;
  role_title: string;
  source: "upload" | "demo";
  aspirational: boolean;
  follow_up_answer_count: number;
  unanswered_follow_up_count: number;
  generated_documents: string[];
}

export interface GenerateApplicationPackRequest {
  analysis: AnalysisResponse;
  follow_up_answers: FollowUpAnswer[];
  user_claim_confirmations?: UserClaimConfirmation[];
  user_notes?: string | null;
}

export interface GenerateApplicationPackResponse {
  metadata: GenerationMetadata;
  tailored_cv_markdown: string;
  cover_letter_markdown: string;
  interview_notes_markdown: string;
  evidence_map_json: EvidenceMatch[];
  application_pack_json: Record<string, unknown>;
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
