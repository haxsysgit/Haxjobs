"""HaxJobs CLI."""
import argparse
import asyncio
import sys

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

    # ── chat / default command ──
    chat = sub.add_parser("chat", help="Open a live conversation with Hax")
    chat.add_argument("--new", action="store_true",
                      help="Create a new session (don't resume latest)")
    chat.add_argument("--resume", default=None, metavar="ID",
                      help="Resume a specific session by ID")
    chat.add_argument("--fake", action="store_true",
                      help="Use fake model — no network")
    chat.add_argument("--fake-delay", type=int, default=0, metavar="MS",
                      help="Per-event delay for fake model (ms, cancellation tests)")
    chat.add_argument("--session-db", default=None,
                      help="Override session database path")
    chat.add_argument("--person-id", default=None,
                      help="Person ID (valid only with --new)")
    chat.add_argument("--track-id", default=None,
                      help="Track ID (valid only with --new)")
    chat.set_defaults(func=cmd_chat)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        # Default: open or resume latest session (same as `haxjobs chat`)
        from haxjobs.interfaces.terminal import run_terminal
        from haxjobs.employment.composition import compose_session
        from haxjobs.employment.host import EmploymentSetupError
        from haxjobs.agent_core.session_store import SessionStore
        from haxjobs.config import SESSION_DB_PATH

        try:
            session_id = None
            # Try to resume latest session first
            store = SessionStore(str(SESSION_DB_PATH))
            try:
                latest = store.latest_session_id()
                if latest:
                    session_id = latest
            finally:
                store.close()

            if session_id:
                print(f"Resuming session: {session_id}")

            session = compose_session(
                session_id=session_id,
                fake=False,
            )
        except EmploymentSetupError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            print("Run 'haxjobs migrate' first.", file=sys.stderr)
            return
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return
        asyncio.run(run_terminal(session))
        return
    args.func(args)


def cmd_chat(args) -> None:
    """Open a live conversation with Hax."""
    from haxjobs.interfaces.terminal import run_terminal
    from haxjobs.employment.composition import compose_session
    from haxjobs.employment.host import EmploymentSetupError
    from haxjobs.agent_core.session_store import SessionStore
    from haxjobs.config import SESSION_DB_PATH

    try:
        session_db = args.session_db or str(SESSION_DB_PATH)

        # Determine session_id
        session_id = args.resume
        if session_id is None and not args.new:
            # Try to resume latest session
            store = SessionStore(session_db)
            try:
                latest = store.latest_session_id()
                if latest:
                    session_id = latest
            finally:
                store.close()

        if session_id:
            print(f"Resuming session: {session_id}")

        session = compose_session(
            session_id=session_id,
            fake=args.fake,
            fake_delay_ms=args.fake_delay or 0,
            session_db_path=session_db,
            person_id=getattr(args, 'person_id', None),
            track_id=getattr(args, 'track_id', None),
        )
    except EmploymentSetupError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print("Run 'haxjobs migrate' first.", file=sys.stderr)
        return
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return

    asyncio.run(run_terminal(session))


if __name__ == "__main__":
    main()
