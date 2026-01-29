# Smart CV Tailor — Product Requirements Document

**Version:** 1.0 (MVP)  
**Last Updated:** January 30, 2026  
**Status:** Draft

---

## 1. Problem Statement

### The Real Pain

Students and junior developers apply to dozens of jobs. Each job posting has different requirements, keywords, and emphasis. The standard advice is "tailor your resume for each role" — but nobody teaches how to do this well, and doing it manually for 50+ applications is brutal.

**What actually happens:**

1. Student copies their master resume
2. Changes the title to match the job
3. Maybe swaps a few buzzwords
4. Hopes for the best
5. Gets ghosted

The result: generic resumes that don't speak to what the employer actually asked for. ATS systems filter them out. Hiring managers skim and move on.

**Why existing tools fail:**

- **Generic resume builders:** Pretty templates, zero intelligence about job matching
- **AI chat tools:** Produce robotic, over-optimized text that reads like it was written by a machine (because it was)
- **Keyword stuffing tools:** Teach bad habits, produce resumes that pass ATS but fail human review

Students don't need another AI that writes their resume. They need a tool that helps them **see what matters** in a job posting and **decide what to emphasize** from their own experience.

---

## 2. Target Users

### Primary: Job-Seeking Students & Junior Developers

**Demographics:**
- Final-year university students (CS, Engineering, Business)
- Bootcamp graduates
- Junior developers with 0-2 years experience
- Career switchers entering tech

**Behaviors:**
- Applying to 20-100+ positions per job search
- Using one "master resume" for everything
- Unclear on what recruiters actually look for
- Time-poor, stressed, often applying late at night
- Skeptical of AI tools that over-promise

**What they need:**
- Speed (not 30 minutes per application)
- Clarity (what should I emphasize for THIS job?)
- Confidence (does my resume actually address what they asked for?)
- Authenticity (this still sounds like me, not a robot)

### Secondary: Career Services Advisors

- Help students at scale
- Need tools that teach good practices, not shortcuts
- Want students to understand WHY changes matter

---

## 3. Core Features

### Must-Have (MVP Scope)

#### 3.1 Job Posting Analyzer
**What it does:**  
User pastes a job description. System extracts and highlights:
- Required skills (hard requirements)
- Preferred skills (nice-to-haves)  
- Key responsibilities
- Implicit expectations (e.g., "fast-paced" = expect tight deadlines)

**Why it matters:**  
Most students don't actually read job postings carefully. They skim, miss nuance, and apply generically. This makes the hidden structure visible.

**Output:**  
Structured breakdown, not a wall of AI-generated text. Visual hierarchy. Clear labels.

---

#### 3.2 Resume Upload & Parsing
**What it does:**  
User uploads their existing resume (PDF or DOCX). System extracts:
- Work experience entries
- Education
- Skills list
- Projects

**Constraints:**
- No resume scoring (those numbers are meaningless)
- No "your resume is 67% optimized" nonsense
- Just clean extraction so we can work with the content

---

#### 3.3 Gap Analysis & Match View
**What it does:**  
Side-by-side comparison:
- Left: What the job asks for
- Right: What your resume currently addresses

