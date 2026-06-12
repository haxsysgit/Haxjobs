from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_PIPELINE = ROOT / "cron" / "run_pipeline.sh"


def test_pipeline_runs_ready_pack_generation_after_evaluation():
    text = RUN_PIPELINE.read_text()

    assert "generate_ready_packs.py --limit 10" in text
    assert "Pack generation" in text

    after_evaluation = text[text.index("# ── Process exactly ONE job using evaluate_with_hermes.py ──"):]
    assert after_evaluation.index("evaluate_with_hermes.py --batch 1") < after_evaluation.index("generate_ready_packs.py --limit 10")


def test_pipeline_generates_packs_even_when_no_jobs_are_pending():
    text = RUN_PIPELINE.read_text()

    no_pending_block = text[text.index('if [ "$PENDING" -eq 0 ]'):text.index('log "Pipeline starting')]
    assert "generate_ready_packs.py --limit 10" in no_pending_block
    assert "sync_db_to_intake.py" in no_pending_block
    assert "exit 0" in no_pending_block
