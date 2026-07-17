# HaxJobs Roadmap

No numbered execution plans are active. The old plan folders were deleted because they described several superseded products at once.

## Now: reduce drift

- keep one product direction
- remove placeholder tools and stale docs
- make current limitations explicit
- keep the frontend parked while backend foundations move

## Next: native agent foundations

Design and build one coherent run lifecycle:

1. durable sessions and messages
2. run state, checkpoints, and resume
3. context selection and assembly
4. token and context-window tracking
5. compaction with explicit summaries
6. tool-call traces, latency, cost, and errors
7. isolated child runs with restricted tools
8. verification hooks and stop conditions

Do this before building the career graph. The agent needs a reliable way to carry and retrieve career context first.

## Then: CLI parity

Expose the shared actions directly:

- profile inspect and build
- job discovery
- job listing and inspection
- fit evaluation
- decisions
- pack generation and inspection
- pipeline and run status

The CLI must call `product_tools.py`, not duplicate it.

## Then: career memory

- replace the flat profile with independent career tracks and evidence-linked records
- migrate existing profile data once
- assemble context by career track and current task
- add source, confidence, verification date, privacy, and evidence metadata

## Then: employability loop

- detect recurring missing skills and evidence
- build realistic roadmaps
- find and rank resources
- suggest proof-building projects
- track progress
- reevaluate target roles after progress
- recommend the next useful move

## Then: continuous operation

- durable scheduled watches
- worker leases and retry state
- idempotent discovery runs
- notifications with approval boundaries
- one self-hosted cloud deployment path

Start with a single-user worker. Multi-tenant SaaS concerns can wait until there is another user.

## Later

- web UI over the finished actions and session API
- recruiter, applicant, and evaluator simulations
- outreach research and drafts
- approved connector queues and sends
- packaging and release work

UI polish is deliberately parked. A clean interface over unfinished actions would still be an unfinished product.
