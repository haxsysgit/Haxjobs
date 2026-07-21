"""HaxJobs TUI — conversational agent chat interface."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import ClassVar

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, RichLog, Static
from textual.worker import Worker, WorkerState

from haxjobs.config import CAREER_DB_PATH
from haxjobs.employment.store import CareerStore


# ── simple message model ──


@dataclass
class Message:
    role: str  # "user" | "hax" | "tool" | "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%H:%M"))
    tool_name: str | None = None
    tool_ok: bool | None = None


# ── the chat app ──


class HaxJobsChat(App):
    """Terminal agent chat — like Pi but for your career."""

    TITLE = "HaxJobs"
    SUB_TITLE = "your career agent"
    CSS = """
    Screen {
        background: #0d1117;
    }

    #chat-scroll {
        height: 1fr;
        padding: 1 2;
        scrollbar-size: 0 0;
    }

    #input-area {
        dock: bottom;
        height: auto;
        padding: 0 2 1 2;
        background: #0d1117;
    }

    #user-input {
        border: tall $accent;
        background: #161b22;
        color: #c9d1d9;
        margin: 0;
    }

    #user-input:focus {
        border: tall $accent-lighten-2;
    }

    RichLog {
        background: #0d1117;
        border: none;
        padding: 0;
    }

    RichLog:focus {
        border: none;
    }

    .hax-name {
        color: #58a6ff;
    }

    .tool-ok {
        color: #3fb950;
    }

    .tool-fail {
        color: #f85149;
    }
    """

    BINDINGS: ClassVar = [
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    messages_list: reactive[list[Message]] = reactive(list)

    def __init__(self):
        super().__init__()
        self._store = CareerStore(str(CAREER_DB_PATH))
        self._thinking = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield VerticalScroll(RichLog(id="chat-log", highlight=True, markup=True, wrap=True), id="chat-scroll")
        with Container(id="input-area"):
            yield Input(placeholder="Message Hax...", id="user-input")
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("")

        # Greeting
        person = self._load_person_name()
        self._add_message(
            Message(
                role="hax",
                content=f"Yo, {person}. I'm Hax — your career agent. What do you want to work on?",
            )
        )

        self.query_one("#user-input", Input).focus()

    def _load_person_name(self) -> str:
        try:
            rows = self._store._conn.execute("SELECT name FROM persons LIMIT 1").fetchall()
            if rows:
                return rows[0]["name"]
        except Exception:
            pass
        return "boss"

    def _add_message(self, msg: Message) -> None:
        log = self.query_one("#chat-log", RichLog)
        ts = f"[dim]{msg.timestamp}[/dim]"

        if msg.role == "user":
            panel = Panel(
                Text(msg.content, style="white"),
                title=f"{ts} you",
                title_align="right",
                border_style="bright_blue",
                padding=(0, 1),
            )
            log.write(panel)

        elif msg.role == "hax":
            panel = Panel(
                Markdown(msg.content),
                title=f"{ts} [bold bright_green]Hax[/bold bright_green]",
                title_align="left",
                border_style="green",
                padding=(0, 1),
            )
            log.write(panel)

        elif msg.role == "tool":
            status = "[green]ok[/green]" if msg.tool_ok else "[red]failed[/red]"
            name = msg.tool_name or "tool"
            panel = Panel(
                Text(msg.content[:300] + ("..." if len(msg.content) > 300 else ""), style="dim"),
                title=f"{ts} [dim]🔧 {name} {status}[/dim]",
                title_align="left",
                border_style="yellow" if msg.tool_ok else "red",
                padding=(0, 1),
            )
            log.write(panel)

        self.messages_list.append(msg)

    def _show_thinking(self) -> None:
        self._thinking = True
        log = self.query_one("#chat-log", RichLog)
        log.write(Text("  ● ● ●", style="dim green"))
        self.query_one("#user-input", Input).disabled = True

    def _hide_thinking(self) -> None:
        self._thinking = False
        log = self.query_one("#chat-log", RichLog)
        # RichLog doesn't support removing lines easily, so we just write the response after
        self.query_one("#user-input", Input).disabled = False
        self.query_one("#user-input", Input).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""

        # Handle slash commands
        if text.startswith("/"):
            await self._handle_slash(text)
            return

        # Regular message
        self._add_message(Message(role="user", content=text))
        self._show_thinking()

        try:
            response = await self._call_agent(text)
            self._hide_thinking()
            self._add_message(Message(role="hax", content=response))
        except Exception as exc:
            self._hide_thinking()
            self._add_message(
                Message(
                    role="hax",
                    content=f"Something broke: {exc}",
                )
            )

    async def _handle_slash(self, text: str) -> None:
        cmd = text.lower().strip()

        if cmd in ("/quit", "/q", "/exit"):
            self.exit()
            return

        if cmd in ("/help", "/h"):
            help_text = (
                "**Commands:**\n"
                "- `/help` — this message\n"
                "- `/quit` — exit\n"
                "- `/profile` — show your career graph\n"
                "- `/clear` — clear chat\n\n"
                "Just type to talk to me about jobs, your career, or anything job-search related."
            )
            self._add_message(Message(role="hax", content=help_text))
            return

        if cmd in ("/profile", "/p"):
            self._add_message(Message(role="user", content=text))
            profile_text = self._build_profile_summary()
            self._add_message(Message(role="hax", content=profile_text))
            return

        if cmd in ("/clear", "/c"):
            log = self.query_one("#chat-log", RichLog)
            log.clear()
            self.messages_list = []
            return

        self._add_message(Message(role="hax", content=f"Unknown command: {text}. Try /help."))

    def _build_profile_summary(self) -> str:
        try:
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
                    skill_names = [f"{s['name']} ({s['proficiency']})" for s in skills]
                    parts.append(f"**Skills:** {', '.join(skill_names)}")
                gaps = store.list_gaps(t["track_id"])
                if gaps:
                    gap_names = [g["skill_name"] for g in gaps]
                    parts.append(f"**Gaps:** {', '.join(gap_names)}")
                parts.append("")

            return "\n".join(parts)
        except Exception as exc:
            return f"Couldn't load profile: {exc}"

    async def _call_agent(self, user_message: str) -> str:
        """Call the agent loop with the user's message."""
        from haxjobs.agent_core.runtime import run_stage0, RunRequest
        from haxjobs.agent_core.types import RunExitReason
        from haxjobs.employment.review_job import build_stage1_tools, assemble_job_review_request
        from haxjobs.model.fake import FakeModelClient

        # For now: use fake model to avoid requiring provider credentials in TUI
        # The fake model returns a canned response acknowledging the message
        fake = FakeModelClient(responses=[])

        system = self._build_system_prompt()
        request = RunRequest(system_message=system, user_message=user_message)

        result = await run_stage0(request, model=fake)

        if result.exit_reason == RunExitReason.COMPLETED:
            parts = result.response_parts or []
            if parts:
                return parts[-1].get("text", str(parts[-1]))
            return "I processed that but don't have a clear answer yet."

        return f"[Agent loop ended: {result.exit_reason.value}]"

    def _build_system_prompt(self) -> str:
        """Build the chat system prompt with Hax identity and profile context."""
        profile_blurb = ""
        try:
            store = self._store
            rows = store._conn.execute("SELECT * FROM persons LIMIT 1").fetchall()
            if rows:
                p = rows[0]
                profile_blurb = (
                    f"You are talking to {p['name']}, a {p['location']}-based "
                    f"software engineer looking for backend/AI roles. "
                    f"Salary target: {p['salary_range']}. "
                    f"Work authorization: {p['work_authorization']}."
                )
        except Exception:
            pass

        return (
            "You are Hax, a career agent. You help people find jobs, evaluate fit, "
            "prepare applications, and navigate their career.\n\n"
            "Your style: sharp, direct, like a smart friend. No corporate speak. "
            "No em dashes. Short sentences. Concrete details.\n\n"
            f"{profile_blurb}\n\n"
            "You have access to tools but only use them when asked. "
            "Respond naturally to conversation. If someone asks about their profile, "
            "tell them to try /profile."
        )


def run_tui(db_path: str | None = None) -> None:
    """Entry point for the TUI."""
    app = HaxJobsChat()
    app.run()
