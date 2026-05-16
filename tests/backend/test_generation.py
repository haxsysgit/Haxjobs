from app.models.analysis import (
    AnalysisMetadata,
    AnalyzeResponse,
    EvidenceMatch,
    FitSummary,
    FollowUpAnswer,
    FollowUpQuestion,
    JDAnalysis,
    JDRequirement,
    UserClaimConfirmation,
)
from app.services.generation import generate_application_pack


def make_analysis_response(mode: str) -> AnalyzeResponse:
    return AnalyzeResponse(
        metadata=AnalysisMetadata(
            mode=mode,  # type: ignore[arg-type]
            source="demo",
            cv_label="Fixture CV",
            jd_label="Fixture JD",
        ),
        fit_summary=FitSummary(
            score=74,
            label="Moderate Fit",
            matched_requirements=3,
            total_requirements=4,
            summary="The candidate has strong Python and API evidence with one adjacent gap.",
        ),
        jd_analysis=JDAnalysis(
            role_title="Backend Engineer",
            section_titles=["The Role"],
            requirements=[
                JDRequirement(
                    id="req-1",
                    text="Strong Python fundamentals",
                    section="The Role",
                    importance="required",
                    category="Python",
                    keywords=["python"],
                ),
                JDRequirement(
                    id="req-2",
                    text="Production Vue exposure",
                    section="The Role",
                    importance="required",
                    category="Frontend",
                    keywords=["vue"],
                ),
                JDRequirement(
                    id="req-3",
                    text="Agent workflow systems",
                    section="The Role",
                    importance="required",
                    category="AI Workflows",
                    keywords=["agents", "mcp"],
                ),
                JDRequirement(
                    id="req-4",
                    text="Kubernetes ownership",
                    section="The Role",
                    importance="required",
                    category="Cloud",
                    keywords=["kubernetes"],
                ),
            ],
            recruiter_concerns=["Code Quality"],
            required_skills=["python", "vue", "mcp"],
            desirable_skills=["docker"],
        ),
        candidate_evidence=[],
        evidence_map=[
            EvidenceMatch(
                requirement_id="req-1",
                requirement_text="Strong Python fundamentals",
                section="The Role",
                importance="required",
                match_label="Strong Match",
                claim_label="Confirmed",
                supporting_evidence=["Built Python APIs in production"],
                suggested_safe_wording="Lead with the existing evidence and keep the wording concrete: Built Python APIs in production",
                risk_warning=None,
            ),
            EvidenceMatch(
                requirement_id="req-2",
                requirement_text="Production Vue exposure",
                section="The Role",
                importance="required",
                match_label="Transferable Match",
                claim_label="Stretch Wording",
                supporting_evidence=["Shipped a small admin panel in Vue"],
                suggested_safe_wording="Use adjacent experience wording and avoid claiming direct ownership where the CV only shows a nearby signal: Shipped a small admin panel in Vue",
                risk_warning="This can be positioned as adjacent experience, but not as a direct stack match.",
            ),
            EvidenceMatch(
                requirement_id="req-3",
                requirement_text="Agent workflow systems",
                section="The Role",
                importance="required",
                match_label="Weak Match",
                claim_label="Needs User Confirmation",
                supporting_evidence=["Built internal MCP tools"],
                suggested_safe_wording="Only mention this if you can expand the example in interview, otherwise keep it framed as exposure rather than proof: Built internal MCP tools",
                risk_warning="The current CV signal is too weak to state as direct experience without a better example.",
            ),
            EvidenceMatch(
                requirement_id="req-4",
                requirement_text="Kubernetes ownership",
                section="The Role",
                importance="required",
                match_label="Gap",
                claim_label="Unsafe Claim",
                supporting_evidence=[],
                suggested_safe_wording="Treat 'Kubernetes ownership' as a gap until new evidence or a user-confirmed example exists.",
                risk_warning="No direct CV evidence was found for this required requirement.",
            ),
        ],
        follow_up_questions=[
            FollowUpQuestion(
                requirement_id="req-3",
                requirement_text="Agent workflow systems",
                question="What production example can you give for agent workflow systems?",
                reason="The signal is still weak.",
                priority="high",
            ),
            FollowUpQuestion(
                requirement_id="req-4",
                requirement_text="Kubernetes ownership",
                question="Do you have any honest adjacent example for Kubernetes ownership?",
                reason="Current evidence is a direct gap.",
                priority="high",
            ),
        ],
        warnings=["One claim needs confirmation and one gap should stay explicit."],
        markdown_report="# Analysis Metadata",
    )


def test_safe_mode_excludes_unresolved_claims_from_tailored_cv() -> None:
    pack = generate_application_pack(make_analysis_response("safe"))
    assert "Strong Python fundamentals" not in pack.tailored_cv_markdown
    assert "Built Python APIs in production" in pack.tailored_cv_markdown
    assert "Production Vue exposure" not in pack.tailored_cv_markdown
    assert "Kubernetes ownership" in pack.tailored_cv_markdown


def test_stretch_mode_allows_transferable_wording() -> None:
    pack = generate_application_pack(make_analysis_response("stretch"))
    assert "Shipped a small admin panel in Vue" in pack.tailored_cv_markdown
    assert "adjacent experience" in pack.cover_letter_markdown


def test_interview_mode_uses_provided_follow_up_answers() -> None:
    pack = generate_application_pack(
        make_analysis_response("interview"),
        follow_up_answers=[
            FollowUpAnswer(
                requirement_id="req-3",
                answer="I built MCP-based internal workflow tooling and can describe the rollout clearly.",
            )
        ],
    )
    assert "User-confirmed follow-up" in pack.interview_notes_markdown
    assert "I built MCP-based internal workflow tooling" in pack.tailored_cv_markdown
    assert pack.metadata.unanswered_follow_up_count == 1


def test_ideal_mode_is_clearly_labeled_as_aspirational() -> None:
    pack = generate_application_pack(make_analysis_response("ideal"))
    assert pack.metadata.aspirational is True
    assert "Aspirational Tailored CV Sample" in pack.tailored_cv_markdown
    assert "aspirational sample cover letter" in pack.cover_letter_markdown.lower()


def test_claim_confirmation_marks_requirement_as_resolved() -> None:
    pack = generate_application_pack(
        make_analysis_response("safe"),
        user_claim_confirmations=[
            UserClaimConfirmation(
                requirement_id="req-3",
                status="confirmed",
                notes="Confirmed through a production internal MCP delivery.",
            )
        ],
    )
    assert "Claim confirmation note for Agent workflow systems" in pack.tailored_cv_markdown
    assert pack.application_pack_json["user_claim_confirmations"][0]["status"] == "confirmed"
