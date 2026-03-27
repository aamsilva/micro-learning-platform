"""
Analytics Module for Micro Learning Platform

This module handles all learning analytics and statistics:
- User learning statistics
- Course analytics
- Progress tracking
- Achievement tracking
- Dashboard data
"""

from datetime import datetime, timedelta
from sqlalchemy import func, desc
from src.models import db, User, Course, Lesson, Quiz, QuizAttempt, Progress, Certificate, Enrollment, UserActivity
from src.auth import get_current_user, AuthError


def get_user_analytics(user_id, period='all'):
    """
    Get comprehensive analytics for a user.
    
    Args:
        user_id: User ID
        period: Time period (week/month/year/all)
    
    Returns:
        dict: User analytics data
    """
    user = User.query.get(user_id)
    
    if not user:
        raise AuthError("User not found")
    
    # Get base stats
    enrolled_courses = Enrollment.query.filter_by(
        user_id=user_id, 
        is_active=True
    ).count()
    
    completed_courses = Certificate.query.filter_by(user_id=user_id).count()
    
    completed_lessons = Progress.query.filter_by(
        user_id=user_id,
        completed=True
    ).count()
    
    # Get quiz stats
    quiz_attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
    total_quiz_attempts = len(quiz_attempts)
    passed_quizzes = sum(1 for a in quiz_attempts if a.passed)
    average_score = sum(a.score for a in quiz_attempts) / total_quiz_attempts if total_quiz_attempts > 0 else 0
    
    # Get time spent
    total_time = db.session.query(
        func.sum(Progress.time_spent_seconds)
    ).filter(
        Progress.user_id == user_id
    ).scalar() or 0
    
    # Get streak
    streak = get_learning_streak(user_id)
    
    # Get certificates
    certificates = Certificate.query.filter_by(user_id=user_id).all()
    
    # Get recent activity
    recent_activity = get_recent_activity(user_id, limit=10)
    
    return {
        'overview': {
            'enrolled_courses': enrolled_courses,
            'completed_courses': completed_courses,
            'completed_lessons': completed_lessons,
            'total_quiz_attempts': total_quiz_attempts,
            'passed_quizzes': passed_quizzes,
            'average_quiz_score': round(average_score, 2),
            'total_learning_time': format_time(total_time),
            'total_time_seconds': total_time,
            'certificates_earned': len(certificates)
        },
        'streak': streak,
        'recent_activity': recent_activity,
        'certificates': [c.to_dict() for c in certificates]
    }


def get_dashboard_data(user_id):
    """
    Get dashboard data for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        dict: Dashboard data
    """
    user = User.query.get(user_id)
    
    if not user:
        raise AuthError("User not found")
    
    # Get enrolled courses with progress
    enrollments = Enrollment.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    courses_in_progress = []
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        if course and course.is_published:
            progress = get_user_progress(user_id, course.id)
            if progress['percentage'] > 0 and progress['percentage'] < 100:
                courses_in_progress.append({
                    'course': course.to_dict(),
                    'progress': progress
                })
    
    # Get recently completed lessons
    recent_progress = Progress.query.filter_by(
        user_id=user_id,
        completed=True
    ).order_by(Progress.completed_at.desc()).limit(5).all()
    
    recent_lessons = []
    for progress in recent_progress:
        lesson = Lesson.query.get(progress.lesson_id)
        if lesson:
            course = Course.query.get(lesson.course_id)
            recent_lessons.append({
                'lesson': lesson.to_dict(),
                'course_title': course.title if course else 'Unknown',
                'completed_at': progress.completed_at.isoformat()
            })
    
    # Get upcoming quizzes
    quiz_results = []
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        if course:
            for lesson in course.lessons:
                if lesson.quiz:
                    # Check if user has attempted
                    attempts = QuizAttempt.query.filter_by(
                        user_id=user_id,
                        quiz_id=lesson.quiz.id
                    ).first()
                    
                    if not attempts or not attempts.passed:
                        quiz_results.append({
                            'lesson_id': lesson.id,
                            'lesson_title': lesson.title,
                            'course_title': course.title,
                            'quiz': lesson.quiz.to_dict()
                        })
    
    # Get recommended courses
    from src.courses import get_recommended_courses
    recommended = get_recommended_courses(user_id, limit=4)
    
    # Get achievements
    achievements = get_achievements(user_id)
    
    # Get streak
    streak = get_learning_streak(user_id)
    
    return {
        'user': user.to_dict(),
        'courses_in_progress': courses_in_progress,
        'recent_lessons': recent_lessons,
        'upcoming_quizzes': quiz_results[:5],
        'recommended_courses': recommended,
        'achievements': achievements,
        'streak': streak,
        'stats': {
            'enrolled': len(enrollments),
            'completed': Certificate.query.filter_by(user_id=user_id).count()
        }
    }