Visual indicators:
- ✅ Covered (your resume mentions this)
- ⚠️ Partial (mentioned but could be stronger)
- ❌ Gap (job asks for it, resume doesn't mention it)

**Why it matters:**  
This is the "aha moment." Students see exactly where their resume falls short for THIS specific role. No vague advice — concrete gaps.

---

#### 3.4 Suggestion Engine
**What it does:**  
For each gap or partial match, provide:
- **Prompt questions:** "You listed Project X. Did this involve [skill from job posting]? If so, consider mentioning it."
- **Rewrite suggestions:** Optional AI-assisted rewrites for bullet points, clearly marked as suggestions
- **Examples:** "Here's how you might phrase this" — not "here's your new resume"

**Critical UX principle:**  
The user decides. We suggest. Every suggestion is editable. Nothing auto-applies.

---

#### 3.5 Tailored Resume Export
**What it does:**  
After user reviews and accepts/edits suggestions:
- Generate a clean, tailored resume
- Export as PDF (ATS-friendly formatting)
- Option to download as DOCX for further editing

**Constraints:**
- No fancy templates (ATS compatibility first)
- Clean, professional, readable by humans and machines
- User's name, their content, their voice

---

### Nice-to-Have (Post-MVP)

| Feature | Why Deferred |
|---------|--------------|
| Cover letter generation | Different problem, different UX |
| LinkedIn profile sync | API complexity, auth flows |
| Application tracking | Scope creep into job board territory |
| Chrome extension for job sites | Distribution win, but MVP is web-first |
| Team/advisor dashboard | B2B feature, not MVP |
| Resume version history | Nice but not critical |

---

## 4. Non-Goals

**We are NOT building:**

1. **A resume writer**  
   We don't write your resume from scratch. You bring content; we help you tailor it.

2. **An ATS score checker**  
   Those scores are made up. Every ATS works differently. We focus on actual alignment, not fake percentages.

3. **A job board or aggregator**  
   We don't find jobs for you. You paste the posting; we help you respond to it.

4. **A chatbot**  
   No conversational UI. No "ask me anything." Structured workflow, clear steps.

5. **A magic solution**  
   We can't fix a resume that has nothing relevant on it. We help you present what you have better — we don't fabricate experience.

6. **100% accuracy in parsing**  
   Job postings and resumes are messy. We'll get most of it right. Users can correct what we miss.

---

## 5. UX Principles

### 5.1 Transparency Over Magic

Every suggestion shows its reasoning:
- "This job mentions React 5 times. Your resume mentions it once, in a project from 2024. Consider expanding."

No black boxes. Users should learn, not just click.

### 5.2 User Control, Always

- Nothing auto-applies
- Every suggestion is a suggestion
- Easy to dismiss, edit, or ignore
- Original resume is never modified — we create a tailored copy

### 5.3 Human Voice Preserved

- Suggestions are framed as options, not replacements
- We don't rewrite their entire bullet point — we show what to add or emphasize
- Final output should read like them, not like ChatGPT

### 5.4 Speed Without Rushing

- Full flow should take 5-10 minutes, not 30
- But we don't auto-submit or skip steps
- Quick ≠ careless

### 5.5 Professional, Not Playful

- No gamification ("You're 80% there! 🎉")
- No mascots, no chatty copy
- Clean UI, minimal chrome, focus on content
- This is a professional tool for a serious task

### 5.6 Honest Limitations

- If we can't parse something, we say so
- If a gap can't be fixed (they require 5 years experience, you have 1), we don't pretend otherwise
- Help users make informed decisions, not feel artificially confident

---

## 6. Success Metrics

### Primary Metrics (MVP Launch)

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| **Completion Rate** | >60% of users who upload a resume complete a tailored export | Core flow works, users find value |
| **Time to First Export** | <10 minutes median | Speed promise delivered |
| **Return Usage** | >30% use it for 2+ job applications | Actual utility, not novelty |

### Secondary Metrics

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| **Suggestion Acceptance Rate** | 40-70% | Too low = bad suggestions. Too high = users aren't thinking. |
| **Manual Edit Rate** | >50% of users edit at least one suggestion | Users engaging, not blindly accepting |
| **NPS Score** | >40 | Would they recommend it? |

### Anti-Metrics (What We Don't Optimize For)

- **Time on site:** We want users to finish quickly, not linger
- **Number of suggestions shown:** More isn't better. Relevant is better.
- **AI-generated word count:** Less intervention is often better

### Qualitative Success Signals

- Users say "I never noticed that the job posting asked for X"
- Users feel more confident submitting the tailored resume
- Career advisors consider recommending it to students
- Zero complaints about "this sounds like a robot wrote it"

---

## 7. Open Questions

1. **Parsing accuracy:** How do we handle badly formatted job postings (e.g., image-based, or rambling paragraphs)?
   
2. **Skill normalization:** "React.js" vs "ReactJS" vs "React" — how fuzzy should matching be?

3. **Multi-language support:** English-first, but is there early demand for other languages?

4. **Privacy:** Do we store resumes? For how long? What's the trust model?

5. **Freemium vs paid:** What limits for free tier? Per-resume? Per-month?

---

## 8. Out of Scope for This Document

- Technical architecture (see ARCHITECTURE.md)
- UI/UX design specifications (see DESIGN.md)
- Go-to-market strategy
- Pricing model details

---

## Appendix: User Stories

**As a student applying to my first internship,**  
I want to understand what a job posting is really asking for,  
So that I can decide if I'm a fit and how to present myself.

**As a bootcamp graduate with non-traditional experience,**  
I want to see how my projects map to job requirements,  
So that I can translate my skills into employer language.

**As someone applying to 50+ jobs,**  
I want to tailor my resume in under 10 minutes per application,  
So that I don't burn out or send the same generic resume everywhere.

**As a career switcher,**  
I want honest feedback on gaps between my experience and job requirements,  
So that I can focus on roles where I have a realistic chance.

---

*This document defines what we're building and why. Implementation details live elsewhere. When in doubt, refer back to the problem statement: help students present their real experience better, for specific jobs, without losing their voice.*
