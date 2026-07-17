# Cold review: Plan 001 Stage 0 observed job review

## Review

### Blockers

1. **Blocker — `Step 12: Write the implementation evidence report` (`plans/001-stage0-observed-job-review.md:756-794`) — two required attestations are self-referential and cannot be produced exactly.**
   - The tracked report must contain the candidate commit SHA, but the candidate commit SHA depends on the report's contents.
   - The report must also contain its own SHA-256 hash; inserting that hash changes the report and therefore changes the hash.
   - **Correction:** Keep the baseline SHA in the report, but put the final candidate SHA and the report/draw.io/PNG hashes in a separate post-commit attestation or tracked manifest that does not hash itself. Add that manifest to Scope and define the exact hashing command. Alternatively, define an explicit canonical hash that excludes the manifest field and provide a verifier.

2. **Blocker — `Step 3: Create machine-readable, source-limited fixtures` (`plans/001-stage0-observed-job-review.md:329-386`) — the cited source does not contain the required exact Job 49 payload.**
   - The plan requires the machine fixture to contain the preserved 5,000-character description (`:353`), but `discussion/fixtures/003-five-job-sample.md:70-107` contains a prose/bullet summary of that description, not the literal 5,000 characters.
   - A zero-context executor would have to invent wording, read the out-of-scope old database, or silently weaken the requirement.
   - **Correction:** Commit a source-limited raw Job 49 fixture as part of the baseline and cite it, or change the requirement to a clearly labelled structured summary and remove the 5,000-character preservation claim.

3. **Blocker — `Model preflight` and `DeepSeek v4 Flash review round` (`plans/001-stage0-observed-job-review.md:280-290,819-879`) — exact-model execution is policy text, not an executable workflow.**
   - No command/tool/API is given to launch the Pro executor, resolve model aliases, inspect returned model identity, dispatch the three independent Flash reviews, or perform the final re-review. An executor cannot attest its own hidden runtime model from these instructions.
   - The application provider's configured live model is also not distinguished clearly from the orchestration models used to implement/review the change.
   - **Correction:** Put dispatch outside the implementation agent and provide an operator/orchestrator runbook with exact launch commands/tool calls, expected model metadata, commit range, independent-context guarantees, and an attestation location. Explicitly distinguish **implementation/review runtime model IDs** from the **Stage 0 live experiment provider model**. STOP if verifiable metadata is unavailable.

4. **Blocker — `Step 10: Run the live Stage 0 experiment in the decided order` (`plans/001-stage0-observed-job-review.md:671-708`) — the sole AI executor is told to complete a “human review.”**
   - The decided experiment and done criteria require human reviews, but the plan has no operator pause, handoff, reviewer identity, or attestation step. Letting the Pro executor fill the rubric would not satisfy the requirement.
   - **Correction:** After each live run, STOP and hand the local `review.md` to an identified human operator. Specify the fields the human must complete and the signal/file that allows execution to resume. The report may record the bounded outcome, not private rubric contents.

### Major

5. **Major — `Baseline gate, run before dispatch` (`plans/001-stage0-observed-job-review.md:26-66`) — the restamp/clean sequence is circular as written.**
   - The operator first commits the baseline, then edits this plan to put that commit in `Planned at`; that edit makes the checkout dirty. Committing the restamp changes HEAD again, so “the current commit is recorded into this plan” is no longer literally true.
   - The repository is currently correctly blocked: HEAD is `5423187` and the working tree is broadly dirty. The problem is the transition out of the blocked state, not the current STOP.
   - **Correction:** Define two values explicitly: `BASELINE_SHA` (the content baseline used for drift) and `PLAN_RESTAMP_COMMIT` (the later plan-only commit). Commit the restamped plan, require clean HEAD at the restamp commit, and run drift from `BASELINE_SHA` over the exact in-scope paths. Do not require a commit to contain its own SHA.

6. **Major — `Step 7: Add the thin experiment CLI` (`plans/001-stage0-observed-job-review.md:574-609`) — the fake manual command is ordered before its default career fixture exists.**
   - `--career-fixture` defaults to `state/experiments/fixtures/backend-career.json` (`:586`), but that file is not created until Step 9 (`:645-669`). Step 7 nevertheless requires `--job 49 --fake` to exit 0 and create a complete receipt.
   - **Correction:** Either create the private fixture before the first CLI run, or make the fake command explicitly use the tracked synthetic fixture, e.g. `--career-fixture tests/fixtures/job_review/career.json`. State whether fake mode ever bypasses fixture loading; preferably it should not.

