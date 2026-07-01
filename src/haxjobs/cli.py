"""HaxJobs CLI."""
import argparse
import sys


def cmd_start(args):
    """Start the HaxJobs server."""
    import uvicorn
    print("Starting HaxJobs on http://{}:{}".format(args.host, args.port))
    uvicorn.run("haxjobs.api_server:app", host=args.host, port=args.port, reload=False)


def main():
    parser = argparse.ArgumentParser(
        prog="haxjobs", description="Self-hosted job search platform"
    )
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="Start the server")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8241)
    start.set_defaults(func=cmd_start)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
