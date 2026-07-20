# HaxJobs design diagrams

This directory holds the visual record of the greenfield HaxJobs design discussion.

Each decided stage should gain:

- an editable `.drawio` source
- a PNG preview when local export works
- a short entry here explaining what the diagram represents
- a link from the relevant `discussion/` note

The diagrams record current decisions. They are not permanently final and may change when later design or implementation exposes a better model.

## Diagrams

### 001. Hax goal and rudimentary run lifecycle

- Source: [001-hax-goal-and-run-lifecycle.drawio](001-hax-goal-and-run-lifecycle.drawio)
- Preview: [001-hax-goal-and-run-lifecycle.png](001-hax-goal-and-run-lifecycle.png)
- Discussion: [../discussion/001-hax-goal-and-run-lifecycle.md](../discussion/001-hax-goal-and-run-lifecycle.md)

Shows Hax as a natural conversational friend over the whole employment process. A mixed user message is understood freely, composed into suitable work, executed through HaxJobs, returned as immediate or later updates, and fed back into future strategy.

### 002. Standing commitment lifecycle

- Source: [002-standing-commitment-lifecycle.drawio](002-standing-commitment-lifecycle.drawio)
- Preview: [002-standing-commitment-lifecycle.png](002-standing-commitment-lifecycle.png)
- Discussion: [../discussion/002-durable-work-and-continuity.md](../discussion/002-durable-work-and-continuity.md)

Shows the difference between:

- the user's request
- the standing promise Hax remembers
- the cadence that says when work is due
- the scheduler that wakes HaxJobs
- one bounded check attempt
- the saved result and curated user update

The main rule is: continuous work means remembering to return, not keeping one process alive forever.

### 003. Stage 0 Observed Job Review

- Source: [003-stage0-observed-job-review.drawio](003-stage0-observed-job-review.drawio)
- Preview: [003-stage0-observed-job-review.png](003-stage0-observed-job-review.png)
- Report: [../docs/implementation-reports/001-stage0-observed-job-review.md](../docs/implementation-reports/001-stage0-observed-job-review.md)

The five-layer Stage 0 architecture: CLI experiment, employment context, no-tool agent core, model boundary, and local artifacts with human verification.

### 004. Stage 1 Source-Inspection Loop

- Source: [004-stage1-source-inspection-loop.drawio](004-stage1-source-inspection-loop.drawio)
- Preview: [004-stage1-source-inspection-loop.png](004-stage1-source-inspection-loop.png)
- Report: [../docs/implementation-reports/002-stage1-source-inspection-loop.md](../docs/implementation-reports/002-stage1-source-inspection-loop.md)

The seven-group Stage 1 architecture: CLI experiment, employment context, bounded agent core (Stage 0 or loop), model boundary, active tool registry, trusted source retrieval, and local evidence with verification. Zero tools in Stage 0, exactly one active tool (`inspect_job_source`) in Stage 1. The model provides a job_ref string; the employment layer resolves it to a trusted fixture URL. Fetched content is untrusted tool output — never system instructions.
