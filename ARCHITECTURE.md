# Smart CV Tailor — Architecture Document

**Version:** 1.0 (MVP)  
**Last Updated:** January 30, 2026  
**Audience:** Developers maintaining or extending this system

---

## 1. System Overview

Smart CV Tailor is a web application that helps users tailor their resumes to specific job postings. The system is intentionally simple: a monolithic Python backend with a lightweight frontend, no microservices, no message queues, no Kubernetes.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Streamlit)                      │
│                                                                  │
│   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│   │  Upload  │ → │   Gap    │ → │ Suggest  │ → │  Export  │    │
│   │   Page   │   │  View    │   │   Page   │   │   Page   │    │
│   └──────────┘   └──────────┘   └──────────┘   └──────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (Python/FastAPI)                     │
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │   Parser    │  │   Matcher   │  │  Suggester  │             │
│   │   Service   │  │   Service   │  │   Service   │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
│          │                │                │                     │
│          ▼                ▼                ▼                     │
│   ┌─────────────────────────────────────────────────────────────┤
│   │                    LLM Gateway                              │
│   │         (Gemini for extraction, Claude for generation)      │
│   └─────────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                               │
│                                                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│   │   Session   │  │    File     │  │   Export    │             │
│   │   Store     │  │   Storage   │  │   Cache     │             │
│   │  (Redis)    │  │   (Local)   │  │  (Local)    │             │
│   └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 Frontend: Streamlit App

**Location:** `/app/frontend/`

**Responsibility:**
- Render the multi-step workflow UI
- Handle file uploads (PDF, DOCX)
- Display gap analysis results
- Show suggestions with accept/edit/dismiss controls
- Trigger PDF/DOCX export

**Why Streamlit:**
- Fast to build for MVP
- Python-native (no separate frontend team needed)
- Good enough for internal/student users
- Easy to replace later if we need React

**What it does NOT do:**
- No business logic
- No LLM calls
- No parsing
- Pure presentation layer

---

### 2.2 Parser Service

**Location:** `/app/services/parser/`

**Responsibility:**
- Extract structured data from raw resume files
- Extract structured data from pasted job descriptions
- Normalize formats (PDF text extraction, DOCX parsing)

**Subcomponents:**

| Module | Input | Output |
|--------|-------|--------|
| `resume_parser.py` | PDF/DOCX file | `UserProfile` object |
| `jd_parser.py` | Raw text | `JobDescription` object |
| `file_extractor.py` | File bytes | Plain text |

**LLM Usage:** Gemini (extraction tasks)

**Why separate:**
- Parsing fails often (messy inputs)
- Needs isolated error handling
- Can swap parsers without touching other code

---

### 2.3 Matcher Service

**Location:** `/app/services/matcher/`

**Responsibility:**
- Compare parsed resume against parsed job description
- Identify skill matches, partial matches, and gaps
- Calculate relevance scores per section
- Generate the "annotated" profile with analysis data

**Subcomponents:**

| Module | Purpose |
|--------|---------|
| `skill_matcher.py` | Fuzzy matching of skills (React vs ReactJS) |
| `section_analyzer.py` | Scores each CV section against JD |
| `gap_detector.py` | Identifies missing skills/requirements |

**LLM Usage:** Minimal (primarily rule-based + embeddings)

**Why rule-based where possible:**
- Deterministic = debuggable
- Faster than LLM calls
- Easier to unit test

---

### 2.4 Suggester Service

**Location:** `/app/services/suggester/`

**Responsibility:**
- Generate tailoring suggestions for each gap
- Produce optional rewrite suggestions for bullet points
- Create prompt questions to help user self-discover content
- Preserve user's original voice

**Subcomponents:**

| Module | Purpose |
|--------|---------|
| `suggestion_engine.py` | Orchestrates suggestion generation |
| `prompt_generator.py` | Creates prompts for LLM |
| `voice_preserving_rewriter.py` | Rewrites bullets without losing tone |

**LLM Usage:** Claude (generation tasks)

**Why Claude for generation:**
- Better at nuanced, human-sounding text
- Less likely to produce robotic output
- Follows instructions more precisely for constrained rewriting

---

### 2.5 LLM Gateway

**Location:** `/app/services/llm/`

**Responsibility:**
- Abstract LLM provider details from business logic
- Handle retries, rate limiting, error handling
- Log all prompts and responses (for debugging)
- Switch between providers based on task type

**Interface:**

```python
class LLMGateway:
    def extract(self, prompt: str, schema: dict) -> dict:
        """Use Gemini for structured extraction"""
        
    def generate(self, prompt: str, constraints: dict) -> str:
        """Use Claude for text generation"""
        
    def embed(self, text: str) -> list[float]:
        """Use lightweight embedding model for matching"""
```

**Why a gateway:**
- Change providers without touching services
- Central logging for all LLM calls
- Single place to implement fallbacks

---

### 2.6 Export Service

**Location:** `/app/services/export/`

**Responsibility:**
- Take final tailored content and render to PDF
- Generate DOCX for users who want to edit further
- Apply ATS-friendly formatting (no tables, no columns, standard fonts)

