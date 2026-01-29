# Smart CV Tailor

A resume editor that helps you tailor your CV for specific job descriptions — without making things up.

---

## The Problem

You find a job posting. You have a resume. You know you should "tailor" it, but:

- You're not sure which parts matter for this specific role
- You don't know what skills to emphasize
- You're worried about accidentally lying or exaggerating
- Most "AI resume tools" either do nothing useful or hallucinate achievements you never had

The result? You either send the same generic resume everywhere, or you spend hours manually tweaking for each application.

---

## Why Most AI Resume Tools Fail

We looked at the landscape. Here's what we found:

| Problem | What Happens |
|---------|--------------|
| **Hallucinated metrics** | "Increased revenue by 40%" — you never measured this |
| **Invented skills** | Tool adds "Kubernetes" because the JD mentions it, even though you've never used it |
| **Black-box changes** | Resume comes out different, but you don't know what changed or why |
| **Over-optimization** | Every bullet becomes a keyword-stuffed mess that reads like SEO spam |
| **ATS mythology** | Tools claim to "beat the ATS" with tricks that don't actually work |

These tools optimize for the wrong thing. They try to game systems instead of helping you present your real experience effectively.

---

## Our Philosophy

**You stay in control.**

This tool doesn't write your resume. It helps you understand the gap between what you have and what the job wants — then gives you specific, explainable suggestions.

Core principles:

1. **No hallucination** — We never invent achievements, metrics, or skills you don't have
2. **Transparency** — Every suggestion comes with a reason you can read and evaluate
3. **User agency** — You accept, edit, or dismiss each change individually
4. **Honest gaps** — If you're missing a required skill, we tell you. We don't fake it.
5. **Reversibility** — Original resume is always preserved. Revert anytime.

---

## Key Features

### Section-Based Resume Editor

Build your resume section by section:

- **Header** — Name, contact info, links
- **Summary** — Professional summary with character count guidance
- **Skills** — Organized by category (Languages, Frameworks, Tools, etc.)
- **Experience** — Multiple entries with role summary and bullet points
- **Education** — Degrees, certifications, relevant coursework
- **Projects** — Personal and professional projects with tech stack

Each section is a first-class citizen. Education isn't an afterthought.

### Optimize for Job

Paste a job description. Get analysis:

- **Matched skills** — What you have that the job wants
- **Missing skills** — What the JD mentions that you haven't listed (only add if you actually have them)
- **Section suggestions** — Which parts of your resume could be improved for this role
- **Match score** — Simple percentage, no false precision

### Apply Optimization (With Explanations)

Run the tailoring pipeline:

- **Skill reordering** — Most relevant skills moved to the front
- **Bullet rewrites** — Verb upgrades, skill injection (conservative)
- **Summary tailoring** — Adjusted to emphasize relevant experience

Every change comes with:
- What was changed
- Why it was changed
- A question to help you decide if it's accurate

You review each suggestion. Nothing is auto-applied.

### Preview Modes

Toggle between:
- **Original resume** — What you entered
- **Optimized resume** — Tailored version for the job

Side-by-side explanations show exactly what changed and why.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐   │
│  │ Header  │ │ Skills  │ │  Exp    │ │  Optimize   │   │
│  │ Editor  │ │ Editor  │ │ Editor  │ │  for Job    │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  Tailoring Pipeline                     │
│                                                         │
│  Step 1: Parse CV (rule-based)                         │
│  Step 2: Parse JD (rule-based)                         │
│  Step 3: Match Skills (keyword matching)               │
│  Step 4: Rewrite CV (conservative, deterministic)      │
│  Step 5: Generate Explanations (template-based)        │
│                                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   TailoredCVResult                      │
│                                                         │
│  - Suggestions (with reasons)                          │
│  - Tailored skills (reordered)                         │
│  - Tailored summary                                    │
│  - Tailored experience bullets                         │
│  - Explanations (global + per-section)                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

