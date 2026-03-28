"""
Social Learning Module
See what colleagues are learning, discussions, collaborative learning
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models import User, Course, Enrollment, Progress, Lesson
from src.models import db
from datetime import datetime, timedelta
from sqlalchemy import func

social_bp = Blueprint('social', __name__, url_prefix='/social')

@social_bp.route('/activity')
@jwt_required()
def colleagues_activity():
    """See what colleagues are learning right now"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Get recent activity from all users
    recent = db.session.query(
        Progress, User, Lesson, Course
    ).join(User).join(Lesson).join(Course).filter(
        Progress.completed == True
    ).order_by(Progress.completed_at.desc()).limit(20).all()
    
    activity = []
    for progress, u, lesson, course in recent:
        time_ago = get_time_ago(progress.completed_at)
        activity.append({
            "user": {
                "id": u.id,
                "name": u.full_name,
                "avatar": u.avatar_url
            },
            "action": "completed",
            "item": lesson.title,
            "course": course.title,
            "time_ago": time_ago
        })
    
    return jsonify({
        "success": True,
        "data": {
            "activity": activity,
            "your_recent_action": get_my_recent_action(user_id)
        }
    })

@social_bp.route('/same-course/<int:course_id>')
@jwt_required()
def users_in_course(course_id):
    """See who's taking the same course"""
    user_id = get_jwt_identity()
    course = Course.query.get(course_id)
    
    # Get all enrolled users
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    
    users_data = []
    for enrollment in enrollments:
        u = User.query.get(enrollment.user_id)
        
        # Get their progress
        completed = Progress.query.filter_by(
            user_id=u.id,
            course_id=course_id,
            completed=True
        ).count()
        
        total_lessons = Lesson.query.filter_by(course_id=course_id).count()
        pct = (completed / total_lessons * 100) if total_lessons > 0 else 0
        
        users_data.append({
            "user": {
                "id": u.id,
                "name": u.full_name,
                "avatar": u.avatar_url,
                "is_me": u.id == user_id
            },
            "progress": completed,
            "total": total_lessons,
            "percentage": round(pct, 1),
            "status": "completed" if pct >= 100 else "in_progress" if pct > 0 else "not_started",
            "last_activity": get_user_last_activity(u.id, course_id)
        })
    
    # Sort by progress
    users_data.sort(key=lambda x: x["percentage"], reverse=True)
    
    return jsonify({
        "success": True,
        "data": {
            "course": course.title,
            "users": users_data,
            "total_enrolled": len(users_data)
        }
    })

@social_bp.route('/suggest-colleagues')
@jwt_required()
def suggest_colleagues():
    """Find colleagues with similar learning paths"""
    user_id = get_jwt_identity()
    
    # Get courses user is taking
    my_courses = [e.course_id for e in Enrollment.query.filter_by(user_id=user_id).all()]
    
    if not my_courses:
        return jsonify({"success": True, "data": {"suggestions": []}})
    
    # Find users with overlapping courses
    suggestions = db.session.query(
        User, func.count(Enrollment.course_id).label('common')
    ).join(Enrollment).filter(
        Enrollment.course_id.in_(my_courses),
        Enrollment.user_id != user_id
    ).group_by(User.id).order_by(func.count(Enrollment.course_id).desc()).limit(5).all()
    
    result = []
    for u, common_count in suggestions:
        # Get their enrolled courses
        their_courses = [e.course_id for e in Enrollment.query.filter_by(user_id=u.id).all()]
        new_courses = set(their_courses) - set(my_courses)
        
        result.append({
            "user": {
                "id": u.id,
                "name": u.full_name,
                "avatar": u.avatar_url
            },
            "common_courses": common_count,
            "new_suggestions": list(new_courses)[:3]
        })
    
    return jsonify({
        "success": True,
        "data": {
            "suggestions": result
        }
    })

@social_bp.route('/learning-teams')
@jwt_required()
def learning_teams():
    """Show learning teams/groups"""
    user_id = get_jwt_identity()
    
    # For now, create dynamic teams based on courses
    courses = Course.query.filter(Course.is_published == True).limit(6).all()
    
    teams = []
    for course in courses:
        enrollments = Enrollment.query.filter_by(course_id=course.id).count()
        
        if enrollments > 0:
            teams.append({
                "id": course.id,
                "name": course.title,
                "members": enrollments,
                "focus": "Course Group"
            })
    
    return jsonify({
        "success": True,
        "data": {
            "teams": teams
        }
    })

@social_bp.route('/feed')
@jwt_required()
def learning_feed():
    """Personalized learning feed - like a social feed"""
    user_id = get_jwt_identity()
    
    # Get my courses
    my_courses = [e.course_id for e in Enrollment.query.filter_by(user_id=user_id).all()]
    
    feed = []
    
    # 1. New courses from colleagues
    if my_courses:
        colleague_activity = db.session.query(
            Progress, User, Course
        ).join(User).join(Course).filter(
            Course.id.in_(my_courses),
            Progress.user_id != user_id,
            Progress.completed_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(Progress.completed_at.desc()).limit(5).all()
        
        for progress, u, course in colleague_activity:
            feed.append({
                "type": "colleague_progress",
                "user": u.full_name,
                "course": course.title,
                "time": get_time_ago(progress.completed_at)
            })
    
    # 2. New courses available
    new_courses = Course.query.filter(
        Course.is_published == True
    ).order_by(Course.created_at.desc()).limit(3).all()
    
    for course in new_courses:
        feed.append({
            "type": "new_course",
            "course": course.title,
            "difficulty": course.difficulty
        })
    
    # 3. Popular in org
    popular = Course.query.order_by(Course.enrollment_count.desc()).limit(2).all()
    for course in popular:
        feed.append({
            "type": "popular",
            "course": course.title,
            "enrolled": course.enrollment_count
        })
    
    return jsonify({
        "success": True,
        "data": {
            "feed": feed[:10]
        }
    })

def get_time_ago(dt):
    """Get human-readable time ago"""
    if not dt:
        return "unknown"
    
    diff = datetime.utcnow() - dt
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        return f"{int(seconds/60)}m ago"
    elif seconds < 86400:
        return f"{int(seconds/3600)}h ago"
    else:
        return f"{int(seconds/86400)}d ago"

def get_my_recent_action(user_id):
    """Get user's most recent action"""
    recent = Progress.query.filter_by(user_id=user_id).order_by(
        Progress.completed_at.desc()
    ).first()
    
    if recent:
        lesson = Lesson.query.get(recent.lesson_id)
        course = Course.query.get(recent.course_id)
        return {
            "lesson": lesson.title if lesson else None,
            "course": course.title if course else None,
            "time": get_time_ago(recent.completed_at)
        }
    
    return None

def get_user_last_activity(user_id, course_id):
    """Get user's last activity in a course"""
    recent = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).order_by(Progress.completed_at.desc()).first()
    
    if recent and recent.completed_at:
        return get_time_ago(recent.completed_at)
    
    return "Not started"