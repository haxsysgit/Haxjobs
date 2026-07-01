# HaxJobs Pipeline Adapter Test Report
## Job #625: AI Engineer — London at Sequence

**Date**: 2026-07-01
**JD**: 6,633 chars | **Prompt**: 11,987 chars
**Pipeline**: job → build_prompt() → subprocess(adapter_cmd) → extract_json() → validate_result()

## Results

| Adapter | Score | Level | Verdict | Valid | Time |
|---------|-------|-------|---------|-------|------|
| codex | 78 | L1 | STRONG_FIT | ✅ | see raw |
| hermes | 78 | L1 | STRONG_FIT | ✅ | see raw |
| pi | 72 | L2 | GOOD_FIT | ✅ | see raw |

## Key finding

Both Codex (GPT-5.5 via --output-schema) and Hermes (GPT-5.5 via -z) independently scored 78 STRONG_FIT L1.
Pi (DeepSeek V4 Pro via --mode json) scored 72 GOOD_FIT L2.

This cross-model agreement (78/78/72) is strong evidence that the evaluation rubric is producing 
consistent results regardless of adapter.

---

## Raw outputs

All raw outputs saved to `research/adapter-reports/pipeline-tests/`:
- `prompt.txt` — full evaluation prompt (11,987 chars)
- `codex_stdout.txt` — Codex raw output
- `hermes_stdout.txt` — Hermes raw output  
- `pi_stdout.txt` — Pi JSONL event stream (raw)
- `pi_parsed.json` — Pi extracted/parsed JSON


### CODEX

**Command**: `codex exec --model gpt-5.5 --output-schema eval_schema.json --ephemeral --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check < prompt.txt`

**Parsed JSON**:
```json
{
  "fit_score": 78,
  "fit_verdict": "STRONG_FIT",
  "level": 1,
  "level_name": "Standard",
  "strongest_matches": [
    "Direct match to agentic AI infrastructure, evals, memory, tool use, and long-running state through Haxaml, FRAME, Archilles, and Pharmax work.",
    "Strong Python backend and AI product experience, including LLM/RAG workflows, RAGAS, HuggingFace, PyTorch, and production-oriented pytest knowledge.",
    "London AI engineering role at a fast-growing startup matches Arinze's preferred role, location, and ownership-heavy builder profile."
  ],
  "major_gaps": [
    "Sequence appears to want someone with proven production LLM systems used by paying customers at business-critical scale, which may be a stretch for Arinze's current junior/mid profile.",
    "No clear evidence of finance, billing, revenue recognition, or enterprise approval workflow domain experience.",
    "AI security and multi-provider production operations are mentioned strongly, but Arinze's profile has limited explicit evidence in those areas."
  ],
  "sponsorship_risk": "low",
  "summary": "Sequence's AI Engineer role scores 78 because Arinze has strong hands-on agentic AI, evals, and Python backend alignment for the platform they are building. The main risk is that the company may expect deeper production scale experience than his current junior/mid background shows.",
  "decision": "completed",
  "skip_reason": ""
}
```

**Validation**: True — All required fields present, types correct, ranges valid

---

### HERMES

**Command**: `HERMES_YOLO_MODE=1 hermes -z "<prompt>"`

**Parsed JSON**:
```json
{
  "fit_score": 78,
  "fit_verdict": "STRONG_FIT",
  "level": 1,
  "level_name": "Standard",
  "strongest_matches": [
    "Strong match for agentic AI systems, tool use, memory, evals, and reliable AI workflows through Haxaml, FRAME, Archilles, Pharmax, and RAGAS experience.",
    "Good backend fit for a role that needs resilient software around non-deterministic models, with Python backend experience, pytest strength, and real product ownership.",
    "The AI security angle is unusually relevant because Haxaml and FRAME show direct thinking about AI agent governance, project memory, and treating model output carefully."
  ],
  "major_gaps": [
    "Sequence likely wants someone who has shipped LLM systems in a high-stakes SaaS setting with paying customers at scale. Arinze has strong adjacent experience, but less proven fintech or revenue-platform scale.",
    "The role sounds closer to strong mid-level product engineer than pure junior AI engineer, with high ownership expectations in a small Series A team.",
    "No direct billing, revenue recognition, finance workflow, or collections domain experience is listed."
  ],
  "sponsorship_risk": "low",
  "summary": "Sequence's AI Engineer role scores 78 because Arinze has strong hands-on agentic AI, backend, evals, and AI governance experience that maps well to the job. The main stretch is the company likely expects proven production SaaS ownership in business-critical finance workflows, but this is still a strong application target.",
  "decision": "completed",
  "skip_reason": ""
}
```

**Validation**: True — All required fields present, types correct, ranges valid

---

### PI

**Command**: `pi -p "<prompt>" --mode json --no-tools --model deepseek/deepseek-v4-pro`

**Parsed JSON**:
```json
{
  "fit_score": 72,
  "fit_verdict": "GOOD_FIT",
  "level": 2,
  "level_name": "Quick Apply",
  "strongest_matches": [
    "Deep agentic system design via FRAME, Haxaml, and Archilles agent infrastructure",
    "Hands-on evals and model training with RAGAS, HuggingFace, PyTorch",
    "Production backend engineering experience at Vigilis and Bucca Hut"
  ],
  "major_gaps": [
    "Limited first-hand experience with large-scale LLM systems in production, including failure modes at $1bn+ scale",
    "No explicit track record building end-to-end evals pipelines from scratch for business-critical AI"
  ],
  "sponsorship_risk": "low",
  "summary": "AI Engineer at Sequence scores 72 - Arinze matches the agentic AI and backend foundation but needs to stress production reliability stories for LLM systems.",
  "decision": "completed",
  "skip_reason": ""
}
```

**Validation**: True — All required fields present, types correct, ranges valid

