"""
Job Description Analyzer (Rule-Based)

Extracts structured data from job postings using keyword matching.

=============================================================================
APPROACH: Keyword Detection, No LLM
=============================================================================

Job descriptions follow predictable patterns. We exploit this:
- "Requirements" / "Required" sections list must-have skills
- "Nice to have" / "Preferred" sections list optional skills
- Bullet points under these headers are the actual items
- Job title is usually at the top or in a clear "Position:" line

This works well for standard job postings but will miss:
- Deeply nested requirements
- Requirements scattered throughout prose
- Non-English postings
- Very creative/non-standard formats

=============================================================================
ASSUMPTIONS
=============================================================================

1. Job title is near the top or clearly labeled
2. Required skills appear after words like "Required", "Must have", etc.
3. Preferred skills appear after words like "Nice to have", "Preferred", etc.
4. Skills are often in bullet points
5. Company name is mentioned (often near title)

=============================================================================
LIMITATIONS (Known Issues)
=============================================================================

- Can't distinguish between years of experience and skill names well
- May include irrelevant bullets (benefits, company description)
- Doesn't understand context ("experience with" vs "no experience needed")
- May miss skills embedded in sentences without bullet points

We accept these for MVP. The review step lets users correct mistakes.
"""

import re
import logging
from typing import Optional

from core.models import JobDescription

logger = logging.getLogger(__name__)


# =============================================================================
# SECTION HEADER PATTERNS
# =============================================================================

# Patterns that indicate required skills follow
REQUIRED_SECTION_PATTERNS = [
    r"required\s*(?:skills|qualifications|experience)?",
    r"requirements",
    r"must\s*have",
    r"what\s*you(?:'ll)?\s*need",
    r"what\s*we(?:'re)?\s*looking\s*for",
    r"minimum\s*qualifications",
    r"basic\s*qualifications",
    r"you\s*(?:should|must)\s*have",
    r"qualifications",
    r"who\s*you\s*are",
]

# Patterns that indicate preferred/optional skills follow
PREFERRED_SECTION_PATTERNS = [
    r"preferred\s*(?:skills|qualifications|experience)?",
    r"nice\s*to\s*have",
    r"bonus\s*(?:points|skills)?",
    r"a\s*plus",
    r"ideal(?:ly)?",
    r"additional\s*(?:skills|qualifications)?",
    r"desired\s*(?:skills|qualifications|experience)?",
    r"it(?:'s|\s*is)\s*a\s*(?:plus|bonus)",
    r"extra\s*credit",
]

# Patterns that indicate responsibilities section
RESPONSIBILITIES_PATTERNS = [
    r"responsibilities",
    r"what\s*you(?:'ll)?\s*(?:do|be\s*doing)",
    r"your\s*role",
    r"the\s*role",
    r"about\s*(?:the|this)\s*(?:role|position|job)",
    r"job\s*description",
    r"key\s*responsibilities",
    r"day\s*to\s*day",
]

# Patterns that indicate sections we should SKIP (not skills)
SKIP_SECTION_PATTERNS = [
    r"benefits",
    r"perks",
    r"compensation",
    r"salary",
    r"about\s*(?:us|the\s*company|our\s*company)",
    r"who\s*we\s*are",
    r"our\s*(?:culture|values|mission)",
    r"how\s*to\s*apply",
    r"equal\s*opportunity",
    r"diversity",
]


# =============================================================================
# SKILL INDICATOR PATTERNS
# =============================================================================

# Words/phrases that often precede skill mentions
SKILL_INDICATORS = [
    r"experience\s*(?:with|in|using)",
    r"proficiency\s*(?:with|in)",
    r"proficient\s*(?:with|in)",
    r"knowledge\s*of",
    r"familiarity\s*with",
    r"expertise\s*(?:with|in)",
    r"skilled\s*(?:with|in)",
    r"hands[-\s]on\s*experience",
    r"working\s*knowledge\s*of",
    r"strong\s*(?:understanding|background)\s*(?:of|in)",
]

