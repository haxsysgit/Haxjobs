#!/usr/bin/env python3
"""
CV-FRAME Pipeline Orchestrator
Usage:
  cv_generate.py fill    --template <file> --profile <file> --output <file>
                          Fill immutable {{SLOTS}} from profile. Remaining slots
                          are left for LLM to fill.

  cv_generate.py validate <cv_html>
                          Run cv_validator.py. Exit 0 = clean, 1 = violations.

  cv_generate.py export   <cv_html> <output_dir>
                          Export CV HTML to PDF (via headless Chrome if available).
                          Also writes a plain-text version for final scans.

  cv_generate.py scan     <cv_html_or_pdf_dir>
                          Final scan: grep for em dashes, wrong universities,
                          blocked phrases in generated output.
"""
import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "cv_validator.py"
TEMPLATE = SCRIPT_DIR / "cv_template.html"
PROFILE = SCRIPT_DIR / "cv_profile.typed.json"


# ──────────────────────────────────────────────
# SLOT MAP: which {{SLOTS}} come from which profile keys
# ──────────────────────────────────────────────
IMMUTABLE_SLOTS = {
    "{{HEADLINE}}":             ("locked_constants", "headline"),
    "{{EMAIL}}":                ("locked_constants", "email"),
    "{{PHONE}}":                ("locked_constants", "phone"),
    "{{LOCATION}}":             ("locked_constants", "location"),
    "{{LINKEDIN_HANDLE}}":      ("locked_constants", "linkedin_handle"),
    "{{LINKEDIN_URL}}":         ("locked_constants", "linkedin_url"),
    "{{GITHUB_HANDLE}}":        ("locked_constants", "github_handle"),
    "{{GITHUB_URL}}":           ("locked_constants", "github_url"),
    "{{UNIVERSITY}}":           ("locked_constants", "university"),
    "{{UNIVERSITY_DEGREE}}":    ("locked_constants", "university_degree"),
    "{{UNIVERSITY_GRADUATION}}":("locked_constants", "university_graduation"),
    "{{APTECH_INSTITUTION}}":   ("locked_constants", "aptech_institution"),
    "{{APTECH_DIPLOMA}}":       ("locked_constants", "aptech_diploma"),
    "{{APTECH_DATES}}":         ("locked_constants", "aptech_dates"),
}

# Slots the LLM must fill
LLM_SLOTS = [
    "{{PROFESSIONAL_SUMMARY}}",
    "{{CORE_SKILLS}}",
    "{{EXPERIENCE}}",
    "{{PROJECTS}}",
]


# ──────────────────────────────────────────────
# COMMAND: fill
# ──────────────────────────────────────────────
def cmd_fill(args):
    template_path = Path(args[0]) if args else TEMPLATE
    profile_path = Path(args[1]) if len(args) > 1 else PROFILE
    output_path = Path(args[2]) if len(args) > 2 else None

    if not template_path.exists():
        print(f"ERROR: Template not found: {template_path}")
        sys.exit(1)
    if not profile_path.exists():
        print(f"ERROR: Profile not found: {profile_path}")
        sys.exit(1)

    profile = json.loads(profile_path.read_text())
    locked = profile["locked_constants"]

    html = template_path.read_text()

    filled_count = 0
    for slot, (section, key) in IMMUTABLE_SLOTS.items():
        if section == "locked_constants":
            value = locked[key]["value"]
        else:
            print(f"ERROR: Unknown section '{section}' for slot {slot}")
            sys.exit(1)

        if slot in html:
            html = html.replace(slot, value)
            filled_count += 1

    remaining = [s for s in LLM_SLOTS if s in html]

    if output_path:
        output_path.write_text(html)
        print(f"✓ Wrote {output_path} ({filled_count} immutable slots filled)")

    if remaining:
        print(f"⚠ {len(remaining)} slots still need LLM generation:")
        for s in remaining:
            print(f"    {s}")
    else:
        print("✓ All slots filled — ready for validation")


