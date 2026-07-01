# HaxJobs Roadmap

The current product architecture is documented in `PRODUCT_ARCHITECTURE.md`.
Implementation plans are tracked in `plans/README.md`.

## Completed (Waves 1-5)

All 29 plans from waves 1-5 are DONE. These built the pipeline infrastructure:
discovery scrapers, config-driven classification, pluggable evaluation,
auto-pack generation, cycle reports, and multi-agent adapter research.

## Wave 6 — Docs Alignment (current)

Aligning all documentation to the new product architecture.

## Wave 6B — Product Foundation (next)

Make HaxJobs a usable product:
- Direct LLM API evaluation (replace agent subprocess)
- Onboarding wizard (CV upload → profile extraction → guided questions)
- Profile evolution (fields that update based on usage)
- Decision loop (apply/skip/reject from dashboard)

See `plans/README.md` for specific plan numbers when created.

## Wave 7 — Learning & Outreach

Make HaxJobs smart:
- Learning engine (processes decisions, evolves preferences)
- Outreach engine (hiring manager discovery, message generation)
- DB lifecycle (cycle tracking, job archiving, cleanup)

## Wave 8 — Polish & Ship

Make HaxJobs a product anyone can use:
- Product packaging (`pip install haxjobs`)
- Web search discovery (beyond ATS scrapers)
- Comprehensive testing