# Common technical skills (expanded list for better matching)
# This is used to identify skills even when not in a clear bullet point
KNOWN_SKILLS = {
    # Programming languages
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl",
    
    # Frontend
    "react", "reactjs", "react.js", "vue", "vuejs", "vue.js", "angular",
    "svelte", "next.js", "nextjs", "nuxt", "nuxtjs", "html", "css", "sass",
    "less", "tailwind", "tailwindcss", "bootstrap", "jquery",
    
    # Backend
    "node.js", "nodejs", "node", "express", "expressjs", "fastapi", "django",
    "flask", "spring", "spring boot", "rails", "ruby on rails", "asp.net",
    "graphql", "rest", "restful", "api", "microservices",
    
    # Databases
    "sql", "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
    "dynamodb", "sqlite", "oracle", "cassandra", "neo4j", "firebase",
    
    # Cloud & DevOps
    "aws", "amazon web services", "azure", "gcp", "google cloud", "heroku",
    "vercel", "netlify", "docker", "kubernetes", "k8s", "terraform",
    "cloudformation", "jenkins", "circleci", "github actions", "gitlab ci",
    "ansible", "puppet", "chef",
    
    # Data & ML
    "pandas", "numpy", "scikit-learn", "sklearn", "tensorflow", "pytorch",
    "keras", "spark", "apache spark", "hadoop", "airflow", "dbt",
    "tableau", "power bi", "looker", "data analysis", "machine learning",
    "deep learning", "nlp", "computer vision",
    
    # Tools & Practices
    "git", "github", "gitlab", "bitbucket", "jira", "confluence", "slack",
    "figma", "postman", "vs code", "vim", "linux", "bash", "shell",
    "agile", "scrum", "kanban", "ci/cd", "tdd", "unit testing",
    
    # Soft skills (sometimes listed)
    "communication", "leadership", "teamwork", "problem solving",
    "project management", "time management",
}

# Phrases that indicate implicit expectations (culture signals)
IMPLICIT_EXPECTATION_PHRASES = {
    "fast-paced": "Expect tight deadlines and quick pivots",
    "fast paced": "Expect tight deadlines and quick pivots",
    "startup": "Less structure, more ownership, possible long hours",
    "self-starter": "Minimal supervision, must be proactive",
    "self starter": "Minimal supervision, must be proactive",
    "wear many hats": "Broad responsibilities beyond job title",
    "entrepreneurial": "Expected to take initiative and ownership",
    "dynamic environment": "Frequent changes and ambiguity",
    "move fast": "Speed valued over perfection",
    "hit the ground running": "Minimal onboarding, immediate expectations",
    "ambiguity": "Unclear requirements, must figure things out",
    "0 to 1": "Building from scratch, high uncertainty",
    "greenfield": "New project, no existing codebase",
    "legacy": "Old codebase, technical debt expected",
}


# =============================================================================
# MAIN ANALYZER CLASS
# =============================================================================


