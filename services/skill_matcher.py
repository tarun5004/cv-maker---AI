"""
Skill Matcher Service

Compares CV skills against job description requirements.

=============================================================================
APPROACH: Direct Comparison + Normalization
=============================================================================

This is intentionally simple:
1. Normalize skill names (React.js → react, Python3 → python)
2. Compare sets directly
3. Return what matched, what's missing, what's extra

No AI, no embeddings, no semantic similarity for MVP.
Just string matching with smart normalization.

Why this works:
- Most skills have standard names
- Normalization handles common variations
- Deterministic = debuggable
- Fast = good UX

Why this sometimes fails:
- "REST API experience" won't match "RESTful services"
- "ML" won't match "Machine Learning"
- Context is lost ("3 years of Python" vs just "Python")

We accept these limitations. Users see the gaps and can correct.

=============================================================================
NORMALIZATION RULES
=============================================================================

We apply these transformations to both CV and JD skills:
1. Lowercase everything
2. Remove common suffixes (.js, .py, etc.)
3. Apply known aliases (ReactJS → react, golang → go)
4. Remove version numbers (Python 3.10 → python)
5. Trim whitespace and punctuation

This lets us match:
- "React.js" with "ReactJS" with "React"
- "Node" with "Node.js" with "NodeJS"
- "Python 3" with "Python3" with "Python"
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from copy import deepcopy

from core.models import UserProfile, JobDescription, CVSection, SectionAnalysis

logger = logging.getLogger(__name__)


# =============================================================================
# SKILL ALIASES
# =============================================================================

# Map variations to a canonical form
# Key = what we might see, Value = what we normalize to
SKILL_ALIASES = {
    # JavaScript ecosystem
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "vue js": "vue",
    "angularjs": "angular",
    "angular.js": "angular",
    "nodejs": "node",
    "node.js": "node",
    "node js": "node",
    "expressjs": "express",
    "express.js": "express",
    "nextjs": "next.js",
    "next js": "next.js",
    "nuxtjs": "nuxt",
    "nuxt.js": "nuxt",
    
    # Languages
    "golang": "go",
    "python3": "python",
    "python 3": "python",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "cpp": "c++",
    "c plus plus": "c++",
    "csharp": "c#",
    "c sharp": "c#",
    
    # Databases
    "postgres": "postgresql",
    "mongo": "mongodb",
    "mongo db": "mongodb",
    "dynamodb": "dynamo",
    "amazon dynamodb": "dynamo",
    
    # Cloud
    "amazon web services": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "microsoft azure": "azure",
    
    # DevOps
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "ci/cd": "cicd",
    "ci cd": "cicd",
    "github actions": "github-actions",
    "gitlab ci": "gitlab-ci",
    
    # Data
    "scikit-learn": "sklearn",
    "scikit learn": "sklearn",
    "tensor flow": "tensorflow",
    "py torch": "pytorch",
    
    # Misc
    "vs code": "vscode",
    "visual studio code": "vscode",
    "rest api": "rest",
    "restful": "rest",
    "restful api": "rest",
}


# =============================================================================
# MATCH RESULT STRUCTURE
# =============================================================================


@dataclass
class SkillMatchResult:
    """
    The result of comparing CV skills against JD requirements.
    
    This is the main output of the matcher.
    Simple structure, easy to debug, easy to display.
    """
    
    # Skills that appear in BOTH CV and JD (required)
    matched_required: list[str] = field(default_factory=list)
    
    # Skills that appear in BOTH CV and JD (preferred)
    matched_preferred: list[str] = field(default_factory=list)
    
    # Skills in JD (required) but NOT in CV — these are gaps
    missing_required: list[str] = field(default_factory=list)
    
    # Skills in JD (preferred) but NOT in CV — opportunities
    missing_preferred: list[str] = field(default_factory=list)
    
    # Skills in CV but NOT in JD — might still be relevant
    extra_skills: list[str] = field(default_factory=list)
    
    # Overall match score (0.0 to 1.0)
    # Based on required skills only — preferred are bonus
    match_score: float = 0.0
    
    def __repr__(self) -> str:
        return (
            f"SkillMatchResult("
            f"matched_req={len(self.matched_required)}, "
            f"matched_pref={len(self.matched_preferred)}, "
            f"missing_req={len(self.missing_required)}, "
            f"missing_pref={len(self.missing_preferred)}, "
            f"extra={len(self.extra_skills)}, "
            f"score={self.match_score:.1%})"
        )


# =============================================================================
# MAIN MATCHER CLASS
# =============================================================================


class SkillMatcher:
    """
    Matches CV skills against job description requirements.
    
    Usage:
        matcher = SkillMatcher()
        result = matcher.match_skills(cv_skills, jd)
        
        # Or with full profile annotation:
        annotated_profile = matcher.match(profile, jd)
    
    The matcher is stateless and deterministic.
    Same inputs always produce same outputs.
    """

    def match_skills(
        self,
        cv_skills: list[str],
        jd: JobDescription,
    ) -> SkillMatchResult:
        """
        Compare a list of CV skills against JD requirements.
        
        This is the core matching logic.
        
        Args:
            cv_skills: List of skills from the CV (e.g., ["Python", "React"])
            jd: The job description with required/preferred skills
            
        Returns:
            SkillMatchResult with categorized skills
        """
        logger.info(f"Matching {len(cv_skills)} CV skills against JD")

        # Normalize all skills for comparison
        cv_normalized = self._normalize_skill_list(cv_skills)
        required_normalized = self._normalize_skill_list(jd.required_skills)
        preferred_normalized = self._normalize_skill_list(jd.preferred_skills)

        # Create lookup maps: normalized → original
        # This lets us report the original skill names, not normalized ones
        cv_lookup = self._create_lookup(cv_skills)
        required_lookup = self._create_lookup(jd.required_skills)
        preferred_lookup = self._create_lookup(jd.preferred_skills)

        # Find matches and gaps
        matched_required_norm = cv_normalized & required_normalized
        matched_preferred_norm = cv_normalized & preferred_normalized
        missing_required_norm = required_normalized - cv_normalized
        missing_preferred_norm = preferred_normalized - cv_normalized
        
        # Extra skills: in CV but not in any JD category
        all_jd_normalized = required_normalized | preferred_normalized
        extra_norm = cv_normalized - all_jd_normalized

        # Convert back to original names
        matched_required = [required_lookup[n] for n in matched_required_norm]
        matched_preferred = [preferred_lookup[n] for n in matched_preferred_norm]
        missing_required = [required_lookup[n] for n in missing_required_norm]
        missing_preferred = [preferred_lookup[n] for n in missing_preferred_norm]
        extra_skills = [cv_lookup[n] for n in extra_norm]

        # Calculate match score based on required skills only
        if len(required_normalized) > 0:
            match_score = len(matched_required_norm) / len(required_normalized)
        else:
            # No required skills specified = assume good match
            match_score = 1.0

        result = SkillMatchResult(
            matched_required=sorted(matched_required),
            matched_preferred=sorted(matched_preferred),
            missing_required=sorted(missing_required),
            missing_preferred=sorted(missing_preferred),
            extra_skills=sorted(extra_skills),
            match_score=match_score,
        )

        logger.info(f"Match result: {result}")
        return result

    def match(
        self,
        profile: UserProfile,
        jd: JobDescription,
    ) -> UserProfile:
        """
        Match CV against JD and annotate the profile.
        
        This is the full matching flow:
        1. Match skills list
        2. Analyze each work experience section
        3. Analyze each project section
        4. Populate analysis fields
        
        Args:
            profile: The user's parsed CV
            jd: The job description
            
        Returns:
            Annotated UserProfile (deep copy, original unchanged)
        """
        logger.info(f"Full profile matching for: {profile.full_name}")

        # Deep copy to avoid mutating original
        annotated = deepcopy(profile)

        # Match skills list
        skill_result = self.match_skills(profile.skills, jd)

        # Store the match result on the profile for later use
        # We use a private attribute since it's not in the model
        annotated._skill_match = skill_result

        # Analyze each work experience section
        for i, section in enumerate(annotated.work_experience):
            analysis = self._analyze_section(section, jd)
            annotated.work_experience[i].analysis = analysis

        # Analyze each project section
        for i, section in enumerate(annotated.projects):
            analysis = self._analyze_section(section, jd)
            annotated.projects[i].analysis = analysis

        # Analyze education (usually less relevant, but check anyway)
        for i, section in enumerate(annotated.education):
            analysis = self._analyze_section(section, jd)
            annotated.education[i].analysis = analysis

        return annotated

    # =========================================================================
    # NORMALIZATION
    # =========================================================================

    def _normalize_skill(self, skill: str) -> str:
        """
        Normalize a single skill name for comparison.
        
        Steps:
        1. Lowercase
        2. Strip whitespace
        3. Remove version numbers
        4. Apply known aliases
        5. Remove common suffixes
        
        Examples:
            "React.js" → "react"
            "Python 3.10" → "python"
            "Node.JS" → "node"
        """
        # Start with lowercase and stripped
        normalized = skill.lower().strip()

        # Remove common punctuation at edges
        normalized = normalized.strip(".,;:-•")

        # Remove version numbers (e.g., "Python 3.10" → "Python")
        normalized = re.sub(r"\s*\d+(\.\d+)*\s*$", "", normalized)
        normalized = re.sub(r"\s*v?\d+(\.\d+)*\s*$", "", normalized)

        # Check aliases first (before removing suffixes)
        if normalized in SKILL_ALIASES:
            normalized = SKILL_ALIASES[normalized]

        # Remove common suffixes if still present
        suffixes_to_remove = [".js", ".py", ".ts", ".go", ".rs"]
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break

        # Check aliases again after suffix removal
        if normalized in SKILL_ALIASES:
            normalized = SKILL_ALIASES[normalized]

        return normalized.strip()

    def _normalize_skill_list(self, skills: list[str]) -> set[str]:
        """
        Normalize a list of skills and return as a set.
        
        Using a set because we only care about presence, not count.
        """
        normalized = set()
        for skill in skills:
            norm = self._normalize_skill(skill)
            if norm:  # Skip empty strings
                normalized.add(norm)
        return normalized

    def _create_lookup(self, skills: list[str]) -> dict[str, str]:
        """
        Create a mapping from normalized → original skill name.
        
        This lets us report the original name (e.g., "React.js")
        while matching on normalized form (e.g., "react").
        """
        lookup = {}
        for skill in skills:
            normalized = self._normalize_skill(skill)
            if normalized and normalized not in lookup:
                # Keep the first occurrence's casing
                lookup[normalized] = skill
        return lookup

    # =========================================================================
    # SECTION ANALYSIS
    # =========================================================================

    def _analyze_section(
        self,
        section: CVSection,
        jd: JobDescription,
    ) -> SectionAnalysis:
        """
        Analyze a single CV section for relevance to the JD.
        
        We look at:
        1. Skills mentioned in the section's description points
        2. Overlap with JD required/preferred skills
        3. What's missing that could plausibly be added
        
        Returns:
            SectionAnalysis with matched skills, score, gaps, explanation
        """
        # Combine all text from the section
        section_text = " ".join(section.description_points)
        section_text += f" {section.title} {section.organization}"
        section_text_lower = section_text.lower()

        # All JD skills (both required and preferred)
        all_jd_skills = jd.required_skills + jd.preferred_skills

        # Find skills mentioned in this section
        matched_skills = []
        for skill in all_jd_skills:
            # Check if skill appears in section text
            skill_normalized = self._normalize_skill(skill)
            
            # Try to match both original and normalized forms
            if (
                skill.lower() in section_text_lower
                or skill_normalized in section_text_lower
            ):
                matched_skills.append(skill)

        # Calculate relevance score
        # Based on how many JD skills appear in this section
        if all_jd_skills:
            relevance_score = len(matched_skills) / len(all_jd_skills)
        else:
            relevance_score = 0.0

        # Limit to 1.0
        relevance_score = min(relevance_score, 1.0)

        # Find gaps: required skills that COULD be added here
        # (skills the section doesn't mention but might be relevant)
        gaps = self._find_section_gaps(section, jd, matched_skills)

        # Build explanation
        explanation = self._build_section_explanation(
            section, matched_skills, relevance_score, jd
        )

        return SectionAnalysis(
            matched_skills=matched_skills,
            relevance_score=relevance_score,
            gaps=gaps,
            explanation=explanation,
        )

    def _find_section_gaps(
        self,
        section: CVSection,
        jd: JobDescription,
        already_matched: list[str],
    ) -> list[str]:
        """
        Find required skills that could plausibly be added to this section.
        
        We can't add "10 years Java experience" to a 3-month internship.
        But if the section mentions "built web apps", we might suggest
        adding specific technologies if they're in the JD.
        
        This is heuristic and will make mistakes. That's okay.
        """
        gaps = []
        matched_normalized = self._normalize_skill_list(already_matched)

        # Only look at required skills for gaps
        for skill in jd.required_skills:
            skill_normalized = self._normalize_skill(skill)

            # Skip if already matched
            if skill_normalized in matched_normalized:
                continue

            # Check if this skill could plausibly fit
            if self._skill_could_fit_section(skill, section):
                gaps.append(skill)

        # Limit to 5 gaps per section (don't overwhelm)
        return gaps[:5]

    def _skill_could_fit_section(self, skill: str, section: CVSection) -> bool:
        """
        Heuristic: Could this skill plausibly be mentioned in this section?
        
        Rules:
        - Technical skills fit technical roles
        - Management skills fit management roles
        - Any skill fits if section has generic tech terms
        
        This is imperfect but better than suggesting SQL to a barista job.
        """
        skill_lower = skill.lower()
        title_lower = section.title.lower()
        org_lower = section.organization.lower()
        description_lower = " ".join(section.description_points).lower()

        # Technical role indicators
        tech_role_words = [
            "engineer", "developer", "programmer", "architect",
            "scientist", "analyst", "devops", "sre", "infrastructure",
            "software", "frontend", "backend", "fullstack", "full-stack",
            "data", "ml", "machine learning", "ai",
        ]

        # Check if this is a technical role
        is_tech_role = any(word in title_lower for word in tech_role_words)

        # Technical skill indicators
        tech_skill_words = [
            "python", "java", "react", "node", "sql", "aws", "docker",
            "kubernetes", "api", "database", "cloud", "linux", "git",
        ]

        is_tech_skill = any(word in skill_lower for word in tech_skill_words)

        # If tech skill and tech role, likely fits
        if is_tech_skill and is_tech_role:
            return True

        # If description mentions technical terms, skill might fit
        tech_description_words = [
            "code", "develop", "build", "implement", "deploy",
            "software", "application", "system", "platform",
            "database", "api", "service", "infrastructure",
        ]

        has_tech_description = any(
            word in description_lower for word in tech_description_words
        )

        if is_tech_skill and has_tech_description:
            return True

        # Management/soft skills fit most roles
        soft_skills = [
            "leadership", "management", "communication", "teamwork",
            "agile", "scrum", "project management",
        ]

        if any(word in skill_lower for word in soft_skills):
            return True

        # Default: don't suggest (conservative)
        return False

    def _build_section_explanation(
        self,
        section: CVSection,
        matched_skills: list[str],
        score: float,
        jd: JobDescription,
    ) -> str:
        """
        Build a human-readable explanation for this section's relevance.
        
        Examples:
        - "Highly relevant. Mentions Python, AWS, and Docker."
        - "Moderately relevant. Mentions React but missing Node experience."
        - "Less relevant. No direct skill matches, but has software experience."
        """
        if score >= 0.3:
            level = "Highly relevant"
        elif score >= 0.1:
            level = "Moderately relevant"
        else:
            level = "Less directly relevant"

        parts = [level + "."]

        if matched_skills:
            skill_list = ", ".join(matched_skills[:4])
            if len(matched_skills) > 4:
                skill_list += f" (+{len(matched_skills) - 4} more)"
            parts.append(f"Mentions: {skill_list}.")
        else:
            parts.append("No direct skill matches found.")

        return " ".join(parts)

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_match_summary(self, profile: UserProfile) -> dict:
        """
        Get a summary of the match for display.
        
        Requires that match() has been called on the profile.
        """
        if not hasattr(profile, "_skill_match"):
            return {"error": "Profile not matched yet. Call match() first."}

        result: SkillMatchResult = profile._skill_match

        return {
            "score_percent": round(result.match_score * 100, 1),
            "matched_required_count": len(result.matched_required),
            "missing_required_count": len(result.missing_required),
            "matched_preferred_count": len(result.matched_preferred),
            "status": self._score_to_status(result.match_score),
            "matched_required": result.matched_required,
            "missing_required": result.missing_required,
            "matched_preferred": result.matched_preferred,
            "missing_preferred": result.missing_preferred,
        }

    def _score_to_status(self, score: float) -> str:
        """Convert match score to human-readable status."""
        if score >= 0.7:
            return "strong"
        elif score >= 0.4:
            return "moderate"
        else:
            return "needs_work"

