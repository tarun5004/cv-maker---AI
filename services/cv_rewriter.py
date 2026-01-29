"""
CV Rewriter Service (Rule-Based MVP)

Applies conservative, template-based rewrites to CV sections.

=============================================================================
PHILOSOPHY: CONSERVATIVE CHANGES ONLY
=============================================================================

This rewriter follows strict rules:

1. NEVER INVENT EXPERIENCE
   - We don't add skills the user didn't mention
   - We don't add metrics that weren't there
   - We don't fabricate responsibilities

2. ONLY REPHRASE WHAT EXISTS
   - Reorder words to front-load relevant skills
   - Use stronger action verbs when appropriate
   - Add explicit skill mentions IF the context implies them

3. PRESERVE THE USER'S VOICE
   - Keep their terminology where possible
   - Maintain their level of detail
   - Don't make it sound robotic

=============================================================================
REWRITE STRATEGIES
=============================================================================

Strategy 1: SKILL FRONT-LOADING
   Before: "Built web applications using modern frameworks"
   After:  "Built React web applications using modern frameworks"
   Why:    If JD wants React and user mentioned "modern frameworks",
           and they have React in their skills, we make it explicit.

Strategy 2: ACTION VERB STRENGTHENING
   Before: "Worked on API development"
   After:  "Developed REST APIs"
   Why:    "Worked on" is weak. "Developed" is stronger.
           Only if we're confident about the action.

Strategy 3: SKILL INJECTION (CONSERVATIVE)
   Before: "Managed cloud infrastructure"
   After:  "Managed AWS cloud infrastructure"
   Why:    If user has AWS in skills and JD wants AWS,
           we make implicit knowledge explicit.
           BUT we add a prompt question to verify.

Strategy 4: METRIC HIGHLIGHTING
   Before: "Improved system performance significantly"
   After:  "Improved system performance significantly"
   Why:    We DON'T add fake metrics. We might suggest
           the user add specifics via a prompt question.

=============================================================================
WHAT WE DON'T DO (YET)
=============================================================================

- Full sentence rewrites (needs AI)
- Tone adjustment (needs AI)
- Summary generation (needs AI)
- Contextual rephrasing (needs AI)

These will be added when we integrate Claude.

"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from copy import deepcopy

from core.models import (
    UserProfile,
    JobDescription,
    CVSection,
    Suggestion,
    TailoredCVResult,
    Explanations,
    SectionExplanation,
)
from services.skill_matcher import SkillMatchResult

logger = logging.getLogger(__name__)


# =============================================================================
# WEAK VERBS → STRONG VERBS MAPPING
# =============================================================================

# These are safe substitutions that don't change meaning
VERB_UPGRADES = {
    "worked on": "contributed to",
    "helped with": "supported",
    "was responsible for": "managed",
    "was in charge of": "led",
    "did": "executed",
    "made": "created",
    "got": "achieved",
    "used": "utilized",
    "tried to": "worked to",
    "assisted with": "assisted in",
}

# Action verbs that are already strong (don't touch these)
STRONG_VERBS = {
    "developed", "built", "created", "designed", "implemented",
    "led", "managed", "architected", "engineered", "deployed",
    "optimized", "improved", "increased", "reduced", "automated",
    "launched", "delivered", "established", "spearheaded", "drove",
}


# =============================================================================
# REWRITE RESULT STRUCTURE
# =============================================================================


@dataclass
class BulletRewrite:
    """
    A single bullet point rewrite suggestion.
    """
    original: str
    rewritten: str
    changes_made: list[str]  # List of changes applied
    confidence: float  # 0.0 to 1.0 - how confident are we
    prompt_question: Optional[str] = None  # Question to verify with user


@dataclass
class SectionRewrite:
    """
    Rewrite results for a single CV section.
    """
    section_title: str
    bullet_rewrites: list[BulletRewrite]
    skills_added: list[str]  # Skills made explicit
    changes_summary: str


@dataclass
class RewriteResult:
    """
    Complete rewrite result for the CV.
    """
    # Reordered skills list (matched first)
    reordered_skills: list[str]
    
    # Per-section rewrites
    section_rewrites: list[SectionRewrite]
    
    # List of all suggestions for UI
    suggestions: list[Suggestion]
    
    # Summary of changes
    summary: str
    
    # Questions to ask the user
    verification_questions: list[str]


# =============================================================================
# MAIN REWRITER CLASS
# =============================================================================


class CVRewriter:
    """
    Rule-based CV rewriter for MVP.
    
    Usage:
        rewriter = CVRewriter()
        result = rewriter.rewrite(profile, jd, skill_match)
    
    This is intentionally conservative. We prefer to:
    - Under-rewrite rather than over-rewrite
    - Ask questions rather than assume
    - Preserve original meaning always
    """

    def rewrite(
        self,
        profile: UserProfile,
        jd: JobDescription,
        skill_match: SkillMatchResult,
    ) -> RewriteResult:
        """
        Rewrite CV sections based on JD requirements.
        
        Args:
            profile: The user's parsed CV
            jd: The job description
            skill_match: Result from skill matching
            
        Returns:
            RewriteResult with suggestions and rewrites
        """
        print("\n" + "=" * 60)
        print("CV REWRITER: Starting rule-based rewrite")
        print("=" * 60)

        # Step 1: Reorder skills
        reordered_skills = self._reorder_skills(
            profile.skills,
            skill_match,
        )
        print(f"✓ Skills reordered ({len(reordered_skills)} total)")

        # Step 2: Collect all skills for injection
        # These are skills in the CV that match the JD
        injectable_skills = self._get_injectable_skills(profile, skill_match)
        print(f"✓ Found {len(injectable_skills)} injectable skills")

        # Step 3: Rewrite work experience sections
        section_rewrites = []
        all_suggestions = []
        all_questions = []

        for section in profile.work_experience:
            print(f"\n📝 Rewriting: {section.title} @ {section.organization}")
            
            rewrite = self._rewrite_section(
                section,
                jd,
                injectable_skills,
            )
            section_rewrites.append(rewrite)
            
            # Collect suggestions from this section
            for bullet_rewrite in rewrite.bullet_rewrites:
                if bullet_rewrite.original != bullet_rewrite.rewritten:
                    suggestion = Suggestion(
                        original_text=bullet_rewrite.original,
                        suggested_text=bullet_rewrite.rewritten,
                        reason="; ".join(bullet_rewrite.changes_made),
                        prompt_question=bullet_rewrite.prompt_question,
                        section_name="work_experience",
                        confidence=bullet_rewrite.confidence,
                        status="pending",
                    )
                    all_suggestions.append(suggestion)
                    
                    if bullet_rewrite.prompt_question:
                        all_questions.append(bullet_rewrite.prompt_question)

        # Step 4: Rewrite project sections (same logic)
        for section in profile.projects:
            print(f"\n📝 Rewriting project: {section.title}")
            
            rewrite = self._rewrite_section(
                section,
                jd,
                injectable_skills,
            )
            section_rewrites.append(rewrite)
            
            for bullet_rewrite in rewrite.bullet_rewrites:
                if bullet_rewrite.original != bullet_rewrite.rewritten:
                    suggestion = Suggestion(
                        original_text=bullet_rewrite.original,
                        suggested_text=bullet_rewrite.rewritten,
                        reason="; ".join(bullet_rewrite.changes_made),
                        prompt_question=bullet_rewrite.prompt_question,
                        section_name="projects",
                        confidence=bullet_rewrite.confidence,
                        status="pending",
                    )
                    all_suggestions.append(suggestion)

        # Step 5: Build summary
        summary = self._build_summary(section_rewrites, skill_match)

        print(f"\n✅ Rewrite complete: {len(all_suggestions)} suggestions")

        return RewriteResult(
            reordered_skills=reordered_skills,
            section_rewrites=section_rewrites,
            suggestions=all_suggestions,
            summary=summary,
            verification_questions=all_questions,
        )

    # =========================================================================
    # SKILL REORDERING
    # =========================================================================

    def _reorder_skills(
        self,
        original_skills: list[str],
        skill_match: SkillMatchResult,
    ) -> list[str]:
        """
        Reorder skills to put matched ones first.
        
        Order:
        1. Matched required skills (most important)
        2. Matched preferred skills (nice to have)
        3. Other skills (still show them)
        
        Why this matters:
        - Recruiters scan quickly
        - First 5-6 skills get most attention
        - Matched skills should be visible immediately
        """
        # Normalize for comparison
        matched_req_lower = {s.lower() for s in skill_match.matched_required}
        matched_pref_lower = {s.lower() for s in skill_match.matched_preferred}

        required = []
        preferred = []
        other = []

        for skill in original_skills:
            skill_lower = skill.lower()
            if skill_lower in matched_req_lower:
                required.append(skill)
            elif skill_lower in matched_pref_lower:
                preferred.append(skill)
            else:
                other.append(skill)

        # Combine in priority order
        reordered = required + preferred + other

        # Log the reordering
        if required:
            print(f"   Top skills (required): {', '.join(required[:5])}")
        if preferred:
            print(f"   Secondary (preferred): {', '.join(preferred[:3])}")

        return reordered

    def _get_injectable_skills(
        self,
        profile: UserProfile,
        skill_match: SkillMatchResult,
    ) -> set[str]:
        """
        Get skills that can potentially be injected into bullet points.
        
        These are skills the user HAS that match the JD.
        We might make them more explicit in bullet points.
        """
        # Combine matched required and preferred
        injectable = set()
        
        for skill in skill_match.matched_required:
            injectable.add(skill.lower())
            
        for skill in skill_match.matched_preferred:
            injectable.add(skill.lower())

        return injectable

    # =========================================================================
    # SECTION REWRITING
    # =========================================================================

    def _rewrite_section(
        self,
        section: CVSection,
        jd: JobDescription,
        injectable_skills: set[str],
    ) -> SectionRewrite:
        """
        Rewrite a single CV section.
        
        Process each bullet point and apply conservative rewrites.
        """
        bullet_rewrites = []
        skills_added = []

        for bullet in section.description_points:
            rewrite = self._rewrite_bullet(
                bullet,
                injectable_skills,
                jd,
            )
            bullet_rewrites.append(rewrite)
            
            # Track which skills we added
            skills_added.extend(rewrite.changes_made)

        # Build changes summary
        num_changed = sum(
            1 for r in bullet_rewrites
            if r.original != r.rewritten
        )
        
        if num_changed == 0:
            changes_summary = "No changes needed - already well-written"
        else:
            changes_summary = f"{num_changed} bullet point(s) improved"

        return SectionRewrite(
            section_title=section.title,
            bullet_rewrites=bullet_rewrites,
            skills_added=list(set(skills_added)),
            changes_summary=changes_summary,
        )

    def _rewrite_bullet(
        self,
        bullet: str,
        injectable_skills: set[str],
        jd: JobDescription,
    ) -> BulletRewrite:
        """
        Rewrite a single bullet point.
        
        Applies multiple rewrite strategies in sequence:
        1. Weak verb strengthening
        2. Skill injection (if appropriate)
        3. Whitespace cleanup
        
        Each change is tracked and explained.
        """
        original = bullet.strip()
        rewritten = original
        changes_made = []
        prompt_question = None
        confidence = 1.0  # Start confident, reduce if we're unsure

        # Strategy 1: Upgrade weak verbs
        rewritten, verb_changes = self._upgrade_verbs(rewritten)
        changes_made.extend(verb_changes)

        # Strategy 2: Try to inject matched skills
        rewritten, skill_changes, question = self._inject_skills(
            rewritten,
            injectable_skills,
            jd,
        )
        changes_made.extend(skill_changes)
        
        if question:
            prompt_question = question
            confidence = 0.7  # Lower confidence when we're asking

        # Strategy 3: Clean up whitespace
        rewritten = self._clean_whitespace(rewritten)

        return BulletRewrite(
            original=original,
            rewritten=rewritten,
            changes_made=changes_made,
            confidence=confidence,
            prompt_question=prompt_question,
        )

    # =========================================================================
    # REWRITE STRATEGIES
    # =========================================================================

    def _upgrade_verbs(self, text: str) -> tuple[str, list[str]]:
        """
        Strategy 1: Replace weak verbs with stronger ones.
        
        Only applies safe substitutions that don't change meaning.
        
        Example:
            "Worked on API development" → "Contributed to API development"
        
        Returns:
            (rewritten_text, list_of_changes)
        """
        changes = []
        result = text

        for weak, strong in VERB_UPGRADES.items():
            # Case-insensitive search
            pattern = re.compile(re.escape(weak), re.IGNORECASE)
            
            if pattern.search(result):
                # Preserve original casing of first letter
                def replace_preserving_case(match):
                    original = match.group(0)
                    if original[0].isupper():
                        return strong.capitalize()
                    return strong
                
                result = pattern.sub(replace_preserving_case, result)
                changes.append(f"Strengthened verb: '{weak}' → '{strong}'")

        return result, changes

    def _inject_skills(
        self,
        text: str,
        injectable_skills: set[str],
        jd: JobDescription,
    ) -> tuple[str, list[str], Optional[str]]:
        """
        Strategy 2: Make implicit skills explicit.
        
        Only injects if:
        1. The skill is in the user's skill list
        2. The skill is required by the JD
        3. The context suggests the skill was used
        
        Example:
            "Built web applications" + user knows React + JD wants React
            → "Built React web applications"
            
        Returns:
            (rewritten_text, list_of_changes, optional_question)
        """
        changes = []
        result = text
        question = None
        text_lower = text.lower()

        # Look for generic terms that could be made specific
        injection_patterns = [
            # (generic_term, skill_category, injection_template)
            ("web application", ["react", "vue", "angular", "next.js"], "web application"),
            ("frontend", ["react", "vue", "angular"], "frontend"),
            ("backend", ["node", "python", "java", "go"], "backend"),
            ("api", ["rest", "graphql"], "API"),
            ("database", ["postgresql", "mysql", "mongodb", "redis"], "database"),
            ("cloud", ["aws", "gcp", "azure"], "cloud"),
            ("mobile app", ["react native", "flutter", "swift", "kotlin"], "mobile app"),
            ("machine learning", ["tensorflow", "pytorch", "sklearn"], "machine learning"),
        ]

        for generic_term, skill_options, template in injection_patterns:
            if generic_term in text_lower:
                # Check if user has any of these skills AND they're in JD
                for skill in skill_options:
                    if skill in injectable_skills:
                        # Check if skill is already mentioned
                        if skill not in text_lower:
                            # Inject the skill
                            # Find the generic term and add skill before it
                            pattern = re.compile(
                                re.escape(generic_term),
                                re.IGNORECASE
                            )
                            
                            def inject_skill(match):
                                original = match.group(0)
                                return f"{skill.title()} {original}"
                            
                            result = pattern.sub(inject_skill, result, count=1)
                            changes.append(f"Added '{skill}' to make skill explicit")
                            
                            # Add verification question
                            question = f"Did this work involve {skill.title()}?"
                            
                            # Only inject one skill per bullet
                            break
                            
                # Only try one pattern per bullet
                if changes:
                    break

        return result, changes, question

    def _clean_whitespace(self, text: str) -> str:
        """
        Clean up whitespace issues.
        
        - Remove double spaces
        - Trim leading/trailing whitespace
        - Ensure proper punctuation spacing
        """
        # Remove double spaces
        result = re.sub(r"\s+", " ", text)
        
        # Trim
        result = result.strip()
        
        # Ensure no space before punctuation
        result = re.sub(r"\s+([.,;:!?])", r"\1", result)
        
        return result

    # =========================================================================
    # SUMMARY BUILDING
    # =========================================================================

    def _build_summary(
        self,
        section_rewrites: list[SectionRewrite],
        skill_match: SkillMatchResult,
    ) -> str:
        """
        Build a human-readable summary of changes.
        """
        total_changes = sum(
            len([r for r in s.bullet_rewrites if r.original != r.rewritten])
            for s in section_rewrites
        )

        if total_changes == 0:
            return (
                "Your CV is already well-written for this role. "
                "Skills have been reordered to highlight the most relevant ones."
            )

        parts = [f"Made {total_changes} improvement(s):"]
        
        # Add skill match context
        if skill_match.matched_required:
            parts.append(
                f"Emphasized: {', '.join(skill_match.matched_required[:3])}"
            )
        
        if skill_match.missing_required:
            parts.append(
                f"Note: Consider addressing gaps in {', '.join(skill_match.missing_required[:2])}"
            )

        return " ".join(parts)

    # =========================================================================
    # FULL TAILORED RESULT BUILDER
    # =========================================================================

    def build_tailored_result(
        self,
        original_profile: UserProfile,
        jd: JobDescription,
        skill_match: SkillMatchResult,
        rewrite_result: RewriteResult,
    ) -> TailoredCVResult:
        """
        Build the complete TailoredCVResult from rewrite results.
        
        This combines all the pieces into the final output structure.
        """
        # Build explanations
        section_explanations = []
        
        for section_rewrite in rewrite_result.section_rewrites:
            if section_rewrite.bullet_rewrites:
                num_changed = sum(
                    1 for r in section_rewrite.bullet_rewrites
                    if r.original != r.rewritten
                )
                
                if num_changed > 0:
                    section_explanations.append(
                        SectionExplanation(
                            section_name=section_rewrite.section_title,
                            changes_made=section_rewrite.changes_summary,
                            reasoning="Made skills more explicit for recruiter scanning",
                        )
                    )

        # Build global strategy explanation
        match_percent = skill_match.match_score * 100
        if match_percent >= 70:
            strategy = (
                f"Strong match ({match_percent:.0f}%). "
                f"Focused on highlighting: {', '.join(skill_match.matched_required[:3])}."
            )
        elif match_percent >= 40:
            strategy = (
                f"Moderate match ({match_percent:.0f}%). "
                f"Emphasized existing strengths while noting gaps."
            )
        else:
            strategy = (
                f"Partial match ({match_percent:.0f}%). "
                f"Consider if this role aligns with your experience."
            )

        explanations = Explanations(
            global_strategy=strategy,
            section_explanations=section_explanations,
        )

        # Build tailored experience (with rewrites applied)
        tailored_experience = self._apply_rewrites_to_sections(
            original_profile.work_experience,
            rewrite_result.section_rewrites,
        )

        return TailoredCVResult(
            original_profile=original_profile,
            job_description=jd,
            suggestions=rewrite_result.suggestions,
            tailored_skills=rewrite_result.reordered_skills,
            tailored_summary=original_profile.summary,  # Unchanged for MVP
            tailored_experience=tailored_experience,
            explanations=explanations,
        )

    def _apply_rewrites_to_sections(
        self,
        original_sections: list[CVSection],
        section_rewrites: list[SectionRewrite],
    ) -> list[CVSection]:
        """
        Apply rewrites to create new section list.
        
        Returns deep copies with rewritten bullet points.
        """
        # Create lookup by title
        rewrite_lookup = {
            sr.section_title: sr
            for sr in section_rewrites
        }

        result = []
        for section in original_sections:
            # Deep copy
            new_section = deepcopy(section)
            
            # Find corresponding rewrite
            if section.title in rewrite_lookup:
                rewrite = rewrite_lookup[section.title]
                
                # Apply rewritten bullets
                new_bullets = [
                    br.rewritten
                    for br in rewrite.bullet_rewrites
                ]
                new_section.description_points = new_bullets

            result.append(new_section)

        return result

