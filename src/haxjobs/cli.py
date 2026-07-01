"""HaxJobs CLI."""
import argparse
import sys


def cmd_start(args):
    """Start the HaxJobs server."""
    from haxjobs.server.main import run
    run(host=args.host, port=args.port, open_browser=not args.no_browser)


def main():
    parser = argparse.ArgumentParser(
        prog="haxjobs", description="Self-hosted job search platform"
    )
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="Start the server")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8241)
    start.add_argument("--no-browser", action="store_true", help="Don't open browser")
    start.set_defaults(func=cmd_start)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
