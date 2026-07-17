# Implementation Plan

## Goal
Correct the two-stage plan set so it is executable from an approved clean baseline, preserves open decisions, and has one unambiguous evidence/review sequence.

## Review Findings

1. **BLOCKER — The required source context is missing.**
   - File: `/home/hax/haxjobs/context.md`
   - Evidence: Reading the user-specified path returned `ENOENT`, and a repository search found no `context.md`.
   - Impact: This review can compare the named plans with discussions 004–006 and the research study, but cannot attest consistency with the missing input.
   - Recommended correction: Restore/provide `context.md`, or explicitly remove it as an input and rerun the plan-set review. Do not infer its contents.

2. **BLOCKER — `plans/` contains four executable-looking plans, not the claimed two.**
   - Files: `plans/README.md`, `plans/001-build-stage-0-observed-job-review.md`, `plans/001-stage0-observed-job-review.md`, `plans/002-build-stage-1-source-tool-loop.md`, `plans/002-stage1-source-inspection-loop.md`
   - Evidence: `plans/README.md` links the latter pair and says there are only two plans, while the former pair remains alongside them with conflicting filenames, module layouts, report names, diagram names, branches, risk ratings, and verification commands.
   - Impact: An executor can select the wrong Plan 001/002, and the two Plan 002 variants depend on different Plan 001 filenames and deliverables.
   - Recommended correction: Keep one canonical 001 and one canonical 002. Delete the superseded pair, or move them outside `plans/` with an unmistakable `REJECTED/SUPERSEDED — DO NOT EXECUTE` header. Update all links after choosing canonical filenames.

3. **BLOCKER — The plans convert open architecture recommendations into accepted decisions without approval evidence.**
   - Files: `discussion/006-pi-inspired-haxjobs-architecture.md`; `discussion/research/2026-07-17-pi-hermes-job-native-harness-study.md`; `plans/README.md`; `plans/001-stage0-observed-job-review.md`
   - Evidence: Discussion 006 has `status: discussing`; its ledger leaves “Pi as architecture reference” and “Physical package split” open. The research study explicitly says recommendations do not become accepted decisions and lists the four-layer/one-package choice under open decisions. The README says the current request accepts that split, and Plan 001 tells the executor to update the decision ledger during implementation.
   - Impact: Implementation would manufacture the approval it is supposed to rely on.
   - Recommended correction: Obtain and record the decision before Plan 001 dispatch, then restamp the plan. The implementation executor may record an already accepted decision but must not decide it. Keep coding workspace, document workspace, and bash/isolation choices open and deferred; the plans currently defer those correctly.

4. **BLOCKER — Baseline restamping instructions conflict with Stage 1 sequencing.**
   - Files: `plans/README.md`; `plans/001-stage0-observed-job-review.md`; `plans/002-stage1-source-inspection-loop.md`
   - Evidence: The README says to restamp “both plans” after committing the current dirty cleanup. Plan 002 correctly says it must instead be restamped to the final reviewed Plan 001 commit after the Job 328 evidence gate.
   - Impact: Restamping Plan 002 to the pre-Plan-001 baseline would make its stated starting symbols and drift gate false.
   - Recommended correction: Before Stage 0, restamp only Plan 001. Leave Plan 002 blocked and placeholder-based. After Plan 001 is accepted, reconcile Plan 002 against the actual Plan 001 final commit and report.

5. **BLOCKER — Plan 002 requires sign-off evidence that Plan 001 never defines or produces.**
   - Files: `plans/001-stage0-observed-job-review.md`; `plans/002-stage1-source-inspection-loop.md`
   - Evidence: Plan 002 greps Plan 001’s report for `SIGNED OFF` and requires advisor sign-off. Plan 001’s exact report headings, required contents, done criteria, and review protocol define no `SIGNED OFF` field or signatory.
   - Impact: A correctly executed Plan 001 still cannot satisfy Plan 002’s admission gate.
   - Recommended correction: Add an explicit acceptance section and machine-checkable marker to Plan 001’s final evidence contract, naming who may sign it, or remove the text grep and gate on specified report fields plus the final review outcome.

