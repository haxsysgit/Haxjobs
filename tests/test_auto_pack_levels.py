"""Tests for auto-pack behavior — L1/L2 auto-pack, L3/L4 do not."""

from pathlib import Path

from db import schema
from db.jobs import insert_job, update_job_pack_status
from db.evaluations import save_evaluation, get_evaluation
from packs_builder.job_pack import build_job_pack


def use_temp_db(monkeypatch, tmp_path):
    db_path = tmp_path / "haxjobs.db"
    monkeypatch.setattr(schema, "DB_PATH", str(db_path))
    schema.init()
    return db_path


def _make_cv_metadata(variant="backend_python"):
    return {
        "pack_owns_cv": False,
        "recommended_cv_variant": variant,
        "role_family": variant,
        "cv_pdf": f"cv_variants/{variant}/cv.pdf",
        "cv_html": f"cv_variants/{variant}/cv.html",
    }


def _make_profile():
    return {
        "name": "Arinze Elenasulu",
        "email": "test@example.com",
        "linkedin": "https://linkedin.com/in/test",
    }


def test_l1_job_gets_pack(monkeypatch, tmp_path):
    """L1 (score 75+) should generate a pack."""
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="Python Backend Engineer",
        company="TestCo",
        location="London",
        jd_text="Python FastAPI PostgreSQL.",
        source="manual",
    )
    from db import schema as s
    conn = s.get_db()
    conn.execute("UPDATE jobs SET role_family=?, recommended_cv_variant=? WHERE id=?",
                 ("backend_python", "backend_python", job_id))
    conn.commit()
    conn.close()

    result = {
        "fit_score": 85,
        "fit_verdict": "STRONG_FIT",
        "level": 1,
        "level_name": "Standard",
        "strongest_matches": ["Python", "FastAPI"],
        "major_gaps": [],
        "summary": "Great fit.",
    }
    save_evaluation(job_id, result)

    # Simulate auto-pack
    job = {"id": job_id, "title": "Python Backend Engineer", "company": "TestCo",
           "location": "London", "source_url": "", "role_family": "backend_python",
           "recommended_cv_variant": "backend_python"}
    pack_result = build_job_pack(
        job=job,
        evaluation=result,
        profile=_make_profile(),
        cv_variant=_make_cv_metadata("backend_python"),
        output_root=str(tmp_path / "packs"),
    )

    assert "pack_dir" in pack_result
    assert Path(pack_result["pack_dir"]).exists()
    # All 6 files should exist
    assert len(pack_result["files"]) == 6
    for f in pack_result["files"]:
        assert Path(f).exists()


def test_l3_job_no_pack_path_expected(monkeypatch, tmp_path):
    """L3 evaluations should NOT auto-pack. The evaluator skips them."""
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="Senior Architect",
        company="BigCorp",
        location="London",
        jd_text="10+ years experience required.",
        source="manual",
    )

    result = {
        "fit_score": 35,
        "fit_verdict": "WEAK_FIT",
        "level": 3,
        "level_name": "Lite",
        "strongest_matches": ["Python"],
        "major_gaps": ["Senior level", "Architecture experience"],
        "summary": "Weak fit — senior role.",
    }
    save_evaluation(job_id, result)

    # Verify level 3 is NOT in AUTO_PACK_LEVELS (default [1, 2])
    from haxjobs_config import AUTO_PACK_LEVELS
    assert 3 not in AUTO_PACK_LEVELS
    assert 4 not in AUTO_PACK_LEVELS
    assert 1 in AUTO_PACK_LEVELS
    assert 2 in AUTO_PACK_LEVELS


def test_template_slots_fully_filled(monkeypatch, tmp_path):
    """Cover letter output must not contain any leftover {slot} markers."""
    use_temp_db(monkeypatch, tmp_path)

    job_id = insert_job(
        title="AI Engineer",
        company="AICorp",
        location="Remote UK",
        jd_text="Build RAG pipelines and fine-tune LLMs.",
        source="manual",
    )
    conn = schema.get_db()
    conn.execute("UPDATE jobs SET role_family=?, recommended_cv_variant=? WHERE id=?",
                 ("ai_engineer_llm", "ai_engineer_llm", job_id))
    conn.commit()
    conn.close()

    result = {
        "fit_score": 88,
        "fit_verdict": "STRONG_FIT",
        "level": 1,
        "level_name": "Standard",
        "strongest_matches": ["RAG", "LLMs", "Python"],
        "major_gaps": ["Production ML ops"],
        "summary": "Strong AI fit.",
    }

    pack_result = build_job_pack(
        job={"id": job_id, "title": "AI Engineer", "company": "AICorp",
             "location": "Remote UK", "source_url": "https://aicorp.com/jobs/1",
             "role_family": "ai_engineer_llm", "recommended_cv_variant": "ai_engineer_llm"},
        evaluation=result,
        profile=_make_profile(),
        cv_variant=_make_cv_metadata("ai_engineer_llm"),
        output_root=str(tmp_path / "packs"),
    )

    # Read cover letter and verify no unfilled slots
    cover_letter_path = Path(pack_result["pack_dir"]) / "cover_letter.md"
    content = cover_letter_path.read_text()

    import re
    unfilled = re.findall(r"\{[a-zA-Z0-9_]+\}", content)
    assert unfilled == [], f"Unfilled template slots: {unfilled}"

    # Also verify no em dashes (banned per style)
    assert "\u2014" not in content, "Cover letter contains em dash"


def test_all_role_templates_load_and_fill(monkeypatch, tmp_path):
    """Every configured role family has a template that fills without errors."""
    use_temp_db(monkeypatch, tmp_path)

    from haxjobs_config import ROLE_PROFILES

    variants = list({r["cv_variant"] for r in ROLE_PROFILES})
    assert len(variants) >= 7, f"Expected at least 7 variants, got {len(variants)}"

    for variant in variants:
        job_id = insert_job(
            title=f"{variant} Engineer",
            company="TestCo",
            location="London",
            jd_text="FastAPI Python backend APIs.",
            source="manual",
        )
        conn = schema.get_db()
        conn.execute("UPDATE jobs SET role_family=?, recommended_cv_variant=? WHERE id=?",
                     (variant, variant, job_id))
        conn.commit()
        conn.close()

        result = {
            "fit_score": 80,
            "fit_verdict": "STRONG_FIT",
            "level": 1,
            "level_name": "Standard",
            "strongest_matches": ["Python"],
            "major_gaps": [],
            "summary": "Good fit.",
        }

        pack_result = build_job_pack(
            job={"id": job_id, "title": f"{variant} Engineer", "company": "TestCo",
                 "location": "London", "source_url": "",
                 "role_family": variant, "recommended_cv_variant": variant},
            evaluation=result,
            profile=_make_profile(),
            cv_variant=_make_cv_metadata(variant),
            output_root=str(tmp_path / "packs"),
        )

        assert Path(pack_result["pack_dir"]).exists()
        # Cover letter should not have unfilled slots
        import re
        cl = (Path(pack_result["pack_dir"]) / "cover_letter.md").read_text()
        unfilled = re.findall(r"\{[a-zA-Z0-9_]+\}", cl)
        assert unfilled == [], f"Unfilled slots in {variant} template: {unfilled}"
        assert "\u2014" not in cl, f"Em dash in {variant} cover letter"
