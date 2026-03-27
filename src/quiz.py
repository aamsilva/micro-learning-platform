"""
Quiz Module for Micro Learning Platform

This module handles all quiz-related functionality:
- Quiz retrieval and creation
- Quiz submission and scoring
- Quiz attempts tracking
- Results and analytics
"""

from datetime import datetime
from flask import request
from src.models import db, Quiz, QuizAttempt, Lesson, Progress
from src.auth import get_current_user, AuthError, log_activity


def create_quiz(lesson_id, user_id, title, description=None, passing_score=70,
                questions=None, time_limit_minutes=None):
    """
    Create a quiz for a lesson.
    
    Args:
        lesson_id: Lesson ID
        user_id: User ID (instructor)
        title: Quiz title
        description: Quiz description
        passing_score: Minimum passing score (percentage)
        questions: List of questions
        time_limit_minutes: Time limit in minutes
    
    Returns:
        Quiz: Created quiz
    """
    lesson = Lesson.query.get(lesson_id)
    
    if not lesson:
        raise AuthError("Lesson not found")
    
    from src.models import Course
    course = Course.query.get(lesson.course_id)
    
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to create quiz for this lesson")
    
    if not questions or len(questions) == 0:
        raise AuthError("Quiz must have at least one question")
    
    # Validate questions format
    for q in questions:
        if 'question' not in q or 'options' not in q or 'correct' not in q:
            raise AuthError("Each question must have 'question', 'options', and 'correct' fields")
        
        if not isinstance(q['options'], list) or len(q['options']) < 2:
            raise AuthError("Each question must have at least 2 options")
        
        if not (0 <= q['correct'] < len(q['options'])):
            raise AuthError("Invalid correct answer index")
    
    quiz = Quiz(
        lesson_id=lesson_id,
        title=title,
        description=description,
        passing_score=passing_score,
        questions=questions,
        time_limit_minutes=time_limit_minutes
    )
    
    db.session.add(quiz)
    db.session.commit()
    
    return quiz


def update_quiz(quiz_id, user_id, **kwargs):
    """
    Update a quiz.
    
    Args:
        quiz_id: Quiz ID
        user_id: User ID
        **kwargs: Fields to update
    
    Returns:
        Quiz: Updated quiz
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    from src.models import Course, Lesson
    lesson = Lesson.query.get(quiz.lesson_id)
    course = Course.query.get(lesson.course_id)
    
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to update this quiz")
    
    allowed_fields = ['title', 'description', 'passing_score', 'questions', 'time_limit_minutes']
    
    for field in allowed_fields:
        if field in kwargs:
            setattr(quiz, field, kwargs[field])
    
    quiz.updated_at = datetime.utcnow()
    db.session.commit()
    
    return quiz


def delete_quiz(quiz_id, user_id):
    """
    Delete a quiz.
    
    Args:
        quiz_id: Quiz ID
        user_id: User ID
    
    Returns:
        bool: True if successful
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    from src.models import Course, Lesson
    lesson = Lesson.query.get(quiz.lesson_id)
    course = Course.query.get(lesson.course_id)
    
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to delete this quiz")
    
    # Delete all attempts first
    QuizAttempt.query.filter_by(quiz_id=quiz_id).delete()
    
    db.session.delete(quiz)
    db.session.commit()
    
    return True


def get_quiz(lesson_id_or_quiz_id, quiz_id=None):
    """
    Get quiz by lesson or quiz ID.
    
    Args:
        lesson_id_or_lesson_id: Lesson ID or Quiz ID
        quiz_id: Quiz ID if first arg is lesson_id
    
    Returns:
        Quiz: Quiz object
    """
    if quiz_id:
        quiz = Quiz.query.get(quiz_id)
    else:
        quiz = Quiz.query.filter_by(lesson_id=lesson_id_or_quiz_id).first()
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    return quiz.to_dict(include_answers=False)


def get_quiz_with_answers(quiz_id):
    """
    Get quiz with correct answers (for instructors).
    
    Args:
        quiz_id: Quiz ID
    
    Returns:
        Quiz: Quiz object with answers
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    return quiz.to_dict(include_answers=True)


def submit_quiz(quiz_id, user_id, answers):
    """
    Submit quiz answers and calculate score.
    
    Args:
        quiz_id: Quiz ID
        user_id: User ID
        answers: List of answers
    
    Returns:
        dict: Quiz results
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    # Check enrollment
    from src.models import Course, Lesson, Enrollment
    lesson = Lesson.query.get(quiz.lesson_id)
    course = Course.query.get(lesson.course_id)
    
    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        course_id=course.id,
        is_active=True
    ).first()
    
    if not enrollment:
        raise AuthError("Not enrolled in this course")
    
    # Get attempt number
    attempt_count = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id
    ).count()
    
    # Calculate score
    score = calculate_score(quiz, answers)
    passed = score >= quiz.passing_score
    
    # Create attempt record
    attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        answers=answers,
        passed=passed,
        attempt_number=attempt_count + 1,
        completed_at=datetime.utcnow()
    )
    
    db.session.add(attempt)
    db.session.commit()
    
    # Log activity
    log_activity(user_id, 'quiz_submitted', {
        'quiz_id': quiz_id,
        'score': score,
        'passed': passed
    })
    
    return {
        'attempt_id': attempt.id,
        'score': score,
        'passed': passed,
        'passing_score': quiz.passing_score,
        'correct_answers': get_correct_count(quiz, answers),
        'total_questions': len(quiz.questions) if quiz.questions else 0,
        'attempt_number': attempt.attempt_number
    }


