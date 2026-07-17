# Five-job development sample for the company-watch slice

## Why this file exists

This is the fixed five-job sample selected randomly from `state/haxjobs.db` on 17 July 2026. It gives the company-watch vertical slice real data to walk through before the new system is designed or built.

The selected job IDs are:

- `49`
- `203`
- `312`
- `328`
- `374`

The old database is development evidence only. Its tables, classifications, scores, and mistakes do not define the greenfield data model.

## What is preserved here

For each job this file records:

- every field from the current `jobs` row
- the complete job-description content currently stored for that job
- the job-specific fields from the linked `evaluations` row
- whether decisions, packs, outreach contacts, or outreach drafts exist
- obvious data-quality problems that the new slice must handle

The `profile_snapshot_json` value is `{}` for all five evaluations.

Each evaluation also points to the same 170,691-character `report_markdown` value for cycle `test-run-2026-06-29`. That value is a cycle-wide report covering 376 jobs, not a report about the individual job. It is not duplicated five times here. Its presence and size are recorded because this is itself a data-model problem.

## Sample summary

| Job ID | Stored title | Stored company | Source | Fit | Stored description |
|---:|---|---|---|---:|---|
| 49 | IT Support Analyst | trainline | Ashby API | 12, Skip | 5,000 characters, cut off mid-sentence |
| 203 | Applied ML Researcher, Fully Remote, up to $90/hr | LinkedIn | LinkedIn local | 38, Weak fit | 156-character title and URL stub |
| 312 | Associate Data Platform Engineer, Cyber Data Platform | LinkedIn | LinkedIn local | 52, Good fit | 166-character title and URL stub |
| 328 | Software Engineer, Mid-Level, Full Stack | LinkedIn | LinkedIn local | 68, Good fit | 149-character title and URL stub |
| 374 | Java Full Stack Developer | LinkedIn | LinkedIn local | 42, Weak fit | 114-character title and URL stub |

# Job 49: Trainline IT Support Analyst

## Stored job row

