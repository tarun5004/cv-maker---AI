"""
Explanation Engine

Generates human-readable explanations for CV tailoring changes.

=============================================================================
PHILOSOPHY: MENTOR, NOT MACHINE
=============================================================================

Every explanation should sound like advice from a helpful career mentor:
- Clear and specific
- References the actual job posting
- Explains the "why" not just the "what"
- Honest about limitations

BAD explanations:
- "Optimized your resume for ATS compatibility" (buzzword soup)
- "Enhanced visibility of key competencies" (corporate speak)
- "AI-powered skill alignment detected synergies" (cringe)

GOOD explanations:
- "We moved Python to the top of your skills because the job lists it first in requirements."
- "We didn't add Kubernetes because you didn't mention it in your experience."
- "This bullet now mentions AWS explicitly because you listed it as a skill."

=============================================================================
EXPLANATION TYPES
=============================================================================

1. GLOBAL STRATEGY
   Overall approach: "Your CV matches 70% of required skills. We focused on..."

2. SECTION EXPLANATIONS
   Per-section changes: "In your Google experience, we made 2 changes..."

3. SKILL EXPLANATIONS
   Why skills were reordered: "React moved up because it's a required skill"

4. CHANGE EXPLANATIONS
   Individual bullet changes: "Added 'REST' because the JD mentions API development"

5. GAP EXPLANATIONS
   What we couldn't fix: "Kubernetes is required but not in your experience"

=============================================================================
TONE GUIDELINES
=============================================================================

- Use "we" not "the system" or "the AI"
- Use "because" to explain reasoning
- Be specific: mention actual skills and sections
- Acknowledge uncertainty: "you might want to verify..."
- Be honest about gaps: "we couldn't address..."

"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from core.models import (
    UserProfile,
    JobDescription,
    Suggestion,
    Explanations,
    SectionExplanation,
    CVSection,
)
from services.skill_matcher import SkillMatchResult

logger = logging.getLogger(__name__)


# =============================================================================
# EXPLANATION TEMPLATES
# =============================================================================

# Templates use {placeholders} for dynamic content
# Keep language simple and specific

GLOBAL_STRATEGY_TEMPLATES = {
    "strong_match": (
        "Great news! Your CV matches {match_percent}% of the required skills. "
        "We focused on making your strongest matches ({top_skills}) more visible "
        "to recruiters who scan quickly."
    ),
    "moderate_match": (
        "Your CV covers {match_percent}% of what {company} is looking for. "
        "We highlighted your relevant experience with {top_skills}. "
        "You might want to think about how to address {gap_skills} if you have related experience."
    ),
    "weak_match": (
        "Honest assessment: your CV matches {match_percent}% of the required skills. "
        "We made the most of what you have ({top_skills}), but there are gaps in {gap_skills}. "
        "Consider whether this role is the right fit, or if you can bridge these gaps."
    ),
    "no_required_skills": (
        "The job posting didn't list specific required skills, so we focused on "
        "general improvements and making your experience clearer."
    ),
}

SKILL_REORDER_TEMPLATES = {
    "moved_up_required": (
        "Moved {skill} higher in your skills list because the job specifically requires it."
    ),
    "moved_up_preferred": (
        "Moved {skill} up because it's listed as a preferred skill for this role."
    ),
    "kept_position": (
        "{skill} stays where it is - it's not mentioned in this job posting, "
        "but still valuable to show."
    ),
}

BULLET_CHANGE_TEMPLATES = {
    "skill_injection": (
        "Added '{skill}' to make it clear you have this experience. "
        "The job requires {skill}, and your skills list shows you know it."
    ),
    "verb_upgrade": (
        "Changed '{old_verb}' to '{new_verb}' - it's a stronger action word "
        "that better conveys what you actually did."
    ),
    "no_change_needed": (
        "This bullet is already well-written for the role. No changes made."
    ),
}

GAP_TEMPLATES = {
    "missing_required": (
        "We couldn't address {skill} because it's not in your CV. "
        "If you do have experience with {skill}, consider adding it to your skills section."
    ),
    "missing_preferred": (
        "{skill} is listed as 'nice to have' but isn't in your CV. "
        "Not a dealbreaker, but worth adding if you have any exposure to it."
    ),
}


# =============================================================================
# EXPLANATION RESULT STRUCTURES
# =============================================================================


@dataclass
class SkillExplanation:
    """Explanation for a single skill's treatment."""
    skill: str
    action: str  # "moved_up", "kept", "not_added"
    reason: str
    from_position: Optional[int] = None
    to_position: Optional[int] = None


