"""Inline prompt_toolkit terminal — submits input to a constructed session, renders events.

Plan 003 Phase 8: The terminal must only consume a constructed session and live events.
CareerStore, provider, and tools stay outside. No alternate-screen app.

Repair round 3: Terminal tracks one owner prompt task (which now includes queued work).
Yields one event-loop tick after creation so the session marks itself busy before
the next key is handled. Cooperative shutdown awaits the owner task, catches
CancelledError explicitly, then force-cancels and closes.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Callable

from prompt_toolkit import PromptSession as PTKSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

from haxjobs.agent_core.errors import safe_error
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

    Lifecycle: tracks one owner prompt task (the session runs a serial chain
    so all queued work completes inside that single task). Shutdown awaits it
    before close.
    """

    def __init__(self, session, *, show_session_info: bool = True):
        self._session = session
        self._show_session_info = show_session_info
        self._owner_task: asyncio.Task | None = None

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
            # ── Cooperative shutdown ──
            # 1. Tell session to abort the current turn
            self._session.abort()
            # 2. Await the one owner task (which includes all queued work)
            if self._owner_task is not None and not self._owner_task.done():
                try:
                    await asyncio.wait_for(self._owner_task, timeout=1.0)
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    pass
            # 3. Force-cancel if still running
            if self._owner_task is not None and not self._owner_task.done():
                self._owner_task.cancel()
                try:
                    await self._owner_task
                except asyncio.CancelledError:
                    pass
            self._owner_task = None
            unsub()
            # 4. Close session (persists final state, releases stores)
            if hasattr(self._session, "close"):
                self._session.close()

    def _on_event(self, event: LiveEvent) -> None:
        """Render a live event to the terminal."""
        try:
            if event.event_type == LiveEventType.USER_MESSAGE_ACCEPTED:
                # When turn_id is empty, this is a replacement notification
                if event.text and not event.turn_id:
                    sys.stdout.write(f"\n[{event.text}]\n")
                    sys.stdout.flush()
                # Otherwise user input is already visible

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
                # The runtime normally supplies an allowlisted message, but
                # the terminal is a second user-facing boundary: never print
                # an arbitrary exception/provider payload.
                sys.stdout.write(f"\n[{safe_error('turn')}]\n")
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
                    # When idle, this task becomes the owner and runs the serial chain
                    # (current turn + any queued work). When busy, it returns QUEUED
                    # immediately.
                    task = asyncio.ensure_future(self._session.prompt(text))

                    if self._owner_task is None or self._owner_task.done():
                        # This is the owner task — track it
                        self._owner_task = task
                        # Yield one tick so the session marks itself busy before
                        # the next key (e.g. Escape) is handled.
                        await asyncio.sleep(0)
                    # else: busy — task returns QUEUED quickly; do not track

                    task.add_done_callback(_safe_prompt_done)

                except EOFError:
                    break
                except KeyboardInterrupt:
                    break
                except Exception:
                    sys.stdout.write(f"\n[{safe_error('turn')}]\n")
                    sys.stdout.flush()


def _safe_prompt_done(t: asyncio.Task) -> None:
    """Done callback for prompt tasks — logs errors, swallows CancelledError."""
    try:
        if t.cancelled():
            return
        exc = t.exception()
        if exc is not None:
            logger.error("prompt task failed: %s", exc)
    except Exception:
        pass


async def run_terminal(
    session,
    *,
    show_session_info: bool = True,
) -> None:
    """Entry point: run the terminal client over a constructed session."""
    client = TerminalClient(session, show_session_info=show_session_info)
    await client.run()