| Field | Stored value |
|---|---|
| `id` | `49` |
| `external_id` | `20260607-174539_ashby_api_trainline_IT_Support_Analyst.json` |
| `title` | `IT Support Analyst` |
| `company` | `trainline` |
| `location` | `London` |
| `source_url` | [Ashby application page](https://jobs.ashbyhq.com/trainline/f240bf55-4683-4284-8222-e7cd0c227d70/application) |
| `source` | `ashby_api` |
| `source_quality` | `direct` |
| `status` | `skipped` |
| `discovered_at` | `2026-06-07 20:50:29` |
| `updated_at` | `2026-06-11 18:25:39` |
| `role_family` | `platform_backend` |
| `role_family_confidence` | `0.30` |
| `recommended_cv_variant` | `platform_backend` |
| `role_family_terms` | `platform`, `cloud`, `azure` |
| `classified_at` | `2026-06-11 18:25:39` |
| `pack_status` | `none` |
| `pack_review_status` | `none` |
| `pack_review_notes` | empty |
| `pack_reviewed_at` | null |
| `pack_dir` | empty |
| `outreach_status` | `none` |

## Complete stored description content

The database stores exactly 5,000 characters and cuts off during the final candidate section. The content contains:

### Company context

- Trainline describes itself as a rail and coach travel platform operating through its mobile app, website, and business partners.
- The listing claims more than 135 million monthly visits, £6.3 billion in annual ticket sales, more than 270 rail and coach partners, operations across more than 40 countries, and a team of more than 1,000 people.
- Named office locations include London, Paris, Barcelona, Milan, Edinburgh, and Madrid.

### Team and role

- The role sits in Workplace Technology and the Tech Support team.
- It is a Tier 2 internal IT-support role, not a software-engineering role.
- The estate includes managed MacOS devices, Windows devices, Azure Active Directory, Windows Server, meeting-room equipment, and internal event support.

### Stored responsibilities

- Manage the ticket lifecycle, dashboards, workloads, and reporting.
- Resolve incidents within service-level targets and escalate to Tier 3 teams.
- Troubleshoot issues and perform root-cause analysis.
- Progress service requests and support internal employees through the IT-service platform, collaboration tools, and an onsite Tech Bar.
- Manage IT assets, hardware refreshes, inventory, secure disposal, onboarding, offboarding, laptop builds, access changes, and asset retrieval.
- Support meeting-room audio and video equipment, remote administration, internal events, security checks, audits, technical documentation, and knowledge sharing.
- Explore automation, AI, and ML for internal process improvements.

### Stored technical requirements

- Windows 11, MacOS, Android, and Linux familiarity.
- JAMF, Intune, mobile-device management, Microsoft 365, Slack, and Atlassian products.
- Active Directory, Azure Active Directory, SaaS systems, and cloud-migration knowledge.
- PCI-DSS, ISO 20071 as written in the source, IT governance, TCP/IP, DNS, DHCP, LAN, WAN, and wireless networking.
- Basic PowerShell, Windows command line, Apple scripting, Bash, security tools, IT-service systems, video-conferencing equipment, Autopilot, MFA, SSO, SAML, and cloud printing.
- Desirable certifications include Microsoft Endpoint Administrator Associate, Apple or JAMF certificates, and CompTIA A+.

### Truncation

The stored description ends during the phrase `resolve issues`. Any content after that point was not kept by the old ingestion path.

## Stored evaluation

| Field | Stored value |
|---|---|
| `evaluation_id` | `52` |
| `fit_score` | `12` |
| `fit_verdict` | `SKIP` |
| `level` | `4` |
| `level_name` | `Skip` |
| `sponsorship_risk` | `low` |
| `evaluation_decision` | `skipped` |
| `evaluated_by` | `hermes` |
| `evaluated_at` | `2026-06-08 11:00:41` |
| `role_type` | empty |
| `agent` | empty |
| `profile_snapshot_json` | `{}` |
| `report_markdown` | 170,691-character cycle-wide report, omitted |
| `report_cycle_id` | `test-run-2026-06-29` |
| `evaluation_pack_dir` | empty |
| `pack_template_id` | empty |

Strongest matches recorded:

- London matches the user's location preference.
- Trainline is a known technology company.

Major gaps recorded:

- This is IT support, not software engineering.
- JAMF, Intune, Windows administration, meeting-room support, and ticket work do not match the Python, FastAPI, and AI track.
- The role has no meaningful coding, system-design, or AI-development work.

Stored summary: this is an enterprise IT-operations role with almost no overlap with the user's Python backend and AI-engineering direction.

Stored skip reason: the role type and technical work do not match the target career direction. The single automation and AI bullet is a process-improvement detail, not the role's main work.

## Related state

- Decisions: `0`
- Packs: none
- Outreach contacts: `0`
- Outreach drafts: `0`

## Data-quality observations

- The direct company identity and source are present.
- The description is substantial but cut off at an arbitrary 5,000-character boundary.
- The old classifier maps an IT-support role to `platform_backend`, even though the evaluation later rejects it as the wrong career track.
- `sponsorship_risk` is stored as `low` even though the description contains no recorded vacancy-level sponsorship evidence.

# Job 203: Mercor Applied ML Researcher

## Stored job row

| Field | Stored value |
|---|---|
| `id` | `203` |
| `external_id` | null |
| `title` | `Applied ML Researcher - Fully Remote | Upto $90/hr` |
| `company` | `LinkedIn` |
| `location` | `London, United Kingdom` |
| `source_url` | [LinkedIn listing](https://uk.linkedin.com/jobs/view/applied-ml-researcher-fully-remote-upto-%2490-hr-at-mercor-4426198337) |
| `source` | `linkedin_local` |
| `source_quality` | `linkedin` |
| `status` | `evaluated` |
| `discovered_at` | `2026-06-13 21:25:00` |
| `updated_at` | `2026-06-14 09:24:40` |
| `role_family` | `ai_engineer_llm` |
| `role_family_confidence` | `0.20` |
| `recommended_cv_variant` | `ai_engineer_llm` |
| `role_family_terms` | `ml` |
| `classified_at` | null |
| `pack_status` | `none` |
| `pack_review_status` | `none` |
| `pack_review_notes` | empty |
| `pack_reviewed_at` | null |
| `pack_dir` | empty |
| `outreach_status` | `none` |

## Complete stored description content

The stored description is only this 156-character stub:

```text
Applied ML Researcher - Fully Remote | Upto $90/hr, https://uk.linkedin.com/jobs/view/applied-ml-researcher-fully-remote-upto-%2490-hr-at-mercor-4426198337
```

No responsibilities, requirements, seniority evidence, employer description, closing date, work-authorization wording, or sponsorship wording are stored.

## Stored evaluation

| Field | Stored value |
|---|---|
| `evaluation_id` | `225` |
| `fit_score` | `38` |
| `fit_verdict` | `WEAK_FIT` |
| `level` | `3` |
| `level_name` | `Lite` |
| `sponsorship_risk` | `low` |
| `evaluation_decision` | `completed` |
| `evaluated_by` | `hermes` |
| `evaluated_at` | `2026-06-14 09:24:40` |
| `role_type` | empty |
| `agent` | empty |
| `profile_snapshot_json` | `{}` |
| `report_markdown` | 170,691-character cycle-wide report, omitted |
| `report_cycle_id` | `test-run-2026-06-29` |
| `evaluation_pack_dir` | empty |
| `pack_template_id` | empty |

Strongest matches recorded:

- Applied AI and ML product experience from Pharmax.
- Model training and fine-tuning with Hugging Face and PyTorch.
- Remote UK work matches the user's stated preferences.

Major gaps recorded:

- The pay level suggests a senior or specialist researcher role above the user's current target.
- The researcher title may require academic research evidence that the user does not have.
- The missing description prevents verification of the actual stack and expectations.

Stored summary: the pay and researcher title point toward an experienced hire. The user's applied AI work is relevant, but it does not prove an academic or research background.

## Related state

- Decisions: `0`
- Packs: none
- Outreach contacts: `0`
- Outreach drafts: `0`

## Data-quality observations

- `company` stores the discovery surface, LinkedIn, rather than the employer, Mercor.
- `external_id` is null even though the LinkedIn URL contains job ID `4426198337`.
- The evaluation makes detailed claims from a record that contains no real description.
- `sponsorship_risk` is `low` without stored sponsorship evidence.

# Job 312: Associate Data Platform Engineer

## Stored job row

| Field | Stored value |
|---|---|
| `id` | `312` |
| `external_id` | null |
| `title` | `Associate Data Platform Engineer - Cyber Data Platform` |
| `company` | `LinkedIn` |
| `location` | `London, United Kingdom` |
| `source_url` | [LinkedIn listing](https://uk.linkedin.com/jobs/view/associate-data-platform-engineer-cyber-data-platform-at-hackajob-4409930992) |
| `source` | `linkedin_local` |
| `source_quality` | `linkedin` |
| `status` | `evaluated` |
| `discovered_at` | `2026-06-13 21:25:02` |
| `updated_at` | `2026-06-14 11:02:40` |
| `role_family` | `platform_backend` |
| `role_family_confidence` | `0.99` |
| `recommended_cv_variant` | `platform_backend` |
| `role_family_terms` | `platform` |
| `classified_at` | null |
| `pack_status` | `none` |
| `pack_review_status` | `none` |
| `pack_review_notes` | empty |
| `pack_reviewed_at` | null |
| `pack_dir` | empty |
| `outreach_status` | `none` |

## Complete stored description content

The stored description is only this 166-character stub:

```text
Associate Data Platform Engineer - Cyber Data Platform, https://uk.linkedin.com/jobs/view/associate-data-platform-engineer-cyber-data-platform-at-hackajob-4409930992
```

No employer identity, responsibilities, requirements, source evidence, work-mode details, closing date, or sponsorship wording are stored in the job row.

## Stored evaluation

| Field | Stored value |
|---|---|
| `evaluation_id` | `353` |
| `fit_score` | `52` |
| `fit_verdict` | `GOOD_FIT` |
| `level` | `2` |
| `level_name` | `Quick Apply` |
| `sponsorship_risk` | `medium` |
| `evaluation_decision` | `completed` |
| `evaluated_by` | `hermes` |
| `evaluated_at` | `2026-06-14 11:02:40` |
| `role_type` | empty |
| `agent` | empty |
| `profile_snapshot_json` | `{}` |
| `report_markdown` | 170,691-character cycle-wide report, omitted |
| `report_cycle_id` | `test-run-2026-06-29` |
| `evaluation_pack_dir` | empty |
| `pack_template_id` | empty |

Strongest matches recorded:

- The evaluation describes it as entry level in London with blended working.
- Python and SQL match the user's existing skills.
- The evaluation says the role includes ML and generative-AI work for threat detection and analytics.

Major gaps recorded:

- Airflow, DBT, Kafka, and Spark are not in the user's current evidence.
- The evaluation identifies Azure and Databricks as stack gaps.
- Data-platform engineering is adjacent to, but not the same as, the active backend and AI direction.

Stored summary: the evaluation identifies Tesco as the employer and treats this as an entry-level London role with relevant Python, SQL, ML, and generative-AI work, but with several data-platform tooling gaps.

## Related state

- Decisions: `0`
- Packs: none
- Outreach contacts: `0`
- Outreach drafts: `0`

## Data-quality observations

- `company` stores LinkedIn rather than the employer.
- The URL identifies Hackajob as the LinkedIn advertiser, while the evaluation identifies Tesco as the employer. These are three different entities collapsed into one unclear company field.
- `external_id` is null even though the URL contains LinkedIn job ID `4409930992`.
- The job row cannot support the detailed evaluation claims because it contains no actual description.

# Job 328: Oritain Software Engineer

## Stored job row

| Field | Stored value |
|---|---|
| `id` | `328` |
| `external_id` | null |
| `title` | `Software Engineer (Mid-Level) - Full Stack` |
| `company` | `LinkedIn` |
| `location` | `London, United Kingdom` |
| `source_url` | [LinkedIn listing](https://uk.linkedin.com/jobs/view/software-engineer-mid-level-%E2%80%93-full-stack-at-oritain-4422048576) |
| `source` | `linkedin_local` |
| `source_quality` | `linkedin` |
| `status` | `evaluated` |
| `discovered_at` | `2026-06-13 21:25:02` |
| `updated_at` | `2026-06-14 11:16:59` |
| `role_family` | `fullstack_python_react` |
| `role_family_confidence` | `0.99` |
| `recommended_cv_variant` | `fullstack_python_react` |
| `role_family_terms` | `full stack` |
| `classified_at` | null |
| `pack_status` | `none` |
| `pack_review_status` | `none` |
| `pack_review_notes` | empty |
| `pack_reviewed_at` | null |
| `pack_dir` | empty |
| `outreach_status` | `none` |

## Complete stored description content

The stored description is only this 149-character stub:

```text
Software Engineer (Mid-Level) - Full Stack, https://uk.linkedin.com/jobs/view/software-engineer-mid-level-%E2%80%93-full-stack-at-oritain-4422048576
```

No responsibilities, requirements, employer description, salary, closing date, work mode, or sponsorship wording are stored.

## Stored evaluation

| Field | Stored value |
|---|---|
| `evaluation_id` | `370` |
| `fit_score` | `68` |
| `fit_verdict` | `GOOD_FIT` |
| `level` | `2` |
| `level_name` | `Quick Apply` |
| `sponsorship_risk` | `low` |
| `evaluation_decision` | `completed` |
| `evaluated_by` | `hermes` |
| `evaluated_at` | `2026-06-14 11:16:59` |
| `role_type` | empty |
| `agent` | empty |
| `profile_snapshot_json` | `{}` |
| `report_markdown` | 170,691-character cycle-wide report, omitted |
| `report_cycle_id` | `test-run-2026-06-29` |
| `evaluation_pack_dir` | empty |
| `pack_template_id` | empty |

Strongest matches recorded:

- Python, Django, and FastAPI align with the user's backend work.
- The evaluation considers the employer's AI-assisted development culture relevant to Haxaml and agent work.
- The London location and company mission were treated as positives.

Major gaps recorded:

- The mid-level title may expect more commercial experience.
- TypeScript and frontend depth are weaker than the user's Python backend work.
- The evaluation identifies limited cloud-platform evidence.

Stored summary: the evaluation identifies Oritain as the employer and considers the role a good fit, with mid-level experience, TypeScript, and cloud depth as the main reservations.

## Related state

- Decisions: `0`
- Packs: none
- Outreach contacts: `0`
- Outreach drafts: `0`

## Data-quality observations

- `company` stores LinkedIn rather than Oritain.
- `external_id` is null even though the URL contains LinkedIn job ID `4422048576`.
- The database gives a confident fit score from a title-and-URL stub.
- `sponsorship_risk` is `low` without vacancy-level sponsorship evidence.
- The evaluation recommends a quick application pack, but no pack or user decision exists.

# Job 374: Java Full Stack Developer

## Stored job row

| Field | Stored value |
|---|---|
| `id` | `374` |
| `external_id` | null |
| `title` | `Java Full stack Developer` |
| `company` | `LinkedIn` |
| `location` | `United Kingdom` |
| `source_url` | [LinkedIn listing](https://uk.linkedin.com/jobs/view/java-full-stack-developer-at-npaworldwide-4416111313) |
| `source` | `linkedin_local` |
| `source_quality` | `linkedin` |
| `status` | `evaluated` |
| `discovered_at` | `2026-06-13 21:25:02` |
| `updated_at` | `2026-06-14 11:53:55` |
| `role_family` | `fullstack_python_react` |
| `role_family_confidence` | `0.99` |
| `recommended_cv_variant` | `fullstack_python_react` |
| `role_family_terms` | `full stack` |
| `classified_at` | null |
| `pack_status` | `none` |
| `pack_review_status` | `none` |
| `pack_review_notes` | empty |
| `pack_reviewed_at` | null |
| `pack_dir` | empty |
| `outreach_status` | `skip_mismatch` |

## Complete stored description content

The stored description is only this 114-character stub:

```text
Java Full stack Developer, https://uk.linkedin.com/jobs/view/java-full-stack-developer-at-npaworldwide-4416111313
```

No responsibilities, requirements, employer identity, location detail, security-clearance wording, work mode, closing date, or sponsorship wording are stored.

## Stored evaluation

| Field | Stored value |
|---|---|
| `evaluation_id` | `417` |
| `fit_score` | `42` |
| `fit_verdict` | `WEAK_FIT` |
| `level` | `3` |
| `level_name` | `Lite` |
| `sponsorship_risk` | `medium` |
| `evaluation_decision` | `completed` |
| `evaluated_by` | `hermes` |
| `evaluated_at` | `2026-06-14 11:53:55` |
| `role_type` | empty |
| `agent` | empty |
| `profile_snapshot_json` | `{}` |
| `report_markdown` | 170,691-character cycle-wide report, omitted |
| `report_cycle_id` | `test-run-2026-06-29` |
| `evaluation_pack_dir` | empty |
| `pack_template_id` | empty |

Strongest matches recorded:

- The evaluation treats the role as entry level.
- React and full-stack product experience are relevant.
- Agile work from Vigilis and Bucca Hut was treated as transferable.

Major gaps recorded:

- Java is the main language and Python is not mentioned.
- The evaluation identifies Cheltenham as outside the user's preferred cities.
- The evaluation infers that government and defence work may require security clearance.

Stored summary: the evaluation describes an entry-level Java role at a government and defence consultancy through NPAworldwide. React and general full-stack experience overlap, but the Java-first stack, location, and possible clearance requirements reduce the fit.

## Related state

- Decisions: `0`
- Packs: none
- Outreach contacts: `0`
- Outreach drafts: `0`

## Data-quality observations

- `company` stores LinkedIn instead of the recruiter, consultancy, or end employer.
- `external_id` is null even though the URL contains LinkedIn job ID `4416111313`.
- The role is classified as `fullstack_python_react` with `0.99` confidence despite being Java-first.
- The location and clearance details used in evaluation are absent from the stored job description.
- `outreach_status` says `skip_mismatch`, while the main job status remains `evaluated` and no user decision exists.

# Cross-sample findings

These five jobs already give the vertical slice several real problems to solve:

## Company and source identity

Four of the five LinkedIn records use `LinkedIn` as the company. The source platform, advertiser, recruiter, actual employer, and possible end client need separate identities and relationships.

## Job identity and deduplication

Four records have null `external_id` values even though their URLs contain stable LinkedIn job IDs. A company watch cannot reliably suppress duplicates or track changed and closed roles without source-specific identity.

## Source completeness

Only one job has a substantial stored description, and that description is cut off. The other four are title-and-URL stubs. The new system must distinguish a discovered lead from a verified vacancy with enough content to assess.

## Evaluation evidence

Several evaluations make detailed claims that cannot be traced to the stored job row. A new evaluation must record which source snapshot supports each material claim and when it was fetched.

## Sponsorship uncertainty

The current `sponsorship_risk` values do not carry their evidence. Company sponsor status, general employer policy, and vacancy-level sponsorship must remain separate claims.

## User profile traceability

All five `profile_snapshot_json` values are empty. The evaluations refer to the user's skills, preferred locations, level, and work authorization without preserving the profile facts used at evaluation time.

## Outcome continuity

All five jobs were evaluated, but none has a user decision. One recommends a quick application pack, yet no pack exists. The new slice needs a clear handoff from finding to update to user response to later outcome.

## Mixed state fields

Job, evaluation, pack, outreach, and decision status are split across several columns and tables with unclear ownership. The new model should derive these states from the real workflow rather than copying the old status vocabulary.

# How this fixture should be used

Walk each job through the new company-watch slice and ask:

1. Is this a company, a source listing, a recruiter listing, or only a lead?
2. What facts are verified from a current source?
3. What is missing before Hax can call it a real vacancy?
4. Which user facts are needed to judge hard constraints?
5. Should this role be ignored, investigated, reported, or evaluated more deeply?
6. What identity prevents it from being reported twice?
7. What update would Hax send, with what uncertainty?
8. What user decision or later outcome should be saved?

The goal is not to preserve the old answers. The goal is to make the new product handle these real records honestly.