**Subcomponents:**

| Module | Purpose |
|--------|---------|
| `pdf_renderer.py` | Uses ReportLab or WeasyPrint |
| `docx_renderer.py` | Uses python-docx |
| `ats_formatter.py` | Strips risky formatting |

**LLM Usage:** None

---

### 2.7 Data Layer

**Session Store (Redis):**
- Stores in-progress tailoring sessions
- Keyed by session ID (not user ID for MVP — no auth)
- TTL: 24 hours
- Holds: parsed resume, parsed JD, current suggestions, user edits

**File Storage (Local/S3):**
- Uploaded resumes (temporary, deleted after session expires)
- Generated exports (cached for download)

**No Database for MVP:**
- No user accounts
- No persistence beyond sessions
- Keeps architecture simple

---

## 3. Data Flow

### Full Pipeline: Upload → Export

```
1. USER UPLOADS RESUME
   │
   ├─→ file_extractor.py extracts text from PDF/DOCX
   │
   └─→ resume_parser.py (+ Gemini) → UserProfile object
       └─→ Stored in session

2. USER PASTES JOB DESCRIPTION
   │
   └─→ jd_parser.py (+ Gemini) → JobDescription object
       └─→ Stored in session

3. GAP ANALYSIS TRIGGERED
   │
   ├─→ skill_matcher.py compares skills (rule-based + embeddings)
   │
   ├─→ section_analyzer.py scores each section
   │
   └─→ gap_detector.py identifies missing requirements
       └─→ Annotated UserProfile stored in session

4. SUGGESTIONS GENERATED
   │
   ├─→ For each gap: suggestion_engine.py (+ Claude)
   │   ├─→ Prompt questions
   │   └─→ Optional rewrite suggestions
   │
   └─→ Suggestions stored in session, displayed to user

5. USER REVIEWS & EDITS
   │
   ├─→ Accept suggestion → applied to tailored draft
   ├─→ Edit suggestion → user's version applied
   └─→ Dismiss suggestion → excluded from draft

6. EXPORT TRIGGERED
   │
   ├─→ ats_formatter.py cleans formatting
   │
   └─→ pdf_renderer.py or docx_renderer.py
       └─→ File returned to user
```

---

## 4. LLM Strategy: Gemini vs Claude

### Why Two Models?

Different models excel at different tasks. Using the right tool for each job produces better results and is more cost-effective.

### Task Allocation

| Task | Model | Reasoning |
|------|-------|-----------|
| **Resume parsing** | Gemini | Structured extraction. Gemini handles JSON schema output well. Fast. Cheap. |
| **JD parsing** | Gemini | Same as above — extraction into structured format. |
| **Skill matching** | Embeddings + rules | No LLM needed. Deterministic. Fast. Debuggable. |
| **Section relevance** | Embeddings | Semantic similarity. No generation needed. |
| **Gap identification** | Rules | If JD requires X and resume doesn't mention X, that's a gap. No LLM needed. |
| **Suggestion generation** | Claude | Nuanced text generation. Needs to sound human, not robotic. |
| **Bullet point rewriting** | Claude | Voice preservation is critical. Claude follows constraints better. |
| **Explanation generation** | Claude | Requires natural language that explains reasoning. |

### Prompt Design Principles

1. **Be specific about constraints:**
   - "Rewrite this bullet point to mention Python. Keep the same structure. Do not add experience the user doesn't have."

2. **Provide examples:**
   - Show before/after pairs in the prompt.

3. **Ask for reasoning:**
   - "Explain why you made this change" — helps with transparency UX.

4. **Limit creativity:**
   - We don't want creative writing. We want constrained editing.

---

## 5. Why This Architecture is Debuggable

### 5.1 Every Step is Inspectable

Each pipeline step produces a concrete artifact:
- `UserProfile` after parsing
- `JobDescription` after JD analysis
- Annotated profile after matching
- Suggestions list before user review

All stored in session. All can be logged. All can be displayed in a debug view.

### 5.2 LLM Calls are Logged

The LLM Gateway logs:
- Full prompt sent
- Full response received
- Latency
- Model used
- Token count

When something goes wrong, you can see exactly what the model saw and said.

### 5.3 Rule-Based Where Possible

Matching and gap detection are primarily rule-based:
- Skill X in JD? Check if skill X in resume.
- If yes → match. If no → gap.

This is trivial to debug. No "why did the AI think this?" questions.

### 5.4 No Hidden State

- No magic prompt chaining that's hard to trace
- No multi-turn conversations with the LLM
- Each LLM call is independent and stateless

### 5.5 Fallbacks are Explicit

If Gemini fails to parse a resume:
1. Log the failure
2. Return a partial result with "we couldn't extract section X"
3. Let user manually correct

No silent failures. No "it just works" black boxes.

---

## 6. Why This Doesn't Feel Like an AI Toy

### 6.1 AI is Infrastructure, Not Interface

Users don't see:
- "Powered by AI" badges
- Spinning "AI is thinking" loaders
- Chat bubbles or conversational UI

Users see:
- A structured workflow with clear steps
- Their content, analyzed and annotated
- Suggestions they control