def calculate_score(quiz, answers):
    """
    Calculate quiz score.
    
    Args:
        quiz: Quiz object
        answers: List of user answers
    
    Returns:
        float: Score percentage
    """
    if not quiz.questions or len(quiz.questions) == 0:
        return 0
    
    correct = 0
    total = len(quiz.questions)
    
    for i, answer in enumerate(answers):
        if i < len(quiz.questions):
            question = quiz.questions[i]
            selected = answer.get('selected')
            
            if selected == question.get('correct'):
                correct += 1
    
    return round((correct / total) * 100, 2) if total > 0 else 0


def get_correct_count(quiz, answers):
    """
    Get count of correct answers.
    
    Args:
        quiz: Quiz object
        answers: List of user answers
    
    Returns:
        int: Number of correct answers
    """
    if not quiz.questions:
        return 0
    
    correct = 0
    for i, answer in enumerate(answers):
        if i < len(quiz.questions):
            question = quiz.questions[i]
            selected = answer.get('selected')
            
            if selected == question.get('correct'):
                correct += 1
    
    return correct


def get_quiz_results(quiz_id, user_id):
    """
    Get user's quiz results.
    
    Args:
        quiz_id: Quiz ID
        user_id: User ID
    
    Returns:
        dict: Quiz results
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    # Get user's attempts
    attempts = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id
    ).order_by(QuizAttempt.completed_at.desc()).all()
    
    if not attempts:
        return error_response("No attempts found")
    
    # Get best score
    best_attempt = max(attempts, key=lambda a: a.score)
    
    return {
        'quiz': quiz.to_dict(include_answers=False),
        'attempts': [a.to_dict() for a in attempts],
        'best_score': best_attempt.score,
        'passed': best_attempt.passed,
        'total_attempts': len(attempts)
    }


def retry_quiz(quiz_id, user_id):
    """
    Get quiz for retry.
    
    Args:
        quiz_id: Quiz ID
        user_id: User ID
    
    Returns:
        dict: Quiz info for retry
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    # Check if can retry (not passing already)
    from src.models import Course, Lesson, Enrollment
    lesson = Lesson.query.get(quiz.lesson_id)
    course = Course.query.get(lesson.course_id)
    
    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        course_id=course.id,
        is_active=True
    ).first()
    
    if not enrollment:
        raise AuthError("Not enrolled in this course")
    
    # Get attempt count
    attempt_count = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id
    ).count()
    
    return {
        'quiz': quiz.to_dict(include_answers=False),
        'attempt_number': attempt_count + 1,
        'time_limit_minutes': quiz.time_limit_minutes
    }


def get_quiz_attempts(quiz_id):
    """
    Get all attempts for a quiz (instructor only).
    
    Args:
        quiz_id: Quiz ID
    
    Returns:
        list: All quiz attempts
    """
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).all()
    return [a.to_dict() for a in attempts]


def get_quiz_statistics(quiz_id):
    """
    Get quiz statistics (instructor only).
    
    Args:
        quiz_id: Quiz ID
    
    Returns:
        dict: Quiz statistics
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    attempts = QuizAttempt.query.filter_by(quiz_id=quiz_id).all()
    
    if not attempts:
        return {
            'total_attempts': 0,
            'average_score': 0,
            'pass_rate': 0,
            'highest_score': 0,
            'lowest_score': 0
        }
    
    scores = [a.score for a in attempts]
    passed = sum(1 for a in attempts if a.passed)
    
    return {
        'total_attempts': len(attempts),
        'average_score': round(sum(scores) / len(scores), 2),
        'pass_rate': round((passed / len(attempts)) * 100, 2),
        'highest_score': max(scores),
        'lowest_score': min(scores),
        'question_count': len(quiz.questions) if quiz.questions else 0
    }


def validate_quiz_questions(questions):
    """
    Validate quiz questions format.
    
    Args:
        questions: List of questions
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not questions:
        return False, "Questions list is empty"
    
    for i, q in enumerate(questions):
        if 'question' not in q:
            return False, f"Question {i+1}: Missing 'question' field"
        
        if 'options' not in q:
            return False, f"Question {i+1}: Missing 'options' field"
        
        if not isinstance(q['options'], list):
            return False, f"Question {i+1}: 'options' must be a list"
        
        if len(q['options']) < 2:
            return False, f"Question {i+1}: Must have at least 2 options"
        
        if 'correct' not in q:
            return False, f"Question {i+1}: Missing 'correct' field"
        
        if not (0 <= q['correct'] < len(q['options'])):
            return False, f"Question {i+1}: Invalid 'correct' index"
    
    return True, None


def grade_quiz(quiz_id, user_id):
    """
    Get detailed grade breakdown for a quiz.
    
    Args:
        quiz_id: Quiz ID
        user_id: User ID
    
    Returns:
        dict: Detailed grade breakdown
    """
    quiz = Quiz.query.get(quiz_id)
    
    if not quiz:
        raise AuthError("Quiz not found")
    
    # Get user's latest attempt
    attempt = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id
    ).order_by(QuizAttempt.completed_at.desc()).first()
    
    if not attempt:
        raise AuthError("No attempt found")
    
    # Build grade breakdown
    breakdown = []
    for i, question in enumerate(quiz.questions):
        user_answer = None
        if i < len(attempt.answers):
            user_answer = attempt.answers[i].get('selected')
        
        breakdown.append({
            'question_number': i + 1,
            'question': question.get('question'),
            'options': question.get('options'),
            'correct_answer': question.get('correct'),
            'user_answer': user_answer,
            'is_correct': user_answer == question.get('correct')
        })
    
    return {
        'attempt': attempt.to_dict(),
        'questions': breakdown,
        'total_correct': get_correct_count(quiz, attempt.answers),
        'total_questions': len(quiz.questions)
    }