def get_learning_streak(user_id):
    """
    Calculate user learning streak.
    
    Args:
        user_id: User ID
    
    Returns:
        dict: Streak information
    """
    # Get completed lessons grouped by date
    completed_dates = db.session.query(
        func.date(Progress.completed_at)
    ).filter(
        Progress.user_id == user_id,
        Progress.completed == True,
        Progress.completed_at.isnot(None)
    ).distinct().order_by(desc(func.date(Progress.completed_at))).all()
    
    if not completed_dates:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'last_activity_date': None
        }
    
    dates = [c[0] for c in completed_dates if c[0]]
    
    if not dates:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'last_activity_date': None
        }
    
    # Calculate current streak
    current_streak = 0
    today = datetime.utcnow().date()
    
    # Check if there's activity today or yesterday
    if dates[0] == today or dates[0] == today - timedelta(days=1):
        current_streak = 1
        check_date = dates[0]
        
        for i in range(1, len(dates)):
            expected_date = check_date - timedelta(days=1)
            if dates[i] == expected_date:
                current_streak += 1
                check_date = dates[i]
            else:
                break
    
    # Calculate longest streak
    longest_streak = 1
    temp_streak = 1
    
    for i in range(1, len(dates)):
        if dates[i] == dates[i-1] - timedelta(days=1):
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 1
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'last_activity_date': dates[0].isoformat() if dates else None
    }


def get_achievements(user_id):
    """
    Get user achievements.
    
    Args:
        user_id: User ID
    
    Returns:
        list: User achievements
    """
    from src.auth import get_user_achievements
    return get_user_achievements(user_id)


def get_recent_activity(user_id, limit=10):
    """
    Get user's recent activity.
    
    Args:
        user_id: User ID
        limit: Number of activities to return
    
    Returns:
        list: Recent activities
    """
    activities = UserActivity.query.filter_by(
        user_id=user_id
    ).order_by(UserActivity.created_at.desc()).limit(limit).all()
    
    return [a.to_dict() for a in activities]


