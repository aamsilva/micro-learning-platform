"""
Course Management Module for Micro Learning Platform

This module handles all course-related functionality:
- Course CRUD operations
- Enrollment management
- Lesson management
- Search and filtering
- Categories and tags
"""

from datetime import datetime
from flask import request
from src.models import db, Course, Lesson, Enrollment, Progress, Certificate, Review, Category, Tag, CourseTag
from src.auth import log_activity, require_auth, get_current_user, AuthError
from src.analytics import track_course_event


def create_course(title, description, instructor_id, category_id=None, 
                  difficulty='beginner', price=0.0, thumbnail_url=None, tags=None):
    """
    Create a new course.
    
    Args:
        title: Course title
        description: Course description
        instructor_id: Instructor's user ID
        category_id: Category ID
        difficulty: Difficulty level (beginner/intermediate/advanced)
        price: Course price
        thumbnail_url: Thumbnail URL
        tags: List of tag names
    
    Returns:
        Course: Created course
    
    Raises:
        AuthError: If validation fails
    """
    # Validate title
    if not title or len(title.strip()) < 3:
        raise AuthError("Course title must be at least 3 characters")
    
    # Validate difficulty
    valid_difficulties = ['beginner', 'intermediate', 'advanced']
    if difficulty not in valid_difficulties:
        raise AuthError(f"Invalid difficulty. Must be one of: {', '.join(valid_difficulties)}")
    
    # Validate price
    if price < 0:
        raise AuthError("Price cannot be negative")
    
    # Check category if provided
    if category_id:
        category = Category.query.get(category_id)
        if not category:
            raise AuthError("Invalid category")
    
    # Create course
    course = Course(
        title=title.strip(),
        description=description,
        instructor_id=instructor_id,
        category_id=category_id,
        difficulty=difficulty,
        price=price,
        thumbnail_url=thumbnail_url,
        is_published=False  # Draft by default
    )
    
    db.session.add(course)
    db.session.flush()  # Get course ID
    
    # Add tags
    if tags:
        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
                db.session.flush()
            
            course_tag = CourseTag(course_id=course.id, tag_id=tag.id)
            db.session.add(course_tag)
    
    db.session.commit()
    
    # Log event
    track_course_event(course.id, 'course_created', instructor_id)
    
    return course


def update_course(course_id, user_id, **kwargs):
    """
    Update a course.
    
    Args:
        course_id: Course ID
        user_id: User ID making the update
        **kwargs: Fields to update
    
    Returns:
        Course: Updated course
    
    Raises:
        AuthError: If not authorized or validation fails
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    # Check authorization (instructor or admin)
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to update this course")
    
    allowed_fields = [
        'title', 'description', 'category_id', 'difficulty', 
        'price', 'thumbnail_url', 'is_published', 'is_featured',
        'duration_hours'
    ]
    
    for field in allowed_fields:
        if field in kwargs:
            setattr(course, field, kwargs[field])
    
    course.updated_at = datetime.utcnow()
    db.session.commit()
    
    track_course_event(course_id, 'course_updated', user_id)
    
    return course


def delete_course(course_id, user_id):
    """
    Delete a course.
    
    Args:
        course_id: Course ID
        user_id: User ID making the deletion
    
    Returns:
        bool: True if successful
    
    Raises:
        AuthError: If not authorized
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    # Check authorization
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to delete this course")
    
    # Soft delete - just mark as unpublished
    course.is_published = False
    course.updated_at = datetime.utcnow()
    db.session.commit()
    
    track_course_event(course_id, 'course_deleted', user_id)
    
    return True


