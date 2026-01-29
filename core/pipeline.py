"""
CV Tailoring Pipeline

This module defines the step-by-step flow from raw inputs to tailored CV.
Think of it as an assembly line: each station does one thing, passes to the next.

=============================================================================
PIPELINE OVERVIEW (MVP)
=============================================================================

    ┌─────────────┐     ┌─────────────┐
    │  Raw CV     │     │  Raw JD     │
    │  (text)     │     │  (text)     │
    └──────┬──────┘     └──────┬──────┘
           │                   │
           ▼                   ▼
    ┌─────────────┐     ┌─────────────┐
    │  STEP 1     │     │  STEP 2     │
    │  Parse CV   │     │  Parse JD   │
    │  (rule)     │     │  (rule)     │
    └──────┬──────┘     └──────┬──────┘
           │                   │
           │   UserProfile     │ JobDescription
           │                   │
           └────────┬──────────┘
                    │
                    ▼
             ┌─────────────┐
             │  STEP 3     │
             │  Match      │
             │  Skills     │
             │  (rule)     │
             └──────┬──────┘
                    │
                    │  Annotated Profile + SkillMatchResult
                    │
                    ▼
             ┌─────────────┐
             │  STEP 4     │
             │  Rewrite    │
             │  (rule)     │
             └──────┬──────┘
                    │
                    │  RewriteResult + Suggestions
                    │
                    ▼
             ┌─────────────┐
             │  STEP 5     │
             │  Explain    │
             │  (rule)     │
             └──────┬──────┘
                    │
                    ▼
             ┌─────────────┐
             │  Tailored   │
             │  CVResult   │
             └─────────────┘

=============================================================================
MVP SCOPE
=============================================================================

All steps now implemented with rule-based services:
- Step 1: CVParser (rule-based)
- Step 2: JDAnalyzer (rule-based)
- Step 3: SkillMatcher (rule-based)
- Step 4: CVRewriter (rule-based, conservative)
- Step 5: ExplanationEngine (template-based)

No AI/LLM in this version. All logic is deterministic and debuggable.

=============================================================================
DESIGN PRINCIPLES
=============================================================================

1. EACH STEP IS INDEPENDENT
   - Can be tested in isolation
   - Can be run manually for debugging
   - Failures don't cascade silently

2. STATE IS EXPLICIT
   - PipelineState holds everything
   - No hidden globals or side effects
   - Easy to inspect at any point

3. PRINT STATEMENTS FOR DEBUGGING
   - Every step prints what it's doing
   - Easy to follow execution flow
   - Remove in production

4. GRACEFUL FAILURE
   - Each step catches exceptions
   - Errors are recorded in state
   - Partial results still available

"""

from dataclasses import dataclass, field
from typing import Optional
import logging

