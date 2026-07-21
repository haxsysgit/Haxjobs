"""Inline prompt_toolkit terminal — submits input to a constructed session, renders events.

Plan 003 Phase 8: The terminal must only consume a constructed session and live events.
CareerStore, provider, and tools stay outside. No alternate-screen app.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import traceback
from typing import Callable

from prompt_toolkit import PromptSession as PTKSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from haxjobs.agent_core.live_events import LiveEvent, LiveEventType

logger = logging.getLogger(__name__)

_STYLE = Style.from_dict({
    "status": "italic",
    "tool": "fg:yellow",
    "error": "fg:red",
    "info": "fg:cyan",
})


class TerminalClient:
    """Thin terminal that submits input to a session and renders live events.

    Import rules:
    - Must not import CareerStore, provider clients, or employment handlers.
    - Only imports the session protocol and live event types.
    """

    def __init__(self, session, *, show_session_info: bool = True):
        self._session = session
        self._show_session_info = show_session_info
        self._prompt_tasks: set[asyncio.Task] = set()

    async def run(self) -> None:
        """Run the interactive terminal loop."""
        if self._show_session_info:
            print(f"\nSession ID: {self._session.session_id}")
            print(f"Resume: haxjobs chat --resume {self._session.session_id}")
            print("Type your message. Enter to submit, Ctrl+J for newline, Escape to interrupt.")
            print("Ctrl+C to clear (or exit if empty), Ctrl+D to exit when empty.\n")

        # Subscribe to live events
        unsub = self._session.subscribe(self._on_event)

        try:
            await self._input_loop()
        finally:
            # Abort any ongoing turn and settle prompt tasks before exit
            self._session.abort()
            for task in list(self._prompt_tasks):
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except (asyncio.CancelledError, Exception):
                        pass
            self._prompt_tasks.clear()
            unsub()

    def _on_event(self, event: LiveEvent) -> None:
        """Render a live event to the terminal."""
        try:
            if event.event_type == LiveEventType.USER_MESSAGE_ACCEPTED:
                pass  # Input is already visible

            elif event.event_type == LiveEventType.TURN_STARTED:
                pass  # Implicit

            elif event.event_type == LiveEventType.ASSISTANT_STARTED:
                sys.stdout.write("\n")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.ASSISTANT_DELTA:
                sys.stdout.write(event.delta)
                sys.stdout.flush()

            elif event.event_type == LiveEventType.ASSISTANT_COMPLETED:
                sys.stdout.write("\n")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.TOOL_REQUESTED:
                pass  # Implicit — tool lifecycle below

            elif event.event_type == LiveEventType.TOOL_STARTED:
                sys.stdout.write(f"\n  [{event.tool_name}] ...")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.TOOL_PROGRESS:
                if event.text:
                    sys.stdout.write(f" {event.text}")
                else:
                    sys.stdout.write(".")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.TOOL_COMPLETED:
                dur = f" ({event.tool_duration_ms:.0f}ms)" if event.tool_duration_ms else ""
                sys.stdout.write(f" ok{dur}\n")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.TOOL_FAILED:
                sys.stdout.write(f" FAILED: {event.error_code or event.error or 'error'}\n")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.TURN_INTERRUPTED:
                sys.stdout.write("\n[interrupted]\n")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.TURN_FAILED:
                sys.stdout.write(f"\n[{event.error or 'failed'}]\n")
                sys.stdout.flush()

            elif event.event_type == LiveEventType.TURN_COMPLETED:
                pass

            elif event.event_type == LiveEventType.SESSION_SETTLED:
                pass  # Prompt will appear

        except Exception:
            pass  # Terminal rendering errors must not break the session

    async def _input_loop(self) -> None:
        """Read user input and submit to the session."""
        bindings = KeyBindings()

        @bindings.add("escape")
        def _(event):
            """Escape: interrupt the active turn."""
            self._session.abort()
            # Don't clear the buffer — keep what user typed

        @bindings.add("c-c")
        def _(event):
            """Ctrl+C: clear if non-empty, exit if empty and idle."""
            buffer = event.app.current_buffer
            if buffer.text:
                buffer.text = ""
            else:
                event.app.exit()

        @bindings.add("c-d")
        def _(event):
            """Ctrl+D: exit when editor is empty."""
            buffer = event.app.current_buffer
            if not buffer.text:
                event.app.exit()

        @bindings.add("c-j")
        def _(event):
            """Ctrl+J: insert newline (guaranteed multiline binding)."""
            event.app.current_buffer.insert_text("\n")

        ptk_session = PTKSession(
            key_bindings=bindings,
            style=_STYLE,
            multiline=False,
            wrap_lines=True,
            complete_while_typing=False,
        )

        with patch_stdout():
            while True:
                try:
                    text = await ptk_session.prompt_async(
                        "> ",
                    )
                    if text is None:
                        break
                    text = text.strip()
                    if not text:
                        continue

                    # Fire session.prompt as a task — do NOT await it inline.
                    # This keeps the input loop active so Escape can call abort
                    # and Enter can use the one-slot busy policy.
                    task = asyncio.ensure_future(self._session.prompt(text))
                    self._prompt_tasks.add(task)
                    task.add_done_callback(lambda t: self._prompt_tasks.discard(t))
                    task.add_done_callback(
                        lambda t: logger.error("prompt task failed: %s", t.exception())
                        if t.exception() else None
                    )

                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
                except Exception as exc:
                    sys.stdout.write(f"\n[{exc}]\n")
                    sys.stdout.flush()


async def run_terminal(
    session,
    *,
    show_session_info: bool = True,
) -> None:
    """Entry point: run the terminal client over a constructed session."""
    client = TerminalClient(session, show_session_info=show_session_info)
    await client.run()