def get_course(course_id, include_details=False):
    """
    Get course details.
    
    Args:
        course_id: Course ID
        include_details: Include lessons and tags
    
    Returns:
        Course: Course object
    
    Raises:
        AuthError: If course not found
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    return course.to_dict(include_details=include_details)


def list_courses(page=1, per_page=20, category_id=None, difficulty=None,
                 instructor_id=None, search=None, sort_by='created_at', 
                 sort_order='desc', include_unpublished=False):
    """
    List courses with filtering and pagination.
    
    Args:
        page: Page number
        per_page: Items per page
        category_id: Filter by category
        difficulty: Filter by difficulty
        instructor_id: Filter by instructor
        search: Search query
        sort_by: Sort field
        sort_order: Sort order (asc/desc)
        include_unpublished: Include unpublished courses
    
    Returns:
        dict: Paginated course list
    """
    query = Course.query
    
    # Apply filters
    if not include_unpublished:
        query = query.filter_by(is_published=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    if instructor_id:
        query = query.filter_by(instructor_id=instructor_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                Course.title.ilike(search_term),
                Course.description.ilike(search_term)
            )
        )
    
    # Apply sorting
    valid_sort_fields = ['created_at', 'title', 'price', 'difficulty', 'average_rating']
    if sort_by not in valid_sort_fields:
        sort_by = 'created_at'
    
    sort_column = getattr(Course, sort_by, Course.created_at)
    if sort_order == 'desc':
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return {
        'courses': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev
    }


def enroll_course(course_id, user_id):
    """
    Enroll user in a course.
    
    Args:
        course_id: Course ID
        user_id: User ID
    
    Returns:
        Enrollment: Created enrollment
    
    Raises:
        AuthError: If enrollment fails
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    if not course.is_published:
        raise AuthError("Course is not available for enrollment")
    
    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()
    
    if existing:
        raise AuthError("Already enrolled in this course")
    
    # Create enrollment
    enrollment = Enrollment(
        user_id=user_id,
        course_id=course_id
    )
    
    db.session.add(enrollment)
    db.session.commit()
    
    track_course_event(course_id, 'course_enrolled', user_id)
    
    return enrollment


def unenroll_course(course_id, user_id):
    """
    Unenroll user from a course.
    
    Args:
        course_id: Course ID
        user_id: User ID
    
    Returns:
        bool: True if successful
    """
    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()
    
    if not enrollment:
        raise AuthError("Not enrolled in this course")
    
    enrollment.is_active = False
    db.session.commit()
    
    track_course_event(course_id, 'course_unenrolled', user_id)
    
    return True


def get_user_enrollments(user_id, active_only=True):
    """
    Get user's course enrollments.
    
    Args:
        user_id: User ID
        active_only: Only active enrollments
    
    Returns:
        list: User enrollments
    """
    query = Enrollment.query.filter_by(user_id=user_id)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
    enrollments = query.all()
    
    return [e.to_dict() for e in enrollments]


# Lesson Management

