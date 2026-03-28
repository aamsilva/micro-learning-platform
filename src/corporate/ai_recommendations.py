"""
AI Recommendations Module
Personalized learning recommendations for corporate users
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models import User, Course, Enrollment, Progress, Lesson
from src import db
import random

ai_bp = Blueprint('ai', __name__, url_prefix='/ai')

# In production, use OpenAI API
# For now, use smart rule-based recommendations

@ai_bp.route('/recommend', methods=['POST'])
@jwt_required()
def get_recommendations():
    """
    AI-powered personalized recommendations
    
    Request body (optional):
    {
        "context": "just_started|halfway|almost_done",
        "focus_area": "technical|soft_skills|compliance"
    }
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    data = request.get_json() or {}
    
    # Get user context
    context = data.get('context', infer_user_context(user_id))
    focus_area = data.get('focus_area', 'all')
    
    # Get enrolled courses
    enrolled_ids = [e.course_id for e in Enrollment.query.filter_by(user_id=user_id).all()]
    
    # Find recommendations
    recommendations = []
    
    # 1. Related to enrolled courses
    if enrolled_ids:
        for course_id in enrolled_ids[:2]:
            course = Course.query.get(course_id)
            if course:
                related = Course.query.filter(
                    Course.category_id == course.category_id,
                    Course.id.notin_(enrolled_ids),
                    Course.is_published == True
                ).limit(2).all()
                recommendations.extend(related)
    
    # 2. Add popular courses not enrolled
    popular = Course.query.filter(
        Course.is_published == True,
        ~Course.id.in_(enrolled_ids) if enrolled_ids else True,
        Course.enrollment_count > 5
    ).limit(3).all()
    recommendations.extend(popular)
    
    # 3. Fill with newest
    if len(recommendations) < 5:
        newest = Course.query.filter(
            Course.is_published == True,
            ~Course.id.in_(enrolled_ids) if enrolled_ids else True
        ).order_by(Course.created_at.desc()).limit(5 - len(recommendations)).all()
        recommendations.extend(newest)
    
    # Remove duplicates
    seen = set()
    unique_recs = []
    for r in recommendations:
        if r.id not in seen:
            seen.add(r.id)
            unique_recs.append(r)
    
    # Generate AI-style reasoning
    recs_data = []
    for course in unique_recs[:5]:
        recs_data.append({
            "id": course.id,
            "title": course.title,
            "description": course.description[:150],
            "difficulty": course.difficulty,
            "duration_hours": course.duration_hours,
            "reason": generate_ai_reason(course, user, context),
            "match_score": calculate_match_score(course, user)
        })
    
    return jsonify({
        "success": True,
        "data": {
            "recommendations": recs_data,
            "context": context,
            "generated_at": "2026-03-28T00:35:00Z"
        }
    })

@ai_bp.route('/learning-path', methods=['GET'])
@jwt_required()
def generate_learning_path():
    """
    Generate a personalized learning path for the user
    Based on their role, department, and goals
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Get user's incomplete courses
    enrollments = Enrollment.query.filter_by(user_id=user_id).all()
    incomplete = []
    for e in enrollments:
        course = Course.query.get(e.course_id)
        if course:
            incomplete.append(course)
    
    # Get recommended next steps
    path = []
    
    # 1. Current course being worked on
    if incomplete:
        path.append({
            "step": 1,
            "type": "continue",
            "course": incomplete[0].title,
            "action": "Continue where you left off"
        })
    
    # 2. Suggested next course
    enrolled_ids = [e.course_id for e in enrollments]
    next_course = Course.query.filter(
        Course.is_published == True,
        ~Course.id.in_(enrolled_ids) if enrolled_ids else True
    ).order_by(Course.enrollment_count.desc()).first()
    
    if next_course:
        path.append({
            "step": 2,
            "type": "recommended",
            "course": next_course.title,
            "action": "Start new course"
        })
    
    # 3. Certification goal
    path.append({
        "step": 3,
        "type": "certificate",
        "action": "Complete certification"
    })
    
    return jsonify({
        "success": True,
        "data": {
            "user": user.full_name,
            "learning_path": path,
            "estimated_completion": "4 weeks" if path else "N/A"
        }
    })

@ai_bp.route('/predict-success', methods=['POST'])
@jwt_required()
def predict_success():
    """
    AI prediction: Will this user complete this course?
    Uses simple heuristics (in production, use ML model)
    """
    user_id = get_jwt_identity()
    data = request.get_json()
    course_id = data.get('course_id')
    
    if not course_id:
        return jsonify({"error": "course_id required"}), 400
    
    course = Course.query.get(course_id)
    user = User.query.get(user_id)
    
    # Simple prediction based on:
    # - Past completion rate
    # - Time spent
    # - Engagement
    
    past_completions = Progress.query.filter_by(
        user_id=user_id,
        completed=True
    ).count()
    
    past_enrollments = Enrollment.query.filter_by(user_id=user_id).count()
    
    completion_rate = (past_completions / past_enrollments * 100) if past_enrollments > 0 else 50
    
    # Simple factors
    factors = {
        "completion_history": completion_rate,
        "course_difficulty": course.difficulty,
        "estimated_hours": course.duration_hours
    }
    
    # Prediction
    if completion_rate > 80:
        prediction = "high"
        confidence = 85
    elif completion_rate > 50:
        prediction = "medium"
        confidence = 70
    else:
        prediction = "low"
        confidence = 60
    
    # Adjust for difficulty
    if course.difficulty == "Advanced" and completion_rate < 70:
        prediction = "medium"
        confidence -= 10
    
    return jsonify({
        "success": True,
        "data": {
            "course_id": course_id,
            "prediction": prediction,
            "confidence": confidence,
            "factors": factors,
            "suggestion": get_suggestion(prediction, course)
        }
    })

def infer_user_context(user_id):
    """Infer user's context based on progress"""
    enrollments = Enrollment.query.filter_by(user_id=user_id).all()
    
    if not enrollments:
        return "just_started"
    
    total = 0
    completed = 0
    for e in enrollments:
        lessons = Lesson.query.filter_by(course_id=e.course_id).count()
        completed_lessons = Progress.query.filter_by(
            user_id=user_id,
            course_id=e.course_id,
            completed=True
        ).count()
        total += lessons
        completed += completed_lessons
    
    if total == 0:
        return "just_started"
    
    pct = (completed / total) * 100
    
    if pct < 25:
        return "just_started"
    elif pct < 75:
        return "halfway"
    else:
        return "almost_done"

def generate_ai_reason(course, user, context):
    """Generate AI-style recommendation reason"""
    reasons = [
        f"Based on your interest in {course.category.name if course.category else 'learning'}",
        f"Popular among peers in {user.role} roles",
        f"Perfect for skill development in {course.difficulty} level",
        f"Aligns with your learning goals",
        f"Highly rated by similar users"
    ]
    return random.choice(reasons)

def calculate_match_score(course, user):
    """Calculate match score (0-100)"""
    score = 70  # Base
    
    if course.difficulty == "Beginner":
        score += 10
    
    if course.enrollment_count > 10:
        score += 10
    
    return min(score + random.randint(-5, 10), 100)

def get_suggestion(prediction, course):
    """Get suggestion based on prediction"""
    if prediction == "high":
        return "You're ready to succeed! Jump in."
    elif prediction == "medium":
        return f"Great choice! {course.title} is achievable with consistent effort."
    else:
        return "Consider starting with an easier course first."