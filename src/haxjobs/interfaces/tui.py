"""HaxJobs TUI — Textual app for browsing the career graph."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static, Tree
from textual.binding import Binding

from haxjobs.config import CAREER_DB_PATH
from haxjobs.employment.store import CareerStore


class _ProfileOverview(Screen):
    """Top-level screen: person + track list."""

    BINDINGS = [
        Binding("q", "quit", "Quit", key_display="q"),
        Binding("escape", "app.pop_screen", "Back", key_display="Esc"),
        Binding("enter", "drill_track", "Track Detail", key_display="Enter"),
    ]

    CSS_PATH = None

    def __init__(self, db_path: str):
        super().__init__()
        self._db_path = db_path

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="person_info")
        yield Static("", id="track_hint")
        yield Tree("Career Tracks", id="track_tree")
        yield Footer()

    def on_mount(self) -> None:
        store = CareerStore(self._db_path)
        try:
            person_rows = store._conn.execute("SELECT * FROM persons").fetchall()
            self._track_map: dict[str, str] = {}

            if not person_rows:
                self.query_one("#person_info", Static).update(
                    "[yellow]No profile data. Run 'haxjobs profile migrate' first.[/yellow]"
                )
                return

            prow = person_rows[0]
            self.query_one("#person_info", Static).update(
                f"[bold]Person:[/bold] {prow['name']} ({prow['person_id']})  |  "
                f"Location: {prow['location']}  |  Salary: {prow['salary_range']}"
            )

            tree = self.query_one("#track_tree", Tree)
            tracks = store.list_tracks(prow["person_id"])
            for track in tracks:
                node = tree.root.add(track["name"])
                node.data = track["track_id"]
                self._track_map[track["name"]] = track["track_id"]

            tree.focus()

            self.query_one("#track_hint", Static).update(
                "Use ↑↓ to navigate tracks, Enter to drill into track detail, q to quit"
            )
        finally:
            store.close()

    def action_drill_track(self) -> None:
        tree = self.query_one("#track_tree", Tree)
        node = tree.cursor_node
        if node is not None and node.data:
            self.app.push_screen(
                _TrackDetail(node.data, node.label.plain if node.label else "Track", self._db_path)
            )


class _TrackDetail(Screen):
    """Track detail screen: skills, gaps, constraints, preferences."""

    BINDINGS = [
        Binding("q", "quit", "Quit", key_display="q"),
        Binding("escape", "app.pop_screen", "Back", key_display="Esc"),
        Binding("tab", "focus_next", "Next", key_display="Tab"),
        Binding("enter", "drill_skill", "Skill Detail", key_display="Enter"),
    ]

    CSS_PATH = None

    def __init__(self, track_id: str, track_name: str, db_path: str):
        super().__init__()
        self._track_id = track_id
        self._track_name = track_name
        self._db_path = db_path

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(f"[bold]Track:[/bold] {self._track_name} ({self._track_id})")
        with Container(id="track_sections"):
            yield Static("[bold]Skills:[/bold]")
            yield Tree("Skills", id="skill_tree")
            yield Static("[bold]Skill Gaps:[/bold]")
            yield DataTable(id="gaps_table")
            yield Static("[bold]Hard Constraints:[/bold]")
            yield DataTable(id="constraints_table")
            yield Static("[bold]Preferences:[/bold]")
            yield DataTable(id="prefs_table")
        yield Footer()

    def on_mount(self) -> None:
        store = CareerStore(self._db_path)
        try:
            # Skills tree
            skill_tree = store.get_skill_tree(self._track_id)
            tree = self.query_one("#skill_tree", Tree)
            self._skill_map: dict[str, str] = {}
            for sid, node in skill_tree.items():
                self._add_skill_node(tree.root, node)

            # Gaps
            gaps = store.list_gaps(self._track_id)
            gt = self.query_one("#gaps_table", DataTable)
            gt.add_columns("Skill", "Target")
            for g in gaps:
                gt.add_row(g["skill_name"], g["target_proficiency"])

            # Constraints
            constraints = store.list_hard_constraints(self._track_id)
            ct = self.query_one("#constraints_table", DataTable)
            ct.add_column("Constraint")
            for c in constraints:
                ct.add_row(c["constraint_text"])

            # Preferences
            prefs = store.list_preferences(self._track_id)
            pt = self.query_one("#prefs_table", DataTable)
            pt.add_columns("Key", "Value", "Weight")
            for p in prefs:
                pt.add_row(p["key"], p["value"], p["weight"])
        finally:
            store.close()

    def _add_skill_node(self, parent, node: dict) -> None:
        prof_icon = {
            "primary": "★",
            "strong": "●",
            "working": "○",
            "learning": "·",
        }.get(node.get("proficiency", "working"), "?")
        label = f"{prof_icon} {node['name']} [{node['proficiency']}]"
        child = parent.add(label)
        child.data = node["skill_id"]
        self._skill_map[node["name"]] = node["skill_id"]
        for sub in node.get("children", []):
            self._add_skill_node(child, sub)

    def action_drill_skill(self) -> None:
        tree = self.query_one("#skill_tree", Tree)
        node = tree.cursor_node
        if node is not None and node.data:
            self.app.push_screen(
                _SkillDetail(node.data, node.label.plain if node.label else "Skill", self._db_path)
            )


class _SkillDetail(Screen):
    """Skill detail screen: metadata + linked evidence."""

    BINDINGS = [
        Binding("q", "quit", "Quit", key_display="q"),
        Binding("escape", "app.pop_screen", "Back", key_display="Esc"),
    ]

    CSS_PATH = None

    def __init__(self, skill_id: str, skill_label: str, db_path: str):
        super().__init__()
        self._skill_id = skill_id
        self._skill_label = skill_label
        self._db_path = db_path

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="skill_info")
        yield Static("[bold]Linked Evidence:[/bold]")
        yield DataTable(id="evidence_table")
        yield Footer()

    def on_mount(self) -> None:
        store = CareerStore(self._db_path)
        try:
            skill = store.get_skill(self._skill_id)
            if skill:
                self.query_one("#skill_info", Static).update(
                    f"[bold]Skill:[/bold] {skill['name']} [{skill['proficiency']}] "
                    f"({skill['skill_id']})"
                )
            evidence = store.list_evidence_for_skill(self._skill_id)
            et = self.query_one("#evidence_table", DataTable)
            et.add_columns("Label", "Source", "Verified")
            for ev in evidence:
                et.add_row(
                    ev["label"],
                    ev["source"],
                    ev.get("verified_at", "never")[:19] if ev.get("verified_at") else "never",
                )
        finally:
            store.close()


class HaxJobsTUI(App):
    """Career graph TUI browser."""

    TITLE = "HaxJobs Career Graph"
    SUB_TITLE = "Profile Browser"
    CSS = """
    Screen {
        background: #1a1a2e;
    }
    """

    def __init__(self, db_path: str | None = None):
        super().__init__()
        self._db_path = str(db_path or CAREER_DB_PATH)

    def on_mount(self) -> None:
        self.push_screen(_ProfileOverview(self._db_path))


def run_tui(db_path: str | None = None) -> None:
    """Entry point for the TUI."""
    app = HaxJobsTUI(db_path)
    app.run()