def get_user_progress(user_id, course_id):
    """
    Get user's progress for a specific course.
    
    Args:
        user_id: User ID
        course_id: Course ID
    
    Returns:
        dict: Progress information
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    total_lessons = Lesson.query.filter_by(course_id=course_id).count()
    
    if total_lessons == 0:
        return {
            'course_id': course_id,
            'total_lessons': 0,
            'completed_lessons': 0,
            'percentage': 0,
            'time_spent': 0
        }
    
    completed = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id,
        completed=True
    ).count()
    
    # Get total time spent
    time_spent = db.session.query(
        func.sum(Progress.time_spent_seconds)
    ).filter(
        Progress.user_id == user_id,
        Progress.course_id == course_id
    ).scalar() or 0
    
    return {
        'course_id': course_id,
        'total_lessons': total_lessons,
        'completed_lessons': completed,
        'percentage': round((completed / total_lessons) * 100, 2),
        'time_spent': format_time(time_spent),
        'time_spent_seconds': time_spent
    }


def get_course_analytics(course_id, user_id):
    """
    Get analytics for a course (instructor only).
    
    Args:
        course_id: Course ID
        user_id: User ID (instructor)
    
    Returns:
        dict: Course analytics
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to view this course's analytics")
    
    # Get enrollment stats
    total_enrolled = Enrollment.query.filter_by(course_id=course_id).count()
    active_enrolled = Enrollment.query.filter_by(
        course_id=course_id, 
        is_active=True
    ).count()
    
    # Get lesson completion stats
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    lesson_stats = []
    
    for lesson in lessons:
        completed = Progress.query.filter_by(
            lesson_id=lesson.id,
            completed=True
        ).count()
        
        lesson_stats.append({
            'lesson_id': lesson.id,
            'lesson_title': lesson.title,
            'completed_count': completed,
            'enrolled_count': total_enrolled,
            'completion_rate': round((completed / total_enrolled) * 100, 2) if total_enrolled > 0 else 0
        })
    
    # Get quiz stats
    quiz_stats = []
    for lesson in lessons:
        if lesson.quiz:
            attempts = QuizAttempt.query.filter_by(quiz_id=lesson.quiz.id).all()
            scores = [a.score for a in attempts]
            
            quiz_stats.append({
                'quiz_id': lesson.quiz.id,
                'quiz_title': lesson.quiz.title,
                'attempts': len(attempts),
                'average_score': round(sum(scores) / len(scores), 2) if scores else 0,
                'pass_rate': round((sum(1 for a in attempts if a.passed) / len(attempts)) * 100, 2) if attempts else 0
            })
    
    # Get rating
    from src.models import Review
    reviews = Review.query.filter_by(course_id=course_id).all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
    
    return {
        'course': course.to_dict(),
        'enrollment': {
            'total': total_enrolled,
            'active': active_enrolled
        },
        'lessons': lesson_stats,
        'quizzes': quiz_stats,
        'rating': {
            'average': round(avg_rating, 2),
            'count': len(reviews)
        }
    }


def get_leaderboard(limit=10, period='all'):
    """
    Get learning leaderboard.
    
    Args:
        limit: Number of users to return
        period: Time period (week/month/year/all)
    
    Returns:
        list: Leaderboard data
    """
    # Query based on completed lessons
    query = db.session.query(
        User.id,
        User.username,
        User.full_name,
        User.avatar_url,
        func.count(Progress.id).label('completed_lessons')
    ).join(
        Progress, User.id == Progress.user_id
    ).filter(
        Progress.completed == True
    )
    
    # Filter by period
    if period == 'week':
        start_date = datetime.utcnow() - timedelta(days=7)
        query = query.filter(Progress.completed_at >= start_date)
    elif period == 'month':
        start_date = datetime.utcnow() - timedelta(days=30)
        query = query.filter(Progress.completed_at >= start_date)
    elif period == 'year':
        start_date = datetime.utcnow() - timedelta(days=365)
        query = query.filter(Progress.completed_at >= start_date)
    
    # Group and order
    query = query.group_by(User.id).order_by(
        desc('completed_lessons')
    ).limit(limit)
    
    results = query.all()
    
    leaderboard = []
    for rank, result in enumerate(results, 1):
        user = User.query.get(result[0])
        leaderboard.append({
            'rank': rank,
            'user': user.to_dict() if user else None,
            'completed_lessons': result[3]
        })
    
    return leaderboard


def get_popular_courses_analytics(limit=10):
    """
    Get analytics for popular courses.
    
    Args:
        limit: Number of courses
    
    Returns:
        list: Popular courses with analytics
    """
    courses = Course.query.filter_by(is_published=True).all()
    
    course_data = []
    for course in courses:
        enrolled = Enrollment.query.filter_by(course_id=course.id).count()
        completed = Certificate.query.filter_by(course_id=course.id).count()
        
        course_data.append({
            'course': course.to_dict(),
            'enrolled': enrolled,
            'completed': completed,
            'completion_rate': round((completed / enrolled) * 100, 2) if enrolled > 0 else 0
        })
    
    # Sort by enrollment
    course_data.sort(key=lambda x: x['enrolled'], reverse=True)
    
    return course_data[:limit]


