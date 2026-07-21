"""Profile CLI handlers — thin, delegate to store and schema."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from haxjobs.config import CAREER_DB_PATH
from haxjobs.employment.schema import (
    CareerTrack,
    EvidenceItem,
    HardConstraint,
    Skill,
    SkillEvidence,
    SkillGap,
)
from haxjobs.employment.store import CareerStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _open_store() -> CareerStore:
    return CareerStore(CAREER_DB_PATH)


def cmd_profile_show(args) -> None:
    """Show career graph overview using Rich formatting."""
    from rich.console import Console
    from rich.table import Table
    from rich.tree import Tree

    store = _open_store()
    try:
        console = Console()

        person_rows = store._conn.execute("SELECT * FROM persons").fetchall()
        if not person_rows:
            console.print("[yellow]No profile data found. Run 'haxjobs profile migrate' first.[/yellow]")
            return

        for prow in person_rows:
            console.print(f"\n[bold]Person:[/bold] {prow['name']} ({prow['person_id']})")
            console.print(f"  Location: {prow['location']}")
            console.print(f"  Salary: {prow['salary_range']}")

            tracks = store.list_tracks(prow["person_id"])
            for track in tracks:
                console.print(f"\n  [bold cyan]Track:[/bold cyan] {track['name']} ({track['track_id']})")

                # Constraints
                constraints = store.list_hard_constraints(track["track_id"])
                if constraints:
                    ct = Table(title="Hard Constraints", show_header=True, header_style="bold")
                    ct.add_column("Constraint")
                    for c in constraints:
                        ct.add_row(c["constraint_text"])
                    console.print(ct)

                # Skills tree
                skill_tree = store.get_skill_tree(track["track_id"])
                if skill_tree:
                    console.print("[bold]Skills:[/bold]")
                    for sid, node in skill_tree.items():
                        _print_skill_tree(console, node, "")

                # Gaps
                gaps = store.list_gaps(track["track_id"])
                if gaps:
                    gt = Table(title="Skill Gaps", show_header=True, header_style="bold")
                    gt.add_column("Skill")
                    gt.add_column("Target")
                    for g in gaps:
                        gt.add_row(g["skill_name"], g["target_proficiency"])
                    console.print(gt)

                # Preferences
                prefs = store.list_preferences(track["track_id"])
                if prefs:
                    pt = Table(title="Preferences", show_header=True, header_style="bold")
                    pt.add_column("Key")
                    pt.add_column("Value")
                    pt.add_column("Weight")
                    for p in prefs:
                        pt.add_row(p["key"], p["value"], p["weight"])
                    console.print(pt)
    finally:
        store.close()


def _print_skill_tree(console, node: dict, prefix: str) -> None:
    """Recursively print a skill tree."""
    prof_color = {
        "primary": "green",
        "strong": "blue",
        "working": "yellow",
        "learning": "dim",
    }.get(node.get("proficiency", "working"), "white")
    console.print(
        f"{prefix}{node['name']} [{prof_color}]{node['proficiency']}[/{prof_color}]"
    )
    for child in node.get("children", []):
        _print_skill_tree(console, child, prefix + "  ")


def cmd_profile_track_add(args) -> None:
    store = _open_store()
    try:
        track = CareerTrack(
            track_id=_short_id("track"),
            person_id=args.person_id,
            name=args.name,
            created_at=_now(),
            updated_at=_now(),
        )
        store.upsert_track(track)
        print(f"Added track: {track.name} ({track.track_id})")
    finally:
        store.close()


def cmd_profile_skill_add(args) -> None:
    store = _open_store()
    try:
        skill = Skill(
            skill_id=_short_id("skill"),
            track_id=args.track_id,
            name=args.name,
            parent_skill_id=args.parent_skill_id or None,
            proficiency=args.proficiency,
            created_at=_now(),
        )
        store.upsert_skill(skill)
        print(f"Added skill: {skill.name} [{skill.proficiency}] ({skill.skill_id})")
    finally:
        store.close()


def cmd_profile_evidence_add(args) -> None:
    store = _open_store()
    try:
        ev = EvidenceItem(
            evidence_id=_short_id("ev"),
            label=args.label,
            source=args.source,
            content=args.content,
            verified_at=_now(),
            privacy_level="public_ok",
            created_at=_now(),
        )
        store.upsert_evidence(ev)
        print(f"Added evidence: {ev.label} ({ev.evidence_id})")
        if args.skill_id:
            store.link_skill_evidence(SkillEvidence(
                skill_id=args.skill_id,
                evidence_id=ev.evidence_id,
            ))
            print(f"  Linked to skill: {args.skill_id}")
    finally:
        store.close()


def cmd_profile_gap_add(args) -> None:
    store = _open_store()
    try:
        gap = SkillGap(
            gap_id=_short_id("gap"),
            track_id=args.track_id,
            skill_name=args.skill_name,
            target_proficiency=args.proficiency,
            note=args.note,
            created_at=_now(),
        )
        store.upsert_gap(gap)
        print(f"Added gap: {gap.skill_name} → {gap.target_proficiency} ({gap.gap_id})")
    finally:
        store.close()


def cmd_profile_constraint_add(args) -> None:
    store = _open_store()
    try:
        hc = HardConstraint(
            constraint_id=_short_id("hc"),
            track_id=args.track_id,
            constraint_text=args.text,
            created_at=_now(),
        )
        store.upsert_hard_constraint(hc)
        print(f"Added constraint: {hc.constraint_text[:60]}... ({hc.constraint_id})")
    finally:
        store.close()


def cmd_profile_migrate(args) -> None:
    from haxjobs.employment.migration import migrate_cli_entrypoint
    store = migrate_cli_entrypoint(args.fixture)
    if store is not None:
        store.close()
