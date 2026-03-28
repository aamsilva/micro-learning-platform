"""
Corporate Employee Portal Module
Simplified dashboard for employees to consume microlearning content
"""
from flask import Blueprint, render_template, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models import User, Course, Enrollment, Progress, Lesson, Quiz, Certificate
from src.models import db as _db

from datetime import datetime, timedelta

corporate_bp = Blueprint('corporate', __name__, url_prefix='/corporate')

@corporate_bp.route('/dashboard')
@jwt_required()
def employee_dashboard():
    """
    Employee Dashboard - Simplified view for corporate users
    Shows: Today's lesson, Progress, Recommended courses, Badges
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get enrolled courses
    enrollments = Enrollment.query.filter_by(user_id=user_id).all()
    enrolled_course_ids = [e.course_id for e in enrollments]
    enrolled_courses = Course.query.filter(Course.id.in_(enrolled_course_ids)).all()
    
    # Get progress stats
    completed_lessons = Progress.query.filter_by(
        user_id=user_id, 
        completed=True
    ).count()
    
    total_lessons = Lesson.query.join(Course).filter(
        Course.id.in_(enrolled_course_ids)
    ).count() if enrolled_course_ids else 0
    
    completion_percentage = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
    
    # Get certificates
    certificates = Certificate.query.filter_by(user_id=user_id).count()
    
    # Get next recommended lesson (first incomplete)
    next_lesson = None
    if enrollments:
        for enrollment in enrollments:
            next_incomplete = Progress.query.filter(
                Progress.user_id == user_id,
                Progress.course_id == enrollment.course_id,
                Progress.completed == False
            ).first()
            if next_incomplete:
                lesson = Lesson.query.get(next_incomplete.lesson_id)
                if lesson:
                    next_lesson = {
                        "id": lesson.id,
                        "title": lesson.title,
                        "course": Course.query.get(enrollment.course_id).title,
                        "duration": "5 min"
                    }
                    break
    
    # Weekly streak calculation (simplified)
    streak = calculate_streak(user_id)
    
    return jsonify({
        "success": True,
        "data": {
            "user": {
                "name": user.full_name,
                "email": user.email,
                "role": user.role
            },
            "stats": {
                "courses_enrolled": len(enrolled_courses),
                "lessons_completed": completed_lessons,
                "total_lessons": total_lessons,
                "completion_percentage": round(completion_percentage, 1),
                "certificates": certificates,
                "streak_days": streak
            },
            "next_lesson": next_lesson,
            "recent_courses": [
                {
                    "id": c.id,
                    "title": c.title,
                    "progress": get_course_progress(user_id, c.id)
                }
                for c in enrolled_courses[:3]
            ]
        }
    })

@corporate_bp.route('/daily-lesson')
@jwt_required()
def daily_lesson():
    """
    Get today's recommended micro-lesson (5 min or less)
    """
    user_id = get_jwt_identity()
    
    # Simple algorithm: get first incomplete lesson
    incomplete = Progress.query.filter(
        Progress.user_id == user_id,
        Progress.completed == False
    ).first()
    
    if incomplete:
        lesson = Lesson.query.get(incomplete.lesson_id)
        course = Course.query.get(incomplete.course_id)
        
        return jsonify({
            "success": True,
            "data": {
                "lesson": {
                    "id": lesson.id,
                    "title": lesson.title,
                    "content": lesson.content[:500],  # First 500 chars
                    "duration": "5 min",
                    "type": lesson.content_type
                },
                "course": {
                    "id": course.id,
                    "title": course.title
                }
            }
        })
    
    return jsonify({
        "success": True,
        "data": {
            "message": "All lessons completed! Check your certificates.",
            "completed": True
        }
    })

@corporate_bp.route('/complete-lesson', methods=['POST'])
@jwt_required()
def complete_lesson():
    """Mark a lesson as complete"""
    user_id = get_jwt_identity()
    data = request.get_json()
    lesson_id = data.get('lesson_id')
    
    if not lesson_id:
        return jsonify({"error": "lesson_id required"}), 400
    
    # Find or create progress
    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return jsonify({"error": "Lesson not found"}), 404
    
    progress = Progress.query.filter_by(
        user_id=user_id,
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = Progress(
            user_id=user_id,
            course_id=lesson.course_id,
            lesson_id=lesson_id,
            completed=True,
            completed_at=datetime.utcnow()
        )
        db.session.add(progress)
    else:
        progress.completed = True
        progress.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "message": "Lesson marked as complete!",
        "streak": calculate_streak(user_id)
    })

@corporate_bp.route('/recommendations')
@jwt_required()
def recommendations():
    """
    AI-powered course recommendations based on:
    - Role/department
    - Incomplete courses
    - Popular courses in organization
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Get enrolled course IDs
    enrolled_ids = [e.course_id for e in Enrollment.query.filter_by(user_id=user_id).all()]
    
    # Get recommended: not enrolled, published, sorted by enrollment count
    recommended = Course.query.filter(
        Course.is_published == True,
        ~Course.id.in_(enrolled_ids) if enrolled_ids else True
    ).order_by(Course.enrollment_count.desc()).limit(5).all()
    
    return jsonify({
        "success": True,
        "data": {
            "recommendations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "description": c.description[:150],
                    "difficulty": c.difficulty,
                    "duration_hours": c.duration_hours,
                    "reason": get_recommendation_reason(c, user)
                }
                for c in recommended
            ]
        }
    })