7. **Major — `Protocol and adapter in model/client.py` (`plans/001-stage0-observed-job-review.md:404-428`) — the failure contract contradicts the protocol.**
   - `ModelClient.complete` is declared to return only `ModelResponse`, while the adapter must produce a typed `ModelFailure`, the fake accepts failures, and the runtime maps “response or failure.” It is unspecified whether failure is returned, raised, or wrapped.
   - **Correction:** Choose one contract and show it exactly, for example `async def complete(...) -> ModelResponse | ModelFailure`, or define one typed exception caught by the runtime. List the bounded failure categories and required safe message behavior.

8. **Major — `Step 5: Create the domain-free Stage 0 agent core` and `Step 7` (`plans/001-stage0-observed-job-review.md:458-516,590-600`) — artifact failure has no data contract.**
   - `RunResult` carries `observer_errors` but no artifact/receipt error or completeness flag. The CLI must preserve the answer yet exit non-zero on artifact errors, and the STOP conditions refer to incomplete receipts. A weaker executor must invent exception and partial-write semantics.
   - **Correction:** Add an explicit `artifact_errors`/`receipt_complete` field (or a typed runtime result), define which files may exist after each failure point, define final event order on artifact failure, and add a deterministic artifact-write-failure test.

9. **Major — `Step 9: Create the private backend-career fixture` (`plans/001-stage0-observed-job-review.md:645-669`) — private input discovery is unspecified and invites unsafe filesystem exploration.**
   - “operator-provided main checkout paths” gives no exact allowlist, transfer mechanism into the isolated worktree, or STOP condition when paths are absent. A zero-context executor may search the home directory or copy excessive profile material.
   - **Correction:** Require the operator to provide one explicit allowlisted input file or pre-sanitized payload, mounted/copied by the operator. State that the executor must not enumerate outside those paths and must STOP if the allowlist is absent. Add a review checklist proving excluded fields are absent without printing their values.

10. **Major — `Step 12: Write the implementation evidence report` and `DeepSeek v4 Flash review round` (`plans/001-stage0-observed-job-review.md:756-794,819-879`) — the report/review lifecycle is incomplete.**
    - Step 12 requires reviewer findings and resolutions before any reviewer has run. Later text updates the report only when accepted findings are fixed. If all three reviews return no accepted findings, there is no mandatory post-review report update/commit. The final re-review is also not explicitly recorded.
    - **Correction:** Create a pre-review report without the ledger, then always run a post-review finalization step that records all review IDs, dispositions, repairs, verification, and final re-review outcome; re-run verification and commit it even when findings are empty.

11. **Major — `DeepSeek v4 Flash review round` (`plans/001-stage0-observed-job-review.md:819-879`) — review count and repair orchestration are ambiguous.**
    - The plan requires three fresh reviewers and then “one final independent Flash re-review,” which is four Flash invocations, while done criteria mention only three roles. “At most two repair rounds” does not define the second repair/re-review sequence. The advisor disposition step has no executable owner/handoff.
    - **Correction:** State the exact total: three parallel initial reviews plus one fresh re-review after each repair round (and therefore the maximum number of calls). Name who dispositions findings, how decisions are handed back, and what happens when there are no findings or a second repair is needed.

12. **Major — `Step 11: Create the current-state diagram` (`plans/001-stage0-observed-job-review.md:710-754`) — verification does not prove the tracked PNG is current.**
    - The source is exported to `/tmp`, while the tracked PNG is checked only for non-zero size. A stale tracked PNG can pass. The local `drawio` command is available and reports version 30.2.4, so this is fixable.
    - **Correction:** Export the final source directly to `diagram/003-stage0-observed-job-review.png`, or export to `/tmp` and compare bytes/hash against the tracked PNG. Add a visual/readability attestation by Reviewer C; XML parsing and size alone do not establish readability.

