from evaluate_with_hermes import build_prompt


def test_evaluator_prompt_routes_packs_to_reusable_cv_variants():
    prompt = build_prompt(
        title="Python Developer",
        company="ExampleCo",
        location="London",
        jd_text="FastAPI PostgreSQL React TypeScript Docker Kubernetes",
        source_url="https://example.com/job",
    )

    assert "reusable CV variant" in prompt
    assert "Generate a new CV" not in prompt
    assert "full CV + cover letter" not in prompt
    assert "CV + cover letter" not in prompt
    assert "cover letter + form answers" in prompt
