---
title: Interactive agent CLI study
status: working reference
created: 2026-07-17
updated: 2026-07-17
scope: Pi, Hermes, Claude Code, and the missing HaxJobs conversational runtime
related:
  - 2026-07-17-pi-hermes-job-native-harness-study.md
  - ../006-pi-inspired-haxjobs-architecture.md
---

# Interactive agent CLI study

This note exists because the first two HaxJobs terminal prototypes were wrong.

The first was a career-graph browser. The second looked like a full-screen chat app and generated fake replies. Neither was an agent interface.

The correction is simple:

> Build the conversational runtime first. The terminal only submits input and renders runtime events.

# What Pi, Hermes, and Claude Code have in common

All three systems separate the terminal from the agent runtime.

```text
terminal editor
    |
    | submit, interrupt, approve, queue
    v
session runtime
    |
    | context assembly, model loop, tool loop, persistence
    v
structured events
    |
    | assistant delta, tool progress, result, error, settled
    v
terminal renderer
```

The terminal does not own prompts, career data, tools, or model calls.

## Pi v0.80.6

The installed Pi runtime is the most useful direct pattern for HaxJobs.

Relevant installed source:

- `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/dist/main.js`
- `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/dist/modes/interactive/interactive-mode.js`
- `/home/hax/.local/lib/node_modules/@earendil-works/pi-coding-agent/dist/core/agent-session.js`
- `/home/hax/.local/lib/node_modules/@earendil-works/pi-agent-core/dist/agent-loop.js`
- `/home/hax/.local/lib/node_modules/@earendil-works/pi-tui/dist/components/editor.js`
- `/home/hax/.local/lib/node_modules/@earendil-works/pi-tui/dist/keybindings.js`

Pi's real split is:

```text
InteractiveMode
    terminal input and event rendering

AgentSession
    prompt boundary, queues, persistence, context, retry, compaction

Agent
    bounded model and tool loop

Tools
    typed effects and partial progress
```

The interactive mode calls `session.prompt(text)` and subscribes to session events. Print mode and RPC mode use the same runtime.

Pi does not enter the alternate-screen terminal mode used by full-screen dashboard apps. It composes an inline conversation in normal terminal scrollback:

```text
header
conversation history
pending messages
working status
editor
footer
```

Input behavior is explicit inside the editor:

```text
Enter         submit
Shift+Enter   newline
Ctrl+J        newline
Escape        interrupt the current run
```

The editor does not guess generic key events from an outer app.

Pi's low-level event family includes:

```text
agent_start
turn_start
message_start
message_update
message_end
tool_execution_start
tool_execution_update
tool_execution_end
turn_end
agent_end
```

The session adds queue, retry, compaction, session-change, and settled events.

Tool progress comes from the tool runtime. The interface never fakes it.

## Hermes v0.16.0

The exact v0.16.0 release was inspected at `/tmp/hermes-agent-016-study`, tag `v2026.6.5`, commit `3c231eb`.

Hermes has two terminal clients:

1. a Python `prompt_toolkit` and Rich client
2. a React and Ink client connected to Python through newline-delimited JSON-RPC

Both eventually call the same runtime:

```text
run_agent.py:AIAgent.run_conversation()
    -> agent/conversation_loop.py:run_conversation()
```

Relevant source:

- `/tmp/hermes-agent-016-study/cli.py`
- `/tmp/hermes-agent-016-study/run_agent.py`
- `/tmp/hermes-agent-016-study/agent/conversation_loop.py`
- `/tmp/hermes-agent-016-study/agent/tool_executor.py`
- `/tmp/hermes-agent-016-study/agent/system_prompt.py`
- `/tmp/hermes-agent-016-study/hermes_state.py`
- `/tmp/hermes-agent-016-study/tui_gateway/server.py`
- `/tmp/hermes-agent-016-study/ui-tui/`

The classic client binds plain Enter to submission. Modified Enter inserts a newline.

The newer client sends:

```text
prompt.submit {session_id, text}
```

Python returns immediately and later emits events such as:

```text
message.start
message.delta
tool.start
tool.progress
tool.complete
approval.request
message.complete
error
```