def create_lesson(course_id, user_id, title, content=None, content_type='text',
                  video_url=None, order=None, duration_minutes=0):
    """
    Create a new lesson.
    
    Args:
        course_id: Course ID
        user_id: User ID (instructor)
        title: Lesson title
        content: Lesson content
        content_type: Type of content (video/text/code)
        video_url: Video URL
        order: Lesson order
        duration_minutes: Duration in minutes
    
    Returns:
        Lesson: Created lesson
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to add lessons to this course")
    
    # Determine order
    if order is None:
        max_order = db.session.query(db.func.max(Lesson.order)).filter_by(
            course_id=course_id
        ).scalar() or 0
        order = max_order + 1
    
    lesson = Lesson(
        course_id=course_id,
        title=title,
        content=content,
        content_type=content_type,
        video_url=video_url,
        order=order,
        duration_minutes=duration_minutes
    )
    
    db.session.add(lesson)
    db.session.commit()
    
    track_course_event(course_id, 'lesson_created', user_id, {'lesson_id': lesson.id})
    
    return lesson


def update_lesson(lesson_id, user_id, **kwargs):
    """
    Update a lesson.
    
    Args:
        lesson_id: Lesson ID
        user_id: User ID
        **kwargs: Fields to update
    
    Returns:
        Lesson: Updated lesson
    """
    lesson = Lesson.query.get(lesson_id)
    
    if not lesson:
        raise AuthError("Lesson not found")
    
    course = Course.query.get(lesson.course_id)
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to update this lesson")
    
    allowed_fields = ['title', 'content', 'content_type', 'video_url', 'order', 'duration_minutes']
    
    for field in allowed_fields:
        if field in kwargs:
            setattr(lesson, field, kwargs[field])
    
    lesson.updated_at = datetime.utcnow()
    db.session.commit()
    
    return lesson


def delete_lesson(lesson_id, user_id):
    """
    Delete a lesson.
    
    Args:
        lesson_id: Lesson ID
        user_id: User ID
    
    Returns:
        bool: True if successful
    """
    lesson = Lesson.query.get(lesson_id)
    
    if not lesson:
        raise AuthError("Lesson not found")
    
    course = Course.query.get(lesson.course_id)
    if course.instructor_id != user_id:
        raise AuthError("Not authorized to delete this lesson")
    
    db.session.delete(lesson)
    db.session.commit()
    
    return True


def get_lesson(lesson_id, include_content=False):
    """
    Get lesson details.
    
    Args:
        lesson_id: Lesson ID
        include_content: Include lesson content
    
    Returns:
        Lesson: Lesson object
    
    Raises:
        AuthError: If lesson not found
    """
    lesson = Lesson.query.get(lesson_id)
    
    if not lesson:
        raise AuthError("Lesson not found")
    
    return lesson.to_dict(include_content=include_content)


def get_course_lessons(course_id, user_id=None):
    """
    Get all lessons for a course.
    
    Args:
        course_id: Course ID
        user_id: Optional user ID for progress info
    
    Returns:
        list: Course lessons with progress
    """
    lessons = Lesson.query.filter_by(
        course_id=course_id
    ).order_by(Lesson.order).all()
    
    result = []
    for lesson in lessons:
        lesson_dict = lesson.to_dict(include_content=True)
        
        # Add progress if user provided
        if user_id:
            progress = Progress.query.filter_by(
                user_id=user_id,
                lesson_id=lesson.id
            ).first()
            lesson_dict['completed'] = progress.completed if progress else False
            lesson_dict['progress_id'] = progress.id if progress else None
        
        result.append(lesson_dict)
    
    return result


# Progress Tracking

def mark_lesson_complete(lesson_id, user_id, time_spent=0):
    """
    Mark a lesson as complete.
    
    Args:
        lesson_id: Lesson ID
        user_id: User ID
        time_spent: Time spent in seconds
    
    Returns:
        Progress: Progress record
    """
    lesson = Lesson.query.get(lesson_id)
    
    if not lesson:
        raise AuthError("Lesson not found")
    
    # Check enrollment
    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        course_id=lesson.course_id,
        is_active=True
    ).first()
    
    if not enrollment:
        raise AuthError("Not enrolled in this course")
    
    # Get or create progress
    progress = Progress.query.filter_by(
        user_id=user_id,
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = Progress(
            user_id=user_id,
            course_id=lesson.course_id,
            lesson_id=lesson_id
        )
        db.session.add(progress)
    
    progress.completed = True
    progress.completed_at = datetime.utcnow()
    progress.time_spent_seconds += time_spent
    
    db.session.commit()
    
    # Check if course is complete
    check_course_completion(user_id, lesson.course_id)
    
    track_course_event(lesson.course_id, 'lesson_completed', user_id, {
        'lesson_id': lesson_id,
        'title': lesson.title
    })
    
    return progress


def update_progress(lesson_id, user_id, time_spent):
    """
    Update lesson progress (time spent).
    
    Args:
        lesson_id: Lesson ID
        user_id: User ID
        time_spent: Time spent in seconds
    """
    lesson = Lesson.query.get(lesson_id)
    
    if not lesson:
        raise AuthError("Lesson not found")
    
    # Get or create progress
    progress = Progress.query.filter_by(
        user_id=user_id,
        lesson_id=lesson_id
    ).first()
    
    if not progress:
        progress = Progress(
            user_id=user_id,
            course_id=lesson.course_id,
            lesson_id=lesson_id
        )
        db.session.add(progress)
    
    progress.time_spent_seconds += time_spent
    
    db.session.commit()


def get_user_progress(user_id, course_id):
    """
    Get user's progress for a course.
    
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
            'percentage': 0
        }
    
    completed = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id,
        completed=True
    ).count()
    
    return {
        'course_id': course_id,
        'total_lessons': total_lessons,
        'completed_lessons': completed,
        'percentage': round((completed / total_lessons) * 100, 2)
    }


