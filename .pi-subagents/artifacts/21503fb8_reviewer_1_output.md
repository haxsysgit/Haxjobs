# Cold review: Plan 002 Stage 1 source-inspection loop

## Review

### Blocker — `## Admission and drift gate`: the gate requires Plan 001 evidence that Plan 001 does not promise to produce

- **Evidence:** `plans/002-stage1-source-inspection-loop.md:27-48` requires two run IDs plus literal `SIGNED OFF` and `Final SHA` matches in the Plan 001 report. The cited authoritative Plan 001 report contract only requires a baseline/candidate SHA, run IDs, rubric outcomes, and reviewer findings (`plans/001-stage0-observed-job-review.md:778-792`); it does not require advisor sign-off or the phrase `Final SHA`. The gate command also searches neither `Job 49` nor either run ID, despite the expected results claiming those facts.
- **Impact:** A fully compliant Plan 001 can still make Plan 002's admission command fail. Conversely, the loose `rg` can pass on incidental prose without proving the expected gate.
- **Correction:** Before dispatch, align the two plans. Either amend Plan 001's report contract to require stable, uniquely parseable fields for advisor status, accepted candidate SHA, both run IDs, and both rubric outcomes, or change Plan 002 to validate the fields Plan 001 actually guarantees. Replace the single alternation grep with exact assertions for each required field and compare the recorded candidate SHA to `git rev-parse HEAD`.

### Blocker — `### Step 11: Write the Plan 002 implementation report`: final-SHA and report-self-hash requirements are self-referential

- **Evidence:** The tracked report must contain Plan 002's “final SHA” and its own hash (`plans/002-stage1-source-inspection-loop.md:683-699`), but it is written before the first candidate commit (`:701-724`) and changed again after review (`:784`). Changing the report changes both its file hash and the commit SHA. Plan 001 contains the same infeasible self-hash requirement (`plans/001-stage0-observed-job-review.md:778-792`), so copying it does not resolve the problem.
- **Impact:** The done criteria cannot be satisfied truthfully by a tracked report in the commit whose SHA/hash it claims to contain.
- **Correction:** Remove the containing commit SHA and report's own SHA-256 from the tracked report. Record the baseline and reviewed parent/candidate SHA with explicit semantics, and have the orchestrator produce a post-commit external attestation (or Git note) containing the final commit and report hash. Keep ordinary hashes for the draw.io and PNG. If a report hash must remain in-file, define a canonical hash that excludes the hash field and provide the exact command.

### Major — `### Step 5: Implement inspect_job_source(job_ref)` / `#### Retrieval boundary`: the SSRF boundary is not safe enough to implement from the stated recipe

- **Evidence:** `plans/002-stage1-source-inspection-loop.md:419-438` says to resolve/check addresses and then use standard-library retrieval, but does not require the connection to use the checked address. A normal `socket.getaddrinfo()` check followed by `urllib.request.urlopen()` performs a second resolution and is exposed to DNS rebinding. `urllib` can also honor environment proxies and automatically follow redirects unless configured otherwise. Redirect count, URL userinfo, ports, HTTPS downgrade, content types, compressed responses, and whether every A/AAAA result must be public are unspecified.
- **Impact:** An implementation can satisfy the written checklist and tests while connecting to an unchecked private address, forwarding through an ambient proxy, following an unsafe redirect, or consuming an unsuitable response. That invalidates the HIGH-risk source-safety done criterion at `:815-816`.
- **Correction:** Specify a concrete transport policy: disable environment proxies; reject userinfo; restrict ports; forbid HTTPS-to-HTTP downgrade; use manual redirects with a small fixed hop cap; require exact normalized host membership; resolve every hop and reject if any candidate is non-public; pin the connection to a validated address while preserving hostname TLS/SNI and verify the peer address; send `Accept-Encoding: identity`; allow only bounded textual content types; read at most cap+1 bytes; and apply a total deadline. Add explicit safe status mapping for 3xx/403/404/410/429/5xx.

### Major — `### Step 7: Add focused deterministic tests`: the proposed fake boundary cannot prove the real fetcher's safety