6. **MAJOR — The review team and final re-review cardinality are inconsistent.**
   - Files: `plans/README.md`; `plans/001-stage0-observed-job-review.md`; `plans/002-stage1-source-inspection-loop.md`
   - Evidence: The shared protocol describes one Pro writer, three fresh Flash reviewers, then one final independent Flash re-review. Plan 002’s done criteria says three Flash reviewers completed “both review passes,” which implies three reviewers in the second pass. The “advisor” who adjudicates and signs off is not identified as a human/operator role or model role.
   - Impact: Dispatch tooling cannot determine whether four or six Flash contexts are required or who owns adjudication.
   - Recommended correction: State one exact roster everywhere, for example: one exact `deepseek-v4-pro` sole writer; three fresh exact `deepseek-v4-flash` initial reviewers; one additional fresh exact `deepseek-v4-flash` final reviewer; named human/operator advisor for adjudication and acceptance. Preserve the no-alias/no-fallback stop condition.

7. **MAJOR — The tracked evidence reports require impossible self-referential identifiers.**
   - Files: `plans/001-stage0-observed-job-review.md`; `plans/002-stage1-source-inspection-loop.md`
   - Evidence: Each tracked report must contain its own SHA-256 hash and the final/candidate commit SHA, even though editing the report changes both its hash and the commit SHA.
   - Impact: The final manifest cannot be truthfully completed as written.
   - Recommended correction: Do not put a report’s own hash or its containing commit SHA inside that report. Hash the diagram and PNG in the report; record the report hash and final commit SHA in an external acceptance receipt, git note, release manifest, or operator output produced after the final commit.

8. **MAJOR — Report/review sequencing is internally circular.**
   - Files: `plans/001-stage0-observed-job-review.md`; `plans/002-stage1-source-inspection-loop.md`
   - Evidence: Each report is required to contain reviewer findings and resolutions before the candidate is frozen and sent to those reviewers. Repairs then update the report and candidate. A final re-review is required, but it is unclear where its result is recorded without changing the reviewed commit again.
   - Impact: There is no uniquely defined final reviewed commit and evidence ledger.
   - Recommended correction: Define: draft report → initial candidate commit → three read-only reviews → adjudication → Pro repairs and finalizes tracked ledger/report → repaired candidate commit → one final read-only review → external acceptance receipt/sign-off against the unchanged commit. If final review finds a defect, repeat within the stated repair-round cap.

9. **MAJOR — The advertised fake CLI is not self-contained for a fresh checkout or installed package.**
   - Files: `plans/README.md`; `plans/001-stage0-observed-job-review.md`; `pyproject.toml`
   - Evidence: The README advertises `uv run haxjobs experiment review-job --job 49 --fake`, but the CLI defaults to ignored `state/experiments/fixtures/backend-career.json`, which is created only later from private operator data. Job fixtures are planned under `discussion/fixtures/harness/`, not package data.
   - Impact: The documented fake command can fail before private setup and may not work when installed outside the repository, despite the “minimal installed CLI” deliverable.
   - Recommended correction: Explicitly classify this as a repository-only experiment and document fixture prerequisites, or ship a non-private demo fixture/package data for fake mode. Keep live mode tied to the truthful private career fixture. Add a clean-checkout/manual-install acceptance check matching the chosen scope.

10. **MAJOR — Private receipt permissions cover only two files even though other receipts contain private text.**
    - File: `plans/001-stage0-observed-job-review.md`
    - Evidence: The artifact step mandates mode `0600` only for `context.json` and `transcript.json`. `result.json` contains the final model result, and `review.md` can contain human notes/excerpts; `manifest.json` may also contain sensitive local metadata.
    - Impact: File privacy depends on directory traversal permissions and ambient umask rather than an explicit per-file contract.
    - Recommended correction: Atomically create every receipt file with mode `0600`; retain run directories at `0700`. Add one POSIX test over all receipt files, not only context/transcript.

