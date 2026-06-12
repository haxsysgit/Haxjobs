# Cover Letter Governance

HaxJobs cover letters are dynamic, but bounded.

## Layer 1: locked facts
The generator can use these facts, but cannot rewrite them into fake claims:
- identity and contact details
- education
- confirmed work history
- confirmed projects
- confirmed skills and depth
- visa or work-authorisation wording once approved by Arinze

## Layer 2: JD-derived slots
The generator may fill these only from the JD or reliable company research:
- company
- role_title
- hiring_manager_or_team
- jd_match_points
- company_reason
- evidence_story
- gap_note

If a hiring manager is not found, use "team". Never guess.

## Layer 3: voice and validator
The letter should sound like Arinze: warm, direct, playful, confident, and a little cheeky where it helps. It should not sound like a corporate template.

Personality is allowed. Hallucination is not.

Validator blocks:
- em dashes
- forbidden AI phrases
- fake metrics
- fake tool depth
- fake names
- unsupported visa or legal claims
- generic company praise