def check_course_completion(user_id, course_id):
    """
    Check if user has completed all lessons in a course.
    
    Args:
        user_id: User ID
        course_id: Course ID
    
    Returns:
        Certificate: If course completed, the certificate
    """
    # Check if already has certificate
    existing = Certificate.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()
    
    if existing:
        return existing
    
    # Get total lessons
    total_lessons = Lesson.query.filter_by(course_id=course_id).count()
    
    # Get completed lessons
    completed = Progress.query.filter_by(
        user_id=user_id,
        course_id=course_id,
        completed=True
    ).count()
    
    # If all complete, generate certificate
    if completed >= total_lessons and total_lessons > 0:
        certificate = generate_certificate(user_id, course_id)
        return certificate
    
    return None


def generate_certificate(user_id, course_id):
    """
    Generate a completion certificate.
    
    Args:
        user_id: User ID
        course_id: Course ID
    
    Returns:
        Certificate: Generated certificate
    """
    certificate = Certificate(
        user_id=user_id,
        course_id=course_id,
        certificate_number=Certificate.generate_certificate_number()
    )
    
    db.session.add(certificate)
    db.session.commit()
    
    track_course_event(course_id, 'certificate_issued', user_id)
    
    return certificate


def get_user_certificates(user_id):
    """
    Get user's certificates.
    
    Args:
        user_id: User ID
    
    Returns:
        list: User certificates
    """
    certificates = Certificate.query.filter_by(user_id=user_id).all()
    return [c.to_dict() for c in certificates]


# Reviews and Ratings

def add_review(course_id, user_id, rating, comment=None):
    """
    Add a review to a course.
    
    Args:
        course_id: Course ID
        user_id: User ID
        rating: Rating (1-5)
        comment: Optional comment
    
    Returns:
        Review: Created review
    """
    course = Course.query.get(course_id)
    
    if not course:
        raise AuthError("Course not found")
    
    # Check enrollment
    enrollment = Enrollment.query.filter_by(
        user_id=user_id,
        course_id=course_id,
        is_active=True
    ).first()
    
    if not enrollment:
        raise AuthError("Must be enrolled to review")
    
    # Validate rating
    if not (1 <= rating <= 5):
        raise AuthError("Rating must be between 1 and 5")
    
    # Check for existing review
    existing = Review.query.filter_by(
        user_id=user_id,
        course_id=course_id
    ).first()
    
    if existing:
        # Update existing review
        existing.rating = rating
        existing.comment = comment
        existing.updated_at = datetime.utcnow()
        db.session.commit()
        return existing
    
    # Create review
    review = Review(
        user_id=user_id,
        course_id=course_id,
        rating=rating,
        comment=comment
    )
    
    db.session.add(review)
    db.session.commit()
    
    track_course_event(course_id, 'review_added', user_id, {'rating': rating})
    
    return review