@corporate_bp.route('/certificates')
@jwt_required()
def my_certificates():
    """Get user's earned certificates"""
    user_id = get_jwt_identity()
    
    certs = Certificate.query.filter_by(user_id=user_id).all()
    
    return jsonify({
        "success": True,
        "data": {
            "certificates": [
                {
                    "id": c.id,
                    "course": Course.query.get(c.course_id).title,
                    "issued_at": c.issued_at.isoformat() if c.issued_at else None,
                    "certificate_number": c.certificate_number
                }
                for c in certs
            ]
        }
    })

@corporate_bp.route('/team-progress')
@jwt_required()
def team_progress():
    """
    For managers: See team progress (simplified)
    Note: In production, add proper permission checks
    """
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Simplified: just return all users progress
    users = User.query.filter(User.role == 'student').limit(20).all()
    
    team_data = []
    for u in users:
        enrollments = Enrollment.query.filter_by(user_id=u.id).count()
        completed = Progress.query.filter_by(user_id=u.id, completed=True).count()
        certs = Certificate.query.filter_by(user_id=u.id).count()
        
        team_data.append({
            "id": u.id,
            "name": u.full_name,
            "courses_enrolled": enrollments,
            "lessons_completed": completed,
            "certificates": certs
        })
    
    return jsonify({
        "success": True,
        "data": {
            "team": team_data,
            "total_members": len(team_data)
        }
    })

def calculate_streak(user_id):
    """Calculate user's learning streak in days"""
    # Simplified: count days with at least one lesson completed
    today = datetime.utcnow().date()
    streak = 0
    
    for i in range(30):  # Check last 30 days
        check_date = today - timedelta(days=i)
        completed = Progress.query.filter(
            Progress.user_id == user_id,
            Progress.completed == True
        ).filter(
            db.func.date(Progress.completed_at) == check_date
        ).count()
        
        if completed > 0:
            streak += 1
        elif i > 0:  # Allow missing today
            break
    
    return streak

def get_course_progress(user_id, course_id):
    """Get completion percentage for a course"""
    total = Lesson.query.filter_by(course_id=course_id).count()
    completed = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id,
        completed=True
    ).count()
    
    return round((completed / total * 100) if total > 0 else 0, 1)

def get_recommendation_reason(course, user):
    """Generate reason for recommendation"""
    reasons = []
    if course.difficulty == "Beginner":
        reasons.append("Good starting point")
    if course.enrollment_count > 10:
        reasons.append("Popular in your organization")
    if user.role == "student" and course.difficulty == "Advanced":
        reasons.append("Challenge yourself")
    
    return reasons[0] if reasons else "Recommended for you"