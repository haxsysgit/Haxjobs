from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_PIPELINE = ROOT / "cron" / "run_pipeline.sh"


def test_cron_pipeline_does_not_generate_application_packs_automatically():
    text = RUN_PIPELINE.read_text()

    assert "evaluate_with_hermes.py --batch 1" in text
    assert "generate_ready_packs.py" not in text
    assert "Pack generation" not in text


def test_no_pending_cron_path_only_runs_maintenance_syncs():
    text = RUN_PIPELINE.read_text()

    no_pending_block = text[text.index('if [ "$PENDING" -eq 0 ]'):text.index('log "Pipeline starting')]
    assert "generate_ready_packs.py" not in no_pending_block
    assert "pipeline_db.py classify-roles" in no_pending_block
    assert "sync_db_to_intake.py" in no_pending_block
    assert "exit 0" in no_pending_block
