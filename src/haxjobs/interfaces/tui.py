"""HaxJobs TUI — terminal agent harness chat interface.

Mirrors Pi's pattern: multi-line editor at bottom, conversation scrollback above,
tool calls inline with status, continuous stream not message bubbles."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import ClassVar

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.reactive import var
from textual.widgets import Footer, Header, RichLog, TextArea, Static

from haxjobs.config import CAREER_DB_PATH


# ── agent call will be wired after TUI structure is solid ──


class HaxJobsChat(App):
    """Terminal agent harness — like Pi but for your job search."""

    TITLE = "HaxJobs"
    SUB_TITLE = "career agent"

    CSS = """
    Screen {
        background: $surface;
    }

    #chat-scroll {
        height: 1fr;
        padding: 0 1;
        scrollbar-size: 0 0;
        border: none;
    }

    #chat-scroll:focus {
        border: none;
    }

    #input-container {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 12;
        padding: 0 1 1 1;
        background: $surface;
    }

    #user-input {
        border: tall $accent;
        background: $panel;
        color: $text;
        margin: 0;
    }

    #user-input:focus {
        border: tall $accent-lighten-1;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: $accent 30%;
        color: $text-muted;
        padding: 0 1;
    }

    RichLog {
        background: $surface;
        border: none;
        padding: 0;
    }

    RichLog:focus {
        border: none;
    }
    """

    BINDINGS: ClassVar = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
        Binding("escape", "abort", "Abort agent", show=False),
    ]

    thinking: var[bool] = var(False)

    def __init__(self):
        super().__init__()
        self._store = None  # CareerStore, lazy init
        self._agent_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(
            RichLog(id="chat-log", highlight=True, markup=True, wrap=True),
            id="chat-scroll",
        )
        with Container(id="input-container"):
            yield TextArea(id="user-input", language=None, show_line_numbers=False)
        yield Static("ctrl+enter — send  |  ctrl+c — quit  |  /help for commands", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("")

        person = self._load_person_name()
        greeting = (
            f"Yo, {person}. I'm Hax. Your career agent.\n\n"
            "I can help with job discovery, evaluating roles, building application packs, "
            "and figuring out what you need to land the next one.\n\n"
            "Type /help to see what I can do."
        )
        self._write_hax(greeting)

        # Focus the input
        self.query_one("#user-input", TextArea).focus()

    def _load_person_name(self) -> str:
        try:
            from haxjobs.employment.store import CareerStore
            if self._store is None:
                self._store = CareerStore(str(CAREER_DB_PATH))
            rows = self._store._conn.execute("SELECT name FROM persons LIMIT 1").fetchall()
            if rows:
                return rows[0]["name"]
        except Exception:
            pass
        return "boss"

    def _log(self, *args, **kwargs) -> None:
        """Write to the chat log."""
        self.query_one("#chat-log", RichLog).write(*args, **kwargs)

    def _write_user(self, text: str) -> None:
        """Write a user message to the log."""
        ts = datetime.now(timezone.utc).strftime("%H:%M")
        self._log(Text(f"\n▸ you  {ts}", style="bold bright_blue"))
        self._log(Text(text, style="white"))

    def _write_hax(self, text: str) -> None:
        """Write a Hax response to the log."""
        ts = datetime.now(timezone.utc).strftime("%H:%M")
        self._log(Text(f"\nHax  {ts}", style="bold bright_green"))
        self._log(Markdown(text))

    def _write_tool(self, name: str, ok: bool, detail: str = "") -> None:
        """Write a tool call to the log."""
        ts = datetime.now(timezone.utc).strftime("%H:%M")
        status = "✓" if ok else "✗"
        color = "green" if ok else "red"
        self._log(Text(f"\n  🔧 {name}  {status}  {ts}", style=f"dim {color}"))
        if detail:
            self._log(Text(f"     {detail[:300]}", style="dim"))

    def _write_error(self, text: str) -> None:
        """Write an error to the log."""
        self._log(Text(f"\n[error]{text}[/error]"))

    # ── actions ──

    def action_quit(self) -> None:
        self.exit()

    def action_abort(self) -> None:
        """Abort a running agent call."""
        if self._agent_running:
            self._agent_running = False
            self._log(Text("\n[dim]Aborted.[/dim]", style="dim"))
            self._set_thinking(False)
        else:
            # If no agent running, pass escape to TextArea
            self.query_one("#user-input", TextArea).focus()

    # ── thinking state ──

    def _set_thinking(self, on: bool) -> None:
        self.thinking = on
        ta = self.query_one("#user-input", TextArea)
        ta.disabled = on
        status = self.query_one("#status-bar", Static)
        if on:
            status.update("[dim]● Hax is thinking...[/dim]  |  esc — abort")
        else:
            status.update("ctrl+enter — send  |  ctrl+c — quit  |  /help for commands")

    # ── input handling ──

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Check for Ctrl+Enter to submit."""
        # TextArea doesn't have a direct "submit" event like Input.
        # We detect Ctrl+Enter via a key binding on the TextArea.
        pass


    # ── on_key for ctrl+enter detection ──

    def on_key(self, event) -> None:
        """Detect ctrl+enter on the TextArea to submit."""
        from textual.keys import Keys

        if event.key == Keys.Enter and event.ctrl:
            ta = self.query_one("#user-input", TextArea)
            text = ta.text.strip()
            if not text:
                return

            ta.text = ""
            self._handle_message(text)
            event.prevent_default()
            event.stop()

    def _handle_message(self, text: str) -> None:
        """Process a user message."""
        if text.startswith("/"):
            self._handle_slash(text)
        else:
            self._write_user(text)
            # Start async agent call
            asyncio.create_task(self._run_agent(text))

    def _handle_slash(self, text: str) -> None:
        """Handle slash commands."""
        cmd = text.lower().strip()

        if cmd in ("/quit", "/q", "/exit"):
            self.exit()
            return

        if cmd in ("/help", "/h"):
            help_text = (
                "**Commands**\n\n"
                "`/help` — this message\n"
                "`/profile` — show your career graph\n"
                "`/quit` — exit\n"
                "`/clear` — clear the scrollback\n\n"
                "Just talk to me normally. I can help with job discovery, "
                "evaluating roles, building packs, and figuring out your next move."
            )
            self._write_hax(help_text)
            return

        if cmd in ("/profile", "/p"):
            self._write_user(text)
            profile_text = self._build_profile_summary()
            self._write_hax(profile_text)
            return

        if cmd in ("/clear", "/c"):
            log = self.query_one("#chat-log", RichLog)
            log.clear()
            return

        self._write_hax(f"Unknown command: `{text}`. Try `/help`.")

    def _build_profile_summary(self) -> str:
        """Build a markdown profile summary from the career graph."""
        try:
            from haxjobs.employment.store import CareerStore

            if self._store is None:
                self._store = CareerStore(str(CAREER_DB_PATH))
            store = self._store

            rows = store._conn.execute("SELECT * FROM persons LIMIT 1").fetchall()
            if not rows:
                return "No profile data. Run `haxjobs migrate` first."

            person = rows[0]
            tracks = store.list_tracks(person["person_id"])
            parts = [
                f"## {person['name']}",
                f"**Location:** {person['location']}",
                f"**Salary range:** {person['salary_range']}",
                f"**Work authorization:** {person['work_authorization']}",
                "",
            ]

            for t in tracks:
                parts.append(f"### {t['name']}")
                skills = store.list_skills(t["track_id"])
                if skills:
                    icons = {"primary": "★", "strong": "●", "working": "○", "learning": "·"}
                    skill_parts = [f"{icons.get(s['proficiency'], '?')} {s['name']} ({s['proficiency']})" for s in skills]
                    parts.append(f"**Skills:** {', '.join(skill_parts)}")
                gaps = store.list_gaps(t["track_id"])
                if gaps:
                    gap_names = [f"{g['skill_name']} → {g['target_proficiency']}" for g in gaps]
                    parts.append(f"**Gaps:** {', '.join(gap_names)}")
                constraints = store.list_hard_constraints(t["track_id"])
                if constraints:
                    c_list = [c["constraint_text"] for c in constraints]
                    parts.append(f"**Hard constraints:** {', '.join(c_list)}")
                preferences = store.list_preferences(t["track_id"])
                if preferences:
                    p_list = [f"{p['key']}: {p['value']}" for p in preferences]
                    parts.append(f"**Preferences:** {', '.join(p_list)}")
                parts.append("")

            return "\n".join(parts)
        except Exception as exc:
            return f"Couldn't load profile: {exc}"

    async def _run_agent(self, user_message: str) -> None:
        """Run the agent loop in response to a user message."""
        self._agent_running = True
        self._set_thinking(True)

        try:
            # For now: simulated agent call that keeps the TUI responsive
            # Will be wired to actual agent loop separately
            await asyncio.sleep(1)

            response = self._build_fake_response(user_message)
            self._write_hax(response)

        except Exception as exc:
            self._write_error(f"Agent call failed: {exc}")
        finally:
            self._agent_running = False
            self._set_thinking(False)

    def _build_fake_response(self, user_message: str) -> str:
        """Build a placeholder response. Replace with real agent call."""
        person = self._load_person_name()
        lower = user_message.lower()

        if any(w in lower for w in ("job", "role", "position", "find", "search", "discover")):
            return (
                "Good question. Job discovery is one of the next things we're building. "
                "Right now I can see your career graph and help you think through what roles "
                "fit, but the actual job scraping and evaluation pipeline isn't wired up yet.\n\n"
                "What kind of role are you looking for? Backend? AI/ML? Platform?"
            )
        if any(w in lower for w in ("profile", "cv", "resume", "skill", "career graph")):
            return self._build_profile_summary()
        if any(w in lower for w in ("hello", "hey", "hi", "yo", "what's up")):
            return f"Yo, {person}. What are we working on today?"

        return (
            f"I hear you, {person}. We're still in the early stages — the career graph "
            "is built, the agent loop works, and now we're wiring up discovery, evaluation, "
            "and packs. What you're asking about isn't fully ready yet, but it's coming.\n\n"
            "For now, try `/profile` to see your career graph, or `/help` for what's available."
        )


def run_tui(db_path: str | None = None) -> None:
    """Entry point for the TUI."""
    app = HaxJobsChat()
    app.run()
