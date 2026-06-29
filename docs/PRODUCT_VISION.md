# HaxJobs Product Vision

## What HaxJobs is

HaxJobs is an autonomous job discovery and application pipeline. It finds jobs, classifies them against Arinze's profile, evaluates fit with configurable agents, generates application packs from reusable templates, and produces cycle reports — all with minimal human intervention.

The user sets up their profile once in `haxjobs.toml`. The pipeline runs. The user reviews the output report. That's the loop.

## Why this exists

Job searching is repetitive: find roles → judge fit → tailor materials → track everything. Most of this is mechanical enough to automate. HaxJobs automates the mechanical parts so Arinze can spend time on the parts that need human judgment: reviewing strong-fit packs, making final application decisions, and doing actual interviews.

## The pipeline

```
DISCOVERY → CLASSIFICATION → EVALUATION → PACK GENERATION → REPORT
```

1. **Discovery** — scrapers find jobs. Hooks dedup, blacklist, and filter. All raw jobs stored.
2. **Classification** — profile-driven from `haxjobs.toml`. No hardcoded taxonomy.
3. **Evaluation** — pluggable agents score fit and assign levels (L1-L4).
4. **Pack Generation** — L1/L2 auto-fill role templates. L3/L4 go to report for manual review.
5. **Report** — markdown digest of every evaluated job with links, scores, pack paths. Delivered via configured channels.

Manual job submissions (paste a JD link) go through the same pipeline — dedup, classify, evaluate, report.

## Product principles

### 1. Autonomous by default

The pipeline should run without human prompts. Discovery, classification, evaluation, and L1/L2 pack generation happen automatically. The user's job is to review output, not drive the process.

### 2. Profile-driven, not hardcoded

Every pipeline decision comes from the user's profile in `haxjobs.toml` — role preferences, work modes, target levels, blacklisted companies, evaluation agent choice. Nothing is hardcoded in Python.

### 3. Truthful over optimized

Packs use real profile evidence. The gap-note system admits what Arinze doesn't know instead of fabricating experience. The 3-agent simulation loop (future) stress-tests packs against real recruiter-style questioning.

### 4. DB is the source of truth

Jobs, evaluations, pack paths, and report content live in SQLite. No scattered JSON files. No dual-write split-brain.

### 5. Simple output, not a dashboard cockpit

The end product is a markdown report: evaluated jobs, links, scores, pack paths. The user reads it, decides what to act on. The dashboard is for browsing and manual review — not the primary interface.

## What HaxJobs is not

- Not a spam bot or auto-applier
- Not a fake-experience generator
- Not a generic resume builder
- Not a heavy CRM
- Not a replacement for Hermes — Hermes is one evaluation agent option
- Not a platform that submits applications without user review

## Future: 3-Agent Simulation Loop (v0.3)

After packs are generated, a coaching simulation stress-tests them:

- **Recruiter Agent** — plays hiring manager, asks real questions about the application
- **Applicant Agent** — answers as Arinze, using only profile evidence
- **Evaluator Agent** — judges whether the application improved, separates safe edits from fabrication

This is coaching: it helps Arinze prepare, not fake feedback. Output: simulation.json per job pack.

## Core success metric

HaxJobs succeeds if Arinze can run one command (or cron fires) and get a report that tells him: what was discovered, how it fits, where the packs are, and what's worth acting on today.
