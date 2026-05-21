# CV Generation Playbook

This note is the practical guide for making HaxJobs better at CV and resume generation.

It is research-backed, but kept compact on purpose.

## Core Rule

HaxJobs should usually generate a tailored resume, not a full academic CV.

Use a full CV only for academic, research, fellowship, and some grant applications.

Use a federal-resume variant for USAJOBS and related U.S. federal applications.

## Universal Rules

These rules should apply to almost every non-academic resume:

- Tailor to one job description at a time.
- Keep the content profile-first and truthful; use evidence checks as internal guardrails.
- Prefer a simple, single-column, ATS-friendly layout.
- Use standard section names like `Summary`, `Experience`, `Education`, and `Skills`.
- Do not place critical content in headers, footers, tables, text boxes, or decorative layouts.
- Use strong action verbs and quantify outcomes where the candidate can defend them.
- Pull keywords from the JD, but only when the CV or user answers support them.
- Avoid generic AI-sounding summary text.
- Default to two pages for experienced private-sector candidates when the profile justifies it.
- Use one page for very early-career or sparse profiles.
- Never exceed three pages for standard private-sector roles; only academic, federal, or explicitly long-form applications should go longer.

## What Good Bullets Look Like

Strong bullets usually follow this pattern:

- action
- scope
- tool or method
- measurable result or concrete outcome

Example pattern:

- `Built X using Y, which improved Z`
- `Led X across Y stakeholders, reducing Z`
- `Analyzed X data with Y, enabling Z decision`

## Role Profiles

HaxJobs should not generate the same resume for every job family.

### Software Engineering

Emphasize:

- shipped systems
- APIs, backend, frontend, infra, testing, deployment
- architecture decisions
- reliability, performance, debugging, ownership

Good keyword buckets:

- languages
- frameworks
- cloud and infra
- testing and CI
- collaboration and mentoring

Avoid:

- long skill dumps with no evidence
- vague claims like `passionate engineer`

### Product Management

Emphasize:

- customer problems
- product decisions
- roadmap ownership
- cross-functional leadership
- metrics, experiments, launches, outcomes

Good keyword buckets:

- prioritization
- stakeholder management
- discovery
- analytics
- experimentation

Avoid:

- pure feature lists with no user or business impact

### Data / Analytics

Emphasize:

- SQL, Python, BI, modeling, experimentation
- data cleaning and analysis process
- dashboards, reports, business decisions enabled
- communication of findings

Good keyword buckets:

- analysis methods
- tools
- reporting
- data quality
- decision support

Avoid:

- listing tools without showing what analysis they enabled

### UX / Design

Emphasize:

- portfolio link
- research, flows, wireframes, prototyping, usability work
- collaboration with PM and engineering
- shipped design outcomes

Good keyword buckets:

- Figma or equivalent
- user research
- prototyping
- accessibility
- design systems

Avoid:

- a design resume with no portfolio reference

### Customer Success / Sales / Operations

Emphasize:

- retention, renewals, adoption, account growth, process improvement
- customer communication
- tools used in workflow
- measurable business outcomes

Good keyword buckets:

- churn or retention
- onboarding
- process improvement
- CRM or support stack
- quota or revenue where defensible

Avoid:

- soft-skill-heavy summaries with no operational proof

### Academic / Research CV

Use a CV instead of a resume when the role is clearly academic or research-led.

Emphasize:

- education
- research
- publications
- presentations
- teaching
- grants, awards, affiliations

Avoid:

- forcing academic work into a short private-sector resume shape when the application explicitly wants a CV

### U.S. Federal Resume

Treat this as its own variant.

Emphasize:

- close alignment to the announcement
- required job data like dates and hours per week
- plain language
- explicit qualification coverage

Avoid:

- assuming a normal private-sector resume is enough

## How HaxJobs Should Fine-Tune Outputs

When tailoring, HaxJobs should change:

1. Summary emphasis
2. Section order
3. Keyword density
4. Which experience bullets are promoted
5. Which gaps trigger follow-up questions

It should not change:

1. core facts
2. unsupported metrics
3. titles, employers, dates, or credentials

## Recommended Product Improvements

Short-term improvements:

- Add a `target_role_family` classifier
- Add role-specific keyword banks
- Add bullet rewrite templates per role family
- Add ATS formatting checks before export
- Add `resume` vs `academic_cv` vs `federal_resume` output modes

Medium-term improvements:

- Score summary quality for specificity and keyword overlap
- Flag generic AI phrases
- Compare output bullets to profile facts before export without exposing that review as the main user workflow
- Add fixtures for software, PM, data, design, customer success, academic, and federal roles

## Source Notes

This playbook was informed by current guidance from:

- Harvard Mignone Career Services on strong resumes, action verbs, and using AI only as an editing aid: https://careerservices.fas.harvard.edu/resources/create-a-strong-resume/
- Harvard resume template guidance: https://cdn-careerservices.fas.harvard.edu/wp-content/uploads/sites/161/2024/07/resume-bullets.pdf
- Jobscan ATS formatting guidance for single-column layouts, standard headings, readable fonts, and safe file types: https://www.jobscan.co/blog/20-ats-friendly-resume-templates/
- UC Davis on when to use a resume versus a CV: https://careercenter.ucdavis.edu/resumes-and-materials/resumes/resume-vs-cv
- Georgetown on academic CV expectations and naming/submission norms: https://careercenter.georgetown.edu/major-career-guides/resumes-cover-letters/curriculum-vitae-cv/
- USAJOBS on the federal-resume exception and required content: https://help.usajobs.gov/faq/application/documents/resume/what-to-include
- U.S. Department of Labor on tailoring federal resumes and choosing chronological, functional, or combination formats when appropriate: https://www.dol.gov/general/jobs/tips-for-writing-a-federal-resume
- Current role-specific resume guidance for software, product, data, and UX resume emphasis from Indeed career resources:
  - https://www.indeed.com/career-advice/resumes-cover-letters/software-engineering-resume-keywords
  - https://www.indeed.com/career-advice/resume-samples/product-manager
  - https://www.indeed.com/career-advice/resumes-cover-letters/data-analyst-resume-keywords
  - https://sg.indeed.com/career-advice/resumes-cover-letters/ux-designer-resume

## Bottom Line

The best resume is not the prettiest one.

It is the clearest, most role-relevant version of the candidate that is easy to skim and still holds up in interview.
