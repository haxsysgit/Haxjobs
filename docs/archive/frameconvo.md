# frameconvo.md — Typed Validation for AI Agent Outputs

**Context:** A conversation about why AI agents hallucinate immutable facts,
and how code-level enforcement prevents it when prompt-level instructions cannot.

---

## Part 1: The Problem — Why Prompts Can't Solve This

### Scenario A: The University Name

You tell an agent:

> "Generate a CV. My university is Middlesex University London."

The agent writes the CV. Halfway through the Professional Summary, it generates the word "Hertfordshire" instead of "Middlesex." Why?

Because the agent isn't *copying* the university name — it's *generating* it from the same probability distribution that produces every other word. "University of [London university]" is a pattern. "Hertfordshire" is a plausible completion. One token of drift and the fact is wrong.

The prompt said "Middlesex." The agent read it. It still wrote Hertfordshire.

**Why prompts fail:** Prompts influence the *direction* of generation but not the *precision* of individual tokens. For any token the agent generates, there's a non-zero probability of a wrong but plausible alternative. The longer the output, the more chances for drift.

### Scenario B: The Project Claim

You tell an agent:

> "Pharmax is a pharmacy management platform. The public repo shows products CRUD, invoices, stock adjustments, and pytest. Do not claim AI features that aren't in the public README."

The agent writes:

> "Integrated AI-powered features for intelligent product queries and inventory insights on top of the operational backend."

Why? Because the agent's training data links "modern SaaS platform" to "AI features." The instruction "do not invent AI features" is a negation — and LLMs are bad at negations. The word "AI" is in the prompt (in the negation), which makes it *more* likely to appear in the output, not less. This is the "don't think of a white bear" problem — mentioning the forbidden thing increases its probability.

**Why prompts fail:** Negations are not gates. Telling an agent what NOT to do primes it to do exactly that.

### Scenario C: The Private Repo Link

You tell an agent:

> "List my projects. Pharmax-backend is private — don't link to it."

The agent generates:

