"""HaxJobs CLI."""
import argparse
import sys

from haxjobs.interfaces.experiment_cli import cmd_experiment_review_job


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="haxjobs", description="Career agent platform"
    )
    sub = parser.add_subparsers(dest="command")

    # ── experiment sub-group ──
    experiment = sub.add_parser("experiment", help="Greenfield experiments")
    exp_sub = experiment.add_subparsers(dest="experiment_command")

    review_job = exp_sub.add_parser("review-job", help="Run the Stage 0 job review")
    review_job.add_argument("--job", type=int, required=True, choices=[49, 328],
                            help="Job fixture ref (49 or 328)")
    review_job.add_argument("--fake", action="store_true",
                            help="Use fake model — no network")
    review_job.add_argument("--live", action="store_true",
                            help="Use configured provider (requires private career fixture)")
    review_job.add_argument("--career-fixture", default=None,
                            help="Path to career fixture JSON")
    review_job.add_argument("--artifacts-dir", default="state/harness-runs",
                            help="Artifact output directory")
    review_job.set_defaults(func=cmd_experiment_review_job)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
