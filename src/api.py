"""
REST API Module for Micro Learning Platform

This module provides all RESTful API endpoints:
- Authentication endpoints
- Course endpoints
- Lesson endpoints
- Quiz endpoints
- Analytics endpoints
- Search endpoints
"""

from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from src.models import db, User, Course, Lesson, Quiz, QuizAttempt, Progress, Certificate, Review, Category, Tag
from src.auth import (
    create_user, authenticate_user, generate_tokens, refresh_access_token,
    get_current_user, require_role, log_activity, change_password,
    update_profile, get_user_stats, get_user_achievements
)
from src.courses import (
    create_course, update_course, delete_course, get_course, list_courses,
    enroll_course, unenroll_course, get_user_enrollments,
    create_lesson, update_lesson, delete_lesson, get_lesson, get_course_lessons,
    mark_lesson_complete, update_progress, get_user_progress, get_user_certificates,
    add_review, get_course_reviews, create_category, list_categories, get_category,
    search_courses, get_featured_courses, get_popular_courses, get_recommended_courses
)
from src.analytics import (
    get_user_analytics, get_course_analytics, get_dashboard_data,
    get_learning_streak, get_achievements
)
from src.quiz import (
    get_quiz, submit_quiz, get_quiz_results, retry_quiz
)

# Create API blueprint
api_bp = Blueprint('api', __name__)


def success_response(data=None, message=None, status=200):
    """Helper for success responses."""
    response = {'success': True}
    if message:
        response['message'] = message
    if data is not None:
        response['data'] = data
    return jsonify(response), status


def error_response(message, status=400, error_code=None):
    """Helper for error responses."""
    response = {'success': False, 'error': message}
    if error_code:
        response['error_code'] = error_code
    return jsonify(response), status


# ==================== Authentication Endpoints ====================

