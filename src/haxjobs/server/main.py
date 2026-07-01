"""Run the FastAPI server."""
import threading
import webbrowser
import uvicorn


def run(host: str = "127.0.0.1", port: int = 8241, open_browser: bool = True):
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run("haxjobs.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
