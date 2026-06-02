# HaxJobs Profile and Account Data Setup

HaxJobs needs two different kinds of user data:

1. Profile/application facts that Hermes can reuse.
2. Job-platform access information that helps Hermes know where the user has accounts.

Important boundary: do **not** store raw passwords in this repo.

## Where local development data lives

Use ignored local files under:

```text
data/private/
```

Suggested main file:

```text
data/private/arinze_profile.local.json
```

That file can contain career facts, saved answers, platform usernames/emails, job-search preferences, and automation preferences.

It should not contain:

- raw passwords
- one-time codes
- backup codes
- full session cookies exported from a browser
- secrets that should live in a password manager

## Credential policy

For LinkedIn, Reed, Indeed, Workday, Greenhouse, Lever, Ashby, and similar platforms:

- Store account presence and login identifier only, for example email/username.
- Store whether manual login is required.
- Store whether the platform is approved for assisted apply.
- Use manual browser login/session reuse later when we implement assisted apply.
- Ask for approval before final submit or before sending outreach.

Good:

```json
{
  "platform": "linkedin",
  "account_status": "active",
  "login_identifier": "name@example.com",
  "manual_login_required": true,
  "assisted_apply_enabled": false
}
```

Bad:

```json
{
  "platform": "linkedin",
  "password": "real-password-here"
}
```

## Sensitive saved answers

Some answers can be reused, but they should still be flagged by sensitivity.

Examples:

- work authorization
- sponsorship requirement
- salary expectations
- notice period / availability
- disability/equal-opportunity forms
- criminal/legal declarations
- demographic questions

Sensitivity levels:

```text
normal               safe to reuse in generated drafts
review_before_use    show before using/submitting
legal_sensitive      never final-submit without fresh approval
never_auto_answer    do not answer automatically
```

## How this supports development

During 0.1.x and 0.2.x, this JSON gives us realistic local data for:

- UserProfile
- ProfileFact
- SavedAnswer
- platform source settings
- HermesTask inputs
- ApprovalCheckpoint examples

Later, HaxJobs should replace manual JSON editing with a profile/survey UI where Hermes can ask questions through HaxJobs.