def get_daily_learning_stats(user_id, days=7):
    """
    Get daily learning statistics.
    
    Args:
        user_id: User ID
        days: Number of days
    
    Returns:
        list: Daily statistics
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get lessons completed per day
    lessons_completed = db.session.query(
        func.date(Progress.completed_at).label('date'),
        func.count(Progress.id).label('count')
    ).filter(
        Progress.user_id == user_id,
        Progress.completed == True,
        Progress.completed_at >= start_date
    ).group_by(
        func.date(Progress.completed_at)
    ).all()
    
    # Get quizzes completed per day
    quizzes_completed = db.session.query(
        func.date(QuizAttempt.completed_at).label('date'),
        func.count(QuizAttempt.id).label('count')
    ).filter(
        QuizAttempt.user_id == user_id,
        QuizAttempt.completed_at >= start_date
    ).group_by(
        func.date(QuizAttempt.completed_at)
    ).all()
    
    # Get time spent per day
    time_spent = db.session.query(
        func.date(Progress.completed_at).label('date'),
        func.sum(Progress.time_spent_seconds).label('total')
    ).filter(
        Progress.user_id == user_id,
        Progress.completed == True,
        Progress.completed_at >= start_date
    ).group_by(
        func.date(Progress.completed_at)
    ).all()
    
    # Build daily data
    daily_stats = {}
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days-i-1)).date()
        daily_stats[date.isoformat()] = {
            'lessons_completed': 0,
            'quizzes_completed': 0,
            'time_spent': 0
        }
    
    for date, count in lessons_completed:
        if date and date.isoformat() in daily_stats:
            daily_stats[date.isoformat()]['lessons_completed'] = count
    
    for date, count in quizzes_completed:
        if date and date.isoformat() in daily_stats:
            daily_stats[date.isoformat()]['quizzes_completed'] = count
    
    for date, total in time_spent:
        if date and date.isoformat() in daily_stats:
            daily_stats[date.isoformat()]['time_spent'] = total
    
    return [
        {
            'date': date,
            **stats
        }
        for date, stats in sorted(daily_stats.items())
    ]


def track_course_event(course_id, event_type, user_id, details=None):
    """
    Track course-related events.
    
    Args:
        course_id: Course ID
        event_type: Type of event
        user_id: User ID
        details: Additional details
    """
    from src.models import UserActivity
    
    activity = UserActivity(
        user_id=user_id,
        activity_type=f"course_{event_type}",
        details=details or {'course_id': course_id}
    )
    
    db.session.add(activity)
    db.session.commit()


def format_time(seconds):
    """
    Format seconds into human-readable time.
    
    Args:
        seconds: Time in seconds
    
    Returns:
        str: Formatted time string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"


def get_platform_stats():
    """
    Get platform-wide statistics (admin only).
    
    Returns:
        dict: Platform statistics
    """
    total_users = User.query.count()
    total_courses = Course.query.count()
    published_courses = Course.query.filter_by(is_published=True).count()
    total_enrollments = Enrollment.query.count()
    total_completions = Certificate.query.count()
    
    # Get recent activity
    recent_activities = UserActivity.query.order_by(
        UserActivity.created_at.desc()
    ).limit(20).all()
    
    return {
        'users': {
            'total': total_users,
            'active': User.query.filter_by(is_active=True).count()
        },
        'courses': {
            'total': total_courses,
            'published': published_courses
        },
        'enrollments': {
            'total': total_enrollments
        },
        'completions': {
            'total': total_completions
        },
        'recent_activity': [a.to_dict() for a in recent_activities]
    }


def get_course_completion_rate(course_id):
    """
    Get completion rate for a course.
    
    Args:
        course_id: Course ID
    
    Returns:
        dict: Completion rate info
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    total_enrolled = Enrollment.query.filter_by(course_id=course_id).count()
    completed = Certificate.query.filter_by(course_id=course_id).count()
    
    return {
        'course_id': course_id,
        'enrolled': total_enrolled,
        'completed': completed,
        'completion_rate': round((completed / total_enrolled) * 100, 2) if total_enrolled > 0 else 0
    }