def get_course_reviews(course_id, page=1, per_page=10):
    """
    Get course reviews.
    
    Args:
        course_id: Course ID
        page: Page number
        per_page: Items per page
    
    Returns:
        dict: Paginated reviews
    """
    pagination = Review.query.filter_by(
        course_id=course_id
    ).order_by(Review.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return {
        'reviews': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages
    }


# Categories and Tags

def create_category(name, description=None, icon='book'):
    """
    Create a category.
    
    Args:
        name: Category name
        description: Category description
        icon: Icon name
    
    Returns:
        Category: Created category
    """
    existing = Category.query.filter_by(name=name).first()
    if existing:
        raise AuthError("Category already exists")
    
    category = Category(
        name=name,
        description=description,
        icon=icon
    )
    
    db.session.add(category)
    db.session.commit()
    
    return category


def list_categories():
    """
    List all categories.
    
    Returns:
        list: Categories
    """
    categories = Category.query.all()
    return [c.to_dict() for c in categories]


def get_category(category_id):
    """
    Get category details.
    
    Args:
        category_id: Category ID
    
    Returns:
        Category: Category object
    """
    category = Category.query.get(category_id)
    
    if not category:
        raise AuthError("Category not found")
    
    return category.to_dict()


# Search

def search_courses(query, filters=None, page=1, per_page=20):
    """
    Search courses.
    
    Args:
        query: Search query
        filters: Optional filters
        page: Page number
        per_page: Items per page
    
    Returns:
        dict: Search results
    """
    filters = filters or {}
    
    # Build search query
    search_term = f"%{query}%"
    base_query = Course.query.filter(
        Course.is_published == True,
        db.or_(
            Course.title.ilike(search_term),
            Course.description.ilike(search_term)
        )
    )
    
    # Apply additional filters
    if filters.get('category_id'):
        base_query = base_query.filter_by(category_id=filters['category_id'])
    
    if filters.get('difficulty'):
        base_query = base_query.filter_by(difficulty=filters['difficulty'])
    
    if filters.get('min_price') is not None:
        base_query = base_query.filter(Course.price >= filters['min_price'])
    
    if filters.get('max_price') is not None:
        base_query = base_query.filter(Course.price <= filters['max_price'])
    
    if filters.get('instructor_id'):
        base_query = base_query.filter_by(instructor_id=filters['instructor_id'])
    
    # Order by relevance (or specified)
    sort_by = filters.get('sort_by', 'created_at')
    sort_order = filters.get('sort_order', 'desc')
    
    sort_column = getattr(Course, sort_by, Course.created_at)
    if sort_order == 'desc':
        base_query = base_query.order_by(sort_column.desc())
    else:
        base_query = base_query.order_by(sort_column.asc())
    
    # Paginate
    pagination = base_query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return {
        'courses': [c.to_dict() for c in pagination.items],
        'total': pagination.total,
        'page': page,
        'per_page': per_page,
        'pages': pagination.pages,
        'query': query
    }


# Featured Courses

def get_featured_courses(limit=6):
    """
    Get featured courses.
    
    Args:
        limit: Number of courses to return
    
    Returns:
        list: Featured courses
    """
    courses = Course.query.filter_by(
        is_published=True,
        is_featured=True
    ).order_by(Course.created_at.desc()).limit(limit).all()
    
    return [c.to_dict() for c in courses]


def get_popular_courses(limit=6, days=30):
    """
    Get popular courses by enrollment.
    
    Args:
        limit: Number of courses
        days: Days to consider
    
    Returns:
        list: Popular courses
    """
    courses = Course.query.filter_by(
        is_published=True
    ).order_by(
        Course.enrollments.count().desc()
    ).limit(limit).all()
    
    return [c.to_dict() for c in courses]


def get_recommended_courses(user_id, limit=6):
    """
    Get recommended courses for a user.
    
    Args:
        user_id: User ID
        limit: Number of courses
    
    Returns:
        list: Recommended courses
    """
    from src.models import Enrollment
    
    # Get user's enrolled course categories
    enrolled = Enrollment.query.filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    enrolled_course_ids = [e.course_id for e in enrolled]
    
    # Get categories the user is interested in
    enrolled_courses = Course.query.filter(
        Course.id.in_(enrolled_course_ids)
    ).all() if enrolled_course_ids else []
    
    category_ids = list(set(c.category_id for c in enrolled_courses if c.category_id))
    
    # Get courses from those categories (not enrolled)
    query = Course.query.filter(
        Course.is_published == True,
        Course.id.notin_(enrolled_course_ids) if enrolled_course_ids else True
    )
    
    if category_ids:
        query = query.filter(Course.category_id.in_(category_ids))
    
    courses = query.order_by(Course.created_at.desc()).limit(limit).all()
    
    return [c.to_dict() for c in courses]