The canonical tool result enters model history separately from the display event. That distinction matters. The UI event is for rendering. The canonical tool-result message is for the model and persistence.

Hermes also shows the right session boundary. Sessions store user messages, assistant messages, tool calls, tool results, model state, and termination details. Career truth or other domain data stays outside the transcript.

## Claude Code

Anthropic does not publish Claude Code's proprietary implementation. Its official behavior and Agent SDK still expose the same runtime shape.

Official references:

- [Interactive mode](https://code.claude.com/docs/en/interactive-mode)
- [CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Agent SDK streaming input](https://code.claude.com/docs/en/agent-sdk/streaming-vs-single-mode.md)
- [Agent SDK sessions](https://code.claude.com/docs/en/agent-sdk/sessions)
- [Permissions](https://code.claude.com/docs/en/permission-modes)
- [Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [Subagents](https://docs.anthropic.com/en/docs/claude-code/sub-agents)

Documented input behavior:

```text
Enter                    submit
Shift+Enter or Ctrl+J     newline
Ctrl+C or Escape          interrupt
Ctrl+G                    external editor
```

The documented streaming and hook interfaces expose model deltas, tool identity, permission requests, tool success and failure, background completion, and session lifecycle.

Claude Code also separates:

```text
interactive CLI
headless structured CLI
Agent SDK
```

These are interfaces over the same agent capability, not separate business implementations.

# What HaxJobs has today

The current greenfield code has a useful Stage 0 and Stage 1 experiment runtime.

## Existing model boundary

`src/haxjobs/model/client.py`

```python
class ModelClient(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse | ModelFailure: ...
```

This is one complete response. It does not stream deltas and has no cancellation signal.

## Existing agent core

`src/haxjobs/agent_core/runtime.py`

`run_stage0()` supports:

- one model call without tools
- a bounded model and tool loop
- a hard cap on model steps
- active tool schemas
- typed tool dispatch
- final `RunResult`
- redacted run receipts
- passive metadata observers

This is an experiment run, not a conversation session.

## Existing events

`src/haxjobs/agent_core/events.py`

Current events describe coarse lifecycle metadata:

```text
run_started
context_prepared
model_started
model_completed
model_failed
tool_requested
tool_started
tool_completed
tool_failed
run_completed
run_failed
```

They intentionally exclude message text, prompt content, tool arguments, and tool results. That is correct for redacted telemetry, but insufficient as the live interface event stream.

The system needs two different event projections:

1. safe persisted telemetry
2. live session events carrying the content needed by the current trusted interface

Do not weaken telemetry redaction to make the terminal work.

## Existing tool registry

`src/haxjobs/agent_core/tools.py`

The tool registry already provides:

- explicit registration
- registered versus active tool separation
- Pydantic input validation
- Pydantic output validation
- structured failures
- bounded result size

It does not provide:

- partial progress callback
- cancellation token
- approval request
- retry-safety declaration
- side-effect classification

## Existing employment host

`src/haxjobs/employment/review_job.py`

The employment layer currently owns:

- Hax's job-review instructions
- frozen job and career fixture context
- `inspect_job_source(job_ref)` registration

It does not yet assemble context from the new `CareerStore`. The current review flow uses `CareerFixture`, not a selected slice of the career graph.

# What is missing before a real interactive interface

| Missing contract | Why the terminal needs it |
|---|---|
| Conversation session | One submitted message must join prior canonical history |
| Streaming model boundary | The terminal must render real assistant progress |
| Live runtime events | Messages and tools need identity and lifecycle |
| Cancellation | Escape must stop provider and tool work cleanly |
| Busy-input policy | New input must queue, interrupt, or wait by explicit rule |
| Session persistence | Conversation must resume after process exit or failure |
| Employment context assembler | CareerStore must provide the relevant slice for this turn |
| Tool progress | Long work must report real progress from the tool |
| Approval requests | External effects must pause on typed approval boundaries |
| Session result | The interface needs a settled state distinct from model completion |

A terminal renderer built before these contracts can only block, inspect private runtime state, duplicate logic, or fake activity.

# The correct HaxJobs boundary

```text
TerminalClient
    submit(text)
    render(event)
    interrupt()
    answer_approval()

EmploymentSession
    prompt(text)
    subscribe(listener)
    abort()
    resume(session_id)

AgentRuntime
    canonical messages
    bounded model and tool loop
    live events
    cancellation
    final interaction result

EmploymentHost
    Hax instructions
    active career track
    selected CareerStore context
    active employment tools
    approval policy

Employment actions
    inspect source
    review job
    later: discover, decide, prepare, monitor
```

The terminal imports `EmploymentSession`. It must not import `CareerStore`, provider clients, or employment action handlers.

The session imports the agent core and an employment host interface.

The agent core remains unaware of jobs, CVs, companies, career tracks, and applications.

# Minimum live event contract

The first useful contract does not need Pi's whole event catalogue.

```text
session_started
user_message_accepted
turn_started
assistant_started
assistant_delta
assistant_completed
tool_started
tool_progress
tool_completed
tool_failed
turn_interrupted
turn_failed
turn_completed
session_settled
```

Later additions should be justified by real pressure:

```text
permission_requested
user_message_queued
background_operation_started
background_operation_completed
session_compacted
subagent_started
subagent_completed
```

# Minimum interaction lifecycle

```text
1. User presses Enter.
2. Editor submits the full text.
3. EmploymentSession persists the user message.
4. Employment context assembler selects relevant career facts.
5. AgentRuntime starts the bounded model and tool loop.
6. Live events stream to the terminal.
7. Tool calls execute through the registry and emit real progress.
8. Canonical tool results enter conversation history.
9. The model continues until a final answer or explicit stop.
10. The session persists the final interaction state.
11. session_settled unlocks the next normal prompt.
```

Escape sends cancellation through the session into the provider call and current tool. It does not merely hide a spinner.

# Terminal library direction

`prompt_toolkit` is the closest Python fit for the first HaxJobs interface because it supports:

- normal terminal scrollback
- explicit Enter submission
- multiline editing
- asynchronous redraw
- completion menus
- key bindings
- bottom toolbars
- input history

Textual naturally encourages a full-screen alternate-buffer app. That can be useful for dashboards, but it fought the intended Pi-style interaction here.

This is not yet a dependency decision. First build a throwaway prompt-toolkit editor proof with direct tests for:

```text
Enter submits
Shift+Enter or Ctrl+J adds a newline
Escape interrupts
Ctrl+C clears then exits
terminal state restores after crash or exit
```

If that proof fails, reconsider the library before building the interface.

# Build order

1. Keep the discarded TUI deleted.
2. Define canonical conversation messages and live runtime events.
3. Add streaming and cancellation to the provider boundary.
4. Add an interruptible multi-turn session around the agent core.
5. Persist canonical messages and tool results.
6. Build career-context selection from `CareerStore`.
7. Adapt one real employment action into the conversational flow.
8. Prove the session through fake-provider trajectory tests.
9. Prove one live conversation without a visual terminal client.
10. Build the smallest prompt-toolkit interface over the tested session.
11. Make `haxjobs` open it only after Enter, streaming, tool rendering, interruption, and resume all pass.

# First acceptance scenarios

## Profile-grounded conversation

```text
Given a migrated career graph
When the user asks what roles fit them now
Then Hax receives selected career context
And streams a real provider response
And the interaction is persisted
And the same session can resume
```

## Tool-backed conversation

```text
Given the user asks about a thin saved job
When Hax calls inspect_job_source
Then the interface receives real tool lifecycle events
And the canonical tool result enters model history
And Hax continues with the source evidence
And no interface code calls the tool directly
```

## Interruption

```text
Given Hax is streaming or running a tool
When the user presses Escape
Then cancellation reaches the active provider or tool
And the partial interaction is persisted honestly
And the terminal returns to a usable prompt
```

# Explicitly rejected

- another profile browser
- another Textual full-screen shell
- message bubbles
- fake agent replies
- fake typing indicators
- interface code reading `CareerStore`
- interface code constructing system prompts
- interface code calling provider clients
- interface code dispatching employment tools
- making `haxjobs` open an interactive interface before the runtime behind it is real
