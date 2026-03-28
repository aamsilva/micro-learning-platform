"""
Gamification Module
Badges, points, leaderboards, and engagement for corporate learning
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models import User, Course, Enrollment, Progress, Certificate, Achievement, UserAchievement
from src import db
from datetime import datetime, timedelta

gamification_bp = Blueprint('gamification', __name__, url_prefix='/gamification')

# Achievement definitions
ACHIEVEMENTS = {
    "first_lesson": {"name": "First Step", "points": 10, "description": "Complete your first lesson"},
    "daily_streak_3": {"name": "Getting Started", "points": 25, "description": "3 day learning streak"},
    "daily_streak_7": {"name": "Week Warrior", "points": 50, "description": "7 day learning streak"},
    "daily_streak_30": {"name": "Monthly Master", "points": 200, "description": "30 day learning streak"},
    "course_complete_1": {"name": "Course Completer", "points": 100, "description": "Complete your first course"},
    "course_complete_5": {"name": "Dedicated Learner", "points": 250, "description": "Complete 5 courses"},
    "lesson_milestone_10": {"name": "Quick Learner", "points": 50, "description": "Complete 10 lessons"},
    "lesson_milestone_50": {"name": "Knowledge Seeker", "points": 150, "description": "Complete 50 lessons"},
    "lesson_milestone_100": {"name": "Scholar", "points": 300, "description": "Complete 100 lessons"},
    "certificate_earned": {"name": "Certified", "points": 75, "description": "Earn your first certificate"},
    "perfect_quiz": {"name": "Perfect Score", "points": 30, "description": "Get 100% on a quiz"},
    "team_player": {"name": "Team Player", "points": 40, "description": "Help a colleague (future)"},
    "early_bird": {"name": "Early Bird", "points": 20, "description": "Complete a lesson before 8am"},
    "night_owl": {"name": "Night Owl", "points": 20, "description": "Complete a lesson after 8pm"},
}

@gamification_bp.route('/profile')
@jwt_required()
def user_profile():
    """Get user's gamification profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    # Calculate stats
    completed_lessons = Progress.query.filter_by(user_id=user_id, completed=True).count()
    completed_courses = Certificate.query.filter_by(user_id=user_id).count()
    certificates = Certificate.query.filter_by(user_id=user_id).count()
    
    # Calculate points
    total_points = completed_lessons * 5 + completed_courses * 100 + certificates * 75
    
    # Get achievements
    user_achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    earned_achievements = [ua.achievement_key for ua in user_achievements]
    
    # Get next achievements
    next_achievements = []
    for key, achievement in ACHIEVEMENTS.items():
        if key not in earned_achievements:
            next_achievements.append({
                "key": key,
                "name": achievement["name"],
                "points": achievement["points"],
                "description": achievement["description"]
            })
    
    return jsonify({
        "success": True,
        "data": {
            "user": {
                "id": user.id,
                "name": user.full_name,
                "avatar": user.avatar_url
            },
            "stats": {
                "total_points": total_points,
                "lessons_completed": completed_lessons,
                "courses_completed": completed_courses,
                "certificates": certificates
            },
            "level": calculate_level(total_points),
            "achievements": {
                "earned": earned_achievements,
                "next": next_achievements[:5]
            }
        }
    })

@gamification_bp.route('/leaderboard')
@jwt_required()
def leaderboard():
    """Get organization leaderboard"""
    limit = request.args.get('limit', 10, type=int)
    
    # Get all users with points
    users = User.query.filter(User.role == 'student').all()
    
    leaderboard_data = []
    for user in users:
        completed = Progress.query.filter_by(user_id=user.id, completed=True).count()
        certificates = Certificate.query.filter_by(user_id=user.id).count()
        points = completed * 5 + certificates * 100
        
        leaderboard_data.append({
            "rank": 0,  # Will be sorted
            "user_id": user.id,
            "name": user.full_name,
            "points": points,
            "lessons_completed": completed,
            "certificates": certificates,
            "level": calculate_level(points)
        })
    
    # Sort by points
    leaderboard_data.sort(key=lambda x: x["points"], reverse=True)
    
    # Add ranks
    for i, entry in enumerate(leaderboard_data):
        entry["rank"] = i + 1
    
    return jsonify({
        "success": True,
        "data": {
            "leaderboard": leaderboard_data[:limit],
            "updated_at": datetime.utcnow().isoformat()
        }
    })

