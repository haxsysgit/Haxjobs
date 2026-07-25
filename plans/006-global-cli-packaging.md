# Global CLI Packaging Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make HaxJobs installable from a wheel as a global conversational career agent that runs from any directory and keeps durable state under `~/.haxjobs`.

**Architecture:** The installed Python package owns code. `~/.haxjobs` owns one user's provider configuration and durable state. The current directory must not affect career identity, databases, sessions, or default configuration. `HAXJOBS_HOME` remains the one explicit override for isolated tests and alternate local profiles.

**Tech Stack:** Python 3.12, standard library `pathlib`, `tomllib`, `getpass`, `argparse`, `uv`, Hatchling, pytest, prompt_toolkit.

---

## Locked decisions

- `haxjobs` opens or resumes the terminal conversation from any directory.
- `haxjobs chat` remains an explicit alias.
- Default runtime home is `~/.haxjobs`, not the repository checkout and not the current directory.
- `HAXJOBS_HOME` overrides that default for tests and deliberate isolated profiles.
- `~/.haxjobs/haxjobs.toml` holds provider configuration and must be mode `0600` on POSIX.
- `~/.haxjobs/state/` holds career and session SQLite files. Runtime directories are created mode `0700` on POSIX.
- `haxjobs setup` is a small attended command. It asks for an OpenAI-compatible API key through `getpass`, with optional provider name, base URL, and model. It writes configuration only. It never calls the provider.
- `haxjobs` does not interpret the current directory as a career workspace. A future explicit workspace option is out of scope.
- Packaging must work from a temporary directory after installing a built wheel into a fresh virtual environment.

## Drift check

Stamped against `6aeb022` after Plans 004 and 005. The live code still has a repo-root-dependent `src/haxjobs/config.py`, a root `haxjobs.toml` with personal legacy values, and `OpenAIModelClient` independently resolving `Path.home() / ".haxjobs" / "haxjobs.toml"`. The package script already exists as `haxjobs = "haxjobs.cli:main"`.

Do not preserve the root config loading just because it exists. It makes a PyPI installation depend on source-checkout files.

## Scope

### In

- Global runtime-home resolution and safe directory creation.
- Provider configuration path shared by config and model client.
- Attended `haxjobs setup` command.
- First-run chat error that points to setup or fixture migration without exposing credentials.
- Wheel build and fresh-install verification script.
- Packaging metadata needed for a clean wheel install.
- Tests, release report, two small diagrams, and a manual proof guide.

### Out

- PyPI publishing credentials or an actual PyPI upload.
- OAuth, a provider picker UI, provider validation calls, or fallback providers.
- Workspace mode, filesystem tools, discovery, packs, watches, web UI, and cloud deployment.
- Importing the current user's private career data into the wheel.
- Moving or deleting the existing development state.

## Files

### Modify

- `src/haxjobs/config.py`
- `src/haxjobs/model/client.py`
- `src/haxjobs/cli.py`
- `pyproject.toml` only if the build needs an explicit package-data declaration
- `README.md`
- `docs/HAXJOBS.md`
- `docs/GETTING_STARTED.md`
- `plans/README.md` only after controller acceptance

### Create

- `src/haxjobs/interfaces/setup_cli.py`
- `tests/test_runtime_home.py`
- `tests/test_setup_cli.py`
- `tests/test_wheel_install.py` only if it can build and install without making normal pytest depend on network or a user home
- `scripts/verify-wheel-install.py`
- `deliverables/006-global-cli-packaging/README.md`
- `deliverables/006-global-cli-packaging/plan.md`
- `deliverables/006-global-cli-packaging/report.md`
- `deliverables/006-global-cli-packaging/manual-proof.md`
- `deliverables/006-global-cli-packaging/rubric.md`
- `deliverables/006-global-cli-packaging/runtime-home.drawio` and PNG
- `deliverables/006-global-cli-packaging/install-flow.drawio` and PNG

## Phase 1: Replace checkout-derived runtime paths

### Task 1: Write the runtime-home tests

**Files:**
- Create: `tests/test_runtime_home.py`
- Modify: `src/haxjobs/config.py`

Write tests that import configuration in subprocesses with controlled environments:

1. No `HAXJOBS_HOME`, arbitrary temporary current directory: home resolves to `Path.home() / ".haxjobs"`.
2. `HAXJOBS_HOME=<tmp>/profile-a`: all state and provider paths resolve under that directory.
3. Importing config does not read a root `haxjobs.toml` and does not create files.
4. Calling the explicit runtime initializer creates only the required home/state directories and uses restrictive POSIX modes when supported.

Run the focused test first and confirm it fails under the current checkout-derived config.

### Task 2: Implement a tiny global-path module

**Files:**
- Modify: `src/haxjobs/config.py`

Delete TOML parsing and all legacy product settings from this runtime path module. Keep only named paths used by current greenfield code:

```python
HAXJOBS_HOME
PROVIDER_CONFIG_PATH
STATE_DIR
CAREER_DB_PATH
SESSION_DB_PATH


def ensure_runtime_home() -> None: ...
```

Use `Path(os.environ.get("HAXJOBS_HOME", Path.home() / ".haxjobs")).expanduser()`.

`ensure_runtime_home()` must create `HAXJOBS_HOME` and `STATE_DIR`, with `parents=True`, `exist_ok=True`, and POSIX mode `0o700`. Do not create provider config until setup writes it. Do not include a migration from the old repo-root config. The user can set `HAXJOBS_HOME` explicitly for a development profile.

Run focused tests, then the full suite.

### Task 3: Share the provider configuration path

**Files:**
- Modify: `src/haxjobs/model/client.py`
- Test: `tests/test_model_streaming.py`

