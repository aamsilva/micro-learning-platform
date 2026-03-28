"""
HR Dashboard Module
For HR teams to manage corporate training and compliance
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models import User, Course, Enrollment, Progress, Certificate, Review
from src.models import db
from datetime import datetime, timedelta
from sqlalchemy import func

hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

@hr_bp.route('/dashboard')
@jwt_required()
def hr_dashboard():
    """HR Dashboard - Overview of organization's learning status"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Only HR and admins can access
    if user.role not in ['admin', 'instructor']:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get overall stats
    total_users = User.query.filter(User.role == 'student').count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    active_enrollments = Enrollment.query.filter(
        Enrollment.enrolled_at >= datetime.utcnow() - timedelta(days=30)
    ).count()
    
    # Completion stats
    completed = Progress.query.filter_by(completed=True).count()
    completion_rate = (completed / total_enrollments * 100) if total_enrollments > 0 else 0
    
    # Certificate stats
    total_certificates = Certificate.query.count()
    
    return jsonify({
        "success": True,
        "data": {
            "overview": {
                "total_employees": total_users,
                "total_courses": total_courses,
                "active_enrollments": active_enrollments,
                "completion_rate": round(completion_rate, 1),
                "certificates_issued": total_certificates
            },
            "period": "last_30_days"
        }
    })

@hr_bp.route('/employees')
@jwt_required()
def employee_list():
    """List all employees with their learning progress"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    users = User.query.filter(User.role == 'student').paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    employee_data = []
    for user in users.items:
        enrollments = Enrollment.query.filter_by(user_id=user.id).count()
        completed = Progress.query.filter_by(user_id=user.id, completed=True).count()
        certificates = Certificate.query.filter_by(user_id=user.id).count()
        
        # Calculate completion percentage
        if enrollments > 0:
            completion_pct = (completed / (enrollments * 6) * 100)  # Assume 6 lessons per course
        else:
            completion_pct = 0
        
        employee_data.append({
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "enrollments": enrollments,
            "lessons_completed": completed,
            "certificates": certificates,
            "completion_percentage": round(completion_pct, 1),
            "last_activity": get_last_activity(user.id)
        })
    
    return jsonify({
        "success": True,
        "data": {
            "employees": employee_data,
            "page": page,
            "per_page": per_page,
            "total": users.total,
            "pages": users.pages
        }
    })

@hr_bp.route('/compliance')
@jwt_required()
def compliance_report():
    """Compliance report - who has completed mandatory training"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if user.role not in ['admin', 'instructor']:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Get all courses
    courses = Course.query.all()
    
    compliance_data = []
    for course in courses:
        total_enrolled = Enrollment.query.filter_by(course_id=course.id).count()
        # In production, track actual completion per user
        completed = Progress.query.join(Enrollment).filter(
            Enrollment.course_id == course.id,
            Progress.completed == True
        ).count()
        
        compliance_pct = (completed / total_enrolled * 100) if total_enrolled > 0 else 0
        
        compliance_data.append({
            "course_id": course.id,
            "course_title": course.title,
            "required": course.is_published,
            "enrolled": total_enrolled,
            "completed": completed,
            "compliance_rate": round(compliance_pct, 1)
        })
    
    return jsonify({
        "success": True,
        "data": {
            "courses": compliance_data,
            "generated_at": datetime.utcnow().isoformat()
        }
    })

@hr_bp.route('/course-stats/<int:course_id>')
@jwt_required()
def course_stats(course_id):
    """Get detailed stats for a specific course"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({"error": "Course not found"}), 404
    
    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    total_enrolled = len(enrollments)
    
    # Calculate completion
    completed = 0
    in_progress = 0
    not_started = 0
    
    for enrollment in enrollments:
        lesson_progress = Progress.query.filter(
            Progress.user_id == enrollment.user_id,
            Progress.course_id == course_id,
            Progress.completed == True
        ).count()
        
        if lesson_progress > 0:
            in_progress += 1
        else:
            not_started += 1
        
        if lesson_progress >= 6:  # Assuming 6 lessons
            completed += 1
    
    # Get average rating
    reviews = Review.query.filter_by(course_id=course_id).all()
    avg_rating = sum([r.rating for r in reviews]) / len(reviews) if reviews else 0
    
    return jsonify({
        "success": True,
        "data": {
            "course": {
                "id": course.id,
                "title": course.title,
                "difficulty": course.difficulty
            },
            "enrollment": {
                "total": total_enrolled,
                "completed": completed,
                "in_progress": in_progress,
                "not_started": not_started
            },
            "completion_rate": round((completed / total_enrolled * 100) if total_enrolled > 0 else 0, 1),
            "average_rating": round(avg_rating, 1),
            "total_reviews": len(reviews)
        }
    })

@hr_bp.route('/reports')
@jwt_required()
def generate_report():
    """Generate various HR reports"""
    report_type = request.args.get('type', 'summary')
    
    if report_type == 'summary':
        # Summary report
        total_users = User.query.filter(User.role == 'student').count()
        total_enrollments = Enrollment.query.count()
        completed = Progress.query.filter_by(completed=True).count()
        
        return jsonify({
            "success": True,
            "data": {
                "type": "summary",
                "generated_at": datetime.utcnow().isoformat(),
                "metrics": {
                    "total_employees": total_users,
                    "total_enrollments": total_enrollments,
                    "completed_lessons": completed,
                    "completion_rate": round((completed / total_enrollments * 100) if total_enrollments > 0 else 0, 1)
                }
            }
        })
    
    elif report_type == 'engagement':
        # Engagement report
        active_users = User.query.filter(User.role == 'student').join(Progress).filter(
            Progress.completed_at >= datetime.utcnow() - timedelta(days=7)
        ).distinct().count()
        
        return jsonify({
            "success": True,
            "data": {
                "type": "engagement",
                "active_users_last_7_days": active_users,
                "engagement_rate": round((active_users / User.query.filter(User.role == 'student').count() * 100), 1)
            }
        })
    
    return jsonify({"error": "Invalid report type"}), 400

def get_last_activity(user_id):
    """Get user's last activity timestamp"""
    last_progress = Progress.query.filter_by(user_id=user_id).order_by(
        Progress.completed_at.desc()
    ).first()
    
    if last_progress and last_progress.completed_at:
        return last_progress.completed_at.isoformat()
    
    return None