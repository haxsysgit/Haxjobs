#!/usr/bin/env python3
"""
Dashboard asset integrity checker.
Verifies that index.html references actually exist on disk.
Prevents the "stale index" bug where Vite builds new hashes but index.html
still references old ones.

Usage:
  python3 check_dashboard.py           # Check only, exit 1 if stale
  python3 check_dashboard.py --fix     # Auto-update index.html with correct hashes
  python3 check_dashboard.py --quiet   # No output, exit code only (for cron/CI)
"""
import os, re, sys, glob

DASHBOARD_DIR = "/home/hermes/haxjobs/dashboard"
INDEX_PATH = os.path.join(DASHBOARD_DIR, "index.html")
ASSETS_DIR = os.path.join(DASHBOARD_DIR, "assets")


def extract_references(html: str) -> list[tuple[str, str]]:
    """Extract (type, path) for all script src and link href references."""
    refs = []
    for m in re.finditer(r'<script[^>]+src="([^"]+)"', html):
        refs.append(("script", m.group(1)))
    for m in re.finditer(r'<link[^>]+href="([^"]+)"', html):
        refs.append(("stylesheet", m.group(1)))
    return refs


def get_actual_assets() -> dict[str, str]:
    """Scan assets dir, return {extension: filename} for JS and CSS."""
    actual = {}
    for f in glob.glob(os.path.join(ASSETS_DIR, "*")):
        ext = os.path.splitext(f)[1]
        if ext in (".js", ".css"):
            actual[ext] = os.path.basename(f)
    return actual


def check():
    """Returns (ok: bool, issues: list[str], fix_map: dict[old_path, new_path])."""
    if not os.path.exists(INDEX_PATH):
        return False, ["index.html not found at " + INDEX_PATH], {}

    html = open(INDEX_PATH).read()
    refs = extract_references(html)
    actual = get_actual_assets()
    issues = []
    fix_map = {}

    for kind, path in refs:
        full = os.path.join(DASHBOARD_DIR, path.lstrip("/"))
        if os.path.exists(full):
            continue

        # Figure out what extension we're looking for
        ext = os.path.splitext(path)[1]
        if ext in actual:
            correct = f"/assets/{actual[ext]}"
            issues.append(
                f"STALE {kind}: index.html references {path} but file does not exist. "
                f"Available: /assets/{actual[ext]}"
            )
            fix_map[path] = correct
        else:
            # Neither the referenced file nor any replacement exists
            issues.append(
                f"MISSING {kind}: index.html references {path} but no {ext} file "
                f"exists in assets/ at all"
            )

    # Also warn about orphaned assets (files in assets/ not referenced)
    asset_paths = {r[1] for r in refs}
    for ext, fname in actual.items():
        asset_ref = f"/assets/{fname}"
        if asset_ref not in asset_paths:
            issues.append(
                f"ORPHAN: {asset_ref} exists on disk but is not referenced in index.html"
            )

    return len([i for i in issues if i.startswith("STALE") or i.startswith("MISSING")]) == 0, issues, fix_map


def fix(fix_map: dict[str, str]):
    """Apply fix_map replacements to index.html."""
    html = open(INDEX_PATH).read()
    for old, new in fix_map.items():
        html = html.replace(old, new)
    backup = INDEX_PATH + ".bak"
    os.rename(INDEX_PATH, backup)
    with open(INDEX_PATH, "w") as f:
        f.write(html)
    print(f"Fixed {len(fix_map)} reference(s). Backup at {backup}")


if __name__ == "__main__":
    quiet = "--quiet" in sys.argv
    do_fix = "--fix" in sys.argv

    ok, issues, fix_map = check()

    if not quiet:
        if not issues:
            print("✓ Dashboard assets OK — all references resolve")
        else:
            for issue in issues:
                prefix = "  ✗" if issue.startswith("STALE") or issue.startswith("MISSING") else "  ⚠"
                print(f"{prefix} {issue}")

    if do_fix and fix_map:
        fix(fix_map)
        # Re-check after fix
        ok2, issues2, _ = check()
        if not quiet:
            if not issues2:
                print("✓ Fix applied — all references now resolve")
            else:
                for i in issues2:
                    print(f"  ⚠ {i}")
        sys.exit(0 if ok2 else 1)

    sys.exit(0 if ok else 1)