@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    required = ['email', 'username', 'password', 'full_name']
    for field in required:
        if field not in data:
            return error_response(f"Missing required field: {field}")
    
    try:
        user = create_user(
            email=data['email'],
            username=data['username'],
            password=data['password'],
            full_name=data['full_name'],
            role=data.get('role', 'student'),
            avatar_url=data.get('avatar_url'),
            bio=data.get('bio')
        )
        
        tokens = generate_tokens(user)
        
        return success_response({
            'user': user.to_dict(include_email=True),
            'tokens': tokens
        }, 'Registration successful', 201)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Login user."""
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return error_response("Email and password required")
    
    try:
        user, tokens = authenticate_user(data['email'], data['password'])
        
        return success_response({
            'user': user.to_dict(include_email=True),
            'tokens': tokens
        }, 'Login successful')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token."""
    user_id = get_jwt_identity()
    
    try:
        tokens = refresh_access_token(user_id)
        return success_response(tokens)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user."""
    # In production, blacklist the token
    return success_response(message='Logout successful')


@api_bp.route('/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    user = get_current_user()
    
    if not user:
        return error_response("User not found", 404)
    
    return success_response(user.to_dict(include_email=True))


@api_bp.route('/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile_endpoint():
    """Update user profile."""
    user = get_current_user()
    data = request.get_json()
    
    try:
        user = update_profile(user.id, **data)
        return success_response(user.to_dict(include_email=True), 'Profile updated')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/auth/change-password', methods=['POST'])
@jwt_required()
def change_password_endpoint():
    """Change user password."""
    user = get_current_user()
    data = request.get_json()
    
    if not data.get('old_password') or not data.get('new_password'):
        return error_response("Old and new password required")
    
    try:
        change_password(user.id, data['old_password'], data['new_password'])
        return success_response(message='Password changed successfully')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/auth/stats', methods=['GET'])
@jwt_required()
def get_stats():
    """Get user statistics."""
    user = get_current_user()
    
    try:
        stats = get_user_stats(user.id)
        return success_response(stats)
    
    except Exception as e:
        return error_response(str(e))


# ==================== Course Endpoints ====================

@api_bp.route('/courses', methods=['GET'])
def get_courses():
    """Get list of courses."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    category_id = request.args.get('category_id', type=int)
    difficulty = request.args.get('difficulty')
    search = request.args.get('search')
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    try:
        result = list_courses(
            page=page,
            per_page=per_page,
            category_id=category_id,
            difficulty=difficulty,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        return success_response(result)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses', methods=['POST'])
@jwt_required()
def create_course_endpoint():
    """Create a new course."""
    user = get_current_user()
    data = request.get_json()
    
    if not user.is_instructor:
        return error_response("Only instructors can create courses", 403)
    
    required = ['title', 'description']
    for field in required:
        if field not in data:
            return error_response(f"Missing required field: {field}")
    
    try:
        course = create_course(
            title=data['title'],
            description=data['description'],
            instructor_id=user.id,
            category_id=data.get('category_id'),
            difficulty=data.get('difficulty', 'beginner'),
            price=data.get('price', 0.0),
            thumbnail_url=data.get('thumbnail_url'),
            tags=data.get('tags')
        )
        
        return success_response(course.to_dict(), 'Course created', 201)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/<int:course_id>', methods=['GET'])
def get_course_endpoint(course_id):
    """Get course details."""
    include_details = request.args.get('include_details', 'false').lower() == 'true'
    
    try:
        course = get_course(course_id, include_details=include_details)
        return success_response(course)
    
    except Exception as e:
        return error_response(str(e), 404)


@api_bp.route('/courses/<int:course_id>', methods=['PUT'])
@jwt_required()
def update_course_endpoint(course_id):
    """Update a course."""
    user = get_current_user()
    data = request.get_json()
    
    try:
        course = update_course(course_id, user.id, **data)
        return success_response(course.to_dict(), 'Course updated')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/<int:course_id>', methods=['DELETE'])
@jwt_required()
def delete_course_endpoint(course_id):
    """Delete a course."""
    user = get_current_user()
    
    try:
        delete_course(course_id, user.id)
        return success_response(message='Course deleted')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/<int:course_id>/enroll', methods=['POST'])
@jwt_required()
def enroll_endpoint(course_id):
    """Enroll in a course."""
    user = get_current_user()
    
    try:
        enrollment = enroll_course(course_id, user.id)
        return success_response(enrollment.to_dict(), 'Enrolled successfully')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/<int:course_id>/unenroll', methods=['POST'])
@jwt_required()
def unenroll_endpoint(course_id):
    """Unenroll from a course."""
    user = get_current_user()
    
    try:
        unenroll_course(course_id, user.id)
        return success_response(message='Unenrolled successfully')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/<int:course_id>/lessons', methods=['GET'])
@jwt_required()
def get_lessons_endpoint(course_id):
    """Get course lessons."""
    user = get_current_user()
    
    try:
        lessons = get_course_lessons(course_id, user.id)
        return success_response(lessons)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/<int:course_id>/reviews', methods=['GET'])
def get_reviews_endpoint(course_id):
    """Get course reviews."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    try:
        result = get_course_reviews(course_id, page, per_page)
        return success_response(result)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/<int:course_id>/reviews', methods=['POST'])
@jwt_required()
def add_review_endpoint(course_id):
    """Add course review."""
    user = get_current_user()
    data = request.get_json()
    
    if 'rating' not in data:
        return error_response("Rating required")
    
    try:
        review = add_review(course_id, user.id, data['rating'], data.get('comment'))
        return success_response(review.to_dict(), 'Review added')
    
    except Exception as e:
        return error_response(str(e))


# ==================== Lesson Endpoints ====================

@api_bp.route('/lessons/<int:lesson_id>', methods=['GET'])
@jwt_required()
def get_lesson_endpoint(lesson_id):
    """Get lesson content."""
    user = get_current_user()
    
    try:
        lesson = get_lesson(lesson_id, include_content=True)
        
        # Check enrollment
        from src.models import Enrollment
        enrollment = Enrollment.query.filter_by(
            user_id=user.id,
            course_id=lesson['course_id'],
            is_active=True
        ).first()
        
        if not enrollment:
            return error_response("Not enrolled in this course", 403)
        
        return success_response(lesson)
    
    except Exception as e:
        return error_response(str(e), 404)


@api_bp.route('/lessons/<int:lesson_id>/complete', methods=['POST'])
@jwt_required()
def complete_lesson_endpoint(lesson_id):
    """Mark lesson as complete."""
    user = get_current_user()
    data = request.get_json() or {}
    
    try:
        progress = mark_lesson_complete(
            lesson_id, 
            user.id, 
            data.get('time_spent', 0)
        )
        return success_response(progress.to_dict(), 'Lesson completed')
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/lessons/<int:lesson_id>/progress', methods=['PUT'])
@jwt_required()
def update_lesson_progress_endpoint(lesson_id):
    """Update lesson progress."""
    user = get_current_user()
    data = request.get_json()
    
    if not data or 'time_spent' not in data:
        return error_response("Time spent required")
    
    try:
        update_progress(lesson_id, user.id, data['time_spent'])
        return success_response(message='Progress updated')
    
    except Exception as e:
        return error_response(str(e))


# ==================== Quiz Endpoints ====================

@api_bp.route('/lessons/<int:lesson_id>/quiz', methods=['GET'])
@jwt_required()
def get_lesson_quiz(lesson_id):
    """Get lesson quiz."""
    user = get_current_user()
    
    try:
        quiz = get_quiz(lesson_id)
        return success_response(quiz)
    
    except Exception as e:
        return error_response(str(e), 404)


@api_bp.route('/quizzes/<int:quiz_id>/submit', methods=['POST'])
@jwt_required()
def submit_quiz_endpoint(quiz_id):
    """Submit quiz answers."""
    user = get_current_user()
    data = request.get_json()
    
    if not data or 'answers' not in data:
        return error_response("Answers required")
    
    try:
        result = submit_quiz(quiz_id, user.id, data['answers'])
        return success_response(result)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/quizzes/<int:quiz_id>/results', methods=['GET'])
@jwt_required()
def get_quiz_results_endpoint(quiz_id):
    """Get quiz results."""
    user = get_current_user()
    
    try:
        results = get_quiz_results(quiz_id, user.id)
        return success_response(results)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/quizzes/<int:quiz_id>/retry', methods=['POST'])
@jwt_required()
def retry_quiz_endpoint(quiz_id):
    """Retry quiz."""
    user = get_current_user()
    
    try:
        result = retry_quiz(quiz_id, user.id)
        return success_response(result)
    
    except Exception as e:
        return error_response(str(e))


# ==================== User Endpoints ====================

@api_bp.route('/users/enrollments', methods=['GET'])
@jwt_required()
def get_enrollments():
    """Get user enrollments."""
    user = get_current_user()
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    try:
        enrollments = get_user_enrollments(user.id, active_only)
        return success_response(enrollments)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/users/certificates', methods=['GET'])
@jwt_required()
def get_certificates():
    """Get user certificates."""
    user = get_current_user()
    
    try:
        certificates = get_user_certificates(user.id)
        return success_response(certificates)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/users/progress/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course_progress(course_id):
    """Get user progress for a course."""
    user = get_current_user()
    
    try:
        progress = get_user_progress(user.id, course_id)
        return success_response(progress)
    
    except Exception as e:
        return error_response(str(e))


# ==================== Analytics Endpoints ====================

@api_bp.route('/analytics/overview', methods=['GET'])
@jwt_required()
def get_analytics_overview():
    """Get user analytics overview."""
    user = get_current_user()
    
    try:
        analytics = get_user_analytics(user.id)
        return success_response(analytics)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/analytics/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    """Get dashboard data."""
    user = get_current_user()
    
    try:
        dashboard = get_dashboard_data(user.id)
        return success_response(dashboard)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/analytics/streak', methods=['GET'])
@jwt_required()
def get_streak():
    """Get learning streak."""
    user = get_current_user()
    
    try:
        streak = get_learning_streak(user.id)
        return success_response(streak)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/analytics/achievements', methods=['GET'])
@jwt_required()
def get_achievements_endpoint():
    """Get user achievements."""
    user = get_current_user()
    
    try:
        achievements = get_achievements(user.id)
        return success_response(achievements)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/analytics/course/<int:course_id>', methods=['GET'])
@jwt_required()
def get_course_analytics_endpoint(course_id):
    """Get course analytics (instructor only)."""
    user = get_current_user()
    
    if not user.is_instructor:
        return error_response("Only instructors can view course analytics", 403)
    
    try:
        analytics = get_course_analytics(course_id, user.id)
        return success_response(analytics)
    
    except Exception as e:
        return error_response(str(e))


# ==================== Search & Browse Endpoints ====================

@api_bp.route('/search', methods=['GET'])
def search():
    """Search courses."""
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Parse filters
    filters = {
        'category_id': request.args.get('category_id', type=int),
        'difficulty': request.args.get('difficulty'),
        'min_price': request.args.get('min_price', type=float),
        'max_price': request.args.get('max_price', type=float),
        'sort_by': request.args.get('sort_by'),
        'sort_order': request.args.get('sort_order', 'desc')
    }
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    try:
        result = search_courses(query, filters, page, per_page)
        return success_response(result)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/featured', methods=['GET'])
def get_featured():
    """Get featured courses."""
    limit = request.args.get('limit', 6, type=int)
    
    try:
        courses = get_featured_courses(limit)
        return success_response(courses)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/popular', methods=['GET'])
def get_popular():
    """Get popular courses."""
    limit = request.args.get('limit', 6, type=int)
    
    try:
        courses = get_popular_courses(limit)
        return success_response(courses)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/courses/recommended', methods=['GET'])
@jwt_required()
def get_recommended():
    """Get recommended courses."""
    user = get_current_user()
    limit = request.args.get('limit', 6, type=int)
    
    try:
        courses = get_recommended_courses(user.id, limit)
        return success_response(courses)
    
    except Exception as e:
        return error_response(str(e))


# ==================== Category Endpoints ====================

@api_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all categories."""
    try:
        categories = list_categories()
        return success_response(categories)
    
    except Exception as e:
        return error_response(str(e))


@api_bp.route('/categories/<int:category_id>', methods=['GET'])
def get_category_endpoint(category_id):
    """Get category details."""
    try:
        category = get_category(category_id)
        return success_response(category)
    
    except Exception as e:
        return error_response(str(e), 404)


@api_bp.route('/categories', methods=['POST'])
@jwt_required()
def create_category_endpoint():
    """Create category (admin only)."""
    user = get_current_user()
    
    if not user.is_admin:
        return error_response("Admin only", 403)
    
    data = request.get_json()
    
    if not data or 'name' not in data:
        return error_response("Category name required")
    
    try:
        category = create_category(
            name=data['name'],
            description=data.get('description'),
            icon=data.get('icon', 'book')
        )
        return success_response(category.to_dict(), 'Category created', 201)
    
    except Exception as e:
        return error_response(str(e))


# ==================== Health Check ====================

@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return success_response({
        'status': 'healthy',
        'version': '1.0.0'
    })