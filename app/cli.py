from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.models.analysis import AnalysisMetadata
from app.services.documents import extract_text_from_path
from app.services.reporting import generate_markdown_report, response_from_report
from app.services.workflow import analyze, generate_pack_from_analysis


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="haxjobs")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a CV against a pasted job description.")
    analyze_parser.add_argument("--cv", required=True, help="Path to a PDF or TXT CV file.")
    analyze_parser.add_argument("--jd-text", required=True, help="Pasted job description text.")
    analyze_parser.add_argument("--mode", default="stretch", help="Analysis mode label.")
    analyze_parser.add_argument("--json-out", help="Optional output path for the JSON report.")
    analyze_parser.add_argument("--md-out", help="Optional output path for the Markdown report.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "analyze":
        parser.error("Unsupported command.")

    cv_text = extract_text_from_path(args.cv)
    report = analyze(cv_text=cv_text, jd_text=args.jd_text, mode=args.mode)
    metadata = AnalysisMetadata(
        mode=args.mode,
        source="upload",
        cv_label=Path(args.cv).name,
        jd_label="CLI Job Description",
    )
    response = response_from_report(report, metadata=metadata)
    pack = generate_pack_from_analysis(analysis=response)

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = Path(args.json_out) if args.json_out else output_dir / "analysis.json"
    md_path = Path(args.md_out) if args.md_out else output_dir / "analysis.md"
    tailored_cv_path = output_dir / "tailored_cv.md"
    cover_letter_path = output_dir / "cover_letter.md"
    evidence_map_path = output_dir / "evidence_map.json"
    interview_notes_path = output_dir / "interview_notes.md"
    application_pack_path = output_dir / "application_pack.json"
    json_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(generate_markdown_report(report, metadata=metadata), encoding="utf-8")
    tailored_cv_path.write_text(pack.tailored_cv_markdown, encoding="utf-8")
    cover_letter_path.write_text(pack.cover_letter_markdown, encoding="utf-8")
    evidence_map_path.write_text(
        json.dumps([match.model_dump(mode="json") for match in pack.evidence_map_json], indent=2),
        encoding="utf-8",
    )
    interview_notes_path.write_text(pack.interview_notes_markdown, encoding="utf-8")
    application_pack_path.write_text(
        json.dumps(pack.application_pack_json, indent=2),
        encoding="utf-8",
    )
    print(f"JSON report written to {json_path}")
    print(f"Markdown report written to {md_path}")
    print(f"Tailored CV written to {tailored_cv_path}")
    print(f"Cover letter written to {cover_letter_path}")
    print(f"Evidence map written to {evidence_map_path}")
    print(f"Interview notes written to {interview_notes_path}")
    print(f"Application pack written to {application_pack_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
