import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "src" / "haxjobs" / "application_templates"
CV_REGISTRY = ROOT / "src" / "haxjobs" / "cv_variants" / "registry.json"


def _load_taxonomy() -> dict:
    """Load role taxonomy from haxjobs.config (TOML-driven)."""
    from haxjobs.config import ROLE_PROFILES
    return {rp["id"]: rp for rp in ROLE_PROFILES}
FORBIDDEN_PHRASES = (
    "I am writing to express",
    "It is with great enthusiasm",
    "your innovative company",
    "leveraged",
    "spearheaded",
    "orchestrated",
    "cutting-edge",
)
REQUIRED_COVER_SLOTS = {
    "{hiring_manager_or_team}",
    "{role_title}",
    "{company}",
    "{jd_match_points}",
    "{company_reason}",
    "{evidence_story}",
    "{gap_note}",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_every_role_family_has_a_reusable_application_template():
    taxonomy = _load_taxonomy()
    cv_registry = load_json(CV_REGISTRY)["variants"]
    template_registry = load_json(TEMPLATE_ROOT / "registry.json")

    assert set(template_registry["templates"]) == set(taxonomy)

    for family, template in template_registry["templates"].items():
        assert template["cv_variant"] == taxonomy[family]["cv_variant"]
        assert template["cv_variant"] in cv_registry
        assert (TEMPLATE_ROOT / template["cv_brief"]).exists()
        assert (TEMPLATE_ROOT / template["cover_letter_template"]).exists()
        assert (TEMPLATE_ROOT / template["pack_template"]).exists()


def test_cover_letter_templates_are_dynamic_personal_and_governed():
    template_registry = load_json(TEMPLATE_ROOT / "registry.json")

    for template in template_registry["templates"].values():
        path = TEMPLATE_ROOT / template["cover_letter_template"]
        text = path.read_text()

        assert "—" not in text
        for phrase in FORBIDDEN_PHRASES:
            assert phrase.lower() not in text.lower()
        assert REQUIRED_COVER_SLOTS <= set(part for part in REQUIRED_COVER_SLOTS if part in text)
        assert "VOICE:" in text
        assert "LOCKED FACTS" in text
        assert "DO NOT INVENT" in text
        assert "swag" in text.lower() or "personality" in text.lower()


def test_cv_variant_briefs_apply_governance_without_per_job_cv_generation():
    template_registry = load_json(TEMPLATE_ROOT / "registry.json")

    for template in template_registry["templates"].values():
        text = (TEMPLATE_ROOT / template["cv_brief"]).read_text()

        assert "pack_owns_cv: false" in text
        assert "No per-job CV generation" in text
        assert "LOCKED FACTS" in text
        assert "DO NOT CLAIM" in text
        assert "{role_title}" not in text, "CV briefs must stay reusable, not per-job tailored"


def test_pack_templates_reference_variant_and_manual_review():
    template_registry = load_json(TEMPLATE_ROOT / "registry.json")

    for family, template in template_registry["templates"].items():
        text = (TEMPLATE_ROOT / template["pack_template"]).read_text()

        assert f"cv_variant: {template['cv_variant']}" in text
        assert "manual_review_required: true" in text
        assert "auto_submit: false" in text
        assert "cover_letter_template" in text
        assert "field_answers" in text
        assert family in text
