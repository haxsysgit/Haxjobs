# Arinze Elenasulu

**Python Backend Engineer | AI & Automation**

London, UK · elenasuluarinze@gmail.com
[linkedin.com/in/arinze-elenasulu](https://linkedin.com/in/arinze-elenasulu) · [github.com/haxsysgit](https://github.com/haxsysgit)

---

## Professional Summary

I have been writing Python since 2020 and it is my strongest language. I build backend systems that people actually rely on every day: APIs, databases, automation workflows, and AI tooling. I care about clean code, honest testing, and shipping software that does not need a prayer circle to stay up. My background sits where backend engineering meets practical AI: I have built production SaaS features, trained and fine-tuned models, and designed agent infrastructure that runs 24/7 on a cloud VPS. I am looking for a role where I can build systems that matter, learn fast, and be a genuinely good person to have on the team.

---

## Core Skills

**Backend Engineering:** Python (primary, since 2020), FastAPI, SQLAlchemy, Alembic, PostgreSQL, REST API design, async/await, JWT authentication, role-based access control, schema design, query optimisation

**AI and Automation:** HuggingFace, PyTorch, RAGAS, model fine-tuning, LLM evaluation, AI agent infrastructure (Archilles, Hermes agent fork), browser automation, agent orchestration, MCP servers

**Testing and Quality:** Advanced pytest (fixtures, parametrisation, integration coverage), structured test design for backend and AI workflows, test-driven development, API test automation

**Infrastructure and DevOps:** Docker (multi-stage builds, docker-compose), Linux, Git/GitHub, CI/CD, structured logging, input validation

**Additional Languages:** Java (Spring Framework, EJB), Flutter/Dart, C++, C (from formal training; Python is my strongest)

---

## Education

**BSc Information Technology**, Middlesex University London  (June 2026)

**Advanced Diploma in Software Engineering (ADSE Java)**, Aptech Computer Education, Lagos (September 2022 to August 2024)
A structured two-year programme combining classroom training with hands-on project work across four semesters. Covered Linux, Python, C++, C, Java, Spring Framework, EJB, Flutter/Dart, MERN and MEAN stacks. Python became my primary language during this period.

---

## Experience

### Software Engineer, Vigilis
*August 2024 to February 2026 · Lagos, Nigeria*

Built and maintained the backend for a pharmacy operations platform handling sales, inventory, payments, and reporting across multiple locations. The system was used day to day by pharmacy staff.

- Designed the full data model and API layer (FastAPI, PostgreSQL, SQLAlchemy) with role-based access, JWT auth, and Alembic migrations that kept the database evolving safely as features shipped.
- Sat with pharmacy staff directly to understand their manual processes. Turned paper workflows and mental checklists into software that cut daily admin time and reduced stock discrepancies.
- Built the invoice lifecycle: create, add line items, finalise with automatic stock deduction, cancel with stock reversal. Every state transition validated and audited.
- Added structured logging, input validation, and business rule enforcement that caught errors at the API boundary before they could corrupt data downstream.
- Owned the backend end to end: feature planning, database design, deployment, monitoring, and production bug fixes. No handoff.

### AI and Backend Engineer (Contract), Bucca Hut
*February 2025 to May 2025*

Built a data analysis and data mining tool for a food business, connecting LLM outputs and mined data insights to real operational decisions. Designed the backend API bridging AI processing with existing workflows. Worked as a contract(extra hands) alongside my position at vigilis Vigilis, delivering the tool from concept to working prototype.

### Software Engineer Intern, Aptech Computer Education
*September 2022 to August 2024 · Lagos, Nigeria*

Completed the Advanced Diploma in Software Engineering (ADSE Java track), a structured two-year programme combining classroom training with hands-on project work.

- Covered the full software engineering stack across four semesters: Linux system administration, Python, C++, C, Java, Spring Framework, Enterprise Java Beans (EJB), Flutter/Dart for mobile, and both MERN and MEAN stacks for full-stack web development.
- Built multiple projects across different technology stacks as part of the programme curriculum, gaining practical exposure to how different languages and frameworks solve similar problems.
- Developed strong fundamentals in object-oriented programming, database design, and software architecture that carried into every role since.
- Python became my primary language during this period and has remained so. I have been studying and building with it continuously since 2020.

---

## Selected Projects

### Pharmax, Pharmacy Management Platform
*Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic*

Built a Saas for an AI-integrated pharmacy operations platform handling product inventory, sales, invoicing, and reporting. The backend skeleton is public on GitHub; the full SaaS code is proprietary.

- Products CRUD with multi-unit pricing (tablets, packs, strips).
- Full invoice lifecycle: draft to finalise (auto stock deduction) to cancel (stock reversal).
- Stock adjustments with audit trail and reorder-level tracking.
- Role-based access with JWT authentication.
- Comprehensive pytest suite covering endpoints, business logic, and edge cases. Used RAGAS for LLM evaluation workflows.

### FRAME, Typed Project Memory Format for AI Agents
*Python, Markdown/YAML, Multi-Agent*
[github.com/haxsysgit/FRAME](https://github.com/haxsysgit/FRAME)

Designed a portable standard that gives AI coding agents structured project context across sessions. Five-part memory model (Facts, Rules, Acts, Map, Expect) capturing project truth, agent rules, session history, module relationships, and expected outcomes. Reduces repeated prompting, context rot, and full-repo rescans across agent sessions. FRAME is the contract; implementations earn alignment with it.

### Haxaml, AI Agent Governance and Project Memory
*Python, MCP, FRAME, System design*
[github.com/haxsysgit/haxaml](https://github.com/haxsysgit/haxaml) · [pypi.org/project/haxaml](https://pypi.org/project/haxaml)

Built and published a governance runtime that enforces project rules for AI coding agents. Five-stage pipeline from Admission to Verification to Recording. MCP server so AI coding tools can read and write FRAME files during a session. Published on PyPI with documentation and setup guides.

### CaseFRAME, Financial Crime Investigation Continuity
*Python, FRAME model*
[github.com/haxsysgit/CaseFRAME](https://github.com/haxsysgit/CaseFRAME)

Applied the FRAME memory model to financial-crime investigation continuity, giving investigators structured context persistence across long-running cases.

### HaxJobs, Automated Job Search Pipeline
*Python, FastAPI, SQLite, React, TypeScript*
[github.com/haxsysgit/Haxjobs](https://github.com/haxsysgit/Haxjobs)

Built an end-to-end automated job discovery and application platform. Multi-platform discovery across Lever, Ashby, and Greenhouse APIs. Pipeline evaluates job fit against my profile using a deterministic classifier and produces structured application packs. Web dashboard for pipeline monitoring with real-time job status views. Runs on Archilles, my 24/7 AI agent infrastructure on a cloud VPS.

---

## Additional Information

- Work authorization: currently on a UK student visa, graduating June 2026. Planning to apply for a Graduate visa (2-year work right). No immediate sponsorship required.
- Availability: available to start immediately.
- Location preference: London, Manchester, Leeds, Remote UK, Hybrid UK.