- **Evidence:** Tests 17-19 claim to prove redirects, public-address rejection, and response limits (`plans/002-stage1-source-inspection-loop.md:515-521`), while `:523` and `:795` direct tests to use a fake fetcher. A fake of the whole fetcher bypasses precisely the production URL/DNS/redirect/byte-limit code those tests need to exercise.
- **Impact:** The suite can be green while the real standard-library fetcher remains vulnerable or unbounded.
- **Correction:** Inject below the safety logic (resolver plus HTTP transport/response), not around the whole production fetcher, for these tests. Add cases for allowed host resolving private, mixed public/private answers, every redirect hop, redirect loops/hop cap, DNS rebinding/peer mismatch, ambient proxy disabling, userinfo/port/downgrade rejection, non-text content, cap+1 bytes, and instruction-shaped hostile HTML. Keep a global socket-open guard so pytest cannot reach the network.

### Major — `### Step 8: Extend the manual CLI without hiding the experiment mode`: fake Stage 1 can accidentally perform a live source request

- **Evidence:** Plan 001 promises `--fake` uses no network (`plans/001-stage0-observed-job-review.md:590-593`). Plan 002 requires `--fake --inspect-source` to exercise a tool (`plans/002-stage1-source-inspection-loop.md:542-564`) but never states that CLI fake mode injects a deterministic fake source transport. The test-only fake-fetcher statement does not define manual CLI behavior.
- **Impact:** The advertised fake smoke command could contact LinkedIn, become nondeterministic, or fail offline, contradicting Plan 001 and the shared fake-mode expectation.
- **Correction:** State that `--fake` injects both the scripted model and a scripted source transport and can never open a socket. Define its deterministic success or blocked observation. Add a CLI regression test that patches socket creation to fail and still proves exactly one tool trajectory and final response.

### Major — `### Step 4: Turn the one-call runtime into one bounded loop`: response precedence and tool-budget semantics are ambiguous

- **Evidence:** The pseudocode stops on final text before examining tool calls (`plans/002-stage1-source-inspection-loop.md:350-360`), but provider responses can contain both assistant content and tool calls. The plan also says “maximum successful tool executions” is one and then says a second requested call is blocked (`:368-372`), which disagree when the first call is malformed, inactive, or raises.
- **Impact:** One executor may silently discard tool calls when content is present; another may execute a later call after a failed first attempt. Message history and the one-effect safety boundary will differ.
- **Correction:** Define exact precedence and accounting. Recommended: if any tool call is present, preserve the complete assistant message and process calls; only content-only responses may finish. Count handler starts as executions; at most the first valid active call may start, and every later call receives `tool_budget_exhausted` in source order. State whether malformed/unknown calls consume the budget. Add mixed-content/tool-call, empty-response, and multi-call mixed-validity tests.

### Major — `## DeepSeek v4 Flash review round` / `## Done criteria`: the Pro/Flash pass count contradicts itself and attestation is too weak

- **Evidence:** The workflow and shared index specify three initial Flash reviewers followed by one final independent Flash re-review (`plans/002-stage1-source-inspection-loop.md:726-786`; `plans/README.md:113-125`). The done criterion instead requires three reviewers to complete “both review passes” (`plans/002-stage1-source-inspection-loop.md:803-806`), implying six reviews. The report asks only for model attestations (`:685-686`), while health checks at `:242` have no executable or externally verifiable gate.
- **Impact:** Completion count is indeterminate, and model self-attestation cannot prove exact-model/no-fallback execution against a particular candidate.
- **Correction:** Match the index explicitly: three distinct initial Flash sessions plus one fresh final Flash session. Require orchestrator/runtime metadata for canonical model ID, distinct session/run ID, role, reviewed commit SHA, and result; do not rely on model prose. Make model availability/identity an advisor pre-dispatch gate, not an implementation command the writer must invent.

### Major — `### Step 10: Create the Stage 1 current-state diagram`: the required architecture omits the model boundary and does not prove the tracked PNG is current

- **Evidence:** The six mandated groups at `plans/002-stage1-source-inspection-loop.md:616-623` omit `haxjobs.model`, even though the plan and shared architecture require a distinct provider/model boundary (`plans/README.md:62-78`) and the diagram must show a tool result returning to the model (`plans/002...:625-631`). The verification exports only `/tmp/haxjobs-stage1-diagram.png` and merely checks that the tracked PNG already exists (`:640-656`); a stale tracked PNG passes.
- **Impact:** The current-state diagram can erase a load-bearing architectural boundary, and the committed preview may not correspond to its source.
- **Correction:** Use seven groups (the clean-drawio skill allows 5-7), adding the model boundary, or explicitly place and label the model projection/provider node without violating the separation. Export the tracked PNG from the final draw.io source, export a second temporary PNG, and `cmp` them (or compare hashes). Record a visual review and verify README links.

