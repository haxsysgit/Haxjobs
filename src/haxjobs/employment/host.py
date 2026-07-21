"""Employment host — connects the generic conversation runtime to real employment data.

Plan 003 Phase 6: provides system_prompt, context_messages, registered tools,
and active tool selection. Uses CareerStore as source.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from haxjobs.agent_core.tools import ToolDefinition, ToolRegistry
from haxjobs.employment.context import build_career_context, build_system_prompt
from haxjobs.employment.job_source import JobSourceFetcher
from haxjobs.employment.store import CareerStore
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

        # Build tool registry with inspect_job_source
        self._tool_registry = self._build_registry()

    def _build_registry(self) -> ToolRegistry:
        """Build ToolRegistry with the inspect_job_source tool."""
        from pydantic import BaseModel, Field
        from haxjobs.employment.job_source import SourceObservation

        class _InspectInput(BaseModel):
            job_ref: str = Field(
                description="The job reference number, e.g. '49' or '328'"
            )

        class _InspectOutput(BaseModel):
            ok: bool
            job_ref: int
            status: str = ""
            visible_text: str = ""
            error: str = ""

        registry = ToolRegistry()
        fetcher = self.job_source_fetcher or JobSourceFetcher()

        async def handler(input_obj: _InspectInput) -> dict[str, Any]:
            # We need a way to resolve job_ref to a fixture.
            # For v1, support refs 49 and 328 mapped to known fixture paths.
            job_ref_str = input_obj.job_ref
            fixture_path = _resolve_job_fixture_path(job_ref_str)

            if fixture_path is None:
                return SourceObservation(
                    ok=False,
                    job_ref=int(job_ref_str) if job_ref_str.isdigit() else 0,
                    source_url="",
                    status="invalid_source",
                    code="unknown_job_ref",
                    error=f"Unknown job reference: {job_ref_str}. Valid refs: 49, 328.",
                ).model_dump()

            from haxjobs.employment.fixtures import JobFixture, load_job_fixture

            job_fixture = load_job_fixture(fixture_path)
            allowed_hosts = tuple(job_fixture.allowed_source_hosts)

            observation = await fetcher.fetch(
                job_ref=job_ref_str,
                job_fixture=job_fixture,
                allowed_hosts=allowed_hosts,
            )
            return observation.model_dump()

        registry.register(
            ToolDefinition(
                name="inspect_job_source",
                description=_INSPECT_SOURCE_DESCRIPTION,
                input_model=_InspectInput,
                output_model=_InspectOutput,
                handler=handler,
            )
        )

        return registry

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
        return ("inspect_job_source",)


_INSPECT_SOURCE_DESCRIPTION = """Retrieve the current page content for a job from its trusted source URL.

Use this tool ONLY when the supplied job evidence is insufficient or may be stale.

Arguments:
  job_ref: the job reference number (a string like "49" or "328")

Returns:
  Current source evidence (visible text, status, warnings), NOT a fit judgement.
  A blocked, unavailable, or missing source is a valid and useful result.
  Never infer facts beyond what the tool actually returns."""


_JOB_FIXTURES: dict[str, str] = {
    "49": "discussion/fixtures/harness/job-49.json",
    "328": "discussion/fixtures/harness/job-328.json",
}


def _resolve_job_fixture_path(job_ref: str) -> str | None:
    """Map a job_ref string to a known fixture path. Returns None for unknown refs."""
    return _JOB_FIXTURES.get(job_ref)
