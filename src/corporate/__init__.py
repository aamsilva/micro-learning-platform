"""
Corporate Module
B2B-specific features for MicroLearn Pro
"""

from .employee_portal import corporate_bp
from .ai_recommendations import ai_bp
from .gamification import gamification_bp
from .hr_dashboard import hr_bp
from .social_learning import social_bp
from .ai_assistant import ai_assistant_bp

__all__ = ['corporate_bp', 'ai_bp', 'gamification_bp', 'hr_bp', 'social_bp', 'ai_assistant_bp']