from core.models import (
    UserProfile,
    JobDescription,
    TailoredCVResult,
    CVSection,
    Suggestion,
    Explanations,
    SectionExplanation,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PIPELINE STATE
# =============================================================================


@dataclass
class PipelineState:
    """
    Holds all data as it flows through the pipeline.
    
    Think of this as a "work in progress" container.
    At the start, most fields are None.
    After each step, more fields get populated.
    At the end, we have everything we need.
    """

    # === INPUTS (set before pipeline runs) ===
    raw_cv_text: str = ""
    raw_jd_text: str = ""

    # === STEP 1 OUTPUT ===
    user_profile: Optional[UserProfile] = None

    # === STEP 2 OUTPUT ===
    job_description: Optional[JobDescription] = None

    # === STEP 3 OUTPUT ===
    # Same as user_profile, but with analysis fields populated
    annotated_profile: Optional[UserProfile] = None
    # Separate skill match result for easy access
    skill_match_result: Optional[object] = None  # SkillMatchResult

    # === STEP 4 OUTPUT ===
    rewrite_result: Optional[object] = None  # RewriteResult from CVRewriter

    # === STEP 5 OUTPUT ===
    full_explanation: Optional[object] = None  # FullExplanation from ExplanationEngine

    # === FINAL OUTPUT ===
    tailored_result: Optional[TailoredCVResult] = None

    # === METADATA ===
    current_step: str = "not_started"
    errors: list[str] = field(default_factory=list)


# =============================================================================
# PIPELINE CLASS
# =============================================================================


class TailoringPipeline:
    """
    Orchestrates the CV tailoring process.
    
    Usage:
        pipeline = TailoringPipeline()
        
        # Option 1: Run everything at once
        result = pipeline.run(raw_cv, raw_jd)
        
        # Option 2: Run step by step (for debugging)
        pipeline.step_1_parse_cv(raw_cv)
        pipeline.step_2_parse_jd(raw_jd)
        pipeline.step_3_match_skills()
        pipeline.step_4_rewrite_cv()
        pipeline.step_5_generate_explanations()
        result = pipeline.get_result()
    """

    def __init__(self):
        """Initialize pipeline with empty state."""
        self.state = PipelineState()

        # Services loaded lazily to avoid circular imports
        self._cv_parser = None
        self._jd_analyzer = None
        self._skill_matcher = None
        self._cv_rewriter = None
        self._explanation_engine = None

    # =========================================================================
    # STEP 1: PARSE CV
    # =========================================================================

    def step_1_parse_cv(self, raw_cv_text: str) -> UserProfile:
        """
        STEP 1: Parse raw CV text into structured UserProfile.
        
        Input:  raw_cv_text (string from PDF/DOCX/pasted)
        Output: UserProfile with name, contact, sections, skills
        
        Uses: Rule-based CVParser (no LLM)
        """
        print("\n" + "=" * 60)
        print("STEP 1: PARSING CV")
        print("=" * 60)

        # Update state
        self.state.current_step = "parsing_cv"
        self.state.raw_cv_text = raw_cv_text

        # Validate input
        if not raw_cv_text or not raw_cv_text.strip():
            error_msg = "CV text is empty. Cannot parse."
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            raise ValueError(error_msg)

        print(f"📄 Input: {len(raw_cv_text)} characters")
        print(f"📄 Preview: {raw_cv_text[:100]}...")

        # Load parser service (lazy)
        self._ensure_cv_parser()

        # Parse the CV
        print("🔄 Parsing CV text...")
        try:
            profile = self._cv_parser.parse(raw_cv_text)
        except Exception as e:
            error_msg = f"CV parsing failed: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            raise

        # Store in state
        self.state.user_profile = profile

        # Print summary for debugging
        print("\n✅ CV Parsed Successfully!")
        print(f"   Name: {profile.full_name}")
        print(f"   Email: {profile.contact_info.email if profile.contact_info else 'N/A'}")
        print(f"   Work Experience: {len(profile.work_experience)} entries")
        print(f"   Education: {len(profile.education)} entries")
        print(f"   Projects: {len(profile.projects)} entries")
        print(f"   Skills: {len(profile.skills)} skills")
        
        if profile.skills:
            print(f"   Skills preview: {', '.join(profile.skills[:5])}...")

        return profile

    # =========================================================================
    # STEP 2: ANALYZE JOB DESCRIPTION
    # =========================================================================

    def step_2_parse_jd(self, raw_jd_text: str) -> JobDescription:
        """
        STEP 2: Parse raw job description into structured JobDescription.
        
        Input:  raw_jd_text (pasted from job posting)
        Output: JobDescription with title, company, required/preferred skills
        
        Uses: Rule-based JDAnalyzer (no LLM)
        """
        print("\n" + "=" * 60)
        print("STEP 2: PARSING JOB DESCRIPTION")
        print("=" * 60)

        # Update state
        self.state.current_step = "parsing_jd"
        self.state.raw_jd_text = raw_jd_text

        # Validate input
        if not raw_jd_text or not raw_jd_text.strip():
            error_msg = "Job description text is empty. Cannot parse."
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            raise ValueError(error_msg)

        print(f"📄 Input: {len(raw_jd_text)} characters")
        print(f"📄 Preview: {raw_jd_text[:100]}...")

        # Load analyzer service (lazy)
        self._ensure_jd_analyzer()

        # Analyze the JD
        print("🔄 Analyzing job description...")
        try:
            jd = self._jd_analyzer.analyze(raw_jd_text)
        except Exception as e:
            error_msg = f"JD analysis failed: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            raise

        # Store in state
        self.state.job_description = jd

        # Print summary for debugging
        print("\n✅ Job Description Analyzed!")
        print(f"   Title: {jd.title}")
        print(f"   Company: {jd.company}")
        print(f"   Required Skills: {len(jd.required_skills)}")
        print(f"   Preferred Skills: {len(jd.preferred_skills)}")
        print(f"   Responsibilities: {len(jd.responsibilities)}")
        
        if jd.required_skills:
            print(f"   Required preview: {', '.join(jd.required_skills[:5])}...")
        if jd.preferred_skills:
            print(f"   Preferred preview: {', '.join(jd.preferred_skills[:5])}...")

        return jd

    # =========================================================================
    # STEP 3: MATCH SKILLS
    # =========================================================================

    def step_3_match_skills(self) -> UserProfile:
        """
        STEP 3: Compare CV skills against JD requirements.
        
        Input:  state.user_profile + state.job_description
        Output: Annotated UserProfile with matched/missing skills per section
        
        Uses: Rule-based SkillMatcher (no LLM)
        
        PRECONDITION: Steps 1 and 2 must be complete.
        """
        print("\n" + "=" * 60)
        print("STEP 3: MATCHING SKILLS")
        print("=" * 60)

        # Update state
        self.state.current_step = "matching"

        # Validate preconditions
        if not self.state.user_profile:
            error_msg = "Step 1 (parse CV) must complete before Step 3"
            print(f"❌ ERROR: {error_msg}")
            raise ValueError(error_msg)
        
        if not self.state.job_description:
            error_msg = "Step 2 (parse JD) must complete before Step 3"
            print(f"❌ ERROR: {error_msg}")
            raise ValueError(error_msg)

        profile = self.state.user_profile
        jd = self.state.job_description

        print(f"🔄 Matching {len(profile.skills)} CV skills against JD...")
        print(f"   JD requires: {len(jd.required_skills)} skills")
        print(f"   JD prefers: {len(jd.preferred_skills)} skills")

        # Load matcher service (lazy)
        self._ensure_skill_matcher()

        # Perform matching
        try:
            # This returns annotated profile with analysis on each section
            annotated_profile = self._skill_matcher.match(profile, jd)
            
            # Also get the raw skill match result for easy access
            skill_result = self._skill_matcher.match_skills(profile.skills, jd)
        except Exception as e:
            error_msg = f"Skill matching failed: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            raise

        # Store in state
        self.state.annotated_profile = annotated_profile
        self.state.skill_match_result = skill_result

        # Print summary for debugging
        print("\n✅ Skills Matched!")
        print(f"   Match Score: {skill_result.match_score:.1%}")
        print(f"   ✓ Matched (required): {len(skill_result.matched_required)}")
        print(f"   ✓ Matched (preferred): {len(skill_result.matched_preferred)}")
        print(f"   ✗ Missing (required): {len(skill_result.missing_required)}")
        print(f"   ✗ Missing (preferred): {len(skill_result.missing_preferred)}")
        print(f"   ○ Extra skills: {len(skill_result.extra_skills)}")

        if skill_result.matched_required:
            print(f"\n   Matched required: {', '.join(skill_result.matched_required[:5])}")
        if skill_result.missing_required:
            print(f"   Missing required: {', '.join(skill_result.missing_required[:5])}")

        # Print section relevance scores
        print("\n   Section Relevance:")
        for i, section in enumerate(annotated_profile.work_experience):
            if section.analysis:
                score = section.analysis.relevance_score
                print(f"     Work[{i}] {section.title}: {score:.1%}")

        return annotated_profile

    # =========================================================================
    # STEP 4: REWRITE CV
    # =========================================================================

    def step_4_rewrite_cv(self) -> object:
        """
        STEP 4: Apply rule-based rewrites to CV sections.
        
        Input:  state.annotated_profile + state.job_description + state.skill_match_result
        Output: RewriteResult with suggestions and rewritten content
        
        Uses: Rule-based CVRewriter (no LLM)
        
        PRECONDITION: Step 3 must be complete.
        """
        print("\n" + "=" * 60)
        print("STEP 4: REWRITING CV")
        print("=" * 60)

        # Update state
        self.state.current_step = "rewriting"

        # Validate preconditions
        if not self.state.annotated_profile:
            error_msg = "Step 3 (match skills) must complete before Step 4"
            print(f"❌ ERROR: {error_msg}")
            raise ValueError(error_msg)

        if not self.state.skill_match_result:
            error_msg = "Step 3 did not produce skill_match_result"
            print(f"❌ ERROR: {error_msg}")
            raise ValueError(error_msg)

        profile = self.state.annotated_profile
        jd = self.state.job_description
        skill_result = self.state.skill_match_result

        print(f"🔄 Applying rule-based rewrites...")
        print(f"   Profile: {profile.full_name}")
        print(f"   Work sections: {len(profile.work_experience)}")
        print(f"   Project sections: {len(profile.projects)}")

        # Load rewriter service (lazy)
        self._ensure_cv_rewriter()

        # Perform rewriting
        try:
            rewrite_result = self._cv_rewriter.rewrite(
                profile=profile,
                jd=jd,
                skill_match=skill_result,
            )
        except Exception as e:
            error_msg = f"CV rewriting failed: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            # Graceful degradation: continue with empty rewrite result
            print("⚠️  Continuing with fallback (no rewrites)")
            rewrite_result = self._build_fallback_rewrite_result(profile, skill_result)

        # Store in state
        self.state.rewrite_result = rewrite_result

        # Print summary for debugging
        print("\n✅ CV Rewritten!")
        print(f"   Skills reordered: {len(rewrite_result.reordered_skills)}")
        print(f"   Suggestions generated: {len(rewrite_result.suggestions)}")
        print(f"   Sections processed: {len(rewrite_result.section_rewrites)}")

        if rewrite_result.suggestions:
            print(f"\n   Sample suggestions:")
            for i, suggestion in enumerate(rewrite_result.suggestions[:3]):
                print(f"     [{i+1}] {suggestion.reason[:50]}...")

        return rewrite_result

    # =========================================================================
    # STEP 5: GENERATE EXPLANATIONS
    # =========================================================================

    def step_5_generate_explanations(self) -> TailoredCVResult:
        """
        STEP 5: Generate human-readable explanations for all changes.
        
        Input:  state.user_profile + state.rewrite_result + state.skill_match_result
        Output: TailoredCVResult with complete explanations
        
        Uses: Template-based ExplanationEngine (no LLM)
        
        PRECONDITION: Step 4 must be complete.
        """
        print("\n" + "=" * 60)
        print("STEP 5: GENERATING EXPLANATIONS")
        print("=" * 60)

        # Update state
        self.state.current_step = "explaining"

        # Validate preconditions
        if not self.state.rewrite_result:
            error_msg = "Step 4 (rewrite CV) must complete before Step 5"
            print(f"❌ ERROR: {error_msg}")
            raise ValueError(error_msg)

        profile = self.state.user_profile
        jd = self.state.job_description
        skill_result = self.state.skill_match_result
        rewrite_result = self.state.rewrite_result

        print(f"🔄 Generating explanations...")

        # Load explanation engine (lazy)
        self._ensure_explanation_engine()

        # Generate explanations
        try:
            full_explanation = self._explanation_engine.explain(
                original_profile=profile,
                skill_match=skill_result,
                jd=jd,
                suggestions=rewrite_result.suggestions,
            )
        except Exception as e:
            error_msg = f"Explanation generation failed: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            # Graceful degradation: continue with fallback explanations
            print("⚠️  Continuing with fallback explanations")
            full_explanation = None

        # Store in state
        self.state.full_explanation = full_explanation

        # Build the final TailoredCVResult
        print("🔄 Building final result...")

        try:
            if full_explanation:
                # Use explanation engine to build the Explanations model
                explanations = self._explanation_engine.build_explanations_model(
                    full_explanation
                )
            else:
                # Fallback explanations
                explanations = self._build_fallback_explanations(skill_result)

            # Build tailored experience with rewrites applied
            tailored_experience = self._apply_rewrites(
                self.state.annotated_profile.work_experience,
                rewrite_result.section_rewrites,
            )

            # Construct final result
            result = TailoredCVResult(
                original_profile=profile,
                job_description=jd,
                suggestions=rewrite_result.suggestions,
                tailored_skills=rewrite_result.reordered_skills,
                tailored_summary=profile.summary,  # Summary unchanged in MVP
                tailored_experience=tailored_experience,
                explanations=explanations,
            )

        except Exception as e:
            error_msg = f"Result building failed: {str(e)}"
            print(f"❌ ERROR: {error_msg}")
            self.state.errors.append(error_msg)
            # Last resort fallback
            result = self._build_fallback_result()

        # Store final result
        self.state.tailored_result = result

        # Print summary
        print("\n✅ Explanations Generated!")
        if full_explanation:
            print(f"   Match score: {full_explanation.match_score_percent}%")
            print(f"   Key points: {len(full_explanation.key_points)}")
            print(f"   Skill explanations: {len(full_explanation.skill_explanations)}")
            print(f"   Gap explanations: {len(full_explanation.gap_explanations)}")
        else:
            print("   (Using fallback explanations)")

        return result

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    def run(self, raw_cv_text: str, raw_jd_text: str) -> TailoredCVResult:
        """
        Run the complete pipeline from start to finish.
        
        This is the simple API for when you don't need step-by-step control.
        
        Args:
            raw_cv_text: The raw resume text
            raw_jd_text: The raw job description text
            
        Returns:
            TailoredCVResult with suggestions and explanations
        """
        print("\n" + "#" * 60)
        print("# CV TAILORING PIPELINE - STARTING")
        print("#" * 60)

        try:
            # Step 1: Parse CV
            self.step_1_parse_cv(raw_cv_text)
            
            # Step 2: Parse JD
            self.step_2_parse_jd(raw_jd_text)
            
            # Step 3: Match skills
            self.step_3_match_skills()
            
            # Step 4: Rewrite CV
            self.step_4_rewrite_cv()
            
            # Step 5: Generate explanations and build result
            self.step_5_generate_explanations()

            self.state.current_step = "complete"

            print("\n" + "#" * 60)
            print("# PIPELINE COMPLETE")
            print("#" * 60)

            # Print final summary
            result = self.state.tailored_result
            print(f"\n📊 FINAL SUMMARY:")
            print(f"   Suggestions: {len(result.suggestions)}")
            print(f"   Skills (reordered): {len(result.tailored_skills)}")
            print(f"   Errors encountered: {len(self.state.errors)}")

            if self.state.errors:
                print(f"\n⚠️  Warnings/Errors:")
                for error in self.state.errors:
                    print(f"   - {error}")

            return result

        except Exception as e:
            self.state.current_step = "failed"
            print(f"\n❌ PIPELINE FAILED: {str(e)}")
            raise

    def get_state(self) -> PipelineState:
        """Get current pipeline state for inspection."""
        return self.state

    def get_result(self) -> Optional[TailoredCVResult]:
        """Get the final result, or None if pipeline isn't complete."""
        return self.state.tailored_result

    def reset(self):
        """Reset pipeline to initial state."""
        print("🔄 Resetting pipeline state...")
        self.state = PipelineState()
        self._cv_parser = None
        self._jd_analyzer = None
        self._skill_matcher = None
        self._cv_rewriter = None
        self._explanation_engine = None
        print("✅ Pipeline reset")

    # =========================================================================
    # SERVICE LOADING (LAZY)
    # =========================================================================

    def _ensure_cv_parser(self):
        """Load CV parser if not already loaded."""
        if self._cv_parser is None:
            print("   Loading CVParser service...")
            from services.cv_parser import CVParser
            self._cv_parser = CVParser()

    def _ensure_jd_analyzer(self):
        """Load JD analyzer if not already loaded."""
        if self._jd_analyzer is None:
            print("   Loading JDAnalyzer service...")
            from services.jd_analyzer import JDAnalyzer
            self._jd_analyzer = JDAnalyzer()

    def _ensure_skill_matcher(self):
        """Load skill matcher if not already loaded."""
        if self._skill_matcher is None:
            print("   Loading SkillMatcher service...")
            from services.skill_matcher import SkillMatcher
            self._skill_matcher = SkillMatcher()

    def _ensure_cv_rewriter(self):
        """Load CV rewriter if not already loaded."""
        if self._cv_rewriter is None:
            print("   Loading CVRewriter service...")
            from services.cv_rewriter import CVRewriter
            self._cv_rewriter = CVRewriter()

    def _ensure_explanation_engine(self):
        """Load explanation engine if not already loaded."""
        if self._explanation_engine is None:
            print("   Loading ExplanationEngine service...")
            from services.explanation_engine import ExplanationEngine
            self._explanation_engine = ExplanationEngine()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _apply_rewrites(
        self,
        original_sections: list[CVSection],
        section_rewrites: list,
    ) -> list[CVSection]:
        """
        Apply rewrites to create new section list.
        
        Returns copies with rewritten bullet points.
        """
        from copy import deepcopy

        # Create lookup by title
        rewrite_lookup = {
            sr.section_title: sr
            for sr in section_rewrites
        }

        result = []
        for section in original_sections:
            # Deep copy to avoid mutating original
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

    def _build_fallback_rewrite_result(self, profile: UserProfile, skill_result):
        """
        Build a minimal rewrite result when rewriter fails.
        
        Just reorders skills, doesn't change any content.
        """
        from services.cv_rewriter import RewriteResult

        # Reorder skills based on match
        reordered_skills = self._reorder_skills(profile.skills, skill_result)

        return RewriteResult(
            reordered_skills=reordered_skills,
            section_rewrites=[],
            suggestions=[],
            summary="Rewriting skipped due to error. Skills reordered only.",
            verification_questions=[],
        )

    def _reorder_skills(
        self,
        original_skills: list[str],
        skill_result,
    ) -> list[str]:
        """
        Reorder skills to put matched ones first.
        """
        matched_req_set = set(s.lower() for s in skill_result.matched_required)
        matched_pref_set = set(s.lower() for s in skill_result.matched_preferred)

        matched_required = []
        matched_preferred = []
        other = []

        for skill in original_skills:
            skill_lower = skill.lower()
            if skill_lower in matched_req_set:
                matched_required.append(skill)
            elif skill_lower in matched_pref_set:
                matched_preferred.append(skill)
            else:
                other.append(skill)

        return matched_required + matched_preferred + other

    def _build_fallback_explanations(self, skill_result) -> Explanations:
        """
        Build fallback explanations when explanation engine fails.
        """
        if skill_result.matched_required or skill_result.missing_required:
            total = len(skill_result.matched_required) + len(skill_result.missing_required)
            coverage = len(skill_result.matched_required) / total
        else:
            coverage = 1.0

        strategy = (
            f"Your CV matches {coverage:.0%} of required skills. "
            f"Skills have been reordered to highlight the most relevant ones."
        )

        return Explanations(
            global_strategy=strategy,
            section_explanations=[
                SectionExplanation(
                    section_name="skills",
                    changes_made="Skills reordered by relevance.",
                    reasoning="Matched skills appear first for recruiter visibility.",
                ),
            ],
        )

    def _build_fallback_result(self) -> TailoredCVResult:
        """
        Build a minimal result when everything fails.
        
        Returns original profile with no changes.
        """
        return TailoredCVResult(
            original_profile=self.state.user_profile,
            job_description=self.state.job_description,
            suggestions=[],
            tailored_skills=self.state.user_profile.skills if self.state.user_profile else [],
            tailored_summary=self.state.user_profile.summary if self.state.user_profile else "",
            tailored_experience=self.state.user_profile.work_experience if self.state.user_profile else [],
            explanations=Explanations(
                global_strategy="An error occurred. Showing original CV without changes.",
                section_explanations=[],
            ),


