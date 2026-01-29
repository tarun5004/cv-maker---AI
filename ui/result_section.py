"""
Result Section UI

This module handles the final step: displaying the tailored CV and explanations.

Design principles:
- Clear section-by-section display
- Show before/after where changes were made
- Explanations in a separate panel
- Easy to copy/export
"""

import streamlit as st


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render_result_section():
    """
    Render the final result section.
    
    Shows:
    - Tailored CV (section by section)
    - Explanations panel
    - Copy/export options
    """
    result = st.session_state.pipeline_result
    state = st.session_state.pipeline_state

    if not result:
        st.error("No results to display. Please go back and process your CV.")
        if st.button("← Start Over"):
            st.session_state.current_step = "upload"
            st.rerun()
        return

    # Header
    st.header("🎉 Your Tailored Resume")
    st.markdown(
        "Here's your resume, optimized for this job. "
        "Review the changes and copy what you need."
    )

    # Two-column layout: CV on left, explanations on right
    col_cv, col_explain = st.columns([2, 1])

    # === LEFT COLUMN: TAILORED CV ===
    with col_cv:
        render_tailored_cv(result, state)

    # === RIGHT COLUMN: EXPLANATIONS ===
    with col_explain:
        render_explanations(result)

    # Navigation
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("← Back to Review", use_container_width=True):
            st.session_state.current_step = "review"
            st.rerun()

    with col3:
        if st.button("🔄 Start New", use_container_width=True):
            # Reset everything
            st.session_state.current_step = "upload"
            st.session_state.raw_cv_text = ""
            st.session_state.raw_jd_text = ""
            st.session_state.pipeline_result = None
            st.session_state.pipeline_state = None
            st.session_state.processing_complete = False
            st.rerun()


# =============================================================================
# TAILORED CV DISPLAY
# =============================================================================

def render_tailored_cv(result, state):
    """
    Display the tailored CV section by section.
    """
    st.subheader("📄 Tailored Resume")

    profile = result.original_profile

    # === HEADER (Name & Contact) ===
    st.markdown("---")
    st.markdown(f"### {profile.full_name}")
    
    if profile.contact_info:
        contact = profile.contact_info
        contact_parts = []
        if contact.email:
            contact_parts.append(contact.email)
        if contact.phone:
            contact_parts.append(contact.phone)
        if contact.linkedin_url:
            contact_parts.append(contact.linkedin_url)
        if contact.github_url:
            contact_parts.append(contact.github_url)
        if contact.location:
            contact_parts.append(contact.location)
        
        if contact_parts:
            st.markdown(" | ".join(contact_parts))

    # === SUMMARY ===
    if result.tailored_summary:
        st.markdown("---")
        st.markdown("#### Summary")
        st.markdown(result.tailored_summary)

    # === SKILLS (Reordered) ===
    st.markdown("---")
    st.markdown("#### Skills")
    
    if result.tailored_skills:
        # Show skills with matched ones highlighted
        if state and state.skill_match_result:
            matched_set = set(
                s.lower() for s in state.skill_match_result.matched_required
            )
            matched_pref_set = set(
                s.lower() for s in state.skill_match_result.matched_preferred
            )
            
            skill_display = []
            for skill in result.tailored_skills:
                if skill.lower() in matched_set:
                    skill_display.append(f"**{skill}** ✓")
                elif skill.lower() in matched_pref_set:
                    skill_display.append(f"**{skill}**")
                else:
                    skill_display.append(skill)
            
            st.markdown(", ".join(skill_display))
            st.caption("✓ = Required by job | **Bold** = Relevant to job")
        else:
            st.markdown(", ".join(result.tailored_skills))

    # === WORK EXPERIENCE ===
    st.markdown("---")
    st.markdown("#### Work Experience")
    
    for section in result.tailored_experience:
        render_experience_section(section)

    # === EDUCATION ===
    if profile.education:
        st.markdown("---")
        st.markdown("#### Education")
        
        for section in profile.education:
            render_experience_section(section)

    # === PROJECTS ===
    if profile.projects:
        st.markdown("---")
        st.markdown("#### Projects")
        
        for section in profile.projects:
            render_experience_section(section)

    # === COPY BUTTON ===
    st.markdown("---")
    
    # Generate copyable text
    cv_text = generate_copyable_cv(result, profile)
    
    st.download_button(
        label="📋 Download as Text",
        data=cv_text,
        file_name="tailored_resume.txt",
        mime="text/plain",
        use_container_width=True,
    )


