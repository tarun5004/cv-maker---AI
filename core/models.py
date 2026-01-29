"""
Data Models for Smart CV Tailor

These dataclasses represent the core entities in our system.
No business logic here — just data shapes.

Design principle: If you can't explain the field to a student, remove it.
"""

from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# Contact Information
# =============================================================================


@dataclass
class ContactInfo:
    """
    How to reach the candidate.
    
    We extract this separately because it appears at the top of every resume
    and doesn't need the same analysis as work experience.
    """

    email: str  # Required — every resume has this
    phone: Optional[str] = None  # Some people omit this for privacy
    linkedin_url: Optional[str] = None  # Common for tech roles
    github_url: Optional[str] = None  # Developers often include this
    location: Optional[str] = None  # City/state, not full address


# =============================================================================
# CV Section (reusable for experience, education, projects)
# =============================================================================


@dataclass
class SectionAnalysis:
    """
    Analysis metadata attached to a CV section AFTER matching.
    
    This is populated by the skill_matcher service, not during parsing.
    We track this separately so we can show users WHY we made suggestions.
    """

    matched_skills: list[str] = field(default_factory=list)
    # Skills from the JD that appear in this section

    relevance_score: float = 0.0
    # 0.0 to 1.0 — how relevant is this section to the target job?
    # Used internally to prioritize suggestions, not shown to users as a "score"

    gaps: list[str] = field(default_factory=list)
    # Skills the JD wants that COULD fit here but aren't mentioned

    explanation: str = ""
    # Human-readable explanation like "This role is highly relevant because..."


@dataclass
class CVSection:
    """
    A single entry in work experience, education, or projects.
    
    We use the same structure for all three because they share the same shape:
    - A title (job title, degree, project name)
    - An organization (company, school, or empty for personal projects)
    - A date range
    - Bullet points describing what happened
    
    This uniformity makes our matching and rewriting logic simpler.
    """

    title: str
    # "Software Engineer", "B.S. Computer Science", "Personal Portfolio Site"

    organization: str
    # "Google", "MIT", "" (empty for personal projects)

    date_range: str
    # "Jan 2022 - Present", "2018 - 2022", "Summer 2023"
    # We keep this as a string because parsing dates is error-prone
    # and we don't need date arithmetic for MVP

    description_points: list[str] = field(default_factory=list)
    # The bullet points. Each string is one bullet.
    # Example: ["Led team of 5 engineers", "Reduced latency by 40%"]

    analysis: Optional[SectionAnalysis] = None
    # Populated AFTER parsing, during the matching phase
    # None means "not yet analyzed"


# =============================================================================
# User Profile (the parsed resume)
# =============================================================================


@dataclass
class UserProfile:
    """
    The structured representation of a user's resume.
    
    This is what we get AFTER parsing a raw PDF/DOCX/text resume.
    All the messy extraction logic lives in cv_parser.py — this is just the result.
    """

    full_name: str
    contact_info: ContactInfo

    summary: str = ""
    # The "About" or "Summary" section at the top
    # Empty if the resume doesn't have one (common for students)

    work_experience: list[CVSection] = field(default_factory=list)
    # Jobs, internships, etc. Usually in reverse chronological order.

    education: list[CVSection] = field(default_factory=list)
    # Degrees, bootcamps, relevant coursework

    skills: list[str] = field(default_factory=list)
    # Flat list: ["Python", "React", "SQL", "Project Management"]
    # We normalize these during matching (React.js → React)

    projects: list[CVSection] = field(default_factory=list)
    # Personal projects, hackathons, open source contributions
    # Important for students who lack work experience

    raw_text: str = ""
    # The original text, preserved for debugging
    # Helps when parsing goes wrong and user asks "why didn't you see X?"


# =============================================================================
# Job Description (the target job)
# =============================================================================


@dataclass
class JobDescription:
    """
    The structured representation of a job posting.
    
    Extracted from the raw text the user pastes in.
    We separate required vs preferred skills because they need different treatment:
    - Missing a required skill = real gap
    - Missing a preferred skill = opportunity, not a problem
    """

    title: str
    # "Senior Software Engineer", "Data Analyst Intern"

    company: str
    # "Google", "Acme Corp"

    raw_text: str
    # Original posting text, preserved for debugging

    required_skills: list[str] = field(default_factory=list)
    # "Must have", "Required", explicitly stated as mandatory

    preferred_skills: list[str] = field(default_factory=list)
    # "Nice to have", "Preferred", "Bonus points for"

    responsibilities: list[str] = field(default_factory=list)
    # What the job actually involves day-to-day

    qualifications: list[str] = field(default_factory=list)
    # Education requirements, years of experience, certifications

    implicit_expectations: list[str] = field(default_factory=list)
    # Inferred from phrases like "fast-paced" (tight deadlines),
    # "self-starter" (minimal supervision), "wear many hats" (broad scope)
    # Helps set realistic expectations for candidates


# =============================================================================
# Suggestion (a single proposed change)
# =============================================================================


@dataclass
class Suggestion:
    """
    One actionable suggestion for improving the resume.
    
    The user will see a list of these and can accept, edit, or dismiss each one.
    We track status so we know what to include in the final export.
    """

    original_text: str
    # What the resume currently says

    suggested_text: str
    # What we suggest changing it to

    reason: str
    # Why we're suggesting this change
    # Example: "The job requires React experience. Your current bullet mentions
    # 'frontend development' but doesn't mention React specifically."

    prompt_question: Optional[str] = None
    # Optional question to help user think
    # Example: "Did this project involve React? If so, consider mentioning it."

    section_name: str = ""
    # Which section this applies to: "work_experience", "projects", etc.

    confidence: float = 1.0
    # 0.0 to 1.0 — how confident are we in this suggestion?

    status: str = "pending"
    # "pending" = not yet reviewed
    # "accepted" = user approved (use suggested_text)
    # "edited" = user modified (use their edit)
    # "dismissed" = user rejected (keep original)


# =============================================================================
# Explanations (why we made changes)
# =============================================================================


@dataclass
class SectionExplanation:
    """Explanation for changes made to a specific section."""

    section_name: str
    # "Work Experience", "Summary", "Projects"

    changes_made: str
    # Human-readable description of what changed

    reasoning: str = ""
    # Why we made these changes


@dataclass
class Explanations:
    """
    All explanations for the tailoring process.
    
    Users see this to understand what we did and why.
    Transparency builds trust — we never make silent changes.
    """

    global_strategy: str
    # High-level summary: "We focused on highlighting your Python and AWS
    # experience, which the job mentions 5 times..."

    section_explanations: list[SectionExplanation] = field(default_factory=list)
    # Detailed breakdown by section


# =============================================================================
# Tailored CV Result (the final output)
# =============================================================================


@dataclass
class TailoredCVResult:
    """
    The complete output of the tailoring pipeline.
    
    Contains:
    1. The original profile (for comparison)
    2. The job description (for context)
    3. Tailored content (after suggestions applied)
    4. All suggestions (for review)
    5. Explanations (for transparency)
    """

    # Original inputs
    original_profile: "UserProfile"
    job_description: "JobDescription"

    # Review data
    suggestions: list[Suggestion]

    # Tailored content sections
    tailored_skills: list[str]  # Reordered to put most relevant first
    tailored_summary: str
    tailored_experience: list[CVSection]

    # Transparency
    explanations: Explanations
