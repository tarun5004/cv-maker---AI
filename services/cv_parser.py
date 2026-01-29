"""
CV Parser Service (Rule-Based)

Parses raw CV/resume text into structured UserProfile.

=============================================================================
APPROACH: Simple Heuristics, No LLM
=============================================================================

We use pattern matching and section headers to extract structure.
This works reasonably well for standard resumes but WILL fail on:
- Creative/non-standard layouts
- Resumes in languages other than English
- Image-based PDFs (we can't see images)
- Extremely sparse resumes

That's okay for MVP. We let users correct mistakes in the review step.

=============================================================================
ASSUMPTIONS
=============================================================================

1. Resume has recognizable section headers (Experience, Education, etc.)
2. Contact info is at the top
3. Bullet points use common markers (-, •, *, or numbered)
4. Dates follow common patterns (2020-2022, Jan 2020 - Present, etc.)
5. English language

=============================================================================
LIMITATIONS (Known Issues)
=============================================================================

- Multi-column layouts will jumble text order
- Tables don't parse well from PDF extraction
- Company/school names on same line as job title may be missed
- Inconsistent formatting within a resume causes problems
- No handling of multiple positions at same company

We accept these limitations for MVP. Users can edit in review.
"""

import re
import logging
from typing import Optional

from core.models import UserProfile, ContactInfo, CVSection

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION HEADER PATTERNS
# =============================================================================

# These are the phrases we look for to identify section boundaries.
# Order matters — we check in this order and take the first match.
# All matching is case-insensitive.

SECTION_PATTERNS = {
    "experience": [
        r"work\s*experience",
        r"professional\s*experience",
        r"employment\s*history",
        r"experience",
        r"work\s*history",
    ],
    "education": [
        r"education",
        r"academic\s*background",
        r"academic\s*history",
        r"qualifications",
    ],
    "skills": [
        r"technical\s*skills",
        r"skills",
        r"core\s*competencies",
        r"technologies",
        r"tools\s*&\s*technologies",
        r"programming\s*languages",
    ],
    "projects": [
        r"projects",
        r"personal\s*projects",
        r"side\s*projects",
        r"portfolio",
        r"open\s*source",
    ],
    "summary": [
        r"summary",
        r"professional\s*summary",
        r"about\s*me",
        r"about",
        r"objective",
        r"profile",
    ],
}


# =============================================================================
# CONTACT INFO PATTERNS
# =============================================================================

# Email: standard pattern
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Phone: various formats (US-centric but catches most international)
PHONE_PATTERN = re.compile(
    r"(?:\+?1?[-.\s]?)?"  # Optional country code
    r"(?:\(?\d{3}\)?[-.\s]?)?"  # Area code
    r"\d{3}[-.\s]?\d{4}"  # Main number
)

# LinkedIn URL
LINKEDIN_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+/?",
    re.IGNORECASE,
)

# GitHub URL
GITHUB_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?github\.com/[\w-]+/?",
    re.IGNORECASE,
)


# =============================================================================
# DATE PATTERNS
# =============================================================================

# Common date range patterns:
# - "Jan 2020 - Present"
# - "2020 - 2022"
# - "01/2020 - 12/2022"
# - "Summer 2021"
# - "2020-Present"

DATE_RANGE_PATTERN = re.compile(
    r"(?:"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|"
    r"Spring|Summer|Fall|Winter|Q[1-4])"
    r"[\s,]*"
    r")?"
    r"\d{2,4}"  # Year
    r"\s*[-–—to]+\s*"  # Separator
    r"(?:"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|"
    r"Spring|Summer|Fall|Winter|Q[1-4])"
    r"[\s,]*"
    r")?"
    r"(?:\d{2,4}|[Pp]resent|[Cc]urrent|[Nn]ow|[Oo]ngoing)",
    re.IGNORECASE,
)


# =============================================================================
# BULLET POINT PATTERNS
# =============================================================================

# Characters that indicate a bullet point at the start of a line
BULLET_MARKERS = re.compile(r"^[\s]*[-•*▪◦‣⁃]|^[\s]*\d+[.)]\s")


# =============================================================================
# MAIN PARSER CLASS
# =============================================================================


