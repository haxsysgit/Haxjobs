"""Employment host — connects the generic conversation runtime to real employment data.

Plan 003 Phase 6: provides system_prompt, context_messages, registered tools,
and active tool selection. Uses CareerStore as source.

Plan 004: tools moved to employment/tools.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from haxjobs.agent_core.tools import ToolRegistry
from haxjobs.employment.context import build_career_context, build_system_prompt
from haxjobs.employment.job_source import JobSourceFetcher
from haxjobs.employment.store import CareerStore
from haxjobs.employment.tools import build_employment_tool_registry
from haxjobs.model.types import ModelMessage


class EmploymentSetupError(Exception):
    """Raised when the career graph is not ready for conversation."""


@dataclass
class EmploymentHost:
    """Provides system prompt, career context, and active tools for each turn.

    Does not read the private migration fixture. CareerStore is the sole source.
    """

    store: CareerStore
    person_id: str
    track_id: str | None = None
    job_source_fetcher: JobSourceFetcher | None = None

    def __post_init__(self) -> None:
        # Validate that the career graph is set up
        person = self.store.get_person(self.person_id)
        if person is None:
            raise EmploymentSetupError(
                f"No person found with ID '{self.person_id}'. "
                f"Run 'haxjobs migrate' first."
            )

        # Resolve track
        if self.track_id is None:
            tracks = self.store.list_tracks(self.person_id)
            if not tracks:
                raise EmploymentSetupError(
                    f"No career tracks found for person '{self.person_id}'. "
                    f"Run 'haxjobs migrate' first."
                )
            self.track_id = tracks[0]["track_id"]

        track = self.store.get_track(self.track_id)
        if track is None:
            raise EmploymentSetupError(
                f"Career track '{self.track_id}' not found. "
                f"Run 'haxjobs migrate' first."
            )
        if track["person_id"] != self.person_id:
            raise EmploymentSetupError(
                f"Career track '{self.track_id}' belongs to person "
                f"'{track['person_id']}', not '{self.person_id}'."
            )

        # Build tool registry with employment tools
        fetcher = self.job_source_fetcher or JobSourceFetcher()
        self._tool_registry, self._active_tools = build_employment_tool_registry(
            store=self.store,
            track_id=self.track_id,
            fetcher=fetcher,
        )

    def system_prompt(self) -> str:
        return build_system_prompt()

    def context_messages(self) -> list[ModelMessage]:
        """Build volatile career context from CareerStore for the current turn."""
        person = self.store.get_person(self.person_id)
        if person is None:
            return []

        track = self.store.get_track(self.track_id)  # type: ignore[arg-type]
        if track is None:
            return []

        skills_flat = self.store.list_skills(self.track_id)  # type: ignore[arg-type]
        skills_tree = self.store.get_skill_tree(self.track_id)  # type: ignore[arg-type]

        # Build evidence by skill
        evidence_by_skill: dict[str, list[dict]] = {}
        for skill in skills_flat:
            evidence_by_skill[skill["skill_id"]] = self.store.list_evidence_for_skill(
                skill["skill_id"]
            )

        gaps = self.store.list_gaps(self.track_id)  # type: ignore[arg-type]
        constraints = self.store.list_hard_constraints(self.track_id)  # type: ignore[arg-type]
        preferences = self.store.list_preferences(self.track_id)  # type: ignore[arg-type]

        return build_career_context(
            person=person,
            track=track,
            skills_tree=skills_tree,
            skills_flat=skills_flat,
            evidence_by_skill=evidence_by_skill,
            gaps=gaps,
            constraints=constraints,
            preferences=preferences,
        )

    def registered_tools(self) -> ToolRegistry:
        return self._tool_registry

    def active_tool_names(self) -> tuple[str, ...]:
        return self._active_tools
