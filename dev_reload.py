#!/usr/bin/env python3
"""Auto-reloading wrapper for haxjobs API server.
Watches server/ and profile/ directories. Restarts on any .py or .json change.
"""
import os
import sys
import time
import signal
import subprocess
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIRS = [
    "/home/hermes/haxjobs/server",
    "/home/hermes/haxjobs/profile",
]
API_SCRIPT = "/home/hermes/haxjobs/api_server.py"
API_PORT = 8800

class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start()

    def start(self):
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
            self.process.wait()
        self.process = subprocess.Popen(
            [sys.executable, API_SCRIPT],
            preexec_fn=os.setsid,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[{time.strftime('%H:%M:%S')}] API server started (PID {self.process.pid})")

    def on_any_event(self, event):
        if event.is_directory:
            return
        path = event.src_path
        if path.endswith(('.py', '.json', '.html', '.css', '.js')):
            print(f"[{time.strftime('%H:%M:%S')}] Change detected: {path}")
            self.start()

if __name__ == "__main__":
    handler = RestartHandler()
    observer = Observer()
    for d in WATCH_DIRS:
        if os.path.isdir(d):
            observer.schedule(handler, d, recursive=True)
            print(f"Watching: {d}")
    observer.start()
    print(f"Auto-reload active on port {API_PORT}. Edit files to trigger restart.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
