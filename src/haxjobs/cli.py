"""HaxJobs CLI."""
import argparse
import sys


def _csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def cmd_start(args):
    """Start the HaxJobs server."""
    from haxjobs.server.main import run
    run(host=args.host, port=args.port, open_browser=not args.no_browser)


def cmd_agent_ask(args):
    """Ask the native HaxJobs agent a question from the terminal."""
    from haxjobs.agent import Agent, build_system_prompt, load_identity

    prompt = " ".join(args.prompt).strip()
    if not prompt and not sys.stdin.isatty():
        prompt = sys.stdin.read().strip()
    if not prompt:
        raise SystemExit("Provide a prompt or pipe one on stdin.")

    system = args.system
    if not args.plain:
        system = build_system_prompt(load_identity(), context_files=system or "")

    tools = _csv(args.tools)
    if tools:
        text = Agent(tools=tools).run_with_tools(
            prompt,
            system=system,
            max_turns=args.max_turns,
        )
    else:
        text = Agent().run(prompt, system=system)
    print(text)


def cmd_dev_reset(args):
    """Reset onboarding state for development — keeps provider config."""
    from pathlib import Path
    from urllib import request

    home = Path.home() / ".haxjobs"
    preserved = {"haxjobs.toml"}
    removed = []

    for p in sorted(home.glob("*")) if home.exists() else []:
        if p.name in preserved:
            continue
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            import shutil

            shutil.rmtree(p)
        removed.append(p.name)

    if removed:
        print(f"Removed: {', '.join(removed)}")
    else:
        print("No files to remove.")
    print(f"Preserved: {', '.join(preserved)}")

    # Also clear in-memory session if server is running
    try:
        req = request.Request(
            f"http://{args.host}:{args.port}/api/onboarding/reset",
            method="POST",
        )
        resp = request.urlopen(req, timeout=2)
        print("Server session: cleared via POST")
    except Exception:
        # Fallback: try GET (newer server code accepts both)
        try:
            resp2 = request.urlopen(
                f"http://{args.host}:{args.port}/api/onboarding/reset",
                timeout=2,
            )
            print("Server session: cleared via GET")
        except Exception:
            print("Server session: not running or needs restart — run: haxjobs dev restart")


def cmd_dev_status(args):
    """Show current onboarding state."""
    from pathlib import Path
    from haxjobs.features.onboarding.service import load_profile

    print(f"Profile file : {'exists' if load_profile() else 'none'}")

    try:
        from urllib import request
        import json
        req = request.Request(f"http://{args.host}:{args.port}/api/onboarding/status")
        resp = request.urlopen(req, timeout=2)
        data = json.loads(resp.read())
        print(f"Server status: {data.get('stage', 'unknown')}")
    except Exception:
        print("Server status: not running")


def cmd_dev_restart(args):
    """Kill running dev server and start a fresh one with reload."""
    import os, signal, subprocess, sys
    from pathlib import Path

    # Kill existing
    killed = False
    for line in os.popen("ss -tlnp 'sport = :8241'").readlines():
        if "pid=" in line:
            import re
            m = re.search(r"pid=(\d+)", line)
            if m:
                os.kill(int(m.group(1)), signal.SIGTERM)
                killed = True
                print(f"Killed pid {m.group(1)}")

    # Reset filesystem state (skip API call since we just killed the server)
    home = Path.home() / ".haxjobs"
    preserved = {"haxjobs.toml"}
    removed = []
    for p in sorted(home.glob("*")) if home.exists() else []:
        if p.name in preserved:
            continue
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            import shutil
            shutil.rmtree(p)
        removed.append(p.name)
    if removed:
        print(f"State reset: {', '.join(removed)}")

    # Start fresh
    print("Starting dev server…")
    os.chdir(args.project_root or os.getcwd())
    subprocess.Popen(
        [sys.executable, "-m", "haxjobs.server.main", "--no-browser"],
        env={**os.environ, "PYTHONPATH": "src:."},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Server: http://{args.host}:{args.port}")
    print(f"Onboarding: http://{args.host}:{args.port}/onboarding")


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        prog="haxjobs", description="Self-hosted job search platform"
    )
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="Start the server")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8241)
    start.add_argument("--no-browser", action="store_true", help="Don't open browser")
    start.set_defaults(func=cmd_start)

    agent = sub.add_parser("agent", help="Use the native HaxJobs agent")
    agent_sub = agent.add_subparsers(dest="agent_command")
    ask = agent_sub.add_parser("ask", help="Ask the agent a question")
    ask.add_argument("prompt", nargs="*", help="Prompt text; stdin is used if omitted")
    ask.add_argument("--system", default=None, help="Extra system/context text")
    ask.add_argument("--plain", action="store_true", help="Skip HaxJobs identity prompt")
    ask.add_argument("--tools", help="Comma-separated tools: web_search,fetch_page,db_query")
    ask.add_argument("--max-turns", type=int, default=5)
    ask.set_defaults(func=cmd_agent_ask)

    dev = sub.add_parser("dev", help="Development utilities")
    dev.add_argument("--host", default="127.0.0.1", help="Server host")
    dev.add_argument("--port", type=int, default=8241, help="Server port")
    dev_sub = dev.add_subparsers(dest="dev_command")

    reset_cmd = dev_sub.add_parser("reset", help="Reset onboarding state (keeps provider config)")
    reset_cmd.set_defaults(func=cmd_dev_reset)

    status_cmd = dev_sub.add_parser("status", help="Show onboarding state")
    status_cmd.set_defaults(func=cmd_dev_status)

    restart_cmd = dev_sub.add_parser("restart", help="Kill current server, reset state, start fresh")
    restart_cmd.add_argument("--project-root", default=None, help="Project directory")
    restart_cmd.set_defaults(func=cmd_dev_restart)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
