"""
Corporate Module
B2B-specific features for MicroLearn Pro
"""

from .employee_portal import corporate_bp
from .ai_recommendations import ai_bp

__all__ = ['corporate_bp', 'ai_bp']