13. **Major — `Step 12: Write the implementation evidence report` (`plans/001-stage0-observed-job-review.md:756-794`) — there is no verification gate for the Markdown report.**
    - The step has exact headings, links, commands, privacy restrictions, ledger, and manifest requirements but no command or expected result. This violates the plan template's per-step verification rule and leaves a weak executor to self-judge completeness.
    - **Correction:** Add a small deterministic verifier (preferably in the focused test file) that checks heading order, required links/fields, relative-link existence, forbidden placeholder markers, and manifest verification. Keep private-content review as an explicit human gate.

14. **Major — `Step 3: Create machine-readable, source-limited fixtures` (`plans/001-stage0-observed-job-review.md:329-386`) — its verification proves only keys and two Job 328 properties.**
    - It does not check Job 49 length/truncation warning, forbidden evaluation fields/prose, bounded `source_status`, provenance/date formats, or Job 328's hidden-claim exclusions. Those requirements are privacy/truth boundaries.
    - **Correction:** Validate both JSON files with the production Pydantic contract and assert all listed exclusions and evidence limits in the focused tests. Define nullable/unknown behavior for `employer_name`, especially Job 328 where the stored company is `LinkedIn` and the employer is only suggested by the URL.

15. **Major — `Step 7: Add the thin experiment CLI` (`plans/001-stage0-observed-job-review.md:582-600`) — manual CLI options are not fully specified.**
    - “optional model settings … with conservative defaults” leaves flag names, types, ranges, defaults, and whether model/base URL/credential can be overridden unstated. This is exactly where weaker executors will improvise and may expose unsafe provider configuration.
    - **Correction:** List each supported flag and exact default (`--timeout`, `--temperature`, `--max-tokens`, if those are the intended set), validation ranges, and explicitly prohibit credential/base-URL/model fallback flags unless required. Add help-text assertions.

### Minor

16. **Minor — `Step 4: Create the model boundary` (`plans/001-stage0-observed-job-review.md:413-424`) — provider configuration has an unnecessary choose-your-own-path.**
    - “from `~/.haxjobs/haxjobs.toml` … or from the already documented environment variable types” does not name the exact TOML schema or environment variables. Existing code uses `[provider]` keys and several environment variable names, but the plan tells the executor not to reuse that service.
    - **Correction:** Inline the accepted TOML keys and exact environment variable names with precedence rules, while stating that values must never be printed. One parser behavior should be authoritative.

17. **Minor — `Scope` versus the handoff template (`plans/001-stage0-observed-job-review.md:202-268`) — ownership of `plans/README.md` is omitted.**
    - The template says executors update the index unless a reviewer dispatcher says it maintains the index. This plan neither puts `plans/README.md` in scope nor states that the advisor owns it.
    - **Correction:** Explicitly say “the advisor/operator maintains `plans/README.md`; executor must not edit it,” or add it to Scope with a final status step.

### Notes / confirmed executable pieces

- **Note — `Baseline gate, run before dispatch`:** The plan correctly identifies that execution must not start from the present checkout. Inspection confirmed the working tree is dirty and HEAD remains `5423187`; this is an intentional active STOP, not a hidden failure.
- **Note — `Step 11: Create the current-state diagram`:** The cited clean-drawio skill exists and matches the requested five-group, thick-arrow, import-safe XML approach. The local `drawio` CLI is installed, so source import/export is executable after the PNG-currentness correction.
- **Note — `Step 7: Add the thin experiment CLI`:** The current `src/haxjobs/cli.py:164-206` uses nested `argparse` subparsers, so adding `experiment review-job` as a sibling is architecturally feasible without modifying `haxjobs agent ask`.
- **Note — privacy baseline:** `/state/` is ignored by `.gitignore:19`, and `git check-ignore` confirmed both the proposed career fixture and run-artifact paths are ignored. Ignore rules do not replace the missing private-input allowlist or file-permission tests.
- **Note — requested context files:** `/home/hax/haxjobs/plan.md` and `/home/hax/haxjobs/progress.md` do not exist. The authoritative plan under review and its cited files were still available; no assumptions were made from missing session context.

## Residual risks

- Exact DeepSeek model availability and alias fidelity cannot be verified from repository files; it requires the orchestration/provider runtime described in the correction above.
- No implementation tests or live provider calls were run because this was a cold read-only plan review and the baseline gate is currently blocked.
- Private source contents were not opened or reproduced.