All logic is **rule-based and deterministic**. No LLM calls in the MVP. You can trace exactly why each suggestion was made.

---

## Why This Is ATS-Friendly

Applicant Tracking Systems (ATS) are simpler than the industry pretends. They mostly:

1. Parse text from your resume
2. Search for keywords
3. Let recruiters filter and search

What actually matters:

| Do This | Why |
|---------|-----|
| Use standard section headings | "Experience", "Education", "Skills" — not "My Journey" |
| Plain text formatting | No tables, columns, or complex layouts |
| List relevant skills | Keywords the recruiter will search for |
| Include job titles and company names | Structured data the ATS can parse |

What doesn't matter (despite what you've heard):

- Specific fonts
- Exact keyword density
- "ATS score" percentages
- File format (PDF works fine)

This tool outputs clean, structured content. No gimmicks.

---

## Screenshots

> *Screenshots to be added*

### Resume Editor
`[screenshot: section-based editor with skills categories]`

### Job Analysis
`[screenshot: matched/missing skills, section suggestions]`

### Optimization Results
`[screenshot: original vs optimized toggle, explanations panel]`

---

## Running Locally

### Prerequisites

- Python 3.10+ (tested on 3.13)
- pip

### Setup

```bash
# Clone the repository
git clone <repo-url>
cd smart-cv-tailor

# Create virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install streamlit

# Run the app
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Project Structure

```
smart-cv-tailor/
├── app.py                    # Main Streamlit application
├── core/
│   ├── models.py             # Data models (UserProfile, JobDescription, etc.)
│   └── pipeline.py           # 5-step tailoring pipeline
├── services/
│   ├── cv_parser.py          # Resume text → structured data
│   ├── jd_analyzer.py        # Job description → requirements
│   ├── skill_matcher.py      # Match resume skills to JD
│   ├── cv_rewriter.py        # Conservative bullet rewrites
│   └── explanation_engine.py # Generate human-readable explanations
├── ui/
│   ├── upload_section.py     # CV/JD upload interface
│   ├── review_section.py     # Suggestion review
│   └── result_section.py     # Final result display
├── PRD.md                    # Product requirements
├── DESIGN.md                 # System design
├── ARCHITECTURE.md           # Technical architecture
└── README.md
```

---

## What's Intentionally NOT Included

We made deliberate choices to exclude:

| Feature | Why Not |
|---------|---------|
| **LLM integration** | Too easy to hallucinate. Rule-based is debuggable. |
| **Auto-apply changes** | User must review and accept each change. |
| **"ATS score"** | Fake precision. No one knows how every ATS works. |
| **PDF parsing** | Error-prone. Better to have user paste/type for MVP. |
| **Cover letter generation** | Different problem. Focus on one thing well. |
| **Job scraping** | Scope creep. Paste the JD yourself. |
| **User accounts** | Not needed for local tool. Session state is enough. |
| **Export to DOCX/PDF** | Copy-paste works. Fancy export is polish, not core. |

These might come later. For now, we ship what works.

---

## Design Decisions

### Why Streamlit?

- Fast to prototype
- Good enough for a local tool
- Session state handles our needs
- No frontend/backend split to maintain

### Why Rule-Based?

- Deterministic: same input → same output
- Debuggable: you can trace every decision
- No API costs or rate limits
- No "AI said so" black box

### Why Section-Based Editor?

- Mirrors how people think about resumes
- Each section has different editing needs
- Progress is visible (N/6 sections filled)
- Easy to extend (add Certifications, Languages, etc.)

---

## Contributing

This is an MVP. The codebase is intentionally simple.

If you want to contribute:

1. Keep it simple
2. Explain your changes
3. Don't add AI unless you can guarantee no hallucination
4. Test with real resumes and job descriptions

---

## License

MIT

---

## Acknowledgments

Built with frustration at the state of "AI resume tools" and a belief that software should help people without lying to them.

---

*Last updated: January 2026*