@dataclass
class BulletExplanation:
    """Explanation for a bullet point change."""
    original: str
    changed: str
    explanation: str
    verification_needed: bool = False


@dataclass
class GapExplanation:
    """Explanation for a skill gap we couldn't address."""
    skill: str
    importance: str  # "required" or "preferred"
    explanation: str
    suggestion: str


@dataclass
class FullExplanation:
    """Complete explanation package for the user."""
    
    # High-level summary
    global_strategy: str
    
    # Match statistics
    match_score_percent: int
    matched_required_count: int
    missing_required_count: int
    
    # Detailed breakdowns
    skill_explanations: list[SkillExplanation]
    section_explanations: list[SectionExplanation]
    gap_explanations: list[GapExplanation]
    
    # Quick summary bullets for UI
    key_points: list[str]


# =============================================================================
# MAIN ENGINE CLASS
# =============================================================================


class ExplanationEngine:
    """
    Generates human-readable explanations for CV changes.
    
    Usage:
        engine = ExplanationEngine()
        explanations = engine.explain(
            original_profile,
            tailored_profile,
            job_description,
            skill_match,
            suggestions,
        )
    
    All explanations are deterministic and template-based.
    No AI, no randomness, same inputs = same outputs.
    """

    def explain(
        self,
        original_profile: UserProfile,
        skill_match: SkillMatchResult,
        jd: JobDescription,
        suggestions: list[Suggestion],
    ) -> FullExplanation:
        """
        Generate complete explanations for all CV changes.
        
        Args:
            original_profile: The user's original CV
            skill_match: Result from skill matching
            jd: The job description
            suggestions: List of suggested changes
            
        Returns:
            FullExplanation with all explanation types
        """
        print("\n" + "=" * 60)
        print("EXPLANATION ENGINE: Generating explanations")
        print("=" * 60)

        # Calculate match statistics
        match_percent = int(skill_match.match_score * 100)
        print(f"📊 Match score: {match_percent}%")

        # Generate global strategy
        global_strategy = self._generate_global_strategy(
            skill_match,
            jd,
        )
        print(f"✓ Global strategy generated")

        # Generate skill explanations
        skill_explanations = self._generate_skill_explanations(
            original_profile.skills,
            skill_match,
        )
        print(f"✓ {len(skill_explanations)} skill explanations")

        # Generate section explanations
        section_explanations = self._generate_section_explanations(
            suggestions,
        )
        print(f"✓ {len(section_explanations)} section explanations")

        # Generate gap explanations
        gap_explanations = self._generate_gap_explanations(
            skill_match,
        )
        print(f"✓ {len(gap_explanations)} gap explanations")

        # Generate key points for quick reading
        key_points = self._generate_key_points(
            skill_match,
            len(suggestions),
        )
        print(f"✓ {len(key_points)} key points")

        return FullExplanation(
            global_strategy=global_strategy,
            match_score_percent=match_percent,
            matched_required_count=len(skill_match.matched_required),
            missing_required_count=len(skill_match.missing_required),
            skill_explanations=skill_explanations,
            section_explanations=section_explanations,
            gap_explanations=gap_explanations,
            key_points=key_points,
        )

    # =========================================================================
    # GLOBAL STRATEGY
    # =========================================================================

    def _generate_global_strategy(
        self,
        skill_match: SkillMatchResult,
        jd: JobDescription,
    ) -> str:
        """
        Generate the high-level strategy explanation.
        
        This is the first thing users see - make it count.
        """
        match_percent = int(skill_match.match_score * 100)
        company = jd.company or "this company"

        # Get top matched skills for display
        top_skills = skill_match.matched_required[:3]
        top_skills_str = self._format_skill_list(top_skills) or "your relevant skills"

        # Get gaps for display
        gap_skills = skill_match.missing_required[:3]
        gap_skills_str = self._format_skill_list(gap_skills) or "some areas"

        # Choose template based on match level
        if not skill_match.matched_required and not skill_match.missing_required:
            template = GLOBAL_STRATEGY_TEMPLATES["no_required_skills"]
            return template
        elif match_percent >= 70:
            template = GLOBAL_STRATEGY_TEMPLATES["strong_match"]
        elif match_percent >= 40:
            template = GLOBAL_STRATEGY_TEMPLATES["moderate_match"]
        else:
            template = GLOBAL_STRATEGY_TEMPLATES["weak_match"]

        return template.format(
            match_percent=match_percent,
            company=company,
            top_skills=top_skills_str,
            gap_skills=gap_skills_str,
        )

    # =========================================================================
    # SKILL EXPLANATIONS
    # =========================================================================

    def _generate_skill_explanations(
        self,
        original_skills: list[str],
        skill_match: SkillMatchResult,
    ) -> list[SkillExplanation]:
        """
        Explain why each skill was reordered (or not).
        
        Focus on the most important changes - don't explain everything.
        """
        explanations = []

        # Create position lookup for original skills
        original_positions = {
            skill.lower(): i
            for i, skill in enumerate(original_skills)
        }

        # Explain matched required skills (most important)
        for i, skill in enumerate(skill_match.matched_required):
            skill_lower = skill.lower()
            original_pos = original_positions.get(skill_lower, -1)
            
            if original_pos > i:
                # Skill moved up
                explanations.append(SkillExplanation(
                    skill=skill,
                    action="moved_up",
                    reason=SKILL_REORDER_TEMPLATES["moved_up_required"].format(
                        skill=skill
                    ),
                    from_position=original_pos + 1,  # 1-indexed for humans
                    to_position=i + 1,
                ))

        # Explain matched preferred skills (if moved significantly)
        for i, skill in enumerate(skill_match.matched_preferred):
            skill_lower = skill.lower()
            original_pos = original_positions.get(skill_lower, -1)
            new_pos = len(skill_match.matched_required) + i
            
            if original_pos > new_pos + 3:  # Only if moved up by more than 3
                explanations.append(SkillExplanation(
                    skill=skill,
                    action="moved_up",
                    reason=SKILL_REORDER_TEMPLATES["moved_up_preferred"].format(
                        skill=skill
                    ),
                    from_position=original_pos + 1,
                    to_position=new_pos + 1,
                ))

        # Limit to top 5 most important changes
        return explanations[:5]

    # =========================================================================
    # SECTION EXPLANATIONS
    # =========================================================================

    def _generate_section_explanations(
        self,
        suggestions: list[Suggestion],
    ) -> list[SectionExplanation]:
        """
        Generate explanations for each section that had changes.
        
        Group suggestions by section and summarize.
        """
        # Group suggestions by section
        by_section: dict[str, list[Suggestion]] = {}
        for suggestion in suggestions:
            section = suggestion.section_name or "unknown"
            if section not in by_section:
                by_section[section] = []
            by_section[section].append(suggestion)

        explanations = []
        
        for section_name, section_suggestions in by_section.items():
            # Count accepted vs pending
            pending = [s for s in section_suggestions if s.status == "pending"]
            
            # Build changes description
            if len(pending) == 1:
                changes = "1 suggested improvement"
            else:
                changes = f"{len(pending)} suggested improvements"

            # Build reasoning from the suggestions
            reasons = set()
            for s in section_suggestions[:3]:  # Sample first 3
                if s.reason:
                    reasons.add(s.reason)

            reasoning = "; ".join(list(reasons)[:2]) if reasons else "General improvements for clarity"

            explanations.append(SectionExplanation(
                section_name=self._format_section_name(section_name),
                changes_made=changes,
                reasoning=reasoning,
            ))

        return explanations

    # =========================================================================
    # GAP EXPLANATIONS
    # =========================================================================

    def _generate_gap_explanations(
        self,
        skill_match: SkillMatchResult,
    ) -> list[GapExplanation]:
        """
        Explain what we COULDN'T do and why.
        
        Honesty builds trust. Don't hide limitations.
        """
        explanations = []

        # Missing required skills (important gaps)
        for skill in skill_match.missing_required[:5]:  # Limit to 5
            explanations.append(GapExplanation(
                skill=skill,
                importance="required",
                explanation=GAP_TEMPLATES["missing_required"].format(skill=skill),
                suggestion=f"If you have any experience with {skill}, add it to your CV.",
            ))

        # Missing preferred skills (less critical)
        for skill in skill_match.missing_preferred[:3]:  # Limit to 3
            explanations.append(GapExplanation(
                skill=skill,
                importance="preferred",
                explanation=GAP_TEMPLATES["missing_preferred"].format(skill=skill),
                suggestion=f"Consider mentioning {skill} if you have even basic exposure.",
            ))

        return explanations

    # =========================================================================
    # KEY POINTS
    # =========================================================================

    def _generate_key_points(
        self,
        skill_match: SkillMatchResult,
        suggestion_count: int,
    ) -> list[str]:
        """
        Generate bullet points for quick reading.
        
        These should be scannable in 5 seconds.
        """
        points = []
        match_percent = int(skill_match.match_score * 100)

        # Overall match
        points.append(f"Your CV matches {match_percent}% of required skills")

        # What matched
        if skill_match.matched_required:
            matched_str = ", ".join(skill_match.matched_required[:3])
            points.append(f"Strong match on: {matched_str}")

        # What's missing
        if skill_match.missing_required:
            missing_str = ", ".join(skill_match.missing_required[:3])
            points.append(f"Gaps to consider: {missing_str}")

        # Changes made
        if suggestion_count > 0:
            points.append(f"We suggest {suggestion_count} improvement(s) to your bullet points")
        else:
            points.append("No major changes needed - your CV is well-written")

        # Skills reordered
        if skill_match.matched_required:
            points.append("Skills reordered to show best matches first")

        return points

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _format_skill_list(self, skills: list[str]) -> str:
        """
        Format a list of skills for display.
        
        Examples:
            ["Python"] → "Python"
            ["Python", "React"] → "Python and React"
            ["Python", "React", "AWS"] → "Python, React, and AWS"
        """
        if not skills:
            return ""
        if len(skills) == 1:
            return skills[0]
        if len(skills) == 2:
            return f"{skills[0]} and {skills[1]}"
        return ", ".join(skills[:-1]) + f", and {skills[-1]}"

    def _format_section_name(self, section_name: str) -> str:
        """
        Format section name for display.
        
        "work_experience" → "Work Experience"
        """
        return section_name.replace("_", " ").title()

    # =========================================================================
    # CORE MODELS BUILDER
    # =========================================================================

    def build_explanations_model(
        self,
        full_explanation: FullExplanation,
    ) -> Explanations:
        """
        Convert FullExplanation to the core Explanations model.
        
        This is for compatibility with TailoredCVResult.
        """
        return Explanations(
            global_strategy=full_explanation.global_strategy,
            section_explanations=full_explanation.section_explanations,
        )

    # =========================================================================
    # SINGLE SUGGESTION EXPLAINER
    # =========================================================================

    def explain_suggestion(
        self,
        suggestion: Suggestion,
        jd: JobDescription,
    ) -> str:
        """
        Generate a detailed explanation for a single suggestion.
        
        Used when user clicks "Why?" on a specific change.
        """
        parts = []

        # Start with what changed
        parts.append(f"Original: \"{suggestion.original_text}\"")
        parts.append(f"Suggested: \"{suggestion.suggested_text}\"")
        parts.append("")

        # Explain why
        if suggestion.reason:
            parts.append(f"Why: {suggestion.reason}")
        else:
            parts.append("Why: General improvement for clarity")

        # Add verification if needed
        if suggestion.prompt_question:
            parts.append("")
            parts.append(f"Before accepting, please verify: {suggestion.prompt_question}")

        # Add confidence context
        if suggestion.confidence < 0.8:
            parts.append("")
            parts.append(
                "Note: We're not 100% sure about this change. "
                "Please review carefully before accepting."
            )

        return "\n".join(parts)

    # =========================================================================
    # DIFF EXPLAINER
    # =========================================================================

    def explain_diff(
        self,
        original: str,
        rewritten: str,
    ) -> str:
        """
        Explain the difference between original and rewritten text.
        
        Simple word-level diff for transparency.
        """
        original_words = set(original.lower().split())
        rewritten_words = set(rewritten.lower().split())

        added = rewritten_words - original_words
        removed = original_words - rewritten_words

        parts = []

        if added:
            parts.append(f"Added: {', '.join(sorted(added))}")
        if removed:
            parts.append(f"Removed: {', '.join(sorted(removed))}")
        if not added and not removed:
            parts.append("Minor wording adjustment (no significant word changes)")

        return "; ".join(parts)

