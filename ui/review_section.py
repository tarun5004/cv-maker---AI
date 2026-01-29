"""
Review Section UI

This module handles the review step: showing suggestions for user approval.

Design principles:
- Clear before/after comparison
- Easy accept/reject actions
- Show reasoning for each suggestion
- Track user decisions
"""

import streamlit as st
from typing import Optional


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render_review_section():
    """
    Render the suggestion review section.
    
    Users see each suggestion with:
    - Original text
    - Suggested text
    - Reason for the change
    - Accept/Reject buttons
    """
    result = st.session_state.pipeline_result
    state = st.session_state.pipeline_state

    if not result:
        st.error("No results to review. Please go back and process your CV.")
        if st.button("← Go Back"):
            st.session_state.current_step = "upload"
            st.rerun()
        return

    # Header
    st.header("📝 Review Suggestions")
    st.markdown(
        "Review each suggestion below. Accept the ones that make sense, "
        "skip the ones that don't. You're in control."
    )

    # Quick stats
    render_match_summary(result, state)

    st.markdown("---")

    # Suggestions list
    suggestions = result.suggestions

    if not suggestions:
        st.info(
            "✨ **Good news!** Your resume is already well-aligned with this job. "
            "No major changes needed."
        )
        st.markdown("We've reordered your skills to highlight the most relevant ones.")
    else:
        st.markdown(f"### Suggested Improvements ({len(suggestions)})")
        st.markdown(
            "*Click to expand each suggestion. Accept or skip based on your judgment.*"
        )

        # Render each suggestion
        for i, suggestion in enumerate(suggestions):
            render_suggestion_card(i, suggestion)

    st.markdown("---")

    # Navigation buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("← Back to Upload", use_container_width=True):
            st.session_state.current_step = "upload"
            st.rerun()
    
    with col3:
        if st.button("View Final Result →", type="primary", use_container_width=True):
            st.session_state.current_step = "result"
            st.rerun()


# =============================================================================
# MATCH SUMMARY
# =============================================================================

def render_match_summary(result, state):
    """
    Show a quick summary of the match analysis.
    """
    col1, col2, col3, col4 = st.columns(4)

    # Match score
    with col1:
        if state and state.skill_match_result:
            score = state.skill_match_result.match_score
            st.metric(
                label="Match Score",
                value=f"{score:.0%}",
                help="Percentage of required skills you have",
            )
        else:
            st.metric("Match Score", "N/A")

    # Matched skills
    with col2:
        if state and state.skill_match_result:
            matched = len(state.skill_match_result.matched_required)
            st.metric(
                label="Skills Matched",
                value=matched,
                help="Required skills found in your CV",
            )
        else:
            st.metric("Skills Matched", "N/A")

    # Missing skills
    with col3:
        if state and state.skill_match_result:
            missing = len(state.skill_match_result.missing_required)
            st.metric(
                label="Skills Gaps",
                value=missing,
                help="Required skills not found in your CV",
            )
        else:
            st.metric("Skills Gaps", "N/A")

    # Suggestions count
    with col4:
        st.metric(
            label="Suggestions",
            value=len(result.suggestions),
            help="Number of improvement suggestions",
        )

    # Show matched skills
    if state and state.skill_match_result:
        skill_result = state.skill_match_result
        
        with st.expander("🎯 Skills Analysis", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**✅ Skills You Have (Required)**")
                if skill_result.matched_required:
                    for skill in skill_result.matched_required[:10]:
                        st.markdown(f"- {skill}")
                else:
                    st.markdown("*None matched*")

            with col2:
                st.markdown("**❌ Skills Gaps (Required)**")
                if skill_result.missing_required:
                    for skill in skill_result.missing_required[:10]:
                        st.markdown(f"- {skill}")
                else:
                    st.markdown("*No gaps — great match!*")


# =============================================================================
# SUGGESTION CARD
# =============================================================================

def render_suggestion_card(index: int, suggestion):
    """
    Render a single suggestion as an expandable card.
    
    Shows:
    - Original text
    - Suggested text (highlighted)
    - Reason for the change
    - Accept/Skip buttons
    """
    # Create a unique key for this suggestion
    key_prefix = f"suggestion_{index}"

    # Get current status from session state (or default to pending)
    status_key = f"{key_prefix}_status"
    if status_key not in st.session_state:
        st.session_state[status_key] = suggestion.status

    current_status = st.session_state[status_key]

    # Determine expander icon based on status
    if current_status == "accepted":
        icon = "✅"
        border_color = "green"
    elif current_status == "dismissed":
        icon = "⏭️"
        border_color = "gray"
    else:
        icon = "📝"
        border_color = "blue"

    # Expander title
    title = f"{icon} Suggestion {index + 1}"
    if suggestion.section_name:
        title += f" ({suggestion.section_name.replace('_', ' ').title()})"

    with st.expander(title, expanded=(current_status == "pending")):
        # Original text
        st.markdown("**Original:**")
        st.text(suggestion.original_text[:200] + "..." if len(suggestion.original_text) > 200 else suggestion.original_text)

        # Suggested text
        st.markdown("**Suggested:**")
        st.success(suggestion.suggested_text[:200] + "..." if len(suggestion.suggested_text) > 200 else suggestion.suggested_text)

        # Reason
        if suggestion.reason:
            st.markdown("**Why this change:**")
            st.info(suggestion.reason)

        # Verification question
        if suggestion.prompt_question:
            st.markdown("**Before accepting, please verify:**")
            st.warning(suggestion.prompt_question)

        # Confidence indicator
        if suggestion.confidence < 0.8:
            st.caption(
                f"⚠️ Confidence: {suggestion.confidence:.0%} — Please review carefully"
            )

        # Action buttons
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("✅ Accept", key=f"{key_prefix}_accept", use_container_width=True):
                st.session_state[status_key] = "accepted"
                # Update the actual suggestion object
                suggestion.status = "accepted"
                st.rerun()

        with col2:
            if st.button("⏭️ Skip", key=f"{key_prefix}_skip", use_container_width=True):
                st.session_state[status_key] = "dismissed"
                suggestion.status = "dismissed"
                st.rerun()

        # Show current status
        if current_status == "accepted":
            st.success("✓ Accepted")
        elif current_status == "dismissed":
            st.info("Skipped")

