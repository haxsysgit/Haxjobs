# CV Best Practices — Encoded for HaxJobs

Research synthesis from industry sources (Indeed, Harvard CV Guide, NBER hiring studies,
Berkeley Career Center, multiple recruiter surveys). The goal: encode what makes a CV
effective into HaxJobs so users graduate with a better profile than they started with —
regardless of industry.

---

## 1. Universal CV structure (all industries)

Every CV needs these sections. HaxJobs profile schema should map 1:1.

| Section | Required by | What belongs |
|---|---|---|
| Contact info | All CVs | Name, email, phone, city/region (not full address), LinkedIn URL optional |
| Professional summary | All CVs | 2-4 lines. Who you are + what you do + what you're looking for |
| Work experience | All CVs | Reverse chronological. Title, company, dates, location, 3-5 bullet achievements per role |
| Education | All CVs | Institution, degree/certification, year. Highest first |
| Skills | All CVs | Hard skills (languages, tools, certs) separate from soft skills |
| Languages | Multilingual roles | Language + proficiency level (native/fluent/intermediate/basic) |

Optional but high-value: certifications, projects, volunteer work, publications, awards.

## 2. Achievement-first language (the #1 differentiator)

**Bad (responsibility):** "Responsible for managing the team."
**Good (achievement):** "Led a team of 6 to deliver 12 projects on time, reducing client churn by 15%."

This applies to **all industries**:

| Industry | Responsibility (weak) | Achievement (strong) |
|---|---|---|
| Barista | "Made coffee drinks" | "Served 150+ customers daily during peak hours with <2 min average wait time" |
| Nurse | "Cared for patients" | "Managed care for 8 patients per shift, reducing medication errors to zero over 12 months" |
| Retail | "Worked the cash register" | "Processed $3,200 in daily transactions with 100% till accuracy over 2 years" |
| Teacher | "Taught classes" | "Improved student test scores by 22% through redesigned curriculum for 3 cohorts of 30 students" |
| Waiter | "Took orders" | "Handled 8-table section during dinner rush, maintaining 4.8/5 customer satisfaction rating" |
| Developer | "Built an API" | "Designed REST API handling 50K req/min, reducing response latency from 400ms to 45ms" |

**Rule:** Every work experience entry should have at least one achievement bullet with a metric.
For lenient/carefree mode, this becomes "preferred" rather than "required."

## 3. Skills — evidence over buzzwords

**Problem:** Resumes that list: "Python, Docker, Leadership, Communication" with no proof.

**Solution in HaxJobs schema:**

```json
{
  "skills": {
    "hard_skills": [
      {
        "name": "Python",
        "proficiency": "advanced",
        "evidence": "4 years production backend; built 3 microservices serving 50K users",
        "years": 4
      }
    ],
    "soft_skills": [
      {
        "name": "Team Leadership",
        "evidence": "Managed team of 6 engineers across 2 product launches"
      }
    ]
  }
}
```

Proficiency scale: `beginner`, `intermediate`, `advanced`, `expert`.

Evidence is:
- Required in strict/serious mode
- Optional in lenient mode
- Skipped in carefree mode

## 4. Red flags that get CVs rejected (across all industries)

| Red flag | Why it kills you |
|---|---|
| Typos/grammar errors | Signals low attention to detail — #1 complaint across healthcare, retail, hospitality |
| Unexplained gaps >1 year | Not always a dealbreaker, but needs a one-line explanation |
| No dates on roles | Recruiters assume hiding something |
| Irrelevant personal info | Photo, marital status, religion, DOB — can trigger bias; illegal to require in many jurisdictions |
| Generic objective statements | "Seeking a challenging position" — says nothing. Use a professional summary instead |
| One-paragraph CV (no sections) | Unreadable; ATS can't parse it |
| 10+ page CV | >2 pages for most roles; >3 for senior/executive. Trim ruthlessly |
| Buzzword vomit | 15 technologies listed with zero context — see Section 3 |
| Inconsistent formatting | Mixed fonts, date formats, bullet styles — signals carelessness |