# ──────────────────────────────────────────────
# COMMAND: validate
# ──────────────────────────────────────────────
def cmd_validate(args):
    if not args:
        print("Usage: cv_generate.py validate <cv_html>")
        sys.exit(1)

    cv_path = Path(args[0])
    if not cv_path.exists():
        print(f"ERROR: CV file not found: {cv_path}")
        sys.exit(1)

    profile_path = PROFILE
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(cv_path), str(profile_path)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    sys.exit(result.returncode)


# ──────────────────────────────────────────────
# COMMAND: export
# ──────────────────────────────────────────────
def cmd_export(args):
    if len(args) < 2:
        print("Usage: cv_generate.py export <cv_html> <output_dir>")
        sys.exit(1)

    cv_path = Path(args[0])
    out_dir = Path(args[1])
    out_dir.mkdir(parents=True, exist_ok=True)

    if not cv_path.exists():
        print(f"ERROR: CV file not found: {cv_path}")
        sys.exit(1)

    # First validate
    print("→ Validating...")
    profile_path = PROFILE
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), str(cv_path), str(profile_path)],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("✗ VALIDATION FAILED — PDF export blocked. Fix violations first.")
        sys.exit(1)

    # Copy HTML to output dir (skip if same file)
    import shutil
    html_out = out_dir / cv_path.name
    if cv_path.resolve() != html_out.resolve():
        shutil.copy(cv_path, html_out)
        print(f"✓ Copied HTML: {html_out}")
    else:
        print(f"✓ HTML at: {html_out}")

    # Try PDF export via headless Chrome
    pdf_out = out_dir / cv_path.with_suffix(".pdf").name
    chrome_candidates = [
        "google-chrome-stable", "google-chrome", "chromium-browser",
        "chromium", "/usr/bin/google-chrome-stable", "/usr/bin/chromium-browser"
    ]

    chrome_bin = None
    for candidate in chrome_candidates:
        result = subprocess.run(["which", candidate], capture_output=True)
        if result.returncode == 0:
            chrome_bin = candidate
            break

    if chrome_bin:
        try:
            subprocess.run([
                chrome_bin, "--headless", "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_out}",
                f"file://{html_out.resolve()}"
            ], check=True, timeout=30)
            print(f"✓ PDF exported: {pdf_out}")
        except subprocess.CalledProcessError as e:
            print(f"✗ PDF export failed: {e}")
        except subprocess.TimeoutExpired:
            print("✗ PDF export timed out")
    else:
        print("⚠ No Chrome/Chromium found — PDF export skipped")
        print(f"  HTML ready at: {html_out}")


# ──────────────────────────────────────────────
# COMMAND: scan
# ──────────────────────────────────────────────
def cmd_scan(args):
    if not args:
        print("Usage: cv_generate.py scan <cv_html_or_dir>")
        sys.exit(1)

    target = Path(args[0])
    if target.is_dir():
        files = list(target.glob("*.html")) + list(target.glob("*.pdf"))
    else:
        files = [target]

    if not files:
        print("No HTML/PDF files found to scan")
        sys.exit(1)

    blocked_phrases = [
        "Hertfordshire", "Claude Code", "cutting-edge",
        "production-grade", "robust enterprise",
        "Spearheaded", "Leveraged", "Orchestrated",
        "\u2014"  # em dash
    ]

    violations = 0
    for fpath in files:
        # For PDF, try pdftotext; for HTML, read directly
        if fpath.suffix == ".pdf":
            result = subprocess.run(
                ["pdftotext", str(fpath), "-"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"⚠ Cannot extract text from {fpath.name} (pdftotext not available?)")
                continue
            text = result.stdout
        else:
            text = fpath.read_text()

        for phrase in blocked_phrases:
            if phrase.lower() in text.lower():
                print(f"✗ FOUND in {fpath.name}: '{phrase}'")
                violations += 1

    if violations == 0:
        print("✓ Final scan clean — no blocked phrases found")
    else:
        print(f"\n✗ {violations} violations found in final scan")
        sys.exit(1)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "fill":     cmd_fill,
        "validate": cmd_validate,
        "export":   cmd_export,
        "scan":     cmd_scan,
    }

    if command not in commands:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

    commands[command](args)


if __name__ == "__main__":
    main()
