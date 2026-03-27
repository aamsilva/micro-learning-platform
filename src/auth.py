"""
Authentication Module for Micro Learning Platform

This module handles all authentication-related functionality:
- User registration and login
- Password hashing with bcrypt
- JWT token generation and validation
- User session management
- Role-based access control
"""

import re
from datetime import datetime, timedelta
from functools import wraps
import bcrypt
from flask import request, jsonify, g
from flask_jwt_extended import (
    create_access_token, 
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from src.models import db, User, UserActivity


class AuthError(Exception):
    """Custom authentication error."""
    def __init__(self, message, status_code=401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def validate_email(email):
    """
    Validate email format.
    
    Args:
        email: Email address to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """
    Validate password strength.
    
    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    
    Args:
        password: Password to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, None


def hash_password(password):
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
    
    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password, hashed):
    """
    Verify a password against its hash.
    
    Args:
        password: Plain text password
        hashed: Hashed password
    
    Returns:
        bool: True if password matches
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_user(email, username, password, full_name, role='student', avatar_url=None, bio=None):
    """
    Create a new user.
    
    Args:
        email: User's email address
        username: Username
        password: Plain text password
        full_name: User's full name
        role: User role (student, instructor, admin)
        avatar_url: Optional avatar URL
        bio: Optional bio
    
    Returns:
        User: Created user object
    
    Raises:
        AuthError: If validation fails or user exists
    """
    # Validate email
    if not validate_email(email):
        raise AuthError("Invalid email format")
    
    # Validate password
    is_valid, error = validate_password(password)
    if not is_valid:
        raise AuthError(error)
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        raise AuthError("Email already registered")
    
    if User.query.filter_by(username=username).first():
        raise AuthError("Username already taken")
    
    # Validate role
    valid_roles = ['student', 'instructor', 'admin']
    if role not in valid_roles:
        raise AuthError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")
    
    # Create user
    password_hash = hash_password(password)
    
    user = User(
        email=email,
        username=username,
        password_hash=password_hash,
        full_name=full_name,
        role=role,
        avatar_url=avatar_url,
        bio=bio
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Log activity
    log_activity(user.id, 'user_registered', {'email': email})
    
    return user


def authenticate_user(email, password):
    """
    Authenticate a user by email and password.
    
    Args:
        email: User's email address
        password: Plain text password
    
    Returns:
        tuple: (user, tokens) if successful
    
    Raises:
        AuthError: If authentication fails
    """
    # Find user
    user = User.query.filter_by(email=email).first()
    
    if not user:
        raise AuthError("Invalid email or password")
    
    if not user.is_active:
        raise AuthError("Account is deactivated")
    
    # Verify password
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    
    # Update last login
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Log activity
    log_activity(user.id, 'user_login', {'email': email})
    
    # Generate tokens
    tokens = generate_tokens(user)
    
    return user, tokens


def generate_tokens(user):
    """
    Generate JWT access and refresh tokens.
    
    Args:
        user: User object
    
    Returns:
        dict: Access and refresh tokens
    """
    # Create additional claims for JWT
    additional_claims = {
        'username': user.username,
        'role': user.role,
        'full_name': user.full_name
    }
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims=additional_claims,
        expires_delta=timedelta(hours=24)
    )
    
    refresh_token = create_refresh_token(
        identity=user.id,
        expires_delta=timedelta(days=30)
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 86400  # 24 hours in seconds
    }


def refresh_access_token(user_id):
    """
    Generate a new access token from a refresh token.
    
    Args:
        user_id: User ID
    
    Returns:
        dict: New access token
    """
    user = User.query.get(user_id)
    
    if not user or not user.is_active:
        raise AuthError("Invalid user")
    
    additional_claims = {
        'username': user.username,
        'role': user.role,
        'full_name': user.full_name
    }
    
    access_token = create_access_token(
        identity=user.id,
        additional_claims=additional_claims,
        expires_delta=timedelta(hours=24)
    )
    
    return {
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 86400
    }


def log_activity(user_id, activity_type, details=None, request_obj=None):
    """
    Log user activity.
    
    Args:
        user_id: User ID
        activity_type: Type of activity
        details: Additional details (dict)
        request_obj: Flask request object for IP/UA
    """
    ip_address = None
    user_agent = None
    
    if request_obj:
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
    
    activity = UserActivity(
        user_id=user_id,
        activity_type=activity_type,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    db.session.add(activity)
    db.session.commit()


def get_current_user():
    """
    Get current authenticated user.
    
    Returns:
        User: Current user or None
    """
    try:
        user_id = get_jwt_identity()
        return User.query.get(user_id)
    except Exception:
        return None


def require_role(*roles):
    """
    Decorator to require specific roles.
    
    Args:
        *roles: Required role names
    
    Returns:
        Decorator function
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = get_current_user()
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            
            if user.role not in roles and 'admin' not in roles:
                return jsonify({
                    'success': False,
                    'error': 'Insufficient permissions'
                }), 403
            
            g.current_user = user
            return fn(*args, **kwargs)
        
        return wrapper
    return decorator


def require_auth(fn):
    """
    Decorator to require authentication.
    
    Args:
        fn: Function to wrap
    
    Returns:
        Wrapped function
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = get_current_user()
        
        if not user:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
        
        g.current_user = user
        return fn(*args, **kwargs)
    
    return wrapper


def optional_auth(fn):
    """
    Decorator for optional authentication.
    
    Args:
        fn: Function to wrap
    
    Returns:
        Wrapped function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Try to get current user, but continue if not found
        try:
            user = get_current_user()
            g.current_user = user
        except Exception:
            g.current_user = None
        
        return fn(*args, **kwargs)
    
    return wrapper


def change_password(user_id, old_password, new_password):
    """
    Change user password.
    
    Args:
        user_id: User ID
        old_password: Current password
        new_password: New password
    
    Returns:
        bool: True if successful
    
    Raises:
        AuthError: If validation fails
    """
    user = User.query.get(user_id)
    
    if not user:
        raise AuthError("User not found")
    
    # Verify old password
    if not verify_password(old_password, user.password_hash):
        raise AuthError("Current password is incorrect")
    
    # Validate new password
    is_valid, error = validate_password(new_password)
    if not is_valid:
        raise AuthError(error)
    
    # Update password
    user.password_hash = hash_password(new_password)
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Log activity
    log_activity(user_id, 'password_changed', {})
    
    return True


def reset_password_request(email):
    """
    Request password reset.
    
    Args:
        email: User's email address
    
    Returns:
        dict: Reset token (in production, would send via email)
    """
    user = User.query.filter_by(email=email).first()
    
    # Always return success to prevent email enumeration
    if user:
        # In production, send reset email
        # For now, just log the request
        log_activity(user.id, 'password_reset_requested', {'email': email})
    
    return {
        'success': True,
        'message': 'If the email exists, a password reset link has been sent'
    }


def update_profile(user_id, **kwargs):
    """
    Update user profile.
    
    Args:
        user_id: User ID
        **kwargs: Fields to update
    
    Returns:
        User: Updated user object
    """
    user = User.query.get(user_id)
    
    if not user:
        raise AuthError("User not found")
    
    allowed_fields = ['full_name', 'avatar_url', 'bio']
    
    for field in allowed_fields:
        if field in kwargs:
            setattr(user, field, kwargs[field])
    
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_activity(user_id, 'profile_updated', {'fields': list(kwargs.keys())})
    
    return user


def deactivate_user(user_id):
    """
    Deactivate user account.
    
    Args:
        user_id: User ID
    
    Returns:
        bool: True if successful
    """
    user = User.query.get(user_id)
    
    if not user:
        raise AuthError("User not found")
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    db.session.commit()
    
    log_activity(user_id, 'account_deactivated', {})
    
    return True


def get_user_stats(user_id):
    """
    Get user statistics.
    
    Args:
        user_id: User ID
    
    Returns:
        dict: User statistics
    """
    from src.models import Enrollment, Progress, Certificate, QuizAttempt
    
    user = User.query.get(user_id)
    
    if not user:
        raise AuthError("User not found")
    
    # Get enrollment count
    enrolled_count = Enrollment.query.filter_by(user_id=user_id, is_active=True).count()
    
    # Get completed courses (courses with certificates)
    completed_count = Certificate.query.filter_by(user_id=user_id).count()
    
    # Get total progress
    total_progress = Progress.query.filter_by(
        user_id=user_id, 
        completed=True
    ).count()
    
    # Get quiz attempts
    quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
    quiz_count = len(quiz_attempts)
    avg_score = sum(a.score for a in quiz_attempts) / quiz_count if quiz_count > 0 else 0
    
    # Get certificates
    certificates = Certificate.query.filter_by(user_id=user_id).all()
    
    return {
        'user': user.to_dict(include_email=True),
        'stats': {
            'enrolled_courses': enrolled_count,
            'completed_courses': completed_count,
            'completed_lessons': total_progress,
            'quiz_attempts': quiz_count,
            'average_quiz_score': round(avg_score, 2),
            'certificates': len(certificates)
        }
    }


def blacklist_token(jti):
    """
    Blacklist a JWT token (for logout).
    
    Args:
        jti: JWT token ID
    
    Returns:
        bool: True if successful
    """
    # In production, store in Redis or database
    # For now, just acknowledge
    return True


def get_user_achievements(user_id):
    """
    Get user achievements.
    
    Args:
        user_id: User ID
    
    Returns:
        list: User achievements
    """
    from src.models import UserAchievement, Achievement
    from src.models import Enrollment, Progress, Certificate, QuizAttempt
    
    achievements = []
    
    # Check enrollment achievements
    enrolled_count = Enrollment.query.filter_by(user_id=user_id).count()
    
    if enrolled_count >= 1:
        achievements.append({
            'name': 'First Steps',
            'description': 'Enrolled in your first course',
            'icon': 'bookmark'
        })
    
    if enrolled_count >= 5:
        achievements.append({
            'name': 'Learner',
            'description': 'Enrolled in 5 courses',
            'icon': 'graduation-cap'
        })
    
    if enrolled_count >= 10:
        achievements.append({
            'name': 'Scholar',
            'description': 'Enrolled in 10 courses',
            'icon': 'trophy'
        })
    
    # Check completion achievements
    completed_count = Certificate.query.filter_by(user_id=user_id).count()
    
    if completed_count >= 1:
        achievements.append({
            'name': 'Graduate',
            'description': 'Completed first course',
            'icon': 'certificate'
        })
    
    if completed_count >= 5:
        achievements.append({
            'name': 'Master Graduate',
            'description': 'Completed 5 courses',
            'icon': 'medal'
        })
    
    # Check quiz achievements
    passed_quizzes = QuizAttempt.query.filter_by(
        user_id=user_id, 
        passed=True
    ).count()
    
    if passed_quizzes >= 10:
        achievements.append({
            'name': 'Quiz Master',
            'description': 'Passed 10 quizzes',
            'icon': 'star'
        })
    
    return achievements