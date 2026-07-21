"""HaxJobs CLI."""
import argparse

from haxjobs.interfaces.experiment_cli import cmd_experiment_review_job
from haxjobs.interfaces.profile_cli import (
    cmd_profile_migrate,
    cmd_profile_show,
    cmd_profile_track_add,
    cmd_profile_skill_add,
    cmd_profile_evidence_add,
    cmd_profile_gap_add,
    cmd_profile_constraint_add,
)


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="haxjobs", description="Career agent platform"
    )
    sub = parser.add_subparsers(dest="command")

    # ── experiment sub-group ──
    experiment = sub.add_parser("experiment", help="Greenfield experiments")
    exp_sub = experiment.add_subparsers(dest="experiment_command")

    review_job = exp_sub.add_parser("review-job", help="Run the job review experiment (Stage 0/1)")
    review_job.add_argument("--job", type=int, required=True, choices=[49, 328],
                            help="Job fixture ref (49 or 328)")
    mode = review_job.add_mutually_exclusive_group()
    mode.add_argument("--fake", action="store_true",
                      help="Use fake model — no network")
    mode.add_argument("--live", action="store_true",
                      help="Use configured provider (requires private career fixture)")
    review_job.add_argument("--career-fixture", default=None,
                            help="Path to career fixture JSON")
    review_job.add_argument("--artifacts-dir", default="state/harness-runs",
                            help="Artifact output directory")
    review_job.add_argument("--inspect-source", action="store_true",
                            help="Activate Stage 1 source inspection tool")
    review_job.add_argument("--max-model-steps", type=int, default=3,
                            help="Maximum model calls (1-5, default 3)")
    review_job.set_defaults(func=cmd_experiment_review_job)

    # ── profile sub-group ──
    profile = sub.add_parser("profile", help="Career profile management")
    prof_sub = profile.add_subparsers(dest="profile_command")

    prof_show = prof_sub.add_parser("show", help="Show career graph overview")
    prof_show.set_defaults(func=cmd_profile_show)

    prof_track = prof_sub.add_parser("track", help="Manage career tracks")
    prof_track.add_argument("sub", choices=["add"], help="Add a career track")
    prof_track.add_argument("--name", required=True, help="Track name")
    prof_track.add_argument("--person-id", default="arinze-elensulu", help="Person ID")
    prof_track.set_defaults(func=cmd_profile_track_add)

    prof_skill = prof_sub.add_parser("skill", help="Manage skills")
    prof_skill.add_argument("sub", choices=["add"], help="Add a skill")
    prof_skill.add_argument("--track-id", required=True, help="Track ID")
    prof_skill.add_argument("--name", required=True, help="Skill name")
    prof_skill.add_argument("--proficiency", default="working",
                            choices=["primary", "strong", "working", "learning"],
                            help="Proficiency level")
    prof_skill.add_argument("--parent-skill-id", default=None, help="Parent skill ID")
    prof_skill.set_defaults(func=cmd_profile_skill_add)

    prof_ev = prof_sub.add_parser("evidence", help="Manage evidence")
    prof_ev.add_argument("sub", choices=["add"], help="Add evidence")
    prof_ev.add_argument("--label", required=True, help="Evidence label")
    prof_ev.add_argument("--source", required=True, help="Evidence source")
    prof_ev.add_argument("--content", required=True, help="Evidence content")
    prof_ev.add_argument("--skill-id", default=None, help="Skill ID to link")
    prof_ev.set_defaults(func=cmd_profile_evidence_add)

    prof_gap = prof_sub.add_parser("gap", help="Manage skill gaps")
    prof_gap.add_argument("sub", choices=["add"], help="Add a gap")
    prof_gap.add_argument("--track-id", required=True, help="Track ID")
    prof_gap.add_argument("--skill-name", required=True, help="Skill name")
    prof_gap.add_argument("--proficiency", default="working",
                          choices=["primary", "strong", "working", "learning"],
                          help="Target proficiency")
    prof_gap.add_argument("--note", default="", help="Optional note")
    prof_gap.set_defaults(func=cmd_profile_gap_add)

    prof_con = prof_sub.add_parser("constraint", help="Manage hard constraints")
    prof_con.add_argument("sub", choices=["add"], help="Add a constraint")
    prof_con.add_argument("--track-id", required=True, help="Track ID")
    prof_con.add_argument("--text", required=True, help="Constraint text")
    prof_con.set_defaults(func=cmd_profile_constraint_add)

    prof_migrate = prof_sub.add_parser("migrate", help="Migrate career fixture to graph")
    prof_migrate.add_argument("--fixture", default=None,
                              help="Path to career fixture JSON")
    prof_migrate.set_defaults(func=cmd_profile_migrate)

    # ── shortcut: haxjobs migrate ──
    migrate_cmd = sub.add_parser("migrate", help="Quick: migrate career fixture to graph")
    migrate_cmd.add_argument("--fixture", default=None,
                             help="Path to career fixture JSON")
    migrate_cmd.set_defaults(func=cmd_profile_migrate)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
