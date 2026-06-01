# HaxJobs Browser Extension

## Purpose

The browser extension lets users save jobs while browsing normally, even when Hermes is not online.

It should be boring, reliable, and low-friction.

## MVP behavior

A user clicks:

```text
Save to HaxJobs
```

The extension captures:

- current URL
- page title
- visible page text
- selected text if any
- source platform guess
- timestamp
- optional user note

Then it sends that payload to HaxJobs as a `JobSourceSnapshot`.

## Why snapshots first

Job boards are inconsistent. LinkedIn, Indeed, Reed, Workday, Greenhouse, Lever, Ashby, and company pages all structure data differently.

The extension should not try to perfectly parse everything in v1.

Instead:

```text
Extension captures raw context
→ HaxJobs stores it
→ Hermes normalizes it later
```

This makes the extension simple and resilient.

## Source detection

Initial source detection can be URL-based:

```text
linkedin.com/jobs → linkedin
indeed.com → indeed
reed.co.uk → reed
myworkdayjobs.com → workday
greenhouse.io → greenhouse
lever.co → lever
ashbyhq.com → ashby
otherwise → company_site or unknown
```

## User notes

The extension should support a short note.

Examples:

- "Looks good, check sponsorship."
- "Maybe too senior."
- "Saw this on LinkedIn, find recruiter later."
- "Generate pack when Hermes is online."

## Privacy

The extension may capture sensitive page text.

Rules:

- only capture after explicit user click
- show what is being saved where possible
- do not capture passwords or form fields intentionally
- do not auto-save browsing history
- allow deletion from HaxJobs

## Future features

Later, the extension can add:

- quick fit estimate after saving
- save selected text as the JD
- show whether the job already exists in HaxJobs
- one-click "ask Hermes to analyze"
- one-click "generate pack"
- status badge for already-applied roles
