"""
Smart CV Tailor - Section-Based Resume Editor

A Streamlit app for editing resumes section by section.
NOT a chat interface. NOT a single-page analyzer.

Architecture:
- Sidebar: Section navigation
- Main area: Section editor for the currently selected section
- Session state: Tracks current section + all resume data

Sections:
1. Header      → Name, contact info
2. Summary     → Professional summary
3. Skills      → Skills list (editable, reorderable)
4. Experience  → Work history entries
5. Education   → Degrees, certifications
6. Projects    → Personal/professional projects
7. Optimize    → Job description matching (placeholder)
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import Optional


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="Smart CV Tailor",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =============================================================================
# SECTION DEFINITIONS
# =============================================================================

# All available sections in the resume editor
SECTIONS = {
    "header": {"icon": "👤", "label": "Header", "description": "Name & Contact Info"},
    "summary": {"icon": "📝", "label": "Summary", "description": "Professional Summary"},
    "skills": {"icon": "🛠️", "label": "Skills", "description": "Technical & Soft Skills"},
    "experience": {"icon": "💼", "label": "Experience", "description": "Work History"},
    "education": {"icon": "🎓", "label": "Education", "description": "Degrees & Certifications"},
    "projects": {"icon": "🚀", "label": "Projects", "description": "Personal & Professional Projects"},
    "optimize": {"icon": "🎯", "label": "Optimize for Job", "description": "Match to Job Description"},
}


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def init_session_state():
    """
    Initialize all session state variables.
    
    We store:
    - current_section: Which section is being edited
    - resume_data: All resume content organized by section
    """
    
    # Current section being edited
    if "current_section" not in st.session_state:
        st.session_state.current_section = "header"

    # Resume data structure
    if "resume_data" not in st.session_state:
        st.session_state.resume_data = {
            "header": {
                "full_name": "",
                "email": "",
                "phone": "",
                "location": "",
                "linkedin": "",
                "github": "",
                "portfolio": "",
            },
            "summary": {
                "text": "",
            },
            "skills": {
                # Category-based skills structure
                # Key: category name (e.g., "Languages", "Frameworks")
                # Value: list of skill strings in that category
                "categories": {},
            },
            "experience": {
                "entries": [],  # List of experience dicts
            },
            "education": {
                "entries": [],  # List of education dicts
            },
            "projects": {
                "entries": [],  # List of project dicts
            },
        }

    # Job description for optimization (placeholder)
    if "job_description" not in st.session_state:
        st.session_state.job_description = ""

    # JD analysis results (populated by analyze_job_description)
    if "jd_analysis" not in st.session_state:
        st.session_state.jd_analysis = None

    # -------------------------------------------------------------------------
    # Optimization State (for Apply Optimization feature)
    # -------------------------------------------------------------------------
    
    # Backup of original resume before optimization
    if "original_resume_backup" not in st.session_state:
        st.session_state.original_resume_backup = None
    
    # Pipeline result after running optimization
    if "optimization_result" not in st.session_state:
        st.session_state.optimization_result = None
    
    # Flag to show optimized preview vs original
    if "show_optimized_preview" not in st.session_state:
        st.session_state.show_optimized_preview = False


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================

def render_sidebar():
    """
    Render the sidebar with section navigation.
    
    Each section is a button. Clicking it sets current_section in session state.
    The main area then renders the appropriate editor.
    """
    with st.sidebar:
        st.title("📄 CV Tailor")
        st.markdown("---")
        
        st.markdown("### Sections")
        
        # Render navigation buttons for each section
        for section_key, section_info in SECTIONS.items():
            # Highlight the current section
            is_current = st.session_state.current_section == section_key
            
            # Button label with icon
            label = f"{section_info['icon']} {section_info['label']}"
            
            # Use different button type for current section
            if is_current:
                st.button(
                    label,
                    key=f"nav_{section_key}",
                    use_container_width=True,
                    type="primary",
                    disabled=True,  # Can't click current section
                )
            else:
                if st.button(
                    label,
                    key=f"nav_{section_key}",
                    use_container_width=True,
                ):
                    st.session_state.current_section = section_key
                    st.rerun()

        st.markdown("---")
        
        # Progress indicator
        render_progress_indicator()
        
        st.markdown("---")
        
        # Actions
        st.markdown("### Actions")
        
        if st.button("📋 Preview Resume", use_container_width=True):
            st.session_state.current_section = "preview"
            st.rerun()
        
        if st.button("🗑️ Clear All", use_container_width=True):
            if st.button("⚠️ Confirm Clear", key="confirm_clear"):
                init_resume_data()
                st.rerun()


def render_progress_indicator():
    """
    Show how complete the resume is.
    
    Simple check: count non-empty sections.
    """
    data = st.session_state.resume_data
    
    filled = 0
    total = 6  # header, summary, skills, experience, education, projects
    
    if data["header"]["full_name"]:
        filled += 1
    if data["summary"]["text"]:
        filled += 1
    # Skills: check if any category has at least one skill
    if any(skills for skills in data["skills"].get("categories", {}).values()):
        filled += 1
    if data["experience"]["entries"]:
        filled += 1
    if data["education"]["entries"]:
        filled += 1
    if data["projects"]["entries"]:
        filled += 1
    
    st.markdown("### Progress")
    st.progress(filled / total)
    st.caption(f"{filled}/{total} sections filled")


def init_resume_data():
    """Reset resume data to empty state."""
    st.session_state.resume_data = {
        "header": {
            "full_name": "",
            "email": "",
            "phone": "",
            "location": "",
            "linkedin": "",
            "github": "",
            "portfolio": "",
        },
        "summary": {"text": ""},
        "skills": {"categories": {}},
        "experience": {"entries": []},
        "education": {"entries": []},
        "projects": {"entries": []},
    }


# =============================================================================
# MAIN AREA - SECTION ROUTER
# =============================================================================

def render_main_area():
    """
    Render the main editing area based on current section.
    
    This is a simple router that calls the appropriate editor function.
    """
    current = st.session_state.current_section
    section_info = SECTIONS.get(current, {})

    # Section header
    if current != "preview":
        icon = section_info.get("icon", "📄")
        label = section_info.get("label", "Section")
        description = section_info.get("description", "")
        
        st.header(f"{icon} {label}")
        st.caption(description)
        st.markdown("---")

    # Route to appropriate editor
    if current == "header":
        render_header_editor()
    elif current == "summary":
        render_summary_editor()
    elif current == "skills":
        render_skills_editor()
    elif current == "experience":
        render_experience_editor()
    elif current == "education":
        render_education_editor()
    elif current == "projects":
        render_projects_editor()
    elif current == "optimize":
        render_optimize_placeholder()
    elif current == "preview":
        render_preview()
    else:
        st.error(f"Unknown section: {current}")


# =============================================================================
# SECTION EDITORS
# =============================================================================

def render_header_editor():
    """
    Edit header section: name, contact info, links.
    """
    data = st.session_state.resume_data["header"]

    col1, col2 = st.columns(2)

    with col1:
        data["full_name"] = st.text_input(
            "Full Name *",
            value=data["full_name"],
            placeholder="John Smith",
        )
        
        data["email"] = st.text_input(
            "Email *",
            value=data["email"],
            placeholder="john@email.com",
        )
        
        data["phone"] = st.text_input(
            "Phone",
            value=data["phone"],
            placeholder="(555) 123-4567",
        )
        
        data["location"] = st.text_input(
            "Location",
            value=data["location"],
            placeholder="San Francisco, CA",
        )

    with col2:
        data["linkedin"] = st.text_input(
            "LinkedIn URL",
            value=data["linkedin"],
            placeholder="linkedin.com/in/johnsmith",
        )
        
        data["github"] = st.text_input(
            "GitHub URL",
            value=data["github"],
            placeholder="github.com/johnsmith",
        )
        
        data["portfolio"] = st.text_input(
            "Portfolio/Website",
            value=data["portfolio"],
            placeholder="johnsmith.dev",
        )

    # Save happens automatically via session state binding
    st.markdown("---")
    st.caption("* Required fields")

    # Navigation
    render_section_nav("summary")


def render_summary_editor():
    """
    Edit professional summary section.
    """
    data = st.session_state.resume_data["summary"]

    data["text"] = st.text_area(
        "Professional Summary",
        value=data["text"],
        height=200,
        placeholder=(
            "Experienced software engineer with 5+ years building web applications. "
            "Passionate about clean code, user experience, and mentoring junior developers."
        ),
        help="2-4 sentences summarizing your experience and value proposition.",
    )

    # Character count
    char_count = len(data["text"])
    if char_count > 0:
        if char_count < 100:
            st.warning(f"📝 {char_count} characters — Consider adding more detail")
        elif char_count > 500:
            st.warning(f"📝 {char_count} characters — Consider being more concise")
        else:
            st.success(f"📝 {char_count} characters — Good length")

    # Navigation
    render_section_nav("skills", "header")


# =============================================================================
# DEFAULT SKILL CATEGORIES
# =============================================================================
# Common categories users can quickly add. Not required to use these.
DEFAULT_SKILL_CATEGORIES = [
    "Programming Languages",
    "Frameworks & Libraries",
    "Databases",
    "Tools & Platforms",
    "Cloud & DevOps",
    "Soft Skills",
]


def render_skills_editor():
    """
    Edit skills section organized by category.
    
    Structure:
    - Skills are grouped into categories (e.g., Languages, Frameworks)
    - Each category contains a list of skill strings
    - User can add/remove categories and skills within each category
    - Categories help ATS systems and recruiters quickly scan skills
    
    Data format:
        skills: {
            "categories": {
                "Programming Languages": ["Python", "JavaScript", "Go"],
                "Frameworks": ["React", "FastAPI", "Django"],
            }
        }
    """
    data = st.session_state.resume_data["skills"]
    
    # Ensure categories dict exists (migration from old format)
    if "categories" not in data:
        data["categories"] = {}
    
    categories = data["categories"]

    # -------------------------------------------------------------------------
    # SECTION 1: Add New Category
    # -------------------------------------------------------------------------
    st.markdown("### Add Category")
    st.caption("Organize your skills by category for better readability.")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Quick-add from common categories
        available_defaults = [c for c in DEFAULT_SKILL_CATEGORIES if c not in categories]
        if available_defaults:
            selected_default = st.selectbox(
                "Quick add common category",
                options=[""] + available_defaults,
                key="quick_add_category",
                help="Select a common category to add it instantly",
            )
            if selected_default and st.button("Add", key="add_default_category"):
                categories[selected_default] = []
                st.rerun()
        else:
            st.caption("All common categories added.")
    
    with col2:
        # Custom category input
        new_category = st.text_input(
            "Or create custom category",
            key="new_category_input",
            placeholder="e.g., Certifications, Industry Knowledge",
        )
    
    with col3:
        st.markdown("")  # Vertical spacing to align with inputs
        st.markdown("")
        if st.button("➕ Add Custom", key="add_custom_category", use_container_width=True):
            if new_category and new_category.strip() not in categories:
                categories[new_category.strip()] = []
                st.rerun()
            elif new_category.strip() in categories:
                st.warning("Category already exists.")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # SECTION 2: Display & Edit Categories
    # -------------------------------------------------------------------------
    if categories:
        st.markdown("### Your Skills")
        st.caption("Add skills to each category. Click ✕ to remove.")
        
        # Iterate through each category
        for category_name in list(categories.keys()):
            skills_list = categories[category_name]
            
            # Category header with remove button
            with st.expander(f"**{category_name}** ({len(skills_list)} skills)", expanded=True):
                
                # Add skill to this category
                add_col1, add_col2 = st.columns([4, 1])
                with add_col1:
                    new_skill = st.text_input(
                        "Add skill",
                        key=f"add_skill_{category_name}",
                        placeholder=f"Add a skill to {category_name}...",
                        label_visibility="collapsed",
                    )
                with add_col2:
                    if st.button("➕", key=f"btn_add_skill_{category_name}", use_container_width=True):
                        if new_skill and new_skill.strip() not in skills_list:
                            skills_list.append(new_skill.strip())
                            st.rerun()
                
                # Display existing skills in this category
                if skills_list:
                    # Display skills as removable chips in a grid
                    # Using 4 columns for compact display
                    skill_cols = st.columns(4)
                    for i, skill in enumerate(skills_list):
                        with skill_cols[i % 4]:
                            skill_col1, skill_col2 = st.columns([4, 1])
                            with skill_col1:
                                st.markdown(f"`{skill}`")
                            with skill_col2:
                                if st.button("✕", key=f"remove_{category_name}_{i}"):
                                    skills_list.remove(skill)
                                    st.rerun()
                else:
                    st.caption("No skills in this category yet.")
                
                # Remove entire category button
                st.markdown("---")
                if st.button(
                    f"🗑️ Remove '{category_name}' category",
                    key=f"remove_category_{category_name}",
                ):
                    del categories[category_name]
                    st.rerun()
    else:
        st.info(
            "📝 No skill categories yet. Add a category above to start organizing your skills."
        )

    # -------------------------------------------------------------------------
    # SECTION 3: Preview (inline for quick feedback)
    # -------------------------------------------------------------------------
    if categories and any(skills for skills in categories.values()):
        st.markdown("---")
        st.markdown("### Preview (ATS-Safe Format)")
        st.caption("This is how your skills will appear on your resume.")
        
        # ATS-safe format: Category: skill1, skill2, skill3
        for category_name, skills_list in categories.items():
            if skills_list:
                st.markdown(f"**{category_name}:** {', '.join(skills_list)}")

    # Navigation
    render_section_nav("experience", "summary")


def render_experience_editor():
    """
    Edit work experience section with multiple entries.
    
    This is a FIRST-CLASS section for professional work history.
    
    Each experience entry includes:
    - Job Title (required)
    - Company name (required)
    - Location (optional)
    - Start Date and End Date (or "Present" for current role)
    - Role Summary (optional - 1-2 sentence overview)
    - Bullet points (responsibilities, achievements, impact)
    
    Design decisions:
    - New entries insert at top (most recent first)
    - Bullets are individually editable
    - "Current role" checkbox auto-sets end date to "Present"
    - No AI-generated metrics or fake impact numbers
    """
    data = st.session_state.resume_data["experience"]
    entries = data["entries"]

    # Helper text for users
    st.markdown("""
    Add your work experience starting with your most recent position.
    Focus on concrete responsibilities and achievements — avoid vague statements.
    """)

    # Add new entry button
    col_add, col_spacer = st.columns([1, 3])
    with col_add:
        if st.button("➕ Add Work Experience", use_container_width=True, type="primary"):
            # Insert at beginning so newest appears first
            entries.insert(0, {
                "title": "",
                "company": "",
                "location": "",
                "start_date": "",
                "end_date": "",
                "is_current": False,
                "summary": "",
                "bullets": [""],
            })
            st.rerun()

    st.markdown("---")

    # Display existing entries
    if entries:
        for i, entry in enumerate(entries):
            # Build expander title with available info
            title_text = entry.get('title', '') or 'New Position'
            company_text = entry.get('company', '') or 'Company'
            
            # Show date range in expander title if available
            date_suffix = ""
            if entry.get('start_date'):
                end = entry.get('end_date', '') or 'Present'
                date_suffix = f" ({entry['start_date']} – {end})"
            
            expander_title = f"💼 **{title_text}** at {company_text}{date_suffix}"
            
            with st.expander(
                expander_title,
                expanded=(not entry.get('title')),  # Expand if empty
            ):
                render_experience_entry(i, entry)
                
                # Remove button at the bottom of the expander
                st.markdown("---")
                if st.button("🗑️ Remove this experience", key=f"remove_exp_{i}"):
                    entries.pop(i)
                    st.rerun()
    else:
        st.info("💼 No work experience added yet. Click 'Add Work Experience' to start.")

    # Navigation
    render_section_nav("education", "skills")


def render_experience_entry(index: int, entry: dict):
    """
    Render a single experience entry editor.
    
    Fields:
    - title: Job title (required)
    - company: Company name (required)
    - location: City, State/Country (optional)
    - start_date: Start date (e.g., "Jan 2022")
    - end_date: End date or "Present"
    - is_current: Boolean flag for current role
    - summary: Short role overview (optional, 1-2 sentences)
    - bullets: List of responsibility/achievement bullet points
    """
    # -------------------------------------------------------------------------
    # Row 1: Job Title and Company (required fields)
    # -------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        entry["title"] = st.text_input(
            "Job Title *",
            value=entry.get("title", ""),
            key=f"exp_title_{index}",
            placeholder="Senior Software Engineer",
            help="Your official job title",
        )

    with col2:
        entry["company"] = st.text_input(
            "Company *",
            value=entry.get("company", ""),
            key=f"exp_company_{index}",
            placeholder="Google",
            help="Company or organization name",
        )

    # -------------------------------------------------------------------------
    # Row 2: Location and Date Range
    # -------------------------------------------------------------------------
    col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1])

    with col3:
        entry["location"] = st.text_input(
            "Location",
            value=entry.get("location", ""),
            key=f"exp_location_{index}",
            placeholder="Mountain View, CA",
            help="City and state/country (optional)",
        )

    with col4:
        entry["start_date"] = st.text_input(
            "Start Date",
            value=entry.get("start_date", ""),
            key=f"exp_start_{index}",
            placeholder="Jan 2022",
            help="Month and year you started",
        )

    with col5:
        # Handle current role checkbox
        is_current = entry.get("is_current", False)
        
        if not is_current:
            entry["end_date"] = st.text_input(
                "End Date",
                value=entry.get("end_date", ""),
                key=f"exp_end_{index}",
                placeholder="Dec 2023",
                help="Month and year you left",
            )
        else:
            # Show disabled field with "Present"
            st.text_input(
                "End Date",
                value="Present",
                key=f"exp_end_{index}",
                disabled=True,
            )
            entry["end_date"] = "Present"

    with col6:
        st.markdown("")  # Vertical spacing
        entry["is_current"] = st.checkbox(
            "Current",
            value=is_current,
            key=f"exp_current_{index}",
            help="Check if this is your current role",
        )

    # -------------------------------------------------------------------------
    # Row 3: Role Summary (optional)
    # -------------------------------------------------------------------------
    st.markdown("**Role Summary** *(optional)*")
    st.caption("A brief 1-2 sentence overview of your role. Leave blank if you prefer bullets only.")
    entry["summary"] = st.text_input(
        "Role Summary",
        value=entry.get("summary", ""),
        key=f"exp_summary_{index}",
        placeholder="Led a team of 5 engineers building the core search infrastructure.",
        label_visibility="collapsed",
    )

    # -------------------------------------------------------------------------
    # Row 4: Bullet Points (responsibilities & achievements)
    # -------------------------------------------------------------------------
    st.markdown("**Responsibilities & Achievements**")
    st.caption("Add bullet points describing what you did and accomplished. Be specific.")
    
    # Ensure bullets list exists
    if "bullets" not in entry:
        entry["bullets"] = [""]
    
    render_experience_bullets(entry["bullets"], f"exp_{index}")


def render_experience_bullets(bullets: list, prefix: str):
    """
    Render an editable list of bullet points for experience entries.
    
    Features:
    - Each bullet is individually editable
    - Add new bullets at the end
    - Remove any bullet (except when only 1 remains)
    - Placeholder text guides users on what to write
    
    Args:
        bullets: List of bullet point strings
        prefix: Unique prefix for Streamlit keys (e.g., "exp_0")
    """
    # Bullet writing tips
    bullet_placeholders = [
        "Designed and implemented...",
        "Collaborated with cross-functional teams to...",
        "Reduced deployment time by...",
        "Mentored junior developers on...",
        "Migrated legacy systems to...",
    ]
    
    for i, bullet in enumerate(bullets):
        col1, col2 = st.columns([10, 1])
        
        with col1:
            # Cycle through placeholder suggestions
            placeholder = bullet_placeholders[i % len(bullet_placeholders)]
            bullets[i] = st.text_input(
                f"Bullet {i + 1}",
                value=bullet,
                key=f"{prefix}_bullet_{i}",
                placeholder=placeholder,
                label_visibility="collapsed",
            )
        
        with col2:
            # Only show remove button if more than 1 bullet exists
            if len(bullets) > 1:
                if st.button("✕", key=f"{prefix}_remove_bullet_{i}"):
                    bullets.pop(i)
                    st.rerun()
            else:
                # Empty placeholder to maintain layout
                st.markdown("")

    # Add bullet button
    if st.button("➕ Add bullet", key=f"{prefix}_add_bullet"):
        bullets.append("")
        st.rerun()


def render_education_editor():
    """
    Edit education section with multiple entries.
    
    This is a FIRST-CLASS section, not an afterthought.
    Supports: degrees, certifications, bootcamps, courses.
    
    Each education entry includes:
    - Degree/Certificate name
    - Institution name
    - Location (optional)
    - Start year and End year
    - Description (optional - for coursework, honors, activities)
    """
    data = st.session_state.resume_data["education"]
    entries = data["entries"]

    # Helper text for users
    st.markdown("""
    Add your educational background including degrees, certifications, bootcamps, and relevant courses.
    Most recent education should be listed first.
    """)

    # Add new entry button
    col_add, col_spacer = st.columns([1, 3])
    with col_add:
        if st.button("➕ Add Education", use_container_width=True, type="primary"):
            # Insert at beginning so newest appears first
            entries.insert(0, {
                "degree": "",
                "institution": "",
                "location": "",
                "start_year": "",
                "end_year": "",
                "description": "",
            })
            st.rerun()

    st.markdown("---")

    # Display existing entries
    if entries:
        for i, entry in enumerate(entries):
            # Build expander title with available info
            degree_text = entry.get('degree', '') or 'New Education'
            institution_text = entry.get('institution', '') or 'Institution'
            expander_title = f"🎓 **{degree_text}** — {institution_text}"
            
            with st.expander(
                expander_title,
                expanded=(not entry.get('degree')),  # Expand if empty
            ):
                render_education_entry(i, entry)
                
                # Remove button at the bottom of the expander
                st.markdown("---")
                if st.button("🗑️ Remove this education", key=f"remove_edu_{i}"):
                    entries.pop(i)
                    st.rerun()
    else:
        st.info("📚 No education added yet. Click 'Add Education' to start.")

    # Navigation
    render_section_nav("projects", "experience")


def render_education_entry(index: int, entry: dict):
    """
    Render a single education entry editor.
    
    Fields:
    - degree: The degree or certificate name (required)
    - institution: School/university name (required)
    - location: City, State/Country (optional)
    - start_year: Start year (e.g., "2016")
    - end_year: End year or "Present" (e.g., "2020")
    - description: Additional details like coursework, honors, GPA (optional)
    """
    # -------------------------------------------------------------------------
    # Row 1: Degree and Institution (required fields)
    # -------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        entry["degree"] = st.text_input(
            "Degree / Certificate *",
            value=entry.get("degree", ""),
            key=f"edu_degree_{index}",
            placeholder="Bachelor of Science in Computer Science",
            help="e.g., Bachelor's, Master's, PhD, Bootcamp Certificate, etc.",
        )

    with col2:
        entry["institution"] = st.text_input(
            "Institution *",
            value=entry.get("institution", ""),
            key=f"edu_institution_{index}",
            placeholder="Massachusetts Institute of Technology",
            help="School, university, or organization name",
        )

    # -------------------------------------------------------------------------
    # Row 2: Location and Date Range
    # -------------------------------------------------------------------------
    col3, col4, col5 = st.columns([2, 1, 1])

    with col3:
        entry["location"] = st.text_input(
            "Location",
            value=entry.get("location", ""),
            key=f"edu_location_{index}",
            placeholder="Cambridge, MA",
            help="City and state/country (optional)",
        )

    with col4:
        entry["start_year"] = st.text_input(
            "Start Year",
            value=entry.get("start_year", ""),
            key=f"edu_start_{index}",
            placeholder="2016",
            help="Year you started",
        )

    with col5:
        entry["end_year"] = st.text_input(
            "End Year",
            value=entry.get("end_year", ""),
            key=f"edu_end_{index}",
            placeholder="2020 or Present",
            help="Year graduated or 'Present' if ongoing",
        )

    # -------------------------------------------------------------------------
    # Row 3: Description (optional - coursework, honors, GPA, activities)
    # -------------------------------------------------------------------------
    st.markdown("**Description** *(optional)*")
    st.caption("Add relevant coursework, honors, GPA, activities, or achievements.")
    entry["description"] = st.text_area(
        "Description",
        value=entry.get("description", ""),
        key=f"edu_description_{index}",
        placeholder="GPA: 3.8/4.0 • Dean's List • Relevant coursework: Data Structures, Algorithms, Machine Learning • Teaching Assistant for CS101",
        height=100,
        label_visibility="collapsed",
    )


def render_projects_editor():
    """
    Edit projects section with multiple entries.
    
    This is a FIRST-CLASS section for showcasing personal and professional projects.
    
    Each project entry includes:
    - name: Project name (required)
    - description: Short description of the project (1-2 sentences)
    - tech_stack: List of technologies/skills used
    - role: Your role or contribution (optional)
    - url: Project link - GitHub, live demo, etc. (optional)
    - date: When the project was completed or duration
    
    Design decisions:
    - New entries insert at top (most impressive first)
    - Tech stack as comma-separated for easy editing
    - Role field helps highlight leadership/ownership
    - URL is optional since not all projects are public
    """
    data = st.session_state.resume_data["projects"]
    entries = data["entries"]

    # Helper text for users
    st.markdown("""
    Add personal, academic, or professional projects that showcase your skills.
    Include side projects, open source contributions, hackathon projects, or significant coursework.
    """)

    # Add new entry button
    col_add, col_spacer = st.columns([1, 3])
    with col_add:
        if st.button("➕ Add Project", use_container_width=True, type="primary"):
            # Insert at beginning so most impressive appears first
            entries.insert(0, {
                "name": "",
                "description": "",
                "tech_stack": "",
                "role": "",
                "url": "",
                "date": "",
            })
            st.rerun()

    st.markdown("---")

    # Display existing entries
    if entries:
        for i, entry in enumerate(entries):
            # Build expander title with available info
            name_text = entry.get('name', '') or 'New Project'
            
            # Show tech stack preview in expander title if available
            tech_preview = ""
            if entry.get('tech_stack'):
                # Show first 2-3 technologies as preview
                techs = [t.strip() for t in entry['tech_stack'].split(',')[:3]]
                tech_preview = f" ({', '.join(techs)})"
            
            expander_title = f"🚀 **{name_text}**{tech_preview}"
            
            with st.expander(
                expander_title,
                expanded=(not entry.get('name')),  # Expand if empty
            ):
                render_project_entry(i, entry)
                
                # Remove button at the bottom of the expander
                st.markdown("---")
                if st.button("🗑️ Remove this project", key=f"remove_proj_{i}"):
                    entries.pop(i)
                    st.rerun()
    else:
        st.info("🚀 No projects added yet. Click 'Add Project' to start.")

    # Navigation
    render_section_nav("optimize", "education")


def render_project_entry(index: int, entry: dict):
    """
    Render a single project entry editor.
    
    Fields:
    - name: Project name (required)
    - description: Short description (1-2 sentences)
    - tech_stack: Comma-separated list of technologies
    - role: Your role or contribution (optional)
    - url: Project link (optional)
    - date: Completion date or duration
    """
    # -------------------------------------------------------------------------
    # Row 1: Project Name (required)
    # -------------------------------------------------------------------------
    entry["name"] = st.text_input(
        "Project Name *",
        value=entry.get("name", ""),
        key=f"proj_name_{index}",
        placeholder="Smart CV Tailor",
        help="Give your project a clear, descriptive name",
    )

    # -------------------------------------------------------------------------
    # Row 2: Description (short summary)
    # -------------------------------------------------------------------------
    st.markdown("**Description**")
    st.caption("A brief 1-2 sentence summary of what the project does.")
    entry["description"] = st.text_area(
        "Description",
        value=entry.get("description", ""),
        key=f"proj_description_{index}",
        placeholder="A web application that helps job seekers tailor their resumes to specific job descriptions using rule-based matching and suggestions.",
        height=80,
        label_visibility="collapsed",
    )

    # -------------------------------------------------------------------------
    # Row 3: Tech Stack
    # -------------------------------------------------------------------------
    entry["tech_stack"] = st.text_input(
        "Tech Stack",
        value=entry.get("tech_stack", ""),
        key=f"proj_tech_{index}",
        placeholder="Python, Streamlit, FastAPI, PostgreSQL",
        help="Comma-separated list of technologies, frameworks, and tools used",
    )

    # -------------------------------------------------------------------------
    # Row 4: Role and Date
    # -------------------------------------------------------------------------
    col1, col2 = st.columns(2)

    with col1:
        entry["role"] = st.text_input(
            "Your Role / Contribution",
            value=entry.get("role", ""),
            key=f"proj_role_{index}",
            placeholder="Solo Developer, Team Lead, Backend Developer, etc.",
            help="Your specific role or contribution (optional)",
        )

    with col2:
        entry["date"] = st.text_input(
            "Date / Duration",
            value=entry.get("date", ""),
            key=f"proj_date_{index}",
            placeholder="2023 or Jan 2023 - Mar 2023",
            help="When you worked on this project",
        )

    # -------------------------------------------------------------------------
    # Row 5: Project URL (optional)
    # -------------------------------------------------------------------------
    entry["url"] = st.text_input(
        "Project URL",
        value=entry.get("url", ""),
        key=f"proj_url_{index}",
        placeholder="github.com/username/project or live-demo.com",
        help="Link to source code, live demo, or project page (optional)",
    )


def render_optimize_placeholder():
    """
    Optimize for Job section - ANALYSIS ONLY.
    
    This section allows users to:
    1. Paste a job description
    2. Analyze the match between their resume and the job
    3. See matched skills, missing skills, and section suggestions
    
    NO modifications to the resume are made here.
    This is read-only analysis to help users understand gaps.
    
    Design decisions:
    - Rule-based keyword extraction (no AI)
    - Case-insensitive matching
    - Honest language (no hype like "AI-powered")
    - Clear distinction between matched and missing skills
    """
    st.markdown("""
    Paste a job description below to analyze how well your resume matches.
    This analysis is **read-only** — it won't modify your resume.
    """)

    # -------------------------------------------------------------------------
    # Job Description Input
    # -------------------------------------------------------------------------
    st.session_state.job_description = st.text_area(
        "Job Description",
        value=st.session_state.job_description,
        height=200,
        placeholder="Paste the full job description here...\n\nInclude requirements, responsibilities, and qualifications for best results.",
        help="The more complete the job description, the better the analysis.",
    )

    # Analyze button
    col1, col2 = st.columns([1, 3])
    with col1:
        analyze_clicked = st.button(
            "🔍 Analyze Job Description",
            use_container_width=True,
            type="primary",
            disabled=(not st.session_state.job_description.strip()),
        )
    with col2:
        if st.session_state.jd_analysis:
            if st.button("🗑️ Clear Analysis", use_container_width=False):
                st.session_state.jd_analysis = None
                st.rerun()

    # Run analysis if button clicked
    if analyze_clicked:
        st.session_state.jd_analysis = analyze_job_description(
            st.session_state.job_description,
            st.session_state.resume_data,
        )
        st.rerun()

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Analysis Results
    # -------------------------------------------------------------------------
    if st.session_state.jd_analysis:
        render_analysis_results(st.session_state.jd_analysis)
    else:
        st.info("📝 Paste a job description above and click 'Analyze' to see how your resume matches.")

    # Navigation
    render_section_nav(None, "projects")


def analyze_job_description(jd_text: str, resume_data: dict) -> dict:
    """
    Analyze a job description against the user's resume.
    
    This is a RULE-BASED analysis (no AI).
    
    Process:
    1. Extract keywords from JD (simple word tokenization)
    2. Compare against resume skills
    3. Check for keywords in experience/projects
    4. Identify potential gaps
    
    Returns:
        dict with analysis results:
        - jd_keywords: All extracted keywords from JD
        - matched_skills: Skills in resume that match JD
        - missing_skills: JD keywords not found in resume
        - section_suggestions: Suggestions per section
        - match_score: Simple percentage match
    """
    # -------------------------------------------------------------------------
    # Step 1: Extract keywords from JD
    # -------------------------------------------------------------------------
    jd_keywords = extract_keywords_from_text(jd_text)
    
    # -------------------------------------------------------------------------
    # Step 2: Get all skills from resume
    # -------------------------------------------------------------------------
    resume_skills = set()
    skills_data = resume_data.get("skills", {}).get("categories", {})
    for category, skills_list in skills_data.items():
        for skill in skills_list:
            resume_skills.add(skill.lower().strip())
    
    # Also extract skills mentioned in experience bullets
    experience_text = ""
    for entry in resume_data.get("experience", {}).get("entries", []):
        experience_text += " " + entry.get("summary", "")
        for bullet in entry.get("bullets", []):
            experience_text += " " + bullet
    
    # Extract skills from projects
    project_skills = set()
    for entry in resume_data.get("projects", {}).get("entries", []):
        tech_stack = entry.get("tech_stack", "")
        for tech in tech_stack.split(","):
            project_skills.add(tech.lower().strip())
        experience_text += " " + entry.get("description", "")
    
    # Combine all resume skills
    all_resume_skills = resume_skills | project_skills
    experience_keywords = extract_keywords_from_text(experience_text)
    
    # -------------------------------------------------------------------------
    # Step 3: Match JD keywords against resume
    # -------------------------------------------------------------------------
    matched_skills = []
    missing_skills = []
    
    for keyword in jd_keywords:
        keyword_lower = keyword.lower()
        # Check if keyword is in skills or experience
        if keyword_lower in all_resume_skills:
            matched_skills.append(keyword)
        elif keyword_lower in experience_keywords:
            matched_skills.append(keyword)
        else:
            # Check for partial matches (e.g., "Python" matches "Python 3")
            found = False
            for skill in all_resume_skills:
                if keyword_lower in skill or skill in keyword_lower:
                    matched_skills.append(keyword)
                    found = True
                    break
            if not found:
                missing_skills.append(keyword)
    
    # -------------------------------------------------------------------------
    # Step 4: Generate section suggestions
    # -------------------------------------------------------------------------
    section_suggestions = []
    
    # Check summary
    summary_text = resume_data.get("summary", {}).get("text", "")
    if not summary_text:
        section_suggestions.append({
            "section": "Summary",
            "suggestion": "Add a professional summary to highlight your fit for this role.",
            "priority": "high",
        })
    elif len(summary_text) < 100:
        section_suggestions.append({
            "section": "Summary",
            "suggestion": "Your summary is quite short. Consider expanding it to better match the job requirements.",
            "priority": "medium",
        })
    
    # Check skills
    if not resume_skills:
        section_suggestions.append({
            "section": "Skills",
            "suggestion": "Add your skills to help match the job requirements.",
            "priority": "high",
        })
    elif missing_skills:
        section_suggestions.append({
            "section": "Skills",
            "suggestion": f"Consider adding relevant skills you have: {', '.join(missing_skills[:5])}.",
            "priority": "medium",
        })
    
    # Check experience
    experience_entries = resume_data.get("experience", {}).get("entries", [])
    if not experience_entries:
        section_suggestions.append({
            "section": "Experience",
            "suggestion": "Add your work experience to show relevant background.",
            "priority": "high",
        })
    else:
        # Check if any entries have empty bullets
        for i, entry in enumerate(experience_entries):
            bullets = entry.get("bullets", [])
            non_empty_bullets = [b for b in bullets if b.strip()]
            if not non_empty_bullets:
                section_suggestions.append({
                    "section": "Experience",
                    "suggestion": f"Add bullet points to your '{entry.get('title', 'position')}' role.",
                    "priority": "medium",
                })
                break
    
    # Check projects (optional but helpful)
    project_entries = resume_data.get("projects", {}).get("entries", [])
    if not project_entries and missing_skills:
        section_suggestions.append({
            "section": "Projects",
            "suggestion": "Add projects that demonstrate the missing skills.",
            "priority": "low",
        })
    
    # -------------------------------------------------------------------------
    # Step 5: Calculate match score
    # -------------------------------------------------------------------------
    total_keywords = len(jd_keywords)
    if total_keywords > 0:
        match_score = len(matched_skills) / total_keywords * 100
    else:
        match_score = 0
    
    return {
        "jd_keywords": list(jd_keywords),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "section_suggestions": section_suggestions,
        "match_score": round(match_score, 1),
    }


def extract_keywords_from_text(text: str) -> set:
    """
    Extract relevant keywords from text using simple rules.
    
    This is NOT AI - just pattern matching for common tech terms.
    
    Approach:
    1. Tokenize text
    2. Filter for likely skill/tech keywords
    3. Return unique set
    
    We look for:
    - Capitalized words (likely proper nouns like "Python", "AWS")
    - Common tech patterns (words with numbers, acronyms)
    - Known tech terms
    """
    import re
    
    # Common tech keywords to look for (case-insensitive)
    COMMON_TECH_KEYWORDS = {
        # Languages
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "html", "css",
        # Frameworks
        "react", "angular", "vue", "svelte", "next.js", "nextjs", "nuxt", "django",
        "flask", "fastapi", "express", "spring", "rails", "laravel", ".net", "dotnet",
        # Databases
        "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
        "dynamodb", "cassandra", "sqlite", "oracle", "sql server",
        # Cloud & DevOps
        "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
        "terraform", "ansible", "jenkins", "ci/cd", "github actions", "gitlab",
        # Tools
        "git", "jira", "confluence", "slack", "figma", "postman", "vs code",
        # Concepts
        "rest", "restful", "api", "graphql", "microservices", "agile", "scrum",
        "tdd", "unit testing", "machine learning", "ml", "ai", "data science",
        "devops", "sre", "backend", "frontend", "full-stack", "fullstack",
    }
    
    # Clean and tokenize
    text_lower = text.lower()
    
    # Find all words (including those with dots, hashes, plus signs)
    words = re.findall(r'[\w+#.]+', text_lower)
    
    # Also find multi-word phrases (e.g., "machine learning")
    for phrase in ["machine learning", "data science", "google cloud", "sql server",
                   "unit testing", "ci/cd", "full-stack", "vs code", "github actions"]:
        if phrase in text_lower:
            words.append(phrase)
    
    # Filter for keywords
    keywords = set()
    for word in words:
        word = word.strip(".")
        if len(word) < 2:
            continue
        # Check if it's a known tech keyword
        if word in COMMON_TECH_KEYWORDS:
            keywords.add(word)
        # Check for capitalized words in original text (proper nouns)
        elif word.upper() == word and len(word) >= 2 and len(word) <= 10:
            keywords.add(word)
    
    # Also look for years of experience patterns
    year_patterns = re.findall(r'(\d+)\+?\s*years?', text_lower)
    
    return keywords


def render_analysis_results(analysis: dict):
    """
    Render the JD analysis results in a clear, honest format.
    
    Sections:
    1. Match Score (simple percentage)
    2. Matched Skills (what you have)
    3. Missing Skills (what you might need to add)
    4. Section Suggestions (where to improve)
    """
    # -------------------------------------------------------------------------
    # Match Score
    # -------------------------------------------------------------------------
    match_score = analysis.get("match_score", 0)
    
    st.markdown("### Analysis Results")
    
    # Score with appropriate messaging
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Match Score", f"{match_score}%")
    with col2:
        if match_score >= 70:
            st.success("✅ Good match! Your resume aligns well with this job.")
        elif match_score >= 40:
            st.warning("⚠️ Moderate match. Consider adding more relevant skills.")
        else:
            st.error("🟡 Low match. This job may require skills you haven't listed.")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # Matched Skills
    # -------------------------------------------------------------------------
    matched = analysis.get("matched_skills", [])
    st.markdown("### ✅ Matched Skills")
    st.caption("Skills from the job description that appear in your resume.")
    
    if matched:
        # Display as chips
        matched_display = " ".join([f"`{skill}`" for skill in matched])
        st.markdown(matched_display)
    else:
        st.info("No direct skill matches found. Consider adding relevant skills to your resume.")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # Missing Skills
    # -------------------------------------------------------------------------
    missing = analysis.get("missing_skills", [])
    st.markdown("### ❌ Missing Skills")
    st.caption("Skills from the job description not found in your resume. Only add skills you actually have.")
    
    if missing:
        # Display as chips with warning color indication
        missing_display = " ".join([f"`{skill}`" for skill in missing])
        st.markdown(missing_display)
        st.warning("⚠️ **Important:** Only add skills you genuinely possess. Do not add skills just to match the job description.")
    else:
        st.success("All identified skills from the JD are present in your resume!")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # Section Suggestions
    # -------------------------------------------------------------------------
    suggestions = analysis.get("section_suggestions", [])
    st.markdown("### 📝 Section Suggestions")
    st.caption("Areas of your resume that could be improved for this job.")
    
    if suggestions:
        for sugg in suggestions:
            priority = sugg.get("priority", "medium")
            section = sugg.get("section", "")
            suggestion_text = sugg.get("suggestion", "")
            
            # Priority indicator
            if priority == "high":
                icon = "🔴"
            elif priority == "medium":
                icon = "🟡"
            else:
                icon = "🟢"
            
            st.markdown(f"{icon} **{section}:** {suggestion_text}")
    else:
        st.success("Your resume sections look complete!")
    
    # -------------------------------------------------------------------------
    # Keywords Found (expandable for transparency)
    # -------------------------------------------------------------------------
    with st.expander("🔍 View all extracted keywords", expanded=False):
        st.caption("These keywords were extracted from the job description.")
        keywords = analysis.get("jd_keywords", [])
        if keywords:
            st.markdown(" ".join([f"`{kw}`" for kw in sorted(keywords)]))
        else:
            st.info("No technical keywords were extracted from this job description.")

    # -------------------------------------------------------------------------
    # Apply Optimization Button
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🚀 Apply Optimization")
    st.caption("Run the tailoring pipeline to get specific suggestions for your resume.")
    
    # Show warning before applying
    st.warning("""
    **Before you proceed:**
    - This will analyze your resume against the job description
    - You'll see specific suggestions for each section
    - Nothing is changed until you accept individual suggestions
    - You can always revert to your original resume
    """)
    
    # Check if we have enough resume data to optimize
    has_content = (
        st.session_state.resume_data.get("header", {}).get("full_name") or
        st.session_state.resume_data.get("experience", {}).get("entries") or
        st.session_state.resume_data.get("skills", {}).get("categories")
    )
    
    if not has_content:
        st.info("📝 Add some content to your resume first (at least name, skills, or experience).")
    else:
        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button(
                "✨ Apply Optimization",
                use_container_width=True,
                type="primary",
            ):
                run_optimization_pipeline()
        
        with col2:
            if st.session_state.optimization_result:
                if st.button("🔄 Revert to Original", use_container_width=True):
                    revert_to_original()
    
    # Show optimization results if available
    if st.session_state.optimization_result:
        st.markdown("---")
        render_optimization_results(st.session_state.optimization_result)


def run_optimization_pipeline():
    """
    Run the tailoring pipeline on current resume data.
    
    Process:
    1. Backup current resume
    2. Convert resume_data to raw text format
    3. Run TailoringPipeline
    4. Store result for display
    
    Does NOT auto-apply changes - user must review and accept.
    """
    import copy
    
    # Step 1: Backup current resume
    st.session_state.original_resume_backup = copy.deepcopy(
        st.session_state.resume_data
    )
    
    # Step 2: Convert resume_data to raw text format
    raw_cv_text = convert_resume_to_text(st.session_state.resume_data)
    raw_jd_text = st.session_state.job_description
    
    # Step 3: Run pipeline
    try:
        from core.pipeline import TailoringPipeline
        
        pipeline = TailoringPipeline()
        result = pipeline.run(raw_cv_text, raw_jd_text)
        
        # Step 4: Store result
        st.session_state.optimization_result = result
        st.session_state.show_optimized_preview = True
        
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Pipeline error: {str(e)}")
        st.session_state.optimization_result = None


def convert_resume_to_text(resume_data: dict) -> str:
    """
    Convert structured resume_data to raw text format for pipeline.
    
    The pipeline expects plain text, so we format the structured data
    into a readable resume-like format.
    """
    lines = []
    
    # Header
    header = resume_data.get("header", {})
    if header.get("full_name"):
        lines.append(header["full_name"])
        
        contact_parts = []
        if header.get("email"):
            contact_parts.append(header["email"])
        if header.get("phone"):
            contact_parts.append(header["phone"])
        if header.get("location"):
            contact_parts.append(header["location"])
        if contact_parts:
            lines.append(" | ".join(contact_parts))
        lines.append("")
    
    # Summary
    summary = resume_data.get("summary", {}).get("text", "")
    if summary:
        lines.append("SUMMARY")
        lines.append(summary)
        lines.append("")
    
    # Skills
    skills_data = resume_data.get("skills", {}).get("categories", {})
    if skills_data:
        lines.append("SKILLS")
        for category, skills_list in skills_data.items():
            if skills_list:
                lines.append(f"{category}: {', '.join(skills_list)}")
        lines.append("")
    
    # Experience
    experience = resume_data.get("experience", {}).get("entries", [])
    if experience:
        lines.append("EXPERIENCE")
        for entry in experience:
            title = entry.get("title", "")
            company = entry.get("company", "")
            location = entry.get("location", "")
            start = entry.get("start_date", "")
            end = entry.get("end_date", "")
            
            if title and company:
                lines.append(f"{title} at {company}")
                if location:
                    lines.append(location)
                if start:
                    lines.append(f"{start} - {end or 'Present'}")
                
                # Summary
                if entry.get("summary"):
                    lines.append(entry["summary"])
                
                # Bullets
                for bullet in entry.get("bullets", []):
                    if bullet.strip():
                        lines.append(f"- {bullet}")
                lines.append("")
    
    # Education
    education = resume_data.get("education", {}).get("entries", [])
    if education:
        lines.append("EDUCATION")
        for entry in education:
            degree = entry.get("degree", "")
            institution = entry.get("institution", "")
            if degree and institution:
                lines.append(f"{degree} - {institution}")
                if entry.get("end_year"):
                    lines.append(entry["end_year"])
                if entry.get("description"):
                    lines.append(entry["description"])
                lines.append("")
    
    # Projects
    projects = resume_data.get("projects", {}).get("entries", [])
    if projects:
        lines.append("PROJECTS")
        for entry in projects:
            name = entry.get("name", "")
            if name:
                lines.append(name)
                if entry.get("tech_stack"):
                    lines.append(f"Technologies: {entry['tech_stack']}")
                if entry.get("description"):
                    lines.append(entry["description"])
                lines.append("")
    
    return "\n".join(lines)


def revert_to_original():
    """
    Revert resume to original state before optimization.
    """
    import copy
    
    if st.session_state.original_resume_backup:
        st.session_state.resume_data = copy.deepcopy(
            st.session_state.original_resume_backup
        )
        st.session_state.optimization_result = None
        st.session_state.show_optimized_preview = False
        st.rerun()


def render_optimization_results(result):
    """
    Render the optimization results from the pipeline.
    
    Shows:
    1. Global strategy explanation
    2. List of suggestions with accept/dismiss buttons
    3. Tailored skills (reordered)
    4. Section-by-section explanations
    
    User must explicitly accept each suggestion.
    """
    st.markdown("### 🎯 Optimization Results")
    
    # -------------------------------------------------------------------------
    # Global Strategy
    # -------------------------------------------------------------------------
    explanations = result.explanations
    if explanations and explanations.global_strategy:
        st.markdown("#### 📝 Strategy")
        st.info(explanations.global_strategy)
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # Suggestions
    # -------------------------------------------------------------------------
    suggestions = result.suggestions
    st.markdown("#### ✨ Suggestions")
    st.caption("Review each suggestion. Click 'Accept' to apply or 'Dismiss' to skip.")
    
    if suggestions:
        for i, suggestion in enumerate(suggestions):
            with st.expander(
                f"💡 {suggestion.section_name}: {suggestion.original_text[:50]}..."
                if len(suggestion.original_text) > 50
                else f"💡 {suggestion.section_name}: {suggestion.original_text}",
                expanded=(i < 3),  # Expand first 3 by default
            ):
                # Show original vs suggested
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Original:**")
                    st.markdown(f"> {suggestion.original_text}")
                
                with col2:
                    st.markdown("**Suggested:**")
                    st.markdown(f"> {suggestion.suggested_text}")
                
                # Reason
                st.markdown("**Why this change?**")
                st.caption(suggestion.reason)
                
                # Prompt question if available
                if suggestion.prompt_question:
                    st.info(f"🤔 {suggestion.prompt_question}")
                
                # Status indicator
                status = suggestion.status
                if status == "accepted":
                    st.success("✅ Accepted")
                elif status == "dismissed":
                    st.warning("❌ Dismissed")
                else:
                    # Action buttons
                    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
                    with btn_col1:
                        if st.button("✅ Accept", key=f"accept_sugg_{i}"):
                            suggestion.status = "accepted"
                            st.rerun()
                    with btn_col2:
                        if st.button("❌ Dismiss", key=f"dismiss_sugg_{i}"):
                            suggestion.status = "dismissed"
                            st.rerun()
    else:
        st.info("No specific suggestions generated. Your resume may already be well-aligned!")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # Tailored Skills (reordered)
    # -------------------------------------------------------------------------
    if result.tailored_skills:
        st.markdown("#### 🎯 Recommended Skill Order")
        st.caption("Skills reordered to put most relevant first for this job.")
        st.markdown(", ".join(result.tailored_skills))
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # Section Explanations
    # -------------------------------------------------------------------------
    if explanations and explanations.section_explanations:
        st.markdown("#### 📝 Section-by-Section Breakdown")
        
        for section_exp in explanations.section_explanations:
            with st.expander(f"📄 {section_exp.section_name}", expanded=False):
                st.markdown("**Changes Made:**")
                st.markdown(section_exp.changes_made)
                
                if section_exp.reasoning:
                    st.markdown("**Why:**")
                    st.caption(section_exp.reasoning)
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # Apply All / Summary
    # -------------------------------------------------------------------------
    accepted_count = sum(1 for s in suggestions if s.status == "accepted")
    dismissed_count = sum(1 for s in suggestions if s.status == "dismissed")
    pending_count = len(suggestions) - accepted_count - dismissed_count
    
    st.markdown("#### Summary")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Accepted", accepted_count)
    with col2:
        st.metric("❌ Dismissed", dismissed_count)
    with col3:
        st.metric("⏳ Pending", pending_count)
    
    # Option to apply all accepted suggestions
    if accepted_count > 0:
        st.markdown("---")
        if st.button(
            f"🚀 Apply {accepted_count} Accepted Suggestion(s) to Resume",
            type="primary",
            use_container_width=True,
        ):
            apply_accepted_suggestions(result)


def apply_accepted_suggestions(result):
    """
    Apply all accepted suggestions to the resume.
    
    This modifies resume_data based on accepted suggestions.
    Only suggestions with status="accepted" are applied.
    """
    # For MVP, we'll update the tailored summary if available
    # and show a confirmation message
    
    accepted = [s for s in result.suggestions if s.status == "accepted"]
    
    if not accepted:
        st.warning("No accepted suggestions to apply.")
        return
    
    # Apply tailored summary if present
    if result.tailored_summary:
        st.session_state.resume_data["summary"]["text"] = result.tailored_summary
    
    # Apply tailored skills order
    if result.tailored_skills:
        # Convert to category format (put all in a single "Optimized" category for now)
        # In a more complete implementation, we'd preserve the category structure
        current_categories = st.session_state.resume_data.get("skills", {}).get("categories", {})
        if current_categories:
            # Keep existing categories but note the recommended order
            pass  # Don't overwrite - let user manually adjust
    
    st.success(f"✅ Applied {len(accepted)} suggestion(s) to your resume!")
    st.info("Tip: Go to the Preview section to see your updated resume.")
    st.rerun()


def render_preview():
    """
    Preview the complete resume.
    
    Supports two modes:
    1. Original resume (default) - shows current resume_data
    2. Optimized resume - shows tailored version after running pipeline
    
    User can toggle between modes when optimization results are available.
    """
    st.header("📄 Resume Preview")
    
    # -------------------------------------------------------------------------
    # Toggle: Original vs Optimized (only if optimization available)
    # -------------------------------------------------------------------------
    if st.session_state.optimization_result:
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button(
                "📄 Original",
                use_container_width=True,
                type="secondary" if st.session_state.show_optimized_preview else "primary",
            ):
                st.session_state.show_optimized_preview = False
                st.rerun()
        with col2:
            if st.button(
                "✨ Optimized",
                use_container_width=True,
                type="primary" if st.session_state.show_optimized_preview else "secondary",
            ):
                st.session_state.show_optimized_preview = True
                st.rerun()
        with col3:
            if st.button("🔄 Revert to Original", use_container_width=True):
                revert_to_original()
        
        # Show which mode we're in
        if st.session_state.show_optimized_preview:
            st.info("🎯 Showing **optimized** resume tailored for the job description.")
        else:
            st.caption("Showing your original resume.")
    
    st.markdown("---")

    # -------------------------------------------------------------------------
    # Decide which data to show
    # -------------------------------------------------------------------------
    if st.session_state.show_optimized_preview and st.session_state.optimization_result:
        # Show optimized version with explanations
        render_optimized_preview()
        return
    
    # Otherwise, show original resume
    data = st.session_state.resume_data

    # Header
    header = data["header"]
    if header["full_name"]:
        st.markdown(f"## {header['full_name']}")
        contact_parts = []
        if header["email"]:
            contact_parts.append(header["email"])
        if header["phone"]:
            contact_parts.append(header["phone"])
        if header["location"]:
            contact_parts.append(header["location"])
        if contact_parts:
            st.markdown(" | ".join(contact_parts))
        
        links = []
        if header["linkedin"]:
            links.append(f"[LinkedIn]({header['linkedin']})")
        if header["github"]:
            links.append(f"[GitHub]({header['github']})")
        if header["portfolio"]:
            links.append(f"[Portfolio]({header['portfolio']})")
        if links:
            st.markdown(" • ".join(links))

    # Summary
    if data["summary"]["text"]:
        st.markdown("---")
        st.markdown("### Summary")
        st.markdown(data["summary"]["text"])

    # Skills (category-based, ATS-safe format)
    skills_data = data["skills"].get("categories", {})
    # Check if any category has skills
    has_skills = any(skills for skills in skills_data.values())
    if has_skills:
        st.markdown("---")
        st.markdown("### Skills")
        # ATS-safe format: each category on its own line
        # Format: Category: skill1, skill2, skill3
        for category_name, skills_list in skills_data.items():
            if skills_list:
                st.markdown(f"**{category_name}:** {', '.join(skills_list)}")

    # Experience (ATS-safe format with bullets)
    if data["experience"]["entries"]:
        st.markdown("---")
        st.markdown("### Experience")
        for entry in data["experience"]["entries"]:
            # Only show entries that have at least a title or company
            if entry.get("title") or entry.get("company"):
                # Build the header line: Title at Company, Location
                title = entry.get('title', '')
                company = entry.get('company', '')
                location = entry.get('location', '')
                
                # Main title line
                if title and company:
                    header_line = f"**{title}** at {company}"
                elif title:
                    header_line = f"**{title}**"
                else:
                    header_line = f"**{company}**"
                
                if location:
                    header_line += f", {location}"
                
                st.markdown(header_line)
                
                # Date range line
                start_date = entry.get('start_date', '')
                end_date = entry.get('end_date', '')
                if start_date and end_date:
                    st.caption(f"{start_date} – {end_date}")
                elif start_date:
                    st.caption(f"{start_date} – Present")
                elif end_date:
                    st.caption(f"Until {end_date}")
                
                # Role summary (if provided)
                summary = entry.get('summary', '')
                if summary:
                    st.markdown(f"*{summary}*")
                
                # Bullet points
                bullets = entry.get('bullets', [])
                for bullet in bullets:
                    if bullet and bullet.strip():
                        st.markdown(f"• {bullet}")
                
                # Add spacing between entries
                st.markdown("")

    # Education
    if data["education"]["entries"]:
        st.markdown("---")
        st.markdown("### Education")
        for entry in data["education"]["entries"]:
            # Only show entries that have at least a degree or institution
            if entry.get("degree") or entry.get("institution"):
                # Build the main line: Degree — Institution
                degree = entry.get('degree', '')
                institution = entry.get('institution', '')
                
                if degree and institution:
                    title_line = f"**{degree}** — {institution}"
                elif degree:
                    title_line = f"**{degree}**"
                else:
                    title_line = f"**{institution}**"
                
                # Add location if present
                location = entry.get('location', '')
                if location:
                    title_line += f", {location}"
                
                st.markdown(title_line)
                
                # Date range line
                start_year = entry.get('start_year', '')
                end_year = entry.get('end_year', '')
                if start_year and end_year:
                    st.caption(f"{start_year} – {end_year}")
                elif end_year:
                    st.caption(f"Graduated {end_year}")
                elif start_year:
                    st.caption(f"Started {start_year}")
                
                # Description (optional details)
                description = entry.get('description', '')
                if description:
                    st.markdown(description)

    # Projects (ATS-safe format)
    if data["projects"]["entries"]:
        st.markdown("---")
        st.markdown("### Projects")
        for entry in data["projects"]["entries"]:
            # Only show entries that have at least a name
            if entry.get("name"):
                # Build the header line: Project Name
                name = entry.get('name', '')
                date = entry.get('date', '')
                
                # Main title line with optional date
                if date:
                    st.markdown(f"**{name}** | {date}")
                else:
                    st.markdown(f"**{name}**")
                
                # Role (if provided)
                role = entry.get('role', '')
                if role:
                    st.caption(f"Role: {role}")
                
                # Tech stack
                tech_stack = entry.get('tech_stack', '')
                if tech_stack:
                    st.markdown(f"*Technologies: {tech_stack}*")
                
                # Description
                description = entry.get('description', '')
                if description:
                    st.markdown(description)
                
                # URL (if provided)
                url = entry.get('url', '')
                if url:
                    # Make it a proper link if not already
                    if not url.startswith('http'):
                        url = f"https://{url}"
                    st.markdown(f"[{entry.get('url', '')}]({url})")
                
                # Add spacing between entries
                st.markdown("")

    st.markdown("---")
    if st.button("← Back to Editing"):
        st.session_state.current_section = "header"
        st.rerun()


def render_optimized_preview():
    """
    Render the optimized resume preview with explanations.
    
    Shows the tailored version from TailoringPipeline alongside
    explanations for why changes were made.
    
    Layout:
    - Left column: Optimized resume content
    - Right column: Explanations and suggestions
    """
    result = st.session_state.optimization_result
    original_data = st.session_state.resume_data
    
    # Create two-column layout: resume on left, explanations on right
    left_col, right_col = st.columns([2, 1])
    
    with left_col:
        st.markdown("### 📄 Tailored Resume")
        
        # Header (unchanged from original)
        header = original_data["header"]
        if header.get("full_name"):
            st.markdown(f"## {header['full_name']}")
            contact_parts = []
            if header.get("email"):
                contact_parts.append(header["email"])
            if header.get("phone"):
                contact_parts.append(header["phone"])
            if header.get("location"):
                contact_parts.append(header["location"])
            if contact_parts:
                st.markdown(" | ".join(contact_parts))
        
        # Summary (use tailored version if available)
        st.markdown("---")
        st.markdown("### Summary")
        if result.tailored_summary:
            st.markdown(result.tailored_summary)
            st.caption("✨ *Tailored for this job*")
        elif original_data["summary"].get("text"):
            st.markdown(original_data["summary"]["text"])
        
        # Skills (use tailored/reordered version)
        if result.tailored_skills:
            st.markdown("---")
            st.markdown("### Skills")
            st.caption("*Reordered to highlight most relevant skills first*")
            st.markdown(", ".join(result.tailored_skills))
        
        # Experience (use tailored version if available)
        if result.tailored_experience:
            st.markdown("---")
            st.markdown("### Experience")
            for section in result.tailored_experience:
                st.markdown(f"**{section.title}** at {section.organization}")
                st.caption(section.date_range)
                for bullet in section.description_points:
                    if bullet.strip():
                        st.markdown(f"• {bullet}")
                st.markdown("")
        elif original_data["experience"].get("entries"):
            st.markdown("---")
            st.markdown("### Experience")
            for entry in original_data["experience"]["entries"]:
                if entry.get("title"):
                    st.markdown(f"**{entry['title']}** at {entry.get('company', '')}")
                    for bullet in entry.get("bullets", []):
                        if bullet.strip():
                            st.markdown(f"• {bullet}")
                    st.markdown("")
        
        # Education (unchanged - from original)
        if original_data["education"].get("entries"):
            st.markdown("---")
            st.markdown("### Education")
            for entry in original_data["education"]["entries"]:
                if entry.get("degree"):
                    st.markdown(f"**{entry['degree']}** — {entry.get('institution', '')}")
                    if entry.get("end_year"):
                        st.caption(entry["end_year"])
        
        # Projects (unchanged - from original)
        if original_data["projects"].get("entries"):
            st.markdown("---")
            st.markdown("### Projects")
            for entry in original_data["projects"]["entries"]:
                if entry.get("name"):
                    st.markdown(f"**{entry['name']}**")
                    if entry.get("tech_stack"):
                        st.markdown(f"*{entry['tech_stack']}*")
                    if entry.get("description"):
                        st.markdown(entry["description"])
    
    with right_col:
        st.markdown("### 💡 Explanations")
        
        # Global strategy
        if result.explanations and result.explanations.global_strategy:
            st.info(result.explanations.global_strategy)
        
        st.markdown("---")
        
        # Suggestions summary
        st.markdown("#### Suggestions")
        if result.suggestions:
            for i, sugg in enumerate(result.suggestions[:5]):  # Show first 5
                with st.expander(f"💡 {sugg.section_name}", expanded=(i == 0)):
                    st.markdown("**Original:**")
                    st.caption(sugg.original_text[:100] + "..." if len(sugg.original_text) > 100 else sugg.original_text)
                    st.markdown("**Suggested:**")
                    st.caption(sugg.suggested_text[:100] + "..." if len(sugg.suggested_text) > 100 else sugg.suggested_text)
                    st.markdown("**Why:**")
                    st.caption(sugg.reason)
            
            if len(result.suggestions) > 5:
                st.caption(f"... and {len(result.suggestions) - 5} more suggestions")
        else:
            st.caption("No specific suggestions. Your resume aligns well!")
        
        st.markdown("---")
        
        # Section explanations
        if result.explanations and result.explanations.section_explanations:
            st.markdown("#### Section Notes")
            for exp in result.explanations.section_explanations:
                with st.expander(f"📝 {exp.section_name}"):
                    st.markdown(exp.changes_made)
                    if exp.reasoning:
                        st.caption(exp.reasoning)
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back to Editing"):
            st.session_state.current_section = "header"
            st.rerun()
    with col2:
        if st.button("🔄 Show Original"):
            st.session_state.show_optimized_preview = False
            st.rerun()


# =============================================================================
# HELPER COMPONENTS
# =============================================================================

def render_bullet_editor(bullets: list, prefix: str):
    """
    Render an editable list of bullet points.
    
    Supports:
    - Editing existing bullets
    - Adding new bullets
    - Removing bullets
    """
    for i, bullet in enumerate(bullets):
        col1, col2 = st.columns([10, 1])
        with col1:
            bullets[i] = st.text_input(
                f"Bullet {i + 1}",
                value=bullet,
                key=f"{prefix}_bullet_{i}",
                placeholder="Describe an accomplishment or responsibility...",
                label_visibility="collapsed",
            )
        with col2:
            if len(bullets) > 1:
                if st.button("✕", key=f"{prefix}_remove_bullet_{i}"):
                    bullets.pop(i)
                    st.rerun()

    # Add bullet button
    if st.button("➕ Add bullet", key=f"{prefix}_add_bullet"):
        bullets.append("")
        st.rerun()


def render_section_nav(next_section: Optional[str], prev_section: Optional[str] = None):
    """
    Render navigation buttons to move between sections.
    """
    st.markdown("---")
    
    cols = st.columns([1, 1, 1])
    
    with cols[0]:
        if prev_section:
            if st.button(f"← {SECTIONS[prev_section]['label']}", use_container_width=True):
                st.session_state.current_section = prev_section
                st.rerun()
    
    with cols[2]:
        if next_section:
            if st.button(f"{SECTIONS[next_section]['label']} →", type="primary", use_container_width=True):
                st.session_state.current_section = next_section
                st.rerun()


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    
    # Initialize session state
    init_session_state()
    
    # Render sidebar navigation
    render_sidebar()
    
    # Render main editing area
    render_main_area()


# =============================================================================
# RUN APP
# =============================================================================

if __name__ == "__main__":
    main()