11. **MAJOR — The Stage 1 SSRF requirements do not fully specify a safe standard-library implementation.**
    - File: `plans/002-stage1-source-inspection-loop.md`
    - Evidence: The plan requires pre-resolving public addresses and validating redirects, but a normal `urllib` request can resolve the hostname again at connection time and can honor environment proxies. That leaves DNS-rebinding and proxy-routing ambiguity.
    - Impact: An implementation can pass the listed checks while connecting somewhere other than the validated public address.
    - Recommended correction: Require proxy behavior to be explicit/disabled for this fetcher and require connection-time binding or peer-address verification against the validated resolution set while preserving TLS hostname verification. Add deterministic tests for DNS answer changes and proxy environment variables. If this cannot be done safely within the standard-library-only boundary, stop and reconsider that constraint rather than weakening SSRF protection.

12. **MINOR — Diagram linkage does not meet the diagram directory’s own policy.**
    - Files: `diagram/README.md`; `plans/001-stage0-observed-job-review.md`; `plans/002-stage1-source-inspection-loop.md`
    - Evidence: `diagram/README.md` says each stage diagram should be linked from the relevant discussion note. The plans update only `diagram/README.md`; Plan 001 limits the discussion 006 edit to decision ledger/status text, and Plan 002 generally excludes discussion edits.
    - Impact: The visual decision record is discoverable only in one direction.
    - Recommended correction: Once the architecture decision is actually accepted, allow the smallest relevant discussion-note link update, or revise `diagram/README.md` policy to say implementation diagrams are linked from implementation reports instead.

13. **MINOR — Plan 001 dependency metadata is inconsistent.**
    - Files: `plans/README.md`; `plans/001-stage0-observed-job-review.md`
    - Evidence: The README table says Plan 001 depends on a clean committed baseline; Plan 001 says “Depends on: none, but execution is blocked by the baseline gate.”
    - Impact: Status parsers and humans receive different dependency information.
    - Recommended correction: Use one value: `Depends on: approved clean baseline and exact-model availability`, with current status blocked until both hold.

## Assessment of Requested Areas

- **Decision status:** Stage 0/no tools, conditional Stage 1/one source tool, Python, Pydantic, local JSONL/logging/pytest/Markdown, and fixture order are decided. The four-layer conceptual split and one physical package remain open in discussion 006/research and must not be treated as approved yet. Workspace and bash decisions are correctly deferred.
- **Dirty-baseline gate:** The plans correctly prohibit stashing, resetting, absorbing, or overwriting the intentional dirty work and correctly require a clean committed baseline before an isolated executor worktree. This review could not independently attest current git status with the available read-only tools. The “restamp both plans” conflict must be fixed.
- **Sequencing:** Stage 0 → human reviews for Jobs 49 and 328 → conditional Stage 1 → human evidence gate is correct. Plan 002’s sign-off and restamp details are not executable as written.
- **Deferrals:** Sessions, memory, compaction, company watches, coding/document tools, application flows, plugins, sub-agents, browser/search fallback, and later stages are appropriately deferred. Do not add plans for them before Stage 1 evidence.
- **Exact model roles:** Exact Pro writer and exact Flash reviewers, no fallback/alias, are clearly intended. Reviewer count and advisor ownership need one canonical statement.
- **Evidence reports:** The reports request useful call paths, commands, run IDs, safe hashes, rubric outcomes, review ledgers, deferrals, and residual risks. Self-hashes, containing-commit SHAs, and review timing must be corrected.
- **Diagrams:** Current-state draw.io plus PNG per stage, under-35-cell guidance, XML geometry checks, and real export checks are appropriate. Resolve duplicate filenames and backlink policy.
- **Manual interface:** Explicit `--fake` versus `--live`, no implicit live/provider fallback, and Stage 1 opt-in via `--inspect-source` are correct. Fresh-checkout/installed fixture availability is unresolved.
- **Only two plans:** Two logical plans are correct. Discussion 004 and the research study explicitly require later scope to come from traces. The directory must nevertheless contain only two canonical executable plans; it currently contains four.

## Tasks

1. **Resolve plan identity and missing input**
   - File: `context.md`, `plans/README.md`, and all four numbered files under `plans/`
   - Changes: Restore/waive `context.md`; select one canonical plan per stage; remove or unmistakably archive duplicates; repair every cross-link.
   - Acceptance: `plans/` exposes exactly README + canonical 001 + canonical 002 as executable material, and a fresh review can read every declared input.

