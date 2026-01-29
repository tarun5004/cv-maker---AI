
## Smart CV Tailor: System Design (MVP)

This document outlines the internal system design and data flow for the Smart CV Tailor MVP. Our goal is to create a clear, debuggable, and modular system.

### 1. Data Models

We'll use simple, dictionary-like structures to represent our data. Think of these as blueprints for the information our system will handle.

---

**`UserProfile`**

Represents the user's base CV information, broken down into manageable sections.

```
UserProfile:
  full_name: string
  contact_info:
    email: string
    phone: string
    linkedin_url: string (optional)
    github_url: string (optional)
  summary: string
  work_experience: list of CVSection
  education: list of CVSection
  skills: list of string
  projects: list of CVSection (optional)
```

---

**`JobDescription`**

Represents the key information extracted from the job posting.

```
JobDescription:
  title: string
  company: string
  raw_text: string
  required_skills: list of string
  responsibilities: list of string
```

---

**`CVSection`**

A generic and reusable structure for different parts of a CV like work experience, education, or projects. This helps us process them uniformly.

```
CVSection:
  title: string (e.g., "Software Engineer" or "B.S. in Computer Science")
  organization: string (e.g., "Tech Company Inc." or "State University")
  date_range: string (e.g., "Jan 2022 - Present")
  description_points: list of string
  analysis:
    matched_skills: list of string
    relevance_score: float (0.0 to 1.0)
    explanation: string
```

**Note on `analysis`:** This sub-field is crucial. We will populate it during the processing pipeline to track *why* a particular section is relevant to the job description.

---

**`TailoredCVResult`**

The final output, containing the rewritten CV and the explanations for the changes.

```
TailoredCVResult:
  tailored_cv:
    summary: string
    work_experience: list of CVSection
    // ... other sections as needed
  explanations:
    global_strategy: string (e.g., "Rephrased summary to highlight skills in Python and AWS, and reordered bullet points in the 'Software Engineer at Tech Company' role to match key responsibilities from the job description.")
    section_by_section: list of
      section_title: string
      changes_made: string
```

### 2. Processing Pipeline

This is the step-by-step journey from the user's raw CV and a job description to a tailored CV.

---

**Step 1: CV Parsing**

-   **Responsibility:** To take the user's raw CV text (e.g., from a file upload or text area) and convert it into our structured `UserProfile` data model.
-   **Input:**
    -   `raw_cv_text`: string
-   **Output:**
    -   `user_profile`: UserProfile object
-   **Process:**
    1.  Use simple rules or regular expressions to identify sections (Summary, Work Experience, etc.).
    2.  For each section, extract the relevant details.
    3.  Populate the `UserProfile` object. We will keep this simple for the MVP, avoiding complex PDF/DOCX parsing. A structured text input is preferred.

---

**Step 2: Job Description (JD) Analysis**

-   **Responsibility:** To extract key requirements and skills from the raw text of the job description.
-   **Input:**
    -   `raw_jd_text`: string
-   **Output:**
    -   `job_description`: JobDescription object
-   **Process:**
    1.  Use a Large Language Model (LLM) or keyword extraction techniques to identify required skills (e.g., "Python", "React", "AWS").
    2.  Similarly, extract key responsibilities or qualifications.
    3.  Populate the `JobDescription` object.

---

**Step 3: Skill & Relevance Matching**

-   **Responsibility:** To compare the user's CV with the job description to find overlaps and determine relevance. This is the core "analysis" phase.
-   **Input:**
    -   `user_profile`: UserProfile
    -   `job_description`: JobDescription
-   **Output:**
    -   An "annotated" `user_profile`: UserProfile where the `analysis` field in each `CVSection` is populated.
-   **Process:**
    1.  Iterate through each `CVSection` in the `user_profile`.
    2.  For each `description_point` (like a bullet point in a job experience), compare it against the `required_skills` and `responsibilities` from the `job_description`.
    3.  If matches are found, add them to the `matched_skills` list for that section.
    4.  Calculate a simple `relevance_score` based on the number and quality of matches.
    5.  Generate a brief `explanation` (e.g., "This role is highly relevant as it mentions 'data analysis' and 'Python', both key requirements in the job description.").

---

**Step 4: CV Rewriting & Tailoring**

-   **Responsibility:** To generate new, tailored content for the CV based on the analysis from the previous step.
-   **Input:**
    -   The "annotated" `user_profile`: UserProfile
    -   `job_description`: JobDescription
-   **Output:**
    -   A `tailored_cv` object, which has the same structure as the CV portion of `TailoredCVResult`.
-   **Process (using an LLM):**
    1.  **Summary:** Generate a new summary. Prompt the LLM with the original summary, the user's top skills, and the most important requirements from the `job_description`.
    2.  **Work Experience:** For each `CVSection` in the work experience, instruct the LLM to reorder and rephrase the `description_points`. Prioritize points that have the highest `relevance_score` and `matched_skills`. The goal is to make the most relevant experience immediately obvious to a recruiter.
    3.  **Skills:** Ensure the skills section prominently features keywords from the `job_description`.

---

**Step 5: Explanation Generation**

-   **Responsibility:** To create a clear, human-readable explanation of *what* was changed and *why*.
-   **Input:**
    -   The original `user_profile`: UserProfile
    -   The final `tailored_cv` object
-   **Output:**
    -   `explanations` object, as defined in `TailoredCVResult`.
-   **Process:**
    1.  Generate a `global_strategy` statement that summarizes the main changes (e.g., "We focused on highlighting your Python and project management skills...").
    2.  Compare the original `CVSection` descriptions with the tailored ones.
    3.  For each section that was changed, create a `changes_made` summary (e.g., "Reordered bullet points to emphasize your experience with financial modeling, which was a key requirement.").

---

**Final Assembly**

-   **Responsibility:** To combine the outputs of the rewriting and explanation steps into the final result.
-   **Input:**
    -   `tailored_cv` object
    -   `explanations` object
-   **Output:**
    -   `TailoredCVResult` object
-   **Process:**
    1.  Simply combine the two inputs into the final data structure, ready to be displayed to the user in the Streamlit UI.
