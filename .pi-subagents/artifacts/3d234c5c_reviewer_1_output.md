## Review

- **Correct:** Stage 0 is explicitly one observed model call with no tools, database, sessions, scheduler, skills, or sub-agents (`discussion/004-minimal-job-native-harness.md:228-242`).
- **Correct:** Stage 1 adds only a bounded loop and `inspect_job_source(job_ref)` (`discussion/004-minimal-job-native-harness.md:244-256`).
- **Correct:** Python, Pydantic, `uv`, pytest, redacted JSONL, and human rubrics are the decided floor; agent frameworks and telemetry platforms remain excluded (`discussion/005-implementation-stack-observability-and-verification.md:40-45`, `92-103`).
- **Correct:** Repository configuration already names the exact model IDs `deepseek-v4-pro` and `deepseek-v4-flash` (`src/haxjobs/features/setup/service.py:9-14`).
- **Blocker:** Execution cannot start from the present checkout. It has 269 status entries: 221 tracked modifications/deletions and 48 untracked files. Required discussion inputs are untracked, while agent implementation files are modified. No staged files exist.
- **Blocker:** A worktree created from current `HEAD` (`54231871520a3c34227fe3468318f44074d76de5`) would not contain the untracked design documents or current tracked edits. Copying, stashing, or silently committing them would violate isolation and ownership.
- **Note:** `discussion/006-pi-inspired-haxjobs-architecture.md` remains `status: discussing`; its coding workspaces, shell, compaction, extensions, and other future features must not enter Stage 0 or Stage 1.
- **Note:** Several existing worktrees are marked prunable. They should not be reused or automatically removed.

# Execution protocol

## 1. Immutable baseline gate

Before allocating a writer:

1. Record:
   - `BASE_SHA`
   - branch
   - `git status --porcelain=v2 -z --untracked-files=all` SHA-256
   - `git worktree list --porcelain`
   - staged-file count
2. Compare every dirty path with:
   - the stage’s in-scope paths
   - required design inputs
   - planned test and diagram paths
3. Proceed only if:
   - the source tree is clean; or
   - dirty paths are disjoint and the operator explicitly approves the committed `BASE_SHA`.
4. Stop if any required input is untracked or differs from `BASE_SHA`.

Never run `git stash`, `git reset`, `git clean`, automatic commits, or copy uncommitted files into the worktree.

**Current result:** STOP. The operator must first provide a committed baseline containing the intended discussion and source state.

## 2. Model-availability gate

The orchestration runtime must allocate these exact canonical IDs:

| Role | Exact model | Count | Permissions |
|---|---|---:|---|
| Plan and implementation writer | `deepseek-v4-pro` | 1 | Write only inside isolated worktree |
| Architecture/scope reviewer | `deepseek-v4-flash` | 1 | Read-only |
| Correctness/security/tests reviewer | `deepseek-v4-flash` | 1 | Read-only |
| Deliverables/manual CLI/drawio reviewer | `deepseek-v4-flash` | 1 | Read-only |

For every lease:

1. Send a unique nonce probe.
2. Require successful completion and scheduler metadata reporting the exact canonical model ID.
3. Record provider, canonical ID, lease/session ID, timestamp, nonce hash, and fallback status.
4. Require four distinct session IDs and three independent reviewer contexts.
5. Reject aliases, automatic fallback, substituted models, or self-reported identity without runtime metadata.

If a model is unavailable or rate-limited, pause or stop. Never substitute another model.

## 3. Worktree and writer isolation

After baseline approval:

```bash
git rev-parse --verify "$BASE_SHA^{commit}"
git show "$BASE_SHA:<required-path>"
git branch --list "exec/stage-${STAGE}-${RUN_ID}"
git worktree list --porcelain
git worktree add -b "exec/stage-${STAGE}-${RUN_ID}" \
  "/tmp/haxjobs-stage-${STAGE}-${RUN_ID}" "$BASE_SHA"
```

Requirements:

- Unique new path and branch.
- The DeepSeek v4 Pro writer’s working directory is the new worktree.
- Repository credentials, `.env`, `state/`, `intake/`, and `~/.haxjobs/haxjobs.toml` are not exposed to the writer.
- Only the Pro writer may alter tracked repository content.
- The controller may create worktrees and external evidence artifacts but may not author repository files.
- The writer commits each candidate and leaves no staged or unstaged tracked changes.
- Do not push or merge automatically.

The implementation plan must be written by that same Pro writer using the template requirements at `.agents/skills/improve/references/plan-template.md:1-11,27-40,85-146`. Number allocation is deterministic: reserve one greater than the highest plan number at `BASE_SHA`.

## 4. Review/fix/re-review flow

For each candidate SHA:

1. Controller runs objective validation and creates a redacted evidence report.
2. Create three fresh read-only reviewer contexts at the same candidate SHA.
3. Do not provide one reviewer’s findings to another.
4. Reviewer scopes:
   - **Architecture/scope:** decided Stage 0/1 boundaries, shared Python boundary, no speculative features.
   - **Correctness/security/tests:** contracts, trace redaction, failures, limits, source retrieval, prompt-injection handling, and test sufficiency.
   - **Deliverables/manual CLI/drawio:** CLI behavior, run receipts, docs, diagram source/PNG, and evidence completeness.