2. **Approve or preserve the architecture decision**
   - File: `discussion/006-pi-inspired-haxjobs-architecture.md`, `plans/README.md`, canonical Plan 001
   - Changes: Record explicit approval before dispatch, or mark the four-layer/one-package layout provisional and stop Plan 001 from changing decision status itself.
   - Acceptance: Discussion status/ledger and plan claims agree exactly; workspace/shell questions remain open.

3. **Make the baseline and admission gates sequentially correct**
   - File: `plans/README.md`, canonical Plans 001 and 002
   - Changes: Restamp Plan 001 only after the clean design baseline; restamp Plan 002 only after accepted Plan 001 evidence; define the Plan 001 sign-off field consumed by Plan 002.
   - Acceptance: No unresolved SHA placeholders remain in a dispatched plan, and each drift command compares against the correct immediate baseline.

4. **Normalize execution and review roles**
   - File: `plans/README.md`, canonical Plans 001 and 002
   - Changes: State exact writer/reviewer counts, freshness, model IDs, no-fallback behavior, adjudicator identity, repair cap, and final sign-off owner once.
   - Acceptance: The same roster and review sequence appears in all three documents.

5. **Repair evidence finalization**
   - File: canonical Plans 001 and 002
   - Changes: Remove self-hash/containing-SHA requirements from tracked reports; define draft, review, repair, final re-review, and external acceptance-receipt ordering.
   - Acceptance: One immutable final candidate commit can be named and attested without modifying it after final review.

6. **Close manual/privacy/security gaps**
   - File: canonical Plans 001 and 002
   - Changes: Make fake-mode fixture prerequisites/package scope explicit; apply `0600` to all private receipts; specify DNS/proxy-safe retrieval and tests.
   - Acceptance: Fake mode works in the documented environment, every private receipt has explicit permissions, and fetch tests cover proxy and DNS-rebinding behavior.

7. **Align evidence navigation and metadata**
   - File: `diagram/README.md`, relevant discussion note, `plans/README.md`, canonical Plan 001
   - Changes: Resolve diagram backlink policy and Plan 001 dependency wording.
   - Acceptance: Diagram/report/discussion links are bidirectionally discoverable under one documented policy, and status tables agree.

## Files to Modify

- `plans/README.md` - canonical plan links, sequential restamping, role roster, and status metadata.
- `plans/001-stage0-observed-job-review.md` or selected canonical 001 - decision gate, evidence finalization, sign-off, fixture/manual scope, and receipt permissions.
- `plans/002-stage1-source-inspection-loop.md` or selected canonical 002 - Plan 001 gate, role count, evidence finalization, and retrieval safety.
- `discussion/006-pi-inspired-haxjobs-architecture.md` - only after explicit approval; accurately record accepted versus open items.
- `diagram/README.md` - clarify implementation-diagram backlink policy.
- Superseded numbered plan files - remove or mark non-executable outside the canonical plan set.

## New Files

- `context.md` - only if it remains a required review/planning input.
- External acceptance receipt or release manifest - records final commit SHA and tracked report hash after the immutable final commit, if such attestation is required.

## Dependencies

- Task 1 precedes every other correction because duplicate plans make file targets ambiguous.
- Task 2 must complete before Plan 001 can be restamped or dispatched.
- Task 3 depends on an approved clean baseline; its Plan 002 portion additionally depends on accepted Plan 001 evidence.
- Tasks 4–7 can be corrected in the canonical documents after Task 1, but must finish before executor dispatch.

## Risks

- Current dirty-tree state was described by the plans but not independently verified in this review.
- Exact model IDs may be unavailable or aliases; the existing stop condition should remain.
- A safe standard-library source fetcher may be more complex than the plan assumes; security must win over the no-new-dependency preference.
- Stage 1 must remain conditional. Passing Stage 0 mechanically is not enough; Job 328’s reviewed trace must demonstrate the source-information gap.
- No Stage 2+ plan should be added until Stage 1 traces identify a repeatable next failure.