def render_experience_section(section):
    """
    Render a single experience/education/project section.
    """
    # Title line
    title_line = f"**{section.title}**"
    if section.organization:
        title_line += f" | {section.organization}"
    if section.date_range:
        title_line += f" | {section.date_range}"
    
    st.markdown(title_line)

    # Bullet points
    for point in section.description_points:
        st.markdown(f"• {point}")

    st.markdown("")  # Spacing


# =============================================================================
# EXPLANATIONS PANEL
# =============================================================================

def render_explanations(result):
    """
    Display explanations for all changes made.
    """
    st.subheader("💡 What We Changed")

    explanations = result.explanations

    # Global strategy
    st.markdown("#### Overall Approach")
    st.info(explanations.global_strategy)

    # Section-by-section explanations
    if explanations.section_explanations:
        st.markdown("#### Changes by Section")
        
        for section_exp in explanations.section_explanations:
            with st.expander(f"📝 {section_exp.section_name}", expanded=False):
                st.markdown(f"**What changed:** {section_exp.changes_made}")
                if section_exp.reasoning:
                    st.markdown(f"**Why:** {section_exp.reasoning}")

    # Show skill reordering explanation
    st.markdown("#### Skills Reordering")
    st.markdown(
        "We moved your most relevant skills to the top of the list. "
        "Recruiters often scan the first few skills quickly, so this helps "
        "your strongest matches stand out."
    )

    # Accepted suggestions summary
    accepted_count = sum(
        1 for s in result.suggestions
        if getattr(s, 'status', 'pending') == 'accepted'
    )
    
    if accepted_count > 0:
        st.markdown("#### Accepted Suggestions")
        st.success(f"You accepted {accepted_count} suggestion(s)")

    # Gaps reminder
    state = st.session_state.pipeline_state
    if state and state.skill_match_result:
        missing = state.skill_match_result.missing_required
        if missing:
            st.markdown("#### Skills to Consider")
            st.warning(
                f"The job requires these skills you haven't mentioned: "
                f"**{', '.join(missing[:5])}**. "
                f"If you have experience with any of these, consider adding them."
            )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_copyable_cv(result, profile) -> str:
    """
    Generate a plain text version of the tailored CV.
    """
    lines = []

    # Header
    lines.append(profile.full_name.upper())
    
    if profile.contact_info:
        contact = profile.contact_info
        contact_parts = []
        if contact.email:
            contact_parts.append(contact.email)
        if contact.phone:
            contact_parts.append(contact.phone)
        if contact.linkedin_url:
            contact_parts.append(contact.linkedin_url)
        if contact.location:
            contact_parts.append(contact.location)
        lines.append(" | ".join(contact_parts))

    lines.append("")

    # Summary
    if result.tailored_summary:
        lines.append("SUMMARY")
        lines.append(result.tailored_summary)
        lines.append("")

    # Skills
    lines.append("SKILLS")
    lines.append(", ".join(result.tailored_skills))
    lines.append("")

    # Work Experience
    lines.append("WORK EXPERIENCE")
    lines.append("")
    for section in result.tailored_experience:
        title_line = section.title
        if section.organization:
            title_line += f" | {section.organization}"
        if section.date_range:
            title_line += f" | {section.date_range}"
        lines.append(title_line)
        
        for point in section.description_points:
            lines.append(f"• {point}")
        lines.append("")

    # Education
    if profile.education:
        lines.append("EDUCATION")
        lines.append("")
        for section in profile.education:
            title_line = section.title
            if section.organization:
                title_line += f" | {section.organization}"
            if section.date_range:
                title_line += f" | {section.date_range}"
            lines.append(title_line)
            
            for point in section.description_points:
                lines.append(f"• {point}")
            lines.append("")

    # Projects
    if profile.projects:
        lines.append("PROJECTS")
        lines.append("")
        for section in profile.projects:
            title_line = section.title
            if section.date_range:
                title_line += f" | {section.date_range}"
            lines.append(title_line)
            
            for point in section.description_points:
                lines.append(f"• {point}")
            lines.append("")

    return "\n".join(lines)