## 5. Industry-specific differences

| Industry | What matters more | What matters less |
|---|---|---|
| Tech/IT | GitHub, portfolio, specific technologies, scale metrics, production experience | Education institution prestige (after first job) |
| Healthcare | Licenses/certifications, clinical hours, patient outcomes, HIPAA knowledge | Portfolio/GitHub |
| Hospitality | Customer volume metrics, satisfaction scores, reliability, language skills | Education |
| Retail | Revenue/sales figures, inventory management, team size | Certifications (unless specialized) |
| Education | Credentials, curriculum design, student outcomes, classroom management | Portfolio |
| Trades/Construction | Certifications, safety record, project scale, equipment proficiency | Soft skills (unless supervisor) |
| Creative/Design | Portfolio, specific tools (Adobe suite), client names, campaign results | Traditional education |

## 6. ATS compatibility (applicant tracking systems)

- Use standard section headings: "Work Experience" not "Where I've Been"
- No tables, text boxes, images, columns, graphics
- No headers/footers for key info — ATS often ignores them
- PDF is safe for most modern ATS (Greenhouse, Lever, Ashby, Workday all handle PDF)
- DOCX is the safest universal format
- Match keywords from the job description naturally (don't keyword-stuff)

## 7. Length rules by seniority

| Level | Max pages |
|---|---|
| Junior (0-3 years) | 1 page |
| Mid (3-10 years) | 1-2 pages |
| Senior (10+ years) | 2 pages |
| Executive/C-level | 2-3 pages |

## 8. What NOT to include

- Photo (triggers bias; illegal to request in US/UK)
- Date of birth / age
- Marital status
- Religion
- Full home address (city/region is enough)
- Salary history
- References ("available upon request" — assume they'll ask)
- Hobbies (unless directly relevant to the role)
- "Curriculum Vitae" or "Resume" as a title — your name is the title

## 9. How HaxJobs encodes these

### Profile schema fields driven by this research

- `work_experience[].achievements` — required array per role, metric-preferring
- `skills.hard_skills[].evidence` — string, context-dependent (mode-driven)
- `skills.hard_skills[].years` — number
- `education[].institution`, `education[].degree`, `education[].year`
- `certifications[].name`, `certifications[].issuer`, `certifications[].year`
- `languages[].name`, `languages[].proficiency` (native/fluent/intermediate/basic)

### Agent prompt rules (onboarding tier)

1. For every work experience entry, ask for ONE specific achievement with a metric.
2. Skills without evidence are accepted only in lenient/carefree mode.
3. Unexplained employment gaps get a targeted question.
4. Generic "objective statement" language is rejected; agent generates professional summary from CV.
5. Buzzword lists trigger a "which of these did you actually use, and where?" follow-up.

### Depth modes

| Mode | Skills evidence | Work achievements | Gap questions | Proof (GitHub/portfolio) | Generic desc tolerance |
|---|---|---|---|---|---|
| strict (senior) | Required per skill | Required with metric | Required for any gap | Required for tech roles | Low — agent challenges all vague claims |
| lenient (mid) | Preferred, not required | Preferred, metric nice-to-have | Asked once, accepted at face value | Mentioned, not enforced | Medium — agent asks once, accepts answer |
| carefree (junior) | Skipped | Skipped (responsibilities OK) | Skipped | Skipped | High — accepts what user gives |

Mode is set in profile: `preferences.profile_depth` = `"strict"` | `"lenient"` | `"carefree"`.
Defaults to `"lenient"` for new users.

---

## Sources

- Indeed Career Guide: Resume sections, ATS best practices, recruiter red flags (2025)
- Harvard CV Guide: structured sections, achievement language
- Berkeley School of Information: resume content guidelines
- NBER working paper 6605: hiring discrimination studies (why photo/DOB/address hurt)
- Multiple recruiter surveys: top rejection reasons across industries
- LinkedIn post by Sanidhya Charan Srivastava (2025): AI engineer resume mistakes
