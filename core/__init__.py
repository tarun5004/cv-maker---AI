"""
Core module - Data models, pipeline, and constants.
"""

from .models import UserProfile, JobDescription, CVSection, TailoredCVResult
from .pipeline import TailoringPipeline
from .constants import SECTION_NAMES, SKILL_CATEGORIES

__all__ = [
    "UserProfile",
    "JobDescription",
    "CVSection",
    "TailoredCVResult",
    "TailoringPipeline",
    "SECTION_NAMES",
    "SKILL_CATEGORIES",
]
