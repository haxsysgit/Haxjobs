"""Reusable CV variant registry for HaxJobs.

A per-job application pack should not generate or own a new CV. It should point
to one reusable CV variant chosen by the role-family classifier.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


Registry = dict[str, Any]


def load_cv_variant_registry(path: str | Path) -> Registry:
    """Load and validate the CV variant registry JSON."""
    registry_path = Path(path)
    registry = json.loads(registry_path.read_text())

    if "default_variant" not in registry:
        raise ValueError("CV variant registry needs default_variant")
    if "variants" not in registry or not isinstance(registry["variants"], dict):
        raise ValueError("CV variant registry needs variants object")
    if registry["default_variant"] not in registry["variants"]:
        raise ValueError("default_variant must exist in variants")

    for variant_id, variant in registry["variants"].items():
        required = {"label", "role_family", "relative_dir", "pdf", "html"}
        missing = required - set(variant)
        if missing:
            raise ValueError(f"{variant_id} missing required fields: {sorted(missing)}")
        if variant["role_family"] != variant_id:
            raise ValueError(f"{variant_id} role_family must match variant id")
        if "Tailored" in variant["pdf"] or "Tailored" in variant["html"]:
            raise ValueError(f"{variant_id} uses stale per-job Tailored naming")

    return registry


def resolve_cv_variant(variant_id: str | None, registry: Registry) -> dict[str, Any]:
    """Resolve a CV variant id, falling back to the registry default."""
    requested = variant_id or registry["default_variant"]
    if requested not in registry["variants"]:
        requested = registry["default_variant"]

    variant = dict(registry["variants"][requested])
    variant["variant_id"] = requested
    return variant


def build_pack_cv_metadata(recommended_cv_variant: str | None, registry: Registry) -> dict[str, Any]:
    """Build the CV reference block stored in per-job pack metadata.

    The pack references the selected CV variant. It does not claim ownership of
    the CV file and should not create job-specific CV names.
    """
    variant = resolve_cv_variant(recommended_cv_variant, registry)
    relative_dir = variant["relative_dir"]
    return {
        "recommended_cv_variant": variant["variant_id"],
        "role_family": variant["role_family"],
        "cv_variant_dir": relative_dir,
        "cv_pdf": f"{relative_dir}/{variant['pdf']}",
        "cv_html": f"{relative_dir}/{variant['html']}",
        "pack_owns_cv": False,
    }