### 6.2 Transparency is Built In

Every suggestion shows why:
- "This job mentions 'team leadership' 3 times. Your resume doesn't mention it. Your role at Company X involved leading a team — consider adding that."

Not: "Here's a better version of your resume."

### 6.3 User Maintains Control

- Nothing auto-applies
- User reviews each suggestion
- User can edit or dismiss
- Original resume is never modified

### 6.4 Outputs are Predictable

- Same input → same output (deterministic where possible)
- LLM temperature set low for generation
- No "creative" rewrites that change meaning

---

## 7. Error Handling Strategy

| Failure Mode | Handling |
|--------------|----------|
| Resume parsing fails | Return partial result, show "we couldn't parse sections X, Y" |
| JD parsing fails | Ask user to re-paste, highlight problematic areas |
| LLM timeout | Retry once, then return cached/partial result |
| LLM rate limit | Queue and retry with backoff |
| File too large | Reject upfront with clear size limit |
| Unsupported format | Reject upfront, list supported formats |
| Session expired | Prompt to re-upload (no silent data loss) |

---

## 8. Security Considerations (MVP)

| Concern | MVP Approach |
|---------|--------------|
| Resume data privacy | Stored in session only, deleted after 24h, no analytics on content |
| LLM data exposure | Use enterprise API agreements, don't send PII in prompts where avoidable |
| File uploads | Validate file type, limit size, scan for malicious content |
| No auth for MVP | Acceptable for MVP; add auth before any paid tier |

---

## 9. Technology Stack (MVP)

| Layer | Technology | Why |
|-------|------------|-----|
| Frontend | Streamlit | Fast to build, Python-native, good enough for MVP |
| Backend | FastAPI | Clean, fast, good for API + async LLM calls |
| Session Store | Redis | Simple, fast, TTL support |
| File Handling | Local filesystem (S3 later) | MVP doesn't need distributed storage |
| PDF Parsing | PyMuPDF (fitz) | Reliable, fast |
| DOCX Parsing | python-docx | Standard, well-maintained |
| PDF Generation | WeasyPrint | Good for text-heavy PDFs |
| LLM - Extraction | Google Gemini API | Good at structured output, cost-effective |
| LLM - Generation | Anthropic Claude API | Best at constrained, human-sounding text |
| Embeddings | Sentence Transformers (local) | Fast, free, no API dependency |

---

## 10. What's NOT in This Architecture

| Missing | Why |
|---------|-----|
| User accounts / auth | MVP is sessionless |
| Database | No persistence needed beyond sessions |
| Background jobs / queues | All processing is synchronous for MVP |
| Microservices | Monolith is simpler to deploy and debug |
| Kubernetes | Overkill for MVP traffic |
| CDN | No static assets worth caching |
| A/B testing framework | Premature optimization |

---

## 11. Future Considerations (Post-MVP)

When we scale beyond MVP:

1. **Add authentication** — Required before any payment or saved history
2. **Move to PostgreSQL** — For user data, version history
3. **Add background jobs** — For slow operations (batch parsing)
4. **Consider React frontend** — If Streamlit becomes limiting
5. **Add observability** — Structured logging, metrics, tracing
6. **Multi-region deployment** — If latency becomes an issue

But not now. MVP first.

---

## Appendix: Directory Structure

```
smart-cv-tailor/
├── app/
│   ├── frontend/
│   │   ├── pages/
│   │   │   ├── upload.py
│   │   │   ├── gap_view.py
│   │   │   ├── suggestions.py
│   │   │   └── export.py
│   │   └── components/
│   │       ├── file_uploader.py
│   │       ├── gap_card.py
│   │       └── suggestion_card.py
│   │
│   ├── services/
│   │   ├── parser/
│   │   │   ├── resume_parser.py
│   │   │   ├── jd_parser.py
│   │   │   └── file_extractor.py
│   │   ├── matcher/
│   │   │   ├── skill_matcher.py
│   │   │   ├── section_analyzer.py
│   │   │   └── gap_detector.py
│   │   ├── suggester/
│   │   │   ├── suggestion_engine.py
│   │   │   ├── prompt_generator.py
│   │   │   └── voice_preserving_rewriter.py
│   │   ├── export/
│   │   │   ├── pdf_renderer.py
│   │   │   ├── docx_renderer.py
│   │   │   └── ats_formatter.py
│   │   └── llm/
│   │       ├── gateway.py
│   │       ├── gemini_client.py
│   │       └── claude_client.py
│   │
│   ├── models/
│   │   ├── user_profile.py
│   │   ├── job_description.py
│   │   └── tailored_result.py
│   │
│   └── utils/
│       ├── session.py
│       └── logging.py
│
├── tests/
│   ├── test_parser/
│   ├── test_matcher/
│   └── test_suggester/
│
├── config/
│   └── settings.py
│
├── PRD.md
├── DESIGN.md
├── ARCHITECTURE.md
└── README.md
```

---

*This document describes HOW the system works. For WHAT we're building, see PRD.md. For data models and pipeline steps, see DESIGN.md.*