class JDAnalyzer:
    """
    Analyzes job description text to extract structured requirements.
    
    Usage:
        analyzer = JDAnalyzer()
        jd = analyzer.analyze(raw_text)
    
    Returns a JobDescription with extracted data.
    Some fields may be empty if we couldn't extract them.
    """

    def analyze(self, raw_text: str) -> JobDescription:
        """
        Analyze job description text and extract structured data.
        
        Args:
            raw_text: The raw job posting text
            
        Returns:
            JobDescription with extracted fields
        """
        logger.info("Starting JD analysis")

        # Clean up text
        text = self._clean_text(raw_text)

        # Extract basic info
        title = self._extract_title(text)
        company = self._extract_company(text)

        # Split into sections
        sections = self._split_into_sections(text)

        # Extract skills from appropriate sections
        required_skills = self._extract_required_skills(text, sections)
        preferred_skills = self._extract_preferred_skills(text, sections)

        # Extract responsibilities
        responsibilities = self._extract_responsibilities(sections)

        # Extract qualifications (education, years of experience)
        qualifications = self._extract_qualifications(text, sections)

        # Detect implicit expectations
        implicit_expectations = self._detect_implicit_expectations(text)

        jd = JobDescription(
            title=title,
            company=company,
            raw_text=raw_text,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            responsibilities=responsibilities,
            qualifications=qualifications,
            implicit_expectations=implicit_expectations,
        )

        logger.info(
            f"Analyzed JD: {title} at {company}, "
            f"{len(required_skills)} required, {len(preferred_skills)} preferred"
        )

        return jd

    # =========================================================================
    # TEXT CLEANING
    # =========================================================================

    def _clean_text(self, text: str) -> str:
        """Clean and normalize job description text."""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Normalize bullet characters
        text = re.sub(r"[▪◦‣⁃►]", "•", text)

        return text.strip()

    # =========================================================================
    # TITLE EXTRACTION
    # =========================================================================

    def _extract_title(self, text: str) -> str:
        """
        Extract the job title.
        
        Strategies:
        1. Look for "Position:", "Role:", "Job Title:" labels
        2. First line if it looks like a title (short, has caps)
        3. Look for common title patterns (Senior X Engineer, etc.)
        """
        lines = text.split("\n")

        # Strategy 1: Labeled title
        for line in lines[:10]:
            # Match patterns like "Position: Software Engineer"
            match = re.match(
                r"(?:position|role|job\s*title|title)\s*[:]\s*(.+)",
                line,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()

        # Strategy 2: First substantial line
        for line in lines[:5]:
            line = line.strip()

            # Skip empty or too short
            if len(line) < 5:
                continue

            # Skip if it looks like a company name only
            if line.lower().startswith(("about", "join", "at ")):
                continue

            # Skip if too long (probably not a title)
            if len(line) > 80:
                continue

            # Skip if it's a section header
            if self._is_section_header(line):
                continue

            # Check for common job title patterns
            title_patterns = [
                r"(?:senior|junior|lead|staff|principal|associate)?\s*"
                r"(?:software|frontend|backend|full\s*stack|data|devops|ml|ai|cloud|platform)?\s*"
                r"(?:engineer|developer|architect|scientist|analyst|manager|designer)",
                r"(?:product|project|program|engineering)\s*manager",
                r"(?:ux|ui|product)\s*designer",
            ]

            for pattern in title_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return line

            # If first real line and looks like a title (not too many words)
            words = line.split()
            if 2 <= len(words) <= 8:
                return line

        return "Unknown Position"

    # =========================================================================
    # COMPANY EXTRACTION
    # =========================================================================

    def _extract_company(self, text: str) -> str:
        """
        Extract the company name.
        
        Strategies:
        1. Look for "Company:", "At:", "About [Company]" labels
        2. Look for "at [Company]" or "[Company] is looking" patterns
        """
        lines = text.split("\n")

        # Strategy 1: Labeled company
        for line in lines[:15]:
            match = re.match(
                r"(?:company|employer|organization)\s*[:]\s*(.+)",
                line,
                re.IGNORECASE,
            )
            if match:
                return match.group(1).strip()

        # Strategy 2: "About [Company]" header
        for line in lines[:20]:
            match = re.match(r"about\s+(.+?)(?:\s*[-|:]|$)", line, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                # Avoid matching "About the role" etc.
                if company.lower() not in ["the role", "this role", "the position", "us"]:
                    return company

        # Strategy 3: "[Company] is looking/hiring"
        first_500 = text[:500]
        match = re.search(
            r"([A-Z][A-Za-z0-9\s&]+?)\s+(?:is\s+)?(?:looking|hiring|seeking)",
            first_500,
        )
        if match:
            return match.group(1).strip()

        return "Unknown Company"

    # =========================================================================
    # SECTION SPLITTING
    # =========================================================================

    def _split_into_sections(self, text: str) -> dict[str, str]:
        """
        Split JD into labeled sections.
        
        Returns dict like:
        {
            "required": "• 5+ years Python\n• AWS experience",
            "preferred": "• Kubernetes\n• ML background",
            "responsibilities": "• Build features\n• Code review",
        }
        """
        sections = {}

        # Build a combined pattern for all section types
        all_patterns = {
            "required": REQUIRED_SECTION_PATTERNS,
            "preferred": PREFERRED_SECTION_PATTERNS,
            "responsibilities": RESPONSIBILITIES_PATTERNS,
            "skip": SKIP_SECTION_PATTERNS,
        }

        # Find all section headers
        section_positions = []

        for section_type, patterns in all_patterns.items():
            for pattern in patterns:
                regex = re.compile(
                    rf"^[\s]*({pattern})[\s]*[:]*[\s]*$",
                    re.IGNORECASE | re.MULTILINE,
                )
                for match in regex.finditer(text):
                    section_positions.append({
                        "type": section_type,
                        "start": match.start(),
                        "end": match.end(),
                    })

        # Sort by position
        section_positions.sort(key=lambda x: x["start"])

        # Extract text for each section
        for i, pos in enumerate(section_positions):
            section_type = pos["type"]

            # Skip sections we don't care about
            if section_type == "skip":
                continue

            start = pos["end"]
            if i + 1 < len(section_positions):
                end = section_positions[i + 1]["start"]
            else:
                end = len(text)

            section_text = text[start:end].strip()

            # Append to existing (might have multiple "required" sections)
            if section_type in sections:
                sections[section_type] += "\n" + section_text
            else:
                sections[section_type] = section_text

        return sections

    def _is_section_header(self, line: str) -> bool:
        """Check if a line is a section header."""
        line_lower = line.lower().strip()

        all_patterns = (
            REQUIRED_SECTION_PATTERNS
            + PREFERRED_SECTION_PATTERNS
            + RESPONSIBILITIES_PATTERNS
            + SKIP_SECTION_PATTERNS
        )

        for pattern in all_patterns:
            if re.match(rf"^{pattern}[\s:]*$", line_lower):
                return True

        return False

    # =========================================================================
    # SKILL EXTRACTION
    # =========================================================================

    def _extract_required_skills(
        self, full_text: str, sections: dict[str, str]
    ) -> list[str]:
        """
        Extract required skills.
        
        Sources:
        1. Explicit "Required" section
        2. Inline "must have X" mentions
        3. Strong requirements language
        """
        skills = []

        # Source 1: From required section
        if "required" in sections:
            section_skills = self._extract_skills_from_text(sections["required"])
            skills.extend(section_skills)

        # Source 2: Inline required mentions
        # Pattern: "must have experience with X" or "X is required"
        required_patterns = [
            r"must\s+have\s+(?:experience\s+(?:with|in)\s+)?(.+?)(?:\.|,|$)",
            r"(?:required|require[ds]?)\s*[:]\s*(.+?)(?:\.|$)",
            r"(.+?)\s+is\s+required",
            r"(.+?)\s+is\s+a\s+must",
        ]

        for pattern in required_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                # Extract individual skills from the match
                extracted = self._extract_skills_from_text(match)
                skills.extend(extracted)

        # Deduplicate while preserving order
        return self._deduplicate_skills(skills)

    def _extract_preferred_skills(
        self, full_text: str, sections: dict[str, str]
    ) -> list[str]:
        """
        Extract preferred/nice-to-have skills.
        
        Sources:
        1. Explicit "Preferred" section
        2. Inline "nice to have" mentions
        """
        skills = []

        # Source 1: From preferred section
        if "preferred" in sections:
            section_skills = self._extract_skills_from_text(sections["preferred"])
            skills.extend(section_skills)

        # Source 2: Inline preferred mentions
        preferred_patterns = [
            r"nice\s+to\s+have\s*[:]\s*(.+?)(?:\.|$)",
            r"(?:preferred|bonus|plus)\s*[:]\s*(.+?)(?:\.|$)",
            r"(.+?)\s+(?:is\s+)?a\s+(?:plus|bonus)",
            r"ideally\s+(?:you\s+have\s+)?(.+?)(?:\.|$)",
        ]

        for pattern in preferred_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                extracted = self._extract_skills_from_text(match)
                skills.extend(extracted)

        return self._deduplicate_skills(skills)

    def _extract_skills_from_text(self, text: str) -> list[str]:
        """
        Extract skills from a chunk of text.
        
        Strategies:
        1. Split by bullet points, extract each
        2. Look for known skills in the text
        3. Look for skill indicator phrases
        """
        skills = []

        # Strategy 1: Extract bullet points
        bullet_pattern = re.compile(r"^[\s]*[-•*]\s*(.+?)$", re.MULTILINE)
        bullets = bullet_pattern.findall(text)

        for bullet in bullets:
            # Clean up the bullet text
            bullet = bullet.strip()

            # Skip if too long (probably a sentence, not a skill)
            if len(bullet) > 100:
                # Try to extract known skills from it
                for skill in KNOWN_SKILLS:
                    if re.search(rf"\b{re.escape(skill)}\b", bullet, re.IGNORECASE):
                        skills.append(skill)
                continue

            # Check if it contains known skills
            found_known = False
            for skill in KNOWN_SKILLS:
                if re.search(rf"\b{re.escape(skill)}\b", bullet, re.IGNORECASE):
                    skills.append(skill)
                    found_known = True

            # If no known skill, add the bullet as-is (might be a skill we don't know)
            if not found_known and len(bullet) < 50:
                # Clean up common prefixes
                bullet = re.sub(
                    r"^(?:experience\s+(?:with|in)|knowledge\s+of|proficiency\s+(?:with|in))\s*",
                    "",
                    bullet,
                    flags=re.IGNORECASE,
                )
                if bullet:
                    skills.append(bullet)

        # Strategy 2: Look for known skills in prose (non-bullet text)
        for skill in KNOWN_SKILLS:
            if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE):
                skills.append(skill)

        return skills

    def _deduplicate_skills(self, skills: list[str]) -> list[str]:
        """Remove duplicate skills while preserving order."""
        seen = set()
        unique = []

        for skill in skills:
            # Normalize for comparison
            normalized = skill.lower().strip()

            # Skip empty or very short
            if len(normalized) < 2:
                continue

            if normalized not in seen:
                seen.add(normalized)
                # Use the original casing
                unique.append(skill.strip())

        return unique

    # =========================================================================
    # RESPONSIBILITIES EXTRACTION
    # =========================================================================

    def _extract_responsibilities(self, sections: dict[str, str]) -> list[str]:
        """
        Extract job responsibilities.
        
        These are the "what you'll do" items.
        """
        responsibilities = []

        if "responsibilities" not in sections:
            return responsibilities

        text = sections["responsibilities"]

        # Extract bullet points
        bullet_pattern = re.compile(r"^[\s]*[-•*]\s*(.+?)$", re.MULTILINE)
        bullets = bullet_pattern.findall(text)

        for bullet in bullets:
            bullet = bullet.strip()
            if len(bullet) > 10:  # Skip very short bullets
                responsibilities.append(bullet)

        # If no bullets found, split by newlines
        if not responsibilities:
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if len(line) > 20:  # Reasonable length for a responsibility
                    responsibilities.append(line)

        return responsibilities[:10]  # Limit to top 10

    # =========================================================================
    # QUALIFICATIONS EXTRACTION
    # =========================================================================

    def _extract_qualifications(
        self, full_text: str, sections: dict[str, str]
    ) -> list[str]:
        """
        Extract qualifications (education, experience level).
        
        These are things like:
        - "B.S. in Computer Science"
        - "5+ years of experience"
        - "PMP certification"
        """
        qualifications = []

        # Look for degree requirements
        degree_patterns = [
            r"(?:bachelor'?s?|master'?s?|ph\.?d\.?|b\.?s\.?|m\.?s\.?|b\.?a\.?|m\.?b\.?a\.?)"
            r"(?:\s+(?:degree\s+)?(?:in|of)\s+[\w\s]+)?",
        ]

        for pattern in degree_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                if match.strip():
                    qualifications.append(match.strip())

        # Look for years of experience
        experience_pattern = re.compile(
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)?",
            re.IGNORECASE,
        )
        matches = experience_pattern.findall(full_text)
        for years in matches:
            qualifications.append(f"{years}+ years experience")

        # Look for certifications
        cert_patterns = [
            r"(?:aws|azure|gcp|google)\s+certifi(?:ed|cation)",
            r"pmp\s+certifi(?:ed|cation)",
            r"scrum\s+(?:master\s+)?certifi(?:ed|cation)",
            r"cissp",
            r"cka|ckad",  # Kubernetes certs
        ]

        for pattern in cert_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                match = re.search(pattern, full_text, re.IGNORECASE)
                qualifications.append(match.group(0))

        return self._deduplicate_skills(qualifications)[:10]

    # =========================================================================
    # IMPLICIT EXPECTATIONS DETECTION
    # =========================================================================

    def _detect_implicit_expectations(self, text: str) -> list[str]:
        """
        Detect implicit expectations from culture signals.
        
        These are phrases that hint at what working there is really like.
        """
        expectations = []
        text_lower = text.lower()

        for phrase, meaning in IMPLICIT_EXPECTATION_PHRASES.items():
            if phrase in text_lower:
                expectations.append(meaning)

        # Deduplicate (some phrases have same meaning)
        return list(set(expectations))