class CVParser:
    """
    Parses raw resume text into structured UserProfile.
    
    Usage:
        parser = CVParser()
        profile = parser.parse(raw_text)
    
    The parsing is best-effort. We extract what we can and leave the rest empty.
    Users can correct mistakes in the review step.
    """

    def parse(self, raw_text: str) -> UserProfile:
        """
        Parse raw CV text into structured UserProfile.
        
        Args:
            raw_text: The raw text extracted from PDF/DOCX or pasted by user
            
        Returns:
            UserProfile with extracted data (some fields may be empty)
        """
        logger.info("Starting CV parsing")

        # Clean up the text
        text = self._clean_text(raw_text)

        # Extract contact info (usually at the top)
        contact_info, name = self._extract_contact_info(text)

        # Split into sections
        sections = self._split_into_sections(text)

        # Parse each section type
        summary = self._parse_summary(sections.get("summary", ""))
        experience = self._parse_experience(sections.get("experience", ""))
        education = self._parse_education(sections.get("education", ""))
        skills = self._parse_skills(sections.get("skills", ""))
        projects = self._parse_projects(sections.get("projects", ""))

        profile = UserProfile(
            full_name=name,
            contact_info=contact_info,
            summary=summary,
            work_experience=experience,
            education=education,
            skills=skills,
            projects=projects,
            raw_text=raw_text,  # Keep original for debugging
        )

        logger.info(f"Parsed CV: {name}, {len(experience)} jobs, {len(education)} education, {len(skills)} skills")
        return profile

    # =========================================================================
    # TEXT CLEANING
    # =========================================================================

    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize raw text.
        
        - Normalize line endings
        - Remove excessive whitespace
        - Remove page numbers and headers/footers (common in PDFs)
        """
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove common PDF artifacts
        # Page numbers like "Page 1 of 2" or just "1" at end of line
        text = re.sub(r"\n\s*(?:Page\s*)?\d+\s*(?:of\s*\d+)?\s*\n", "\n", text)

        # Remove excessive blank lines (keep max 2)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    # =========================================================================
    # CONTACT INFO EXTRACTION
    # =========================================================================

    def _extract_contact_info(self, text: str) -> tuple[ContactInfo, str]:
        """
        Extract contact information and name from resume text.
        
        Assumption: Contact info is in the first ~10 lines.
        Name is usually the first non-empty line.
        
        Returns:
            (ContactInfo, full_name)
        """
        # Look at the top portion of the resume
        lines = text.split("\n")[:15]
        top_text = "\n".join(lines)

        # Extract email
        email_match = EMAIL_PATTERN.search(top_text)
        email = email_match.group(0) if email_match else ""

        # Extract phone
        phone_match = PHONE_PATTERN.search(top_text)
        phone = phone_match.group(0) if phone_match else None

        # Extract LinkedIn
        linkedin_match = LINKEDIN_PATTERN.search(top_text)
        linkedin = linkedin_match.group(0) if linkedin_match else None

        # Extract GitHub
        github_match = GITHUB_PATTERN.search(top_text)
        github = github_match.group(0) if github_match else None

        # Extract name (first substantial line that isn't contact info)
        name = self._extract_name(lines)

        # Extract location (city, state — usually near contact info)
        location = self._extract_location(top_text)

        contact_info = ContactInfo(
            email=email,
            phone=phone,
            linkedin_url=linkedin,
            github_url=github,
            location=location,
        )

        return contact_info, name

    def _extract_name(self, lines: list[str]) -> str:
        """
        Extract the person's name.
        
        Heuristic: The name is usually the first line that:
        - Has 2-4 words
        - Doesn't contain @ or http (not email/URL)
        - Doesn't look like a section header
        - Is relatively short (< 50 chars)
        """
        for line in lines[:5]:  # Only check first 5 lines
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip if it's an email or URL
            if "@" in line or "http" in line.lower() or "www." in line.lower():
                continue

            # Skip if it looks like a phone number (mostly digits)
            digit_ratio = sum(c.isdigit() for c in line) / max(len(line), 1)
            if digit_ratio > 0.3:
                continue

            # Skip if it's too long (probably not a name)
            if len(line) > 50:
                continue

            # Skip if it looks like a section header
            if self._is_section_header(line):
                continue

            # Check word count (names are usually 2-4 words)
            words = line.split()
            if 1 <= len(words) <= 5:
                return line

        return "Unknown"

    def _extract_location(self, text: str) -> Optional[str]:
        """
        Extract location (city, state/country).
        
        Common patterns:
        - "San Francisco, CA"
        - "New York, NY 10001"
        - "London, UK"
        - "Seattle, Washington"
        
        This is best-effort. Many formats will be missed.
        """
        # Pattern: City, STATE or City, State
        location_pattern = re.compile(
            r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*,\s*"
            r"([A-Z]{2}|[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
            r"(?:\s+\d{5}(?:-\d{4})?)?"  # Optional ZIP
        )

        match = location_pattern.search(text)
        if match:
            return match.group(0).strip()

        return None

    # =========================================================================
    # SECTION SPLITTING
    # =========================================================================

    def _split_into_sections(self, text: str) -> dict[str, str]:
        """
        Split resume text into labeled sections.
        
        Returns dict like:
        {
            "experience": "Software Engineer at Google...",
            "education": "B.S. Computer Science...",
            "skills": "Python, React, SQL...",
        }
        """
        # Find all section headers and their positions
        section_positions = []

        for section_type, patterns in SECTION_PATTERNS.items():
            for pattern in patterns:
                # Look for pattern at start of line (with optional whitespace)
                regex = re.compile(
                    rf"^[\s]*({pattern})[\s]*[:]*[\s]*$",
                    re.IGNORECASE | re.MULTILINE,
                )
                for match in regex.finditer(text):
                    section_positions.append({
                        "type": section_type,
                        "start": match.start(),
                        "end": match.end(),
                        "header": match.group(0),
                    })

        # Sort by position
        section_positions.sort(key=lambda x: x["start"])

        # Remove duplicates (same section type found multiple times)
        seen_types = set()
        unique_positions = []
        for pos in section_positions:
            if pos["type"] not in seen_types:
                seen_types.add(pos["type"])
                unique_positions.append(pos)

        # Extract text for each section
        sections = {}
        for i, pos in enumerate(unique_positions):
            # Section content starts after the header
            start = pos["end"]

            # Section ends at the next section (or end of text)
            if i + 1 < len(unique_positions):
                end = unique_positions[i + 1]["start"]
            else:
                end = len(text)

            section_text = text[start:end].strip()
            sections[pos["type"]] = section_text

        return sections

    def _is_section_header(self, line: str) -> bool:
        """Check if a line looks like a section header."""
        line_lower = line.lower().strip()

        for patterns in SECTION_PATTERNS.values():
            for pattern in patterns:
                if re.match(rf"^{pattern}[\s:]*$", line_lower):
                    return True

        return False

    # =========================================================================
    # SECTION PARSING
    # =========================================================================

    def _parse_summary(self, text: str) -> str:
        """
        Parse the summary/about section.
        
        This is usually just free-form text, so we return it cleaned up.
        """
        if not text:
            return ""

        # Remove any bullet markers at the start
        text = re.sub(r"^[\s]*[-•*]\s*", "", text, flags=re.MULTILINE)

        # Join lines into paragraphs
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        return " ".join(lines)

    def _parse_experience(self, text: str) -> list[CVSection]:
        """
        Parse work experience section into list of CVSection.
        
        Expected format (variations exist):
            Software Engineer
            Google | Jan 2020 - Present
            - Built microservices handling 1M requests/day
            - Led team of 3 engineers
        """
        if not text:
            return []

        return self._parse_entries(text)

    def _parse_education(self, text: str) -> list[CVSection]:
        """
        Parse education section into list of CVSection.
        
        Expected format:
            B.S. Computer Science
            MIT | 2016 - 2020
            - GPA: 3.8
            - Relevant coursework: Algorithms, ML
        """
        if not text:
            return []

        return self._parse_entries(text)

    def _parse_projects(self, text: str) -> list[CVSection]:
        """
        Parse projects section into list of CVSection.
        
        Expected format:
            Personal Portfolio Website
            2023
            - Built with React and TypeScript
            - Deployed on Vercel
        """
        if not text:
            return []

        return self._parse_entries(text)

    def _parse_entries(self, text: str) -> list[CVSection]:
        """
        Generic entry parser for experience, education, and projects.
        
        Strategy:
        1. Split text into chunks (one per entry)
        2. For each chunk, extract title, org, dates, bullets
        
        This is the trickiest part because formatting varies wildly.
        """
        entries = []
        lines = text.split("\n")

        # Group lines into entries
        # Heuristic: A new entry starts when we see a line that looks like a title
        # (not a bullet, not a date-only line)

        current_entry_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            # Is this a new entry?
            # New entry indicators:
            # - Not a bullet point
            # - Doesn't start with a date
            # - Isn't too long (titles are usually short)

            is_bullet = bool(BULLET_MARKERS.match(line))
            is_date_line = bool(DATE_RANGE_PATTERN.match(line)) and len(line) < 30
            is_likely_title = not is_bullet and not is_date_line and len(line) < 100

            # If this looks like a new title and we have accumulated lines, save the current entry
            if is_likely_title and current_entry_lines and not self._looks_like_continuation(line, current_entry_lines):
                entry = self._parse_single_entry(current_entry_lines)
                if entry:
                    entries.append(entry)
                current_entry_lines = []

            current_entry_lines.append(line)

        # Don't forget the last entry
        if current_entry_lines:
            entry = self._parse_single_entry(current_entry_lines)
            if entry:
                entries.append(entry)

        return entries

    def _looks_like_continuation(self, line: str, prev_lines: list[str]) -> bool:
        """
        Check if a line is a continuation of the previous entry or a new one.
        
        Heuristics:
        - If we only have 1 previous line, next non-bullet is likely org/date
        - If line contains |, it's likely org/date info
        - If line is all caps, it might be a header
        """
        if len(prev_lines) <= 1:
            # Could be org/date line
            if "|" in line or DATE_RANGE_PATTERN.search(line):
                return True

        return False

    def _parse_single_entry(self, lines: list[str]) -> Optional[CVSection]:
        """
        Parse a single entry (job, degree, project) from its lines.
        """
        if not lines:
            return None

        # First line is usually the title
        title = lines[0]
        organization = ""
        date_range = ""
        description_points = []

        # Look for organization and dates in the first few lines
        for i, line in enumerate(lines[1:4], start=1):
            # Check for date range
            date_match = DATE_RANGE_PATTERN.search(line)
            if date_match:
                date_range = date_match.group(0)
                # Remove date from line to get org
                remaining = line.replace(date_range, "").strip()
                remaining = remaining.strip("|").strip("-").strip("–").strip()
                if remaining and not organization:
                    organization = remaining

            # Check for organization (line with | separator or before date)
            elif "|" in line:
                parts = line.split("|")
                for part in parts:
                    part = part.strip()
                    if DATE_RANGE_PATTERN.search(part):
                        date_range = DATE_RANGE_PATTERN.search(part).group(0)
                    elif not organization:
                        organization = part

            # If line looks like a company/school name (no bullet, short, has caps)
            elif not BULLET_MARKERS.match(line) and len(line) < 60:
                if not organization:
                    organization = line

        # Remaining lines are bullet points
        for line in lines[1:]:
            # Skip if we already used this line for org/date
            if line == organization:
                continue
            if date_range and date_range in line and len(line) < 40:
                continue

            # Check if it's a bullet point
            if BULLET_MARKERS.match(line):
                # Remove the bullet marker
                bullet_text = BULLET_MARKERS.sub("", line).strip()
                if bullet_text:
                    description_points.append(bullet_text)
            elif len(line) > 20:
                # Long line without bullet might still be a description
                # Check if previous lines had bullets (then this is probably continuation)
                if description_points:
                    # Append to last bullet
                    description_points[-1] += " " + line
                else:
                    # Treat as bullet
                    description_points.append(line)

        # Clean up organization (remove stray punctuation)
        organization = organization.strip("|-–•").strip()

        # Skip if we didn't extract anything meaningful
        if not title or title == organization:
            return None

        return CVSection(
            title=title,
            organization=organization,
            date_range=date_range,
            description_points=description_points,
        )

    def _parse_skills(self, text: str) -> list[str]:
        """
        Parse skills section into flat list of skills.
        
        Skills sections have many formats:
        - "Python, React, SQL, Docker"
        - "Languages: Python, Java | Frameworks: React, Django"
        - "- Python\n- React\n- SQL"
        """
        if not text:
            return []

        skills = []

        # Remove category labels like "Languages:", "Frameworks:"
        text = re.sub(r"[A-Za-z]+\s*:", " ", text)

        # Remove bullet markers
        text = re.sub(r"[-•*▪◦‣⁃]", " ", text)

        # Split on common delimiters
        # Comma, pipe, newline, semicolon
        parts = re.split(r"[,|\n;]", text)

        for part in parts:
            skill = part.strip()

            # Skip empty or too short
            if len(skill) < 2:
                continue

            # Skip if it's a category label we missed
            if skill.lower() in ["skills", "tools", "technologies", "languages"]:
                continue

            # Skip if too long (probably not a skill)
            if len(skill) > 50:
                continue

            skills.append(skill)

        # Remove duplicates while preserving order
        seen = set()
        unique_skills = []
        for skill in skills:
            skill_lower = skill.lower()
            if skill_lower not in seen:
                seen.add(skill_lower)
                unique_skills.append(skill)

        return unique_skills

