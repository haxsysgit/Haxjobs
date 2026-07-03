"""Run the FastAPI server."""
import argparse
import threading
import webbrowser

import uvicorn


def run(host: str = "127.0.0.1", port: int = 8241, open_browser: bool = True, reload: bool = False):
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run("haxjobs.app:app", host=host, port=port, reload=reload)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8241)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload", action="store_true", help="Reload backend on code changes")
    args = parser.parse_args()
    run(host=args.host, port=args.port, open_browser=not args.no_browser, reload=args.reload)


if __name__ == "__main__":
    main()