5. Each reviewer returns `approve`, `changes-required`, or `blocked`, plus evidence-backed findings.
6. Any blocker or major finding returns to the same Pro writer.
7. The controller may consolidate findings but may not modify code.
8. The Pro writer fixes, commits a new candidate SHA, and reruns every validation.
9. All three roles re-review the new SHA in fresh independent contexts.
10. Final acceptance requires three approvals on the identical candidate SHA.

Stop after three fix rounds, on conflicting product requirements, scope expansion, model substitution, or a verification failure that remains after two reasonable fixes.

# Stage 0 contract

## Required behavior

Expose:

```bash
uv run haxjobs experiment review-job \
  --job job-49 \
  --career-fixture "$HAXJOBS_CAREER_FIXTURE" \
  --output-dir "$RUN_DIR/job-49"
```

And the same command for `job-328`.

Stage 0 must provide:

- One provider-neutral model boundary and one scripted fake.
- One stable Hax instruction block.
- One job-review flow instruction block.
- Source-labelled user request, career fixture, and job fixture.
- Exactly one model request and no tool schemas.
- Configured real provider with no fallback.
- Versioned, redacted JSONL events.
- Run ID, timing, exact model ID, instruction/fixture hashes, usage when available, safe stop reason, and sanitized failures.
- Local answer and human-rubric artifacts with restrictive permissions.
- Checked-in non-private Job 49 and Job 328 fixtures.
- A schema/example for the private career fixture, but no real profile or credentials.
- No database, sessions, retrieval, compaction, scheduler, skills, sub-agents, web UI, or new agent framework.

## Stage 0 tests

Deterministically prove:

- Fixture validation and source labels.
- Stable context ordering.
- Hidden old evaluations never enter model context.
- Fake model receives one request with zero tools.
- Complete trace on success and sanitized trace on failure.
- Trace contains hashes/IDs rather than raw profile or credentials.
- Job 49 fixture retains IT-support evidence and unknown sponsorship.
- Job 328 contains only supported title/URL evidence.
- Tests perform no network calls.
- CLI runs without source edits.

## Stage 0 manual checks

Use `umask 077` and an output directory outside the repository.

1. Run Job 49 first.
2. Confirm conversational negative recommendation, IT-support classification, concrete supplied responsibilities, and unknown sponsorship.
3. Run Job 328 second.
4. Confirm insufficient evidence, no unsupported Django/FastAPI/TypeScript/cloud/company/sponsorship claims, and source inspection as the next useful check.
5. A human completes and signs both rubric files.
6. Evidence records only run IDs, hashes, verdicts, and artifact permissions—not answers or private fixture content.

## Stage 0 machine-checkable done criteria

- Full pytest suite exits 0.
- Python compilation exits 0.
- `bash -n cron/run_pipeline.sh` exits 0.
- Frontend typecheck, lint, and build pass if present at the approved baseline.
- Focused Stage 0 tests pass with no network.
- CLI help shows `experiment review-job`.
- Trace schema validation passes for both live runs.
- Both human rubrics are complete and accepted.
- No tool-call event exists in either Stage 0 trace.
- No private fixture, answer, credential, or runtime artifact is tracked.
- Diagram checks below pass.
- Changed paths equal the approved allowlist.
- Candidate worktree is clean and has no staged files.
- Source checkout status fingerprint is unchanged.
- Three reviewers approve the same candidate SHA.

# Stage 1 contract

Stage 1 begins from the accepted Stage 0 SHA in a new worktree. Stage 0’s Job 328 rubric must explicitly record source inspection as the demonstrated missing capability.

Expose:

```bash
uv run haxjobs experiment review-job \
  --job job-328 \
  --career-fixture "$HAXJOBS_CAREER_FIXTURE" \
  --allow-source-inspection \
  --output-dir "$RUN_DIR/job-328"
```

## Required behavior

Add only:

- Bounded model → tool → model loop.
- Typed tool schema and strict registry.
- Exactly one active tool: `inspect_job_source(job_ref)`.
- `job_ref` must resolve through the active fixture; the model cannot supply an arbitrary URL.
- Unknown tools and malformed arguments become structured failures.
- Tool results preserve call order.
- Step-limit termination is explicit and traced.
- Source results contain job reference, source type, final URL, UTC observation time, status, bounded content, warnings, and structured failure.
- Redirects, private/local targets, oversized responses, unsupported schemes, and timeouts are rejected safely.
- Fetched content is labelled untrusted evidence and cannot override instructions.
- Retrieval failure, blocking, or a closed role remains a valid result.

Reuse or harden the existing public-fetch boundary rather than creating a second fetch stack (`src/haxjobs/agent/tools_web.py:77-106`).

## Stage 1 tests

Add deterministic tests for:

- Job 49 completes without calling the source tool when supplied evidence is enough.
- Job 328 requests `inspect_job_source` when enabled.
- Exactly one tool is exposed.
- Arbitrary URLs cannot be passed.
- Unknown tools and malformed arguments do not execute.
- Private/local URLs and unsafe redirects are blocked.
- Blocked, gone, timeout, and successful retrieval results are structured.
- Content and output limits apply.
- Prompt-injection text remains untrusted tool content.
- Tool results precede the next model request.
- Step limit always stops.
- Unit tests use fake HTTP/model boundaries and no network.

## Stage 1 manual checks

Run Job 49 and Job 328 with `--allow-source-inspection`.

- Job 49 trace should show zero source calls.
- Job 328 trace should show one `inspect_job_source` call for `job-328`.
- If retrieval succeeds, the answer must use only returned evidence.
- If blocked, gone, or failed, the answer must preserve uncertainty.
- Human rubrics accept either retrieval outcome when handled truthfully.

## Stage 1 machine-checkable done criteria

All Stage 0 engineering gates continue to pass, plus:

- Stage 1 base is the accepted Stage 0 SHA.
- Exactly one tool schema is exposed.
- All source-tool and bounded-loop tests pass.
- No unit test performs network access.
- Job 49 manual trace has zero tool calls.
- Job 328 manual trace has exactly one correctly scoped tool call.
- Both Stage 1 human rubrics are accepted.
- No new product actions, database schema, workflow engine, coding tools, scheduler, sessions, or UI are introduced.
- Updated diagram checks pass.
- Three reviewers approve the same Stage 1 candidate SHA.
- Candidate and source checkout have no staged files.

# Current-state draw.io and PNG gate

Use one current-state pair, updated after each stage:

- `diagram/003-minimal-job-native-harness-current-state.drawio`
- `diagram/003-minimal-job-native-harness-current-state.png`

Also update `diagram/README.md` and a companion current-state Markdown document.

Checks:

1. `drawio --version` reports `30.2.4`.
2. XML parses with `xml.etree.ElementTree`.
3. Root uses `mxfile host="drawio" version="30.2.4"`.
4. Page is `1400x900`.
5. Five to seven swimlane groups, at most 35 cells.
6. Every edge has child `<mxGeometry relative="1" as="geometry" />`.
7. Inter-group edges use orthogonal routing and width 2 or 3.
8. No custom diagram ID, raw `<font>` markup, file paths in nodes, or `.mmd` files.
9. Stage 0 diagram shows no tools.
10. Stage 1 shows only `inspect_job_source`, the bounded loop, and trace/evaluation path.
11. Real export succeeds:

```bash
drawio --export --format png \
  --output /tmp/haxjobs-diagram-check.png \
  diagram/003-minimal-job-native-harness-current-state.drawio
test -s /tmp/haxjobs-diagram-check.png
file /tmp/haxjobs-diagram-check.png | grep -q 'PNG image data'
compare -metric AE \
  diagram/003-minimal-job-native-harness-current-state.png \
  /tmp/haxjobs-diagram-check.png null: 2>/tmp/haxjobs-diagram-ae
test "$(cat /tmp/haxjobs-diagram-ae)" = "0"
```

# Evidence report schema

The controller stores this outside the repository and validates it before review:

```json
{
  "schemaVersion": 1,
  "stage": 0,
  "runId": "opaque-id",
  "baseSha": "40-char SHA",
  "candidateSha": "40-char SHA",
  "models": {
    "writer": {
      "canonicalId": "deepseek-v4-pro",
      "sessionId": "opaque-id",
      "fallbackUsed": false
    },
    "reviewers": [
      {
        "role": "architecture-scope",
        "canonicalId": "deepseek-v4-flash",
        "sessionId": "opaque-id",
        "verdict": "approve"
      }
    ]
  },
  "changedFiles": [
    {
      "path": "relative/path",
      "status": "added|modified|deleted",
      "sha256": "hex"
    }
  ],
  "testsAddedOrUpdated": ["relative/path"],
  "commandsRun": [
    {
      "command": "redacted command",
      "exitCode": 0,
      "result": "passed",
      "summary": "non-sensitive summary"
    }
  ],
  "validationOutput": ["concise non-sensitive result"],
  "manualRuns": [
    {
      "fixture": "job-49",
      "runId": "opaque-id",
      "traceSha256": "hex",
      "rubricSha256": "hex",
      "verdict": "accepted"
    }
  ],
  "diagram": {
    "drawioPath": "relative/path",
    "pngPath": "relative/path",
    "drawioVersion": "30.2.4",
    "cells": 0,
    "vertices": 0,
    "edges": 0,
    "pixelDifference": 0
  },
  "reviewRounds": [
    {
      "candidateSha": "40-char SHA",
      "approvals": 3,
      "blockers": 0
    }
  ],
  "residualRisks": [],
  "outOfScopeFiles": [],
  "noStagedFiles": true,
  "sourceStatusUnchanged": true
}
```

Raw prompts, answers, private career material, environment values, authorization headers, and provider credentials must never enter this report.