> [github.com/haxsysgit/Pharmax-backend](https://github.com/haxsysgit/Pharmax-backend)

Why? Because the agent's training associates "project" with "GitHub link." The pattern is so strong that the instruction to suppress it gets overridden. The agent sees the repo name in context, the URL is a natural completion, and out it comes.

**Why prompts fail:** Statistical patterns in training data are stronger than instructions in a prompt. The agent's default mode is "include the link" — suppressing it requires the instruction to overcome millions of training examples.

---

## Part 2: The Solution — Code-Level Enforcement

The pattern is always the same:

```
SOURCE OF TRUTH  →  LLM GENERATION  →  VALIDATOR  →  SHIP
   (locked data)      (free text)       (code gate)    (output)
```

The validator is a Python script. It is not a prompt. It is not an LLM. It is deterministic code that checks specific things and returns pass/fail.

### How It Works: Three Validation Strategies

#### Strategy 1: Exact Match — "This must be here"

**Use when:** A piece of text must appear verbatim in the output.

**Example:** University name.

```python
# In the profile (cv_profile.typed.json):
"university": "Middlesex University London"

# In the validator (cv_validator.py):
def check_locked_constants(cv_text, profile):
    violations = []
    for key, value in profile["locked"].items():
        if value not in cv_text:
            violations.append(f"MISSING: '{key}' → '{value}' not found in CV")
    return violations
```

**What happens:** The validator opens the generated CV, reads every line, and checks if "Middlesex University London" appears anywhere. If it doesn't — or if the agent wrote "University of Hertfordshire" — the check fails. PDF export is blocked.

**Why this works:** The agent can write "Hertfordshire" but the validator will grep for "Middlesex University London" and fail if it's missing. The agent can't pass the check with the wrong value. There's no way to "prompt engineer" around a string match.

#### Strategy 2: Absence Check — "This must NOT be here"

**Use when:** Certain words or phrases must never appear in the output.

**Example:** Forbidden claims about Pharmax.

```python
# In the profile:
"pharmax": {
    "blocked_claims": [
        "AI-powered", "AI-assisted", "intelligent queries",
        "inventory insights", "machine learning", "LLM-powered"
    ]
}

# In the validator:
def check_forbidden_claims(cv_text, projects):
    violations = []
    for proj_name, proj in projects.items():
        for claim in proj["blocked_claims"]:
            if claim.lower() in cv_text.lower():
                violations.append(
                    f"FORBIDDEN: '{claim}' found in {proj_name} section"
                )
    return violations
```

**What happens:** Even if the agent writes "Integrated AI-powered features for intelligent product queries," the validator finds "AI-powered" and "intelligent queries" in the text and fails the build. The agent cannot sneak a forbidden claim past a substring match.

**Why this works:** The validator doesn't care *why* the agent wrote it. It doesn't negotiate. It just checks: does this string appear? If yes, fail. No ambiguity.

#### Strategy 3: Membership Gate — "Only these are allowed"

**Use when:** The output should only reference items from an approved list.

**Example:** Repo URLs in CV.

```python
# In the profile:
"pharmax": {
    "repo_url": "https://github.com/haxsysgit/Pharmax-backend",
    "show_url": false   # ← do not include this URL in the CV
},
"haxaml": {
    "repo_url": "https://github.com/haxsysgit/haxaml",
    "show_url": true    # ← this one is fine to include
}

# In the validator:
def check_repo_visibility(cv_text, projects):
    import re
    violations = []
    urls_found = re.findall(r'github\.com/haxsysgit/(\S+)', cv_text)
    
    for found_repo in urls_found:
        found_repo = found_repo.rstrip('/').rstrip(')')
        for proj_name, proj in projects.items():
            if proj.get("repo_url") and found_repo in proj["repo_url"]:
                if not proj.get("show_url", True):
                    violations.append(
                        f"PRIVATE REPO: {proj_name} URL found but show_url=false"
                    )
    return violations
```

**What happens:** The validator finds all GitHub URLs in the CV, cross-references them against the project registry, and fails if any URL belongs to a project with `show_url: false`. Even if the agent writes the Pharmax link 10 times, the validator catches it.

**Why this works:** The agent can generate URLs freely. The validator checks them against an allowlist. Anything not on the allowlist is flagged. This is the same pattern as a firewall — allow by default is dangerous, deny by default is safe.

---

## Part 3: The Full Picture — A Real Validation Run

Let's walk through what happens when the validator runs against the broken Palantir CV:

```bash
$ python3 cv_validator.py Palantir_broken_CV.md cv_profile.typed.json

============================================================
FAILED: LOCKED CONSTANTS (1 violation)
============================================================
  ✗ MISSING: 'university' → 'Middlesex University London' not found in CV

============================================================
FAILED: WRONG UNIVERSITIES (1 violation)
============================================================
  ✗ 'Hertfordshire' found but 'Middlesex University London' missing

============================================================
FAILED: FORBIDDEN CLAIMS (2 violations)
============================================================
  ✗ FORBIDDEN: 'AI-powered' found in pharmax section
  ✗ FORBIDDEN: 'intelligent queries' found in pharmax section

============================================================
FAILED: PRIVATE REPOS (1 violation)
============================================================
  ✗ PRIVATE REPO: pharmax URL found but show_url=false

============================================================
PASSED: EM DASHES (0 found)
PASSED: BLOCKED VERBS (0 found)
PASSED: CLAUDE CODE (not found)
PASSED: SECTION COMPLETENESS (summary 72 words, 5 skill groups)
PASSED: EDUCATION ORDER (Middlesex before Aptech)

✗ 5 TOTAL VIOLATIONS — fix before PDF export
```

The agent produced a CV with 5 violations. The validator caught all 5. The PDF was never exported. Arinze never saw a broken CV.

Now the agent regenerates the CV with the violations fixed. Same validator runs again:

```bash
$ python3 cv_validator.py Palantir_fixed_CV.md cv_profile.typed.json

============================================================
PASSED: LOCKED CONSTANTS (all 18 fields present)
PASSED: WRONG UNIVERSITIES (0 found)
PASSED: FORBIDDEN CLAIMS (0 found)
PASSED: PRIVATE REPOS (0 found)
PASSED: EM DASHES (0 found)
PASSED: BLOCKED VERBS (0 found)
PASSED: CLAUDE CODE (not found)
PASSED: SECTION COMPLETENESS (summary 68 words, 5 skill groups)
PASSED: EDUCATION ORDER (Middlesex before Aptech)
PASSED: DATE FORMAT (all ranges valid)

✓ ALL CHECKS PASSED — CV is clean for PDF export
```

Now the PDF is generated. Arinze gets a CV he can actually use.

---

## Part 4: Why This Pattern Works (and Prompts Don't)

### The Fundamental Asymmetry

| | Prompt-based enforcement | Code-based enforcement |
|---|---|---|
| **What it is** | "Please don't do X" | `assert X not in output` |
| **Failure mode** | Silent. You don't know it failed until you read the output. | Loud. Exit code 1, violations printed to stdout. |
| **Bypassable?** | Yes. The agent can ignore the instruction. | No. The check runs regardless of what the agent wrote. |
| **Auditable?** | No. You'd have to manually read every word. | Yes. Every run produces a pass/fail log. |
| **Fixable?** | If it fails once, it'll fail again. Same prompt, same model, same drift. | If it fails, the violation tells you exactly what's wrong. Fix and rerun. |

### The "Don't Think of a White Bear" Problem

Every forbidden phrase in a prompt becomes *more* likely to appear in the output, not less. This is well-documented in LLM research — negations increase the probability of the negated term.

Example:

```
Prompt: "Do not claim AI-powered features for Pharmax."
Agent internal state: [Pharmax] [AI-powered] [features] → high activation
Output: "...built an AI-powered platform with intelligent features..."
```

The words "AI-powered" and "features" are right there in the prompt. The agent's attention mechanism lit them up. The instruction to suppress them creates tension, but the words are already activated — and in a long generation, activation wins over instruction.

Compare with validation:

```python
# The agent never sees this. It runs AFTER generation.
assert "AI-powered" not in cv_text
```

The agent has no idea the check exists. It cannot "game" it. It cannot be influenced by it. The check is invisible to the generation process and applies after the fact.

### The "Drift Accumulation" Problem

Every token the agent generates carries a small probability of error. Over 500 tokens (a typical CV), the probability that at least one token drifts is significant.

Prompt-based enforcement asks the agent to maintain perfect accuracy across all 500 tokens. Code-based enforcement only asks the agent to generate text — and then checks the ~20 tokens that actually matter (university name, dates, URLs, forbidden phrases).

This is the difference between "please be perfect" and "do your best, I'll check the important parts."

---

## Part 5: Beyond CVs — Where This Pattern Applies

### Email Generation

**Without validation:**

> Agent: "Your meeting is scheduled for Thursday, June 12th at 3pm."
> Reality: Thursday is June 14th.

**With validation:**

```python
def validate_meeting_email(email_text, calendar_event):
    violations = []
    # Check the date is correct
    if calendar_event.date_str not in email_text:
        violations.append(f"Date mismatch: expected {calendar_event.date_str}")
    # Check the day name matches the date
    expected_day = calendar_event.date_obj.strftime("%A")
    if expected_day not in email_text:
        violations.append(f"Day mismatch: {calendar_event.date_str} is a {expected_day}")
    # Check the time is correct
    if calendar_event.time_str not in email_text:
        violations.append(f"Time mismatch: expected {calendar_event.time_str}")
    return violations
```

### Report Generation

**Without validation:**

> Agent: "Revenue grew 47% year-over-year to £3.2M."
> Reality: Revenue grew 12% to £2.8M.

**With validation:**

```python
def validate_financial_report(report_text, metrics):
    violations = []
    for metric_name, metric in metrics.items():
        # Check the number appears somewhere near the metric name
        pattern = rf'{metric_name}.*?{metric["value"]}'
        if not re.search(pattern, report_text):
            violations.append(
                f"Metric '{metric_name}': expected value {metric['value']} "
                f"({metric['change']}%) not found in context"
            )
    return violations
```

### API Call Generation

**Without validation:**

> Agent generates: `requests.post("https://api.stripe.com/v1/charges")`
> But the codebase uses: `stripe.Charge.create()`

**With validation:**

```python
def validate_api_calls(code_text, allowed_patterns):
    violations = []
    for pattern in allowed_patterns["required"]:
        if pattern not in code_text:
            violations.append(f"Required pattern '{pattern}' not found")
    for pattern in allowed_patterns["forbidden"]:
        if pattern in code_text:
            violations.append(f"Forbidden pattern '{pattern}' found")
    return violations
```

---

## Part 6: The Meta Point

The reason this conversation matters is that it exposes a gap in how we think about AI agents.

The default assumption is: "If I tell the agent what to do clearly enough, it will do it correctly."

The reality is: "The agent will generate plausible text. Some of it will be wrong. The only way to guarantee correctness is to check the important parts with code."

This isn't a limitation of any specific model. It's a property of autoregressive text generation. Every token is a probability sample. Over enough tokens, errors are inevitable.

The shift is from **trust-based** to **verify-based** agent output handling:

| Trust-based | Verify-based |
|---|---|
| "The agent read the profile, so it knows my university." | "The validator will grep for Middlesex and fail if it's wrong." |
| "I told the agent not to include AI claims." | "The validator blocks any output containing 'AI-powered'." |
| "The agent should know not to link private repos." | "The validator cross-references every URL against an allowlist." |
| "I'll catch mistakes when I review." | "Mistakes are caught before I ever see the output." |

The CV governance system is one implementation of this pattern. The pattern itself applies anywhere an AI agent produces output that must contain or exclude specific facts.