Replace the client-local `Path.home()` constant with `PROVIDER_CONFIG_PATH` from config. Preserve explicit `credentials_path` injection for tests.

Add a regression showing `HAXJOBS_HOME` changes the default credentials location. Never place an API key in a test or report.

## Phase 2: Make first-run setup honest

### Task 4: Write setup command tests

**Files:**
- Create: `tests/test_setup_cli.py`
- Create: `src/haxjobs/interfaces/setup_cli.py`
- Modify: `src/haxjobs/cli.py`

Test setup with monkeypatched `input` and `getpass.getpass`:

1. It creates the configured home and writes a TOML file with name, model, base URL, and API key.
2. The written config has provider fields expected by `OpenAIModelClient`.
3. Re-running setup requires explicit overwrite confirmation. Declining leaves existing content unchanged.
4. POSIX permissions are `0600` when the platform supports them.
5. Setup never imports or instantiates `AsyncOpenAI`.

### Task 5: Implement `haxjobs setup`

**Files:**
- Create: `src/haxjobs/interfaces/setup_cli.py`
- Modify: `src/haxjobs/cli.py`

Add one `setup` subcommand. Prompts are deliberately small:

```text
Provider name [deepseek]:
Model [deepseek-v4-flash]:
Base URL [https://api.deepseek.com/v1]:
API key:
```

Use `getpass.getpass` for the key. Reject an empty key. Write TOML using a small local string formatter with values escaped for TOML strings. Write atomically through a same-directory temporary file, chmod it `0600`, then replace the destination. Do not log or print the key.

When a normal non-fake chat cannot find provider config, print only:

```text
No provider is configured. Run `haxjobs setup`.
```

When career data is missing, keep the current fixture-migration guidance. A fake chat must continue to run without provider configuration.

### Task 6: Initialize runtime only for real commands

**Files:**
- Modify: `src/haxjobs/cli.py`
- Test: `tests/test_cli.py`

Call `ensure_runtime_home()` after argparse has accepted a command and before setup, chat, profile, or migrate execution. `haxjobs --help` must not create `~/.haxjobs`.

The bare `haxjobs` path must still resume the latest session and open terminal chat. It must behave the same from two different temporary current directories when they share `HAXJOBS_HOME`.

## Phase 3: Prove the wheel is actually usable

### Task 7: Add a no-network wheel verifier

**Files:**
- Create: `scripts/verify-wheel-install.py`

Write a standard-library Python script that:

1. Builds the wheel with `uv build`.
2. Creates a temporary virtual environment with `uv venv`.
3. Installs the newly built local wheel only. No index, no network.
4. Uses a temporary `HAXJOBS_HOME` and a temporary working directory outside the repo.
5. Runs `haxjobs --help`.
6. Runs `haxjobs setup` with scripted stdin or a test-only safe noninteractive path. If the production command cannot safely accept scripted input, call the setup function from a short isolated Python script instead.
7. Runs fixture migration using the tracked synthetic career fixture.
8. Runs a fake new chat and a fake resume through a PTY or the existing terminal test helper.
9. Asserts provider config, career DB, and session DB all live under the temporary home, never under the checkout.

The verifier must not read the operator's home, credentials, or state. It must leave its temporary directory cleaned up unless a failure needs a printed path.

### Task 8: Add narrow package-install regression coverage

**Files:**
- Create or modify: `tests/test_wheel_install.py`

Only add a pytest wrapper if the wheel check runs quickly and reliably with local dependencies. Otherwise keep the expensive full fresh-install proof in `scripts/verify-wheel-install.py` and unit-test its command/path construction. Do not make every normal test suite rebuild a wheel.

## Phase 4: Docs and delivery proof

### Task 9: Refresh current docs

**Files:**
- Modify: `README.md`
- Modify: `docs/HAXJOBS.md`
- Modify: `docs/GETTING_STARTED.md`

Document the exact user flow:

```bash
uv tool install haxjobs
haxjobs setup
haxjobs
```

Explain that runtime data lives in `~/.haxjobs`, `HAXJOBS_HOME` is for isolated profiles and tests, and current directory is not career state. Do not promise a PyPI upload before one happens.

### Task 10: Create delivery evidence

Create the delivery folder with a copied plan, implementation report, rubric, manual proof, and two clean Draw.io diagrams:

- `runtime-home`: installed package, `~/.haxjobs`, state DBs, provider TOML, optional current directory.
- `install-flow`: build wheel, fresh environment, setup, migrate synthetic fixture, fake chat, resume.

Both diagrams need valid XML, readable PNGs, orthogonal connectors, and no file-path soup inside nodes. Keep each under 35 non-root cells.

## Required verification

```bash
PYTHONPATH=src:. uv run -- python3 -m pytest -q tests/
PYTHONPATH=src:. uv run -- python3 -m py_compile $(find src tests -name '*.py')
uv lock --check
git diff --check
PYTHONPATH=src:. uv run -- python3 scripts/verify-wheel-install.py
```

Also run:

```bash
HAXJOBS_HOME="$(mktemp -d)" PYTHONPATH=src:. uv run -- haxjobs --help
```

It must not create files for help output.

## Stop conditions

Stop and report instead of guessing if:

- A clean wheel needs checkout-only data files to launch.
- A provider setup path would expose API keys through argv, logs, tests, or reports.
- Fake chat or session resume requires a live provider.
- The installer writes outside its temporary `HAXJOBS_HOME`.
- A requested change would turn the current directory into implicit career state.

## Completion report

The implementation report must list changed paths, exact test count, wheel filename, fresh-install command results, artifact checks, and any deferred PyPI upload. It must say that PyPI publication itself needs an owner-controlled token and version decision.
