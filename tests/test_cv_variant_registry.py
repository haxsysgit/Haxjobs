import json
from pathlib import Path

import pytest

from cv_variants.registry import load_cv_variant_registry, resolve_cv_variant, build_pack_cv_metadata


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "cv_variants" / "registry.json"


def _load_role_families():
    """Get role family data from haxjobs_config (TOML-driven)."""
    from haxjobs_config import ROLE_PROFILES
    # ROLE_PROFILES is a list; convert to dict keyed by id for consistency
    return {rp["id"]: rp for rp in ROLE_PROFILES}


def test_registry_covers_all_taxonomy_cv_variants():
    registry = load_cv_variant_registry(REGISTRY_PATH)
    taxonomy = _load_role_families()

    expected_variants = {family["cv_variant"] for family in taxonomy.values()}
    assert expected_variants == set(registry["variants"])


def test_variant_filenames_are_stable_and_not_per_job_tailored():
    registry = load_cv_variant_registry(REGISTRY_PATH)

    for variant_id, variant in registry["variants"].items():
        assert "Tailored" not in variant["pdf"]
        assert "Tailored" not in variant["html"]
        assert variant["pdf"].startswith("Arinze_Elenasulu_")
        assert variant["pdf"].endswith("_CV.pdf")
        assert variant["html"].endswith("_CV.html")
        assert variant["role_family"] == variant_id


def test_resolve_cv_variant_returns_copy_free_reference():
    registry = load_cv_variant_registry(REGISTRY_PATH)

    resolved = resolve_cv_variant("backend_python", registry)

    assert resolved["variant_id"] == "backend_python"
    assert resolved["role_family"] == "backend_python"
    assert resolved["pdf"].endswith("Arinze_Elenasulu_Backend_Python_CV.pdf")
    assert resolved["relative_dir"] == "cv_variants/backend_python"


def test_resolve_unknown_variant_falls_back_to_backend_python():
    registry = load_cv_variant_registry(REGISTRY_PATH)

    resolved = resolve_cv_variant("unknown", registry)

    assert resolved["variant_id"] == registry["default_variant"]
    assert resolved["role_family"] == "backend_python"


def test_pack_cv_metadata_references_reusable_variant_without_owning_cv():
    registry = load_cv_variant_registry(REGISTRY_PATH)

    metadata = build_pack_cv_metadata(
        recommended_cv_variant="ai_engineer_llm",
        registry=registry,
    )

    assert metadata == {
        "recommended_cv_variant": "ai_engineer_llm",
        "role_family": "ai_engineer_llm",
        "cv_variant_dir": "cv_variants/ai_engineer_llm",
        "cv_pdf": "cv_variants/ai_engineer_llm/Arinze_Elenasulu_AI_LLM_Engineer_CV.pdf",
        "cv_html": "cv_variants/ai_engineer_llm/Arinze_Elenasulu_AI_LLM_Engineer_CV.html",
        "pack_owns_cv": False,
    }


def test_pull_script_exists():
    script = ROOT / "scripts" / "pull-cv-variants"
    assert script.exists()
    text = script.read_text()
    assert "rsync" in text
    assert "cv_variants/" in text
    # Remote path is configurable via HAXJOBS_REMOTE_HOME


def test_backend_python_source_is_ready():
    """The first CV variant (backend_python) must have its source ready."""
    registry = load_cv_variant_registry(REGISTRY_PATH)

    variant = registry["variants"]["backend_python"]
    assert variant["source_status"] == "generated", (
        f"Expected generated, got {variant['source_status']}"
    )
    assert "source_md" in variant, "source_md field missing from registry"
    assert variant["source_md"] == "cv_variants/backend_python/cv_source.md"

    source_path = ROOT / variant["source_md"]
    assert source_path.exists(), f"CV source file not found: {source_path}"


def test_seed_script_promotes_existing_pack_cvs_without_tailored_names():
    script = ROOT / "scripts" / "seed-cv-variants-from-packs"
    assert script.exists()
    text = script.read_text()
    assert "Tailored_CV" not in text
    assert "Python_Developer" in text
    assert "Palantir_Forward_Deployed_AI_Engineer" in text
    assert "PROMOTIONS" in text
    assert '"backend_python"' in text
    assert '"target_pdf"' in text