@gamification_bp.route('/team-leaderboard/<int:department_id>')
@jwt_required()
def team_leaderboard(department_id):
    """Get department/team leaderboard"""
    # For now, just return all students (in production, filter by department)
    limit = request.args.get('limit', 10, type=int)
    
    users = User.query.filter(User.role == 'student').limit(50).all()
    
    leaderboard_data = []
    for user in users:
        completed = Progress.query.filter_by(user_id=user.id, completed=True).count()
        certificates = Certificate.query.filter_by(user_id=user.id).count()
        points = completed * 5 + certificates * 100
        
        leaderboard_data.append({
            "rank": 0,
            "user_id": user.id,
            "name": user.full_name,
            "points": points,
            "level": calculate_level(points)
        })
    
    leaderboard_data.sort(key=lambda x: x["points"], reverse=True)
    
    for i, entry in enumerate(leaderboard_data):
        entry["rank"] = i + 1
    
    return jsonify({
        "success": True,
        "data": {
            "team_leaderboard": leaderboard_data[:limit],
            "department_id": department_id
        }
    })

@gamification_bp.route('/check-achievements', methods=['POST'])
@jwt_required()
def check_achievements():
    """Check and award achievements after an action"""
    user_id = get_jwt_identity()
    
    # Get user's current achievements
    user_achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    earned = [ua.achievement_key for ua in user_achievements]
    
    new_achievements = []
    
    # Check lesson-based achievements
    completed_lessons = Progress.query.filter_by(user_id=user_id, completed=True).count()
    
    if completed_lessons >= 1 and "first_lesson" not in earned:
        new_achievements.append("first_lesson")
    if completed_lessons >= 10 and "lesson_milestone_10" not in earned:
        new_achievements.append("lesson_milestone_10")
    if completed_lessons >= 50 and "lesson_milestone_50" not in earned:
        new_achievements.append("lesson_milestone_50")
    if completed_lessons >= 100 and "lesson_milestone_100" not in earned:
        new_achievements.append("lesson_milestone_100")
    
    # Check course completion
    certificates = Certificate.query.filter_by(user_id=user_id).count()
    
    if certificates >= 1 and "course_complete_1" not in earned:
        new_achievements.append("course_complete_1")
    if certificates >= 5 and "course_complete_5" not in earned:
        new_achievements.append("course_complete_5")
    if certificates >= 1 and "certificate_earned" not in earned:
        new_achievements.append("certificate_earned")
    
    # Award new achievements
    for achievement_key in new_achievements:
        if achievement_key in ACHIEVEMENTS:
            ua = UserAchievement(
                user_id=user_id,
                achievement_key=achievement_key,
                points_awarded=ACHIEVEMENTS[achievement_key]["points"]
            )
            db.session.add(ua)
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": {
            "new_achievements": new_achievements,
            "achievement_details": [
                {"key": k, **ACHIEVEMENTS[k]} for k in new_achievements
            ]
        }
    })

@gamification_bp.route('/all-achievements')
@jwt_required()
def all_achievements():
    """Get all available achievements"""
    achievements = []
    for key, achievement in ACHIEVEMENTS.items():
        achievements.append({
            "key": key,
            **achievement
        })
    
    return jsonify({
        "success": True,
        "data": {
            "achievements": achievements
        }
    })

def calculate_level(points):
    """Calculate user level based on points"""
    if points < 50:
        return {"level": 1, "title": "Beginner", "next_title": "Learner", "points_to_next": 50 - points}
    elif points < 150:
        return {"level": 2, "title": "Learner", "next_title": "Advanced", "points_to_next": 150 - points}
    elif points < 300:
        return {"level": 3, "title": "Advanced", "next_title": "Expert", "points_to_next": 300 - points}
    elif points < 500:
        return {"level": 4, "title": "Expert", "next_title": "Master", "points_to_next": 500 - points}
    else:
        return {"level": 5, "title": "Master", "next_title": None, "points_to_next": 0}