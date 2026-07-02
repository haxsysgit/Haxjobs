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

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
