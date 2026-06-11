#!/usr/bin/env python3
"""
CV Profile Helper — interactive tool for maintaining cv_profile.typed.json.
Usage:
  cv_profile_helper.py list-projects
  cv_profile_helper.py add-project <key>
  cv_profile_helper.py edit-project <key>
  cv_profile_helper.py list-locked
  cv_profile_helper.py edit-locked <key>
"""
import json
import sys
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parent / "cv_profile.typed.json"


def load():
    if not PROFILE_PATH.exists():
        print(f"ERROR: Profile not found at {PROFILE_PATH}")
        sys.exit(1)
    return json.loads(PROFILE_PATH.read_text())


def save(profile):
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
    print(f"✓ Saved {PROFILE_PATH}")


def cmd_list_projects():
    profile = load()
    registry = profile["project_registry"]
    print(f"\n{len(registry)} projects registered:\n")
    for key, proj in registry.items():
        url = proj.get("repo_url") or "(no repo)"
        visible = "PUBLIC" if proj.get("include_url_in_cv") else "PRIVATE"
        print(f"  [{key}] {proj['display_name']}")
        print(f"        {proj['subtitle']}")
        print(f"        Stack: {', '.join(proj.get('tech_stack', []))}")
        print(f"        Repo:  {url} ({visible})")
        print(f"        Evidence: {len(proj.get('public_evidence', []))} allowed bullets")
        blocked = proj.get("forbidden_claims", [])
        if blocked:
            print(f"        Blocked: {len(blocked)} forbidden claims")
        print()


def cmd_add_project(key):
    if not key:
        print("Usage: cv_profile_helper.py add-project <key>")
        sys.exit(1)

    profile = load()
    if key in profile["project_registry"]:
        print(f"ERROR: Project '{key}' already exists. Use edit-project instead.")
        sys.exit(1)

    print(f"\nAdding new project: {key}")
    print("Enter values (Ctrl+C to cancel):\n")

    try:
        display_name = input("  Display name: ").strip()
        subtitle = input("  Subtitle: ").strip()
        tech_stack = [t.strip() for t in input("  Tech stack (comma-separated): ").split(",") if t.strip()]
        repo_url = input("  Repo URL (or leave blank): ").strip() or None
        pypi_url = input("  PyPI URL (or leave blank): ").strip() or None
        is_public = input("  Include repo URL in CV? (y/n): ").strip().lower() == "y"

        print("\n  Add public_evidence bullets (one per line, empty line to finish):")
        evidence = []
        while True:
            line = input("    > ").strip()
            if not line:
                break
            evidence.append(line)

        print("\n  Add forbidden_claims (one per line, empty line to finish):")
        forbidden = []
        while True:
            line = input("    > ").strip()
            if not line:
                break
            forbidden.append(line)

        profile["project_registry"][key] = {
            "display_name": display_name,
            "subtitle": subtitle,
            "repo_url": repo_url,
            "repo_visibility": "public" if is_public else "private",
            "include_url_in_cv": is_public,
            "pypi_url": pypi_url,
            "tech_stack": tech_stack,
            "public_evidence": evidence,
            "forbidden_claims": forbidden,
        }

        save(profile)
        print(f"\n✓ Project '{key}' added to registry")

    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        sys.exit(0)


def cmd_edit_project(key):
    if not key:
        print("Usage: cv_profile_helper.py edit-project <key>")
        sys.exit(1)

    profile = load()
    if key not in profile["project_registry"]:
        print(f"ERROR: Project '{key}' not found. Use list-projects to see available keys.")
        sys.exit(1)

    proj = profile["project_registry"][key]
    print(f"\nEditing: [{key}] {proj['display_name']}")
    print(f"  Subtitle: {proj['subtitle']}")
    print(f"  Stack: {', '.join(proj.get('tech_stack', []))}")
    print(f"  Repo URL: {proj.get('repo_url') or '(none)'}")
    print(f"  Include in CV: {proj.get('include_url_in_cv')}")
    print(f"\n  public_evidence ({len(proj.get('public_evidence', []))} bullets):")
    for i, bullet in enumerate(proj.get("public_evidence", [])):
        print(f"    [{i}] {bullet}")
    print(f"\n  forbidden_claims ({len(proj.get('forbidden_claims', []))}):")
    for i, claim in enumerate(proj.get("forbidden_claims", [])):
        print(f"    [{i}] {claim}")

    print("\nWhat would you like to edit?")
    print("  1. Toggle include_url_in_cv")
    print("  2. Add public_evidence bullet")
    print("  3. Remove public_evidence bullet")
    print("  4. Add forbidden_claim")
    print("  5. Remove forbidden_claim")
    print("  6. Edit tech stack")
    print("  0. Cancel")

    try:
        choice = input("\n  Choice: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        return

    if choice == "1":
        current = proj.get("include_url_in_cv", False)
        proj["include_url_in_cv"] = not current
        proj["repo_visibility"] = "public" if not current else "private"
        print(f"  Toggled: include_url_in_cv = {proj['include_url_in_cv']}")
    elif choice == "2":
        bullet = input("  New bullet: ").strip()
        if bullet:
            proj.setdefault("public_evidence", []).append(bullet)
            print(f"  Added bullet: {bullet}")
    elif choice == "3":
        idx = input("  Index to remove: ").strip()
        try:
            idx = int(idx)
            removed = proj["public_evidence"].pop(idx)
            print(f"  Removed: {removed}")
        except (ValueError, IndexError):
            print("  Invalid index")
            return
    elif choice == "4":
        claim = input("  New forbidden claim: ").strip()
        if claim:
            proj.setdefault("forbidden_claims", []).append(claim)
            print(f"  Added claim: {claim}")
    elif choice == "5":
        idx = input("  Index to remove: ").strip()
        try:
            idx = int(idx)
            removed = proj["forbidden_claims"].pop(idx)
            print(f"  Removed: {removed}")
        except (ValueError, IndexError):
            print("  Invalid index")
            return
    elif choice == "6":
        stack = input("  New tech stack (comma-separated): ").strip()
        proj["tech_stack"] = [t.strip() for t in stack.split(",") if t.strip()]
        print(f"  Updated stack: {', '.join(proj['tech_stack'])}")
    elif choice == "0":
        print("Cancelled.")
        return
    else:
        print(f"Unknown choice: {choice}")
        return

    save(profile)


def cmd_list_locked():
    profile = load()
    locked = profile["locked_constants"]
    print(f"\n{len(locked)} locked constants:\n")
    for key, spec in locked.items():
        print(f"  [{key}] = \"{spec['value']}\"")


def cmd_edit_locked(key):
    if not key:
        print("Usage: cv_profile_helper.py edit-locked <key>")
        sys.exit(1)

    profile = load()
    if key not in profile["locked_constants"]:
        print(f"ERROR: Locked constant '{key}' not found. Use list-locked to see available keys.")
        sys.exit(1)

    current = profile["locked_constants"][key]["value"]
    print(f"  [{key}] = \"{current}\"")
    new_val = input("  New value: ").strip()
    if new_val and new_val != current:
        profile["locked_constants"][key]["value"] = new_val
        save(profile)
        print(f"  Updated: \"{current}\" → \"{new_val}\"")
    else:
        print("  No change.")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else None

    commands = {
        "list-projects": lambda: cmd_list_projects(),
        "add-project":   lambda: cmd_add_project(key),
        "edit-project":  lambda: cmd_edit_project(key),
        "list-locked":   lambda: cmd_list_locked(),
        "edit-locked":   lambda: cmd_edit_locked(key),
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

    commands[command]()


if __name__ == "__main__":
    main()