### Major — `### Step 12: Run full verification and commit the candidate`: done criteria are not backed by objective commands

- **Evidence:** `git status --short` and `git diff --check` (`plans/002-stage1-source-inspection-loop.md:701-724`) do not prove an allowlisted scope, ignored artifact paths, report headings, root CLI discoverability, CLI range validation, exact event counts, or that the tracked PNG matches source. The shared plan index requires discovery through root `haxjobs --help` (`plans/README.md:127-140`), but Plan 002 verifies only nested help. The inline Step 6 command still contains executor-chosen `...` (`plans/002...:480-491`), so it is not runnable as written.
- **Impact:** Several done criteria remain human assertions, contrary to the plan-template requirement for commands with expected results.
- **Correction:** Add exact commands/tests for: root and nested help; `--max-model-steps` values 0/1/5/6; no tool without the flag; socket-free fake mode; receipt event counts; report headings; `git check-ignore` for local artifacts; an allowlisted `git diff --name-only <baseline>..HEAD`; and PNG equivalence. Define the `build_stage1_tools` signature now and provide a literal runnable snippet.

### Minor — `#### Trusted source configuration`: it duplicates Plan 001 fixture fields

- **Evidence:** Plan 002 says to add canonical source URL and source type (`plans/002-stage1-source-inspection-loop.md:409-417`), but Plan 001 already requires `source_url` and `source_type` (`plans/001-stage0-observed-job-review.md:333-349`).
- **Impact:** A cold executor may introduce both `source_url` and `canonical_source_url`, creating needless migration and ambiguity over which is authoritative.
- **Correction:** State that existing `source_url` is the canonical source URL and add only `allowed_redirect_hosts` (plus any precisely named policy fields actually needed), or explicitly prescribe a rename and all callers/tests to update.

### Minor — `### Step 7` and `### Step 8`: CLI and untrusted-content cases are under-tested

- **Evidence:** The test list covers tool mechanics but not argparse range rejection, root help, live/fake exclusivity regression, progress/failure output, response containing both text and calls, empty provider output, or hostile fetched text attempting to issue instructions (`plans/002-stage1-source-inspection-loop.md:493-564`).
- **Impact:** User-facing CLI regressions and the “untrusted data, never instructions” rule can slip through while core tests pass.
- **Correction:** Add the smallest semantic tests for those cases. Assert role/source/observation labels and message placement rather than trying to assert that a model obeys malicious content.

### Minor — plan identity is ambiguous in the repository

- **Evidence:** Both `plans/001-stage0-observed-job-review.md` and `plans/001-build-stage-0-observed-job-review.md` claim to be Plan 001, but they prescribe different modules, CLI flags, filenames, and report headings. The index and Plan 002 correctly cite the former.
- **Impact:** A zero-context executor searching for “Plan 001” can read the stale incompatible plan and conclude that Plan 002's expected symbols or commands are wrong.
- **Correction:** Mark `plans/001-build-stage-0-observed-job-review.md` prominently as superseded or remove/rename it before dispatch. In Plan 002, state that only the exact dependency path at line 18 is authoritative.

### Note — current preconditions and inspected commands

- `/home/hax/haxjobs/plan.md` and `/home/hax/haxjobs/progress.md` do not exist. This is consistent with `plans/README.md`, which explicitly rejects requiring those files; no plan defect follows.
- The checkout is intentionally very dirty and Plan 001 has not landed, so Plan 002 is correctly blocked. Current root CLI help exposes only `start`, `agent`, and `dev`; that is expected before Plan 001. `drawio` is installed at `/usr/bin/drawio`, and `uv lock --check` passed.
- No repository files were edited. Only this required review artifact was written.

## Residual risks

- Even after the textual fetch policy is corrected, a reviewer must inspect the actual socket/TLS connection path; URL validation alone does not prove the connected peer was validated.
- Live LinkedIn behavior is inherently unstable. A blocked result is acceptable, but it cannot substitute for deterministic transport-policy tests.
- Exact-model execution and review independence depend on orchestration metadata outside this repository and cannot be established by the implementation report alone.