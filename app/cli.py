from __future__ import annotations

import argparse
from pathlib import Path

from app.models.analysis import AnalysisMetadata
from app.services.documents import extract_text_from_path
from app.services.reporting import generate_markdown_report, response_from_report
from app.services.workflow import analyze


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

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = Path(args.json_out) if args.json_out else output_dir / "analysis.json"
    md_path = Path(args.md_out) if args.md_out else output_dir / "analysis.md"
    json_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")
    md_path.write_text(generate_markdown_report(report, metadata=metadata), encoding="utf-8")
    print(f"JSON report written to {json_path}")
    print(f"Markdown report written to {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
