#!/usr/bin/env python3
"""Import the ignored local HaxJobs profile JSON into the development database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from haxjobs_api.database import Base, SessionLocal, engine
from haxjobs_api.services.profile_import import import_profile_from_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a local HaxJobs profile JSON file.")
    parser.add_argument(
        "profile_json",
        nargs="?",
        default="data/private/arinze_profile.local.json",
        help="Path to ignored local profile JSON. Defaults to data/private/arinze_profile.local.json",
    )
    args = parser.parse_args()

    profile_path = Path(args.profile_json)
    if not profile_path.exists():
        raise SystemExit(f"Profile JSON not found: {profile_path}")

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        result = import_profile_from_json(session, profile_path)

    print(f"Imported profile: {result.profile.full_name} ({result.profile.id})")
    print(f"Facts imported: {result.facts_imported}")
    print(f"Saved answers imported: {result.saved_answers_imported}")


if __name__ == "__main__":
    main()
