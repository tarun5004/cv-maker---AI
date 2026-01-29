"""
Upload Section UI

This module handles the first step: collecting CV and job description text.

Design principles:
- Clear instructions
- Example placeholders
- Input validation
- No overwhelming options
"""

import streamlit as st


# =============================================================================
# SAMPLE DATA (for demo/testing)
# =============================================================================

SAMPLE_CV = """John Smith
john.smith@email.com | (555) 123-4567 | linkedin.com/in/johnsmith | github.com/johnsmith
San Francisco, CA

SUMMARY
Software engineer with 3 years of experience building web applications. 
Passionate about clean code and user experience.

WORK EXPERIENCE

Software Engineer | TechCorp Inc. | Jan 2022 - Present
• Developed and maintained web applications using modern frameworks
• Collaborated with cross-functional teams to deliver features on time
• Improved application performance by optimizing database queries
• Participated in code reviews and mentored junior developers

Junior Developer | StartupXYZ | Jun 2020 - Dec 2021
• Built responsive frontend interfaces for client projects
• Worked on API development and integration
• Assisted in migrating legacy systems to cloud infrastructure

EDUCATION

Bachelor of Science in Computer Science | State University | 2016 - 2020
• GPA: 3.7/4.0
• Relevant coursework: Data Structures, Algorithms, Web Development

SKILLS
Python, JavaScript, React, Node.js, SQL, Git, Docker, AWS, Agile

PROJECTS

Personal Portfolio Website | 2023
• Designed and built a responsive portfolio site
• Implemented contact form with email integration
"""

SAMPLE_JD = """Senior Software Engineer
Google | Mountain View, CA

About the Role
We're looking for a Senior Software Engineer to join our Cloud Platform team.
You'll work on building scalable infrastructure that powers millions of users.

Responsibilities
• Design and implement backend services using Python and Go
• Build and maintain REST APIs and microservices
• Collaborate with product managers and designers
• Mentor junior engineers and conduct code reviews
• Participate in on-call rotations

Requirements
• 5+ years of software engineering experience
• Strong proficiency in Python
• Experience with cloud platforms (AWS, GCP, or Azure)
• Knowledge of containerization (Docker, Kubernetes)
• Experience with SQL and NoSQL databases
• Bachelor's degree in Computer Science or related field

Nice to Have
• Experience with React or modern frontend frameworks
• Knowledge of machine learning concepts
• Open source contributions
• Experience with distributed systems
"""


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render_upload_section():
    """
    Render the upload/paste section for CV and JD.
    
    Users paste their resume and job description here.
    We validate inputs before allowing them to proceed.
    """
    st.header("📤 Upload Your Documents")
    st.markdown(
        "Paste your resume and the job description below. "
        "We'll analyze both and suggest targeted improvements."
    )

    # Two-column layout for CV and JD
    col1, col2 = st.columns(2)

    # === LEFT COLUMN: CV ===
    with col1:
        st.subheader("Your Resume")
        st.markdown("*Paste the text content of your resume*")
        
        # Text area for CV
        cv_text = st.text_area(
            label="Resume Text",
            value=st.session_state.raw_cv_text,
            height=400,
            placeholder="Paste your resume here...\n\nTip: Copy from your Word/Google Doc or PDF",
            key="cv_input",
            label_visibility="collapsed",
        )
        
        # Update session state
        st.session_state.raw_cv_text = cv_text

        # Character count
        cv_chars = len(cv_text.strip())
        if cv_chars > 0:
            st.caption(f"📝 {cv_chars} characters")
        
        # Load sample button
        if st.button("📋 Load Sample CV", key="load_sample_cv", use_container_width=True):
            st.session_state.raw_cv_text = SAMPLE_CV
            st.rerun()

    # === RIGHT COLUMN: JD ===
    with col2:
        st.subheader("Job Description")
        st.markdown("*Paste the job posting you're applying to*")
        
        # Text area for JD
        jd_text = st.text_area(
            label="Job Description Text",
            value=st.session_state.raw_jd_text,
            height=400,
            placeholder="Paste the job description here...\n\nTip: Copy from LinkedIn, company website, etc.",
            key="jd_input",
            label_visibility="collapsed",
        )
        
        # Update session state
        st.session_state.raw_jd_text = jd_text

        # Character count
        jd_chars = len(jd_text.strip())
        if jd_chars > 0:
            st.caption(f"📝 {jd_chars} characters")
        
        # Load sample button
        if st.button("📋 Load Sample JD", key="load_sample_jd", use_container_width=True):
            st.session_state.raw_jd_text = SAMPLE_JD
            st.rerun()

    # === VALIDATION AND PROCEED ===
    st.markdown("---")

    # Validate inputs
    cv_valid = len(st.session_state.raw_cv_text.strip()) >= 100
    jd_valid = len(st.session_state.raw_jd_text.strip()) >= 50

    # Show validation messages
    if not cv_valid and st.session_state.raw_cv_text.strip():
        st.warning("⚠️ Your resume seems too short. Please paste the full content.")
    
    if not jd_valid and st.session_state.raw_jd_text.strip():
        st.warning("⚠️ The job description seems too short. Please paste the full posting.")

    # Proceed button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if cv_valid and jd_valid:
            if st.button(
                "🚀 Analyze My Resume",
                type="primary",
                use_container_width=True,
            ):
                # Move to processing step
                st.session_state.current_step = "processing"
                st.session_state.processing_complete = False
                st.session_state.processing_error = None
                st.rerun()
        else:
            st.button(
                "🚀 Analyze My Resume",
                type="primary",
                use_container_width=True,
                disabled=True,
            )
            if not cv_valid or not jd_valid:
                st.caption("Please paste both your resume and the job description to continue.")

    # === TIPS SECTION ===
    with st.expander("💡 Tips for better results"):
        st.markdown("""
        **For your resume:**
        - Paste the full text, including all sections
        - Include your name, contact info, experience, education, and skills
        - Don't worry about formatting — we only analyze the content
        
        **For the job description:**
        - Include the full posting, not just the title
        - The more detail, the better we can match your skills
        - Include requirements, responsibilities, and "nice to haves"
        
        **What we analyze:**
        - Skills mentioned in both documents
        - Experience relevance to the role
        - Gaps between your profile and job requirements
        """)
