---
name: haxaml-governed-flow
description: Use when work changes repository code, config, or governed docs and you
  must follow the Haxaml lifecycle.
metadata:
  generator: haxaml-setup
  target: generic
  kind: skills
  scope: project
  version: 0.7.4
  recipe_hash: e6bc72674832773aa262c24ca34e8cc563a1ec26dfd779c27ad514f73104871c
---

# Haxaml Governed Flow

This skill is installed for `Generic AGENTS` in `project` scope and governs repository-changing work through the Haxaml lifecycle.

## Use When

- The task changes repository code, configuration, or governed documentation.
- You need a deterministic flow for materials, planning, verification, and recorded outcomes.
- The repo has setup-managed instructions, skills, or workflow entrypoints that should stay aligned.

## Do Not Use

- The request is casual, off-topic, or does not touch governed repo state.
- A one-off answer can be given safely without entering the repo workflow.
- The task belongs to a different specialized skill or tool contract that explicitly owns the work.

## Required Inputs

- A concrete task statement, the relevant repository path, and any known target files or tests.
- Any owner-provided materials, credentials, schema details, or environment constraints needed before building.
- Whether workflow adaptation is involved through hooks, agents, background runs, or CI entrypoints.

## Lifecycle Flow

1. Read the active setup-managed instructions and the smallest relevant repository slice.
2. Use the Haxaml lifecycle when it is available: about, guidance, prebuild, context_pack, build, verify, record, expect_sync.
3. If lifecycle tooling is unavailable, follow the manual fallback checklist exactly.
4. Gather missing materials before building, then make the smallest safe change that satisfies the task.
5. Verify with direct evidence and report what changed, what was checked, and what still risks failure.


## Generic AGENTS expectations

- Treat this skill as the local workflow contract when work changes repository code, config, or governed docs.
- Read only the files needed for the current task, then verify with direct evidence before claiming success.
- Keep changes narrow, reported publicly, and easy for the next agent to continue.

## Success Criteria

- The change follows the lifecycle or documented fallback path instead of skipping straight to edits.
- Required materials, assumptions, verification evidence, and residual risks are explicit in the final report.
- Edits stay narrow, reversible, and aligned with setup-managed instructions for this target.

## Output Contract

- Summarize the task, relevant assumptions, and the concrete files or configs touched.
- State what was verified and cite the command, test, or direct inspection that produced the evidence.
- Call out any remaining risks, manual follow-up, or unresolved ambiguity before claiming completion.

## Escalation Rules

- Ask before destructive operations, broad refactors, policy changes, or replacing user-authored native instructions.
- Escalate when required materials are missing, the config shape is unsafe to merge, or target ownership is ambiguous.
- Do not silently drop provider-native files that setup is supposed to preserve or adopt.

## Fallback Path

1. Read the local instructions and the relevant source files before editing.
2. Classify the task, note risks, and state assumptions publicly.
3. Make the smallest safe change that satisfies the request.
4. Verify with commands, tests, or direct inspection and report evidence.
5. Record what changed and any remaining risks before claiming completion.

## Examples

### Example 1

- Task: add a small feature in one module.
- Behavior: inspect the module and the closest tests, make the narrowest safe edit, verify it directly, and report the concrete evidence plus remaining risk.

### Example 2

- Task: update an MCP config entry.
- Behavior: merge only the Haxaml-owned config block, preserve unrelated keys or tables, preview the exact block, and escalate if the file shape is unsafe to edit automatically.
