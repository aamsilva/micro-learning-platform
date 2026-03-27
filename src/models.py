"""
Database Models for Micro Learning Platform

This module defines all SQLAlchemy models for the LMS including:
- User (authentication and profiles)
- Course (course information)
- Lesson (lesson content)
- Quiz (assessments)
- Progress (learning progress)
- Certificate (completion certificates)
- Review (course ratings)
- Category (course categories)
- Tag (course tags)
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid

# Initialize SQLAlchemy - will be configured in main.py
db = SQLAlchemy()


class User(db.Model):
    """
    User model for authentication and profile management.
    
    Attributes:
        id: Primary key
        email: User's email (unique)
        username: Username (unique)
        password_hash: Hashed password
        full_name: User's full name
        role: User role (student, instructor, admin)
        avatar_url: Profile picture URL
        bio: User biography
        created_at: Account creation timestamp
        updated_at: Last profile update timestamp
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, instructor, admin
    avatar_url = db.Column(db.String(500), default=None)
    bio = db.Column(db.Text, default=None)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    enrolled_courses = db.relationship('Enrollment', back_populates='user', lazy='dynamic')
    instructor_courses = db.relationship('Course', back_populates='instructor', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='user', lazy='dynamic')
    certificates = db.relationship('Certificate', back_populates='user', lazy='dynamic')
    progress = db.relationship('Progress', back_populates='user', lazy='dynamic')
    quiz_attempts = db.relationship('QuizAttempt', back_populates='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self, include_email=False):
        """Convert user to dictionary."""
        data = {
            'id': self.id,
            'username': self.username,
            'full_name': self.full_name,
            'role': self.role,
            'avatar_url': self.avatar_url,
            'bio': self.bio,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_email:
            data['email'] = self.email
        return data
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_instructor(self):
        return self.role in ['instructor', 'admin']


class Category(db.Model):
    """
    Course category model.
    
    Attributes:
        id: Primary key
        name: Category name
        description: Category description
        icon: Icon name for UI
        created_at: Creation timestamp
    """
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='book')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    courses = db.relationship('Course', back_populates='category', lazy='dynamic')
    
    def __repr__(self):
        return f'<Category {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'course_count': self.courses.count()
        }


class Tag(db.Model):
    """
    Tag model for course tagging.
    
    Attributes:
        id: Primary key
        name: Tag name (unique)
        created_at: Creation timestamp
    """
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Many-to-many relationship with Course
    courses = db.relationship('CourseTag', back_populates='tag', lazy='dynamic')
    
    def __repr__(self):
        return f'<Tag {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'course_count': self.courses.count()
        }


class Course(db.Model):
    """
    Course model representing a learning course.
    
    Attributes:
        id: Primary key
        title: Course title
        description: Course description
        thumbnail_url: Course thumbnail image
        instructor_id: Foreign key to User
        category_id: Foreign key to Category
        difficulty: Course difficulty level
        price: Course price
        is_published: Publication status
        is_featured: Featured status for homepage
        duration_hours: Estimated course duration
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = 'courses'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    thumbnail_url = db.Column(db.String(500), default=None)
    instructor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'))
    difficulty = db.Column(db.String(20), default='beginner')  # beginner, intermediate, advanced
    price = db.Column(db.Float, default=0.0)
    is_published = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    duration_hours = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instructor = db.relationship('User', back_populates='instructor_courses')
    category = db.relationship('Category', back_populates='courses')
    lessons = db.relationship('Lesson', back_populates='course', lazy='dynamic', order_by='Lesson.order')
    enrollments = db.relationship('Enrollment', back_populates='course', lazy='dynamic')
    reviews = db.relationship('Review', back_populates='course', lazy='dynamic')
    certificates = db.relationship('Certificate', back_populates='course', lazy='dynamic')
    tags = db.relationship('CourseTag', back_populates='course', lazy='dynamic')
    
    def __repr__(self):
        return f'<Course {self.title}>'
    
    def to_dict(self, include_details=False):
        """Convert course to dictionary."""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'thumbnail_url': self.thumbnail_url,
            'instructor_id': self.instructor_id,
            'instructor_name': self.instructor.full_name if self.instructor else None,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'difficulty': self.difficulty,
            'price': self.price,
            'is_published': self.is_published,
            'is_featured': self.is_featured,
            'duration_hours': self.duration_hours,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'lesson_count': self.lessons.count(),
            'enrollment_count': self.enrollments.count(),
            'average_rating': self.get_average_rating()
        }
        
        if include_details:
            data['tags'] = [tag.tag.to_dict() for tag in self.tags]
            data['lessons'] = [lesson.to_dict() for lesson in self.lessons]
        
        return data
    
    def get_average_rating(self):
        """Calculate average course rating."""
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(r.rating for r in reviews) / len(reviews)
    
    def get_enrollment_count(self):
        """Get total enrolled students."""
        return self.enrollments.count()
    
    def is_enrolled(self, user_id):
        """Check if user is enrolled."""
        return self.enrollments.filter_by(user_id=user_id).first() is not None
    
    def get_completion_percentage(self, user_id):
        """Get user's completion percentage for this course."""
        enrollment = self.enrollments.filter_by(user_id=user_id).first()
        if not enrollment:
            return 0
        
        total_lessons = self.lessons.count()
        if total_lessons == 0:
            return 0
        
        completed_lessons = Progress.query.filter_by(
            user_id=user_id,
            course_id=self.id,
            completed=True
        ).count()
        
        return round((completed_lessons / total_lessons) * 100, 2)


class CourseTag(db.Model):
    """Many-to-many relationship between Course and Tag."""
    __tablename__ = 'course_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('tags.id'), nullable=False)
    
    # Relationships
    course = db.relationship('Course', back_populates='tags')
    tag = db.relationship('Tag', back_populates='courses')
    
    def __repr__(self):
        return f'<CourseTag course={self.course_id} tag={self.tag_id}>'


class Enrollment(db.Model):
    """
    Enrollment model tracking user course enrollments.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        course_id: Foreign key to Course
        enrolled_at: Enrollment timestamp
        is_active: Active enrollment status
    """
    __tablename__ = 'enrollments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    user = db.relationship('User', back_populates='enrolled_courses')
    course = db.relationship('Course', back_populates='enrollments')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_enrollment'),
    )
    
    def __repr__(self):
        return f'<Enrollment user={self.user_id} course={self.course_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'enrolled_at': self.enrolled_at.isoformat() if self.enrolled_at else None,
            'is_active': self.is_active,
            'course': self.course.to_dict() if self.course else None
        }


class Lesson(db.Model):
    """
    Lesson model for course content.
    
    Attributes:
        id: Primary key
        course_id: Foreign key to Course
        title: Lesson title
        content: Lesson content (text or code)
        content_type: Type of content (video, text, code)
        video_url: URL for video content
        order: Lesson order within course
        duration_minutes: Estimated lesson duration
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    content_type = db.Column(db.String(20), default='text')  # video, text, code
    video_url = db.Column(db.String(500), default=None)
    order = db.Column(db.Integer, default=0)
    duration_minutes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    course = db.relationship('Course', back_populates='lessons')
    quiz = db.relationship('Quiz', back_populates='lesson', uselist=False)
    progress = db.relationship('Progress', back_populates='lesson', lazy='dynamic')
    
    def __repr__(self):
        return f'<Lesson {self.title}>'
    
    def to_dict(self, include_content=False):
        """Convert lesson to dictionary."""
        data = {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'content_type': self.content_type,
            'video_url': self.video_url,
            'order': self.order,
            'duration_minutes': self.duration_minutes,
            'has_quiz': self.quiz is not None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        if include_content:
            data['content'] = self.content
        
        return data
    
    def get_next_lesson(self):
        """Get the next lesson in the course."""
        return Lesson.query.filter(
            Lesson.course_id == self.course_id,
            Lesson.order > self.order
        ).order_by(Lesson.order).first()
    
    def get_prev_lesson(self):
        """Get the previous lesson in the course."""
        return Lesson.query.filter(
            Lesson.course_id == self.course_id,
            Lesson.order < self.order
        ).order_by(Lesson.order.desc()).first()


class Quiz(db.Model):
    """
    Quiz model for lesson assessments.
    
    Attributes:
        id: Primary key
        lesson_id: Foreign key to Lesson
        title: Quiz title
        description: Quiz description
        passing_score: Minimum passing score (percentage)
        questions: JSON array of questions
        time_limit_minutes: Optional time limit
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    passing_score = db.Column(db.Integer, default=70)
    questions = db.Column(db.JSON, default=list)
    time_limit_minutes = db.Column(db.Integer, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lesson = db.relationship('Lesson', back_populates='quiz')
    attempts = db.relationship('QuizAttempt', back_populates='quiz', lazy='dynamic')
    
    def __repr__(self):
        return f'<Quiz {self.title}>'
    
    def to_dict(self, include_answers=False):
        """Convert quiz to dictionary."""
        data = {
            'id': self.id,
            'lesson_id': self.lesson_id,
            'title': self.title,
            'description': self.description,
            'passing_score': self.passing_score,
            'question_count': len(self.questions) if self.questions else 0,
            'time_limit_minutes': self.time_limit_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # Include questions (without correct answers for security)
        if self.questions:
            if include_answers:
                data['questions'] = self.questions
            else:
                # Strip correct answers
                data['questions'] = [
                    {
                        'question': q.get('question'),
                        'options': q.get('options')
                    }
                    for q in self.questions
                ]
        
        return data
    
    def get_question_count(self):
        """Get total number of questions."""
        return len(self.questions) if self.questions else 0


class QuizAttempt(db.Model):
    """
    Quiz attempt tracking model.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        quiz_id: Foreign key to Quiz
        score: Score achieved
        answers: User's answers (JSON)
        passed: Whether user passed
        attempt_number: Which attempt this is
        completed_at: Completion timestamp
    """
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Float, default=0.0)
    answers = db.Column(db.JSON, default=list)
    passed = db.Column(db.Boolean, default=False)
    attempt_number = db.Column(db.Integer, default=1)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='quiz_attempts')
    quiz = db.relationship('Quiz', back_populates='attempts')
    
    def __repr__(self):
        return f'<QuizAttempt user={self.user_id} quiz={self.quiz_id} score={self.score}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'quiz_id': self.quiz_id,
            'score': self.score,
            'answers': self.answers,
            'passed': self.passed,
            'attempt_number': self.attempt_number,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def calculate_score(self):
        """Calculate quiz score based on answers."""
        if not self.quiz or not self.quiz.questions:
            return 0
        
        correct = 0
        total = len(self.quiz.questions)
        
        for i, answer in enumerate(self.answers):
            if i < len(self.quiz.questions):
                question = self.quiz.questions[i]
                if answer.get('selected') == question.get('correct'):
                    correct += 1
        
        return (correct / total * 100) if total > 0 else 0


class Progress(db.Model):
    """
    Learning progress tracking model.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        course_id: Foreign key to Course
        lesson_id: Foreign key to Lesson
        completed: Completion status
        time_spent_seconds: Time spent on lesson
        completed_at: Completion timestamp
    """
    __tablename__ = 'progress'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    time_spent_seconds = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime, default=None)
    
    # Relationships
    user = db.relationship('User', back_populates='progress')
    course = db.relationship('Course')
    lesson = db.relationship('Lesson', back_populates='progress')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'lesson_id', name='unique_lesson_progress'),
    )
    
    def __repr__(self):
        return f'<Progress user={self.user_id} lesson={self.lesson_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'lesson_id': self.lesson_id,
            'completed': self.completed,
            'time_spent_seconds': self.time_spent_seconds,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'lesson': self.lesson.to_dict() if self.lesson else None
        }
    
    def mark_complete(self):
        """Mark progress as complete."""
        self.completed = True
        self.completed_at = datetime.utcnow()


class Certificate(db.Model):
    """
    Course completion certificate model.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        course_id: Foreign key to Course
        certificate_number: Unique certificate ID
        issued_at: Certificate issue timestamp
    """
    __tablename__ = 'certificates'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    certificate_number = db.Column(db.String(50), unique=True, nullable=False)
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='certificates')
    course = db.relationship('Course', back_populates='certificates')
    
    def __repr__(self):
        return f'<Certificate {self.certificate_number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'certificate_number': self.certificate_number,
            'issued_at': self.issued_at.isoformat() if self.issued_at else None,
            'user': self.user.to_dict() if self.user else None,
            'course': self.course.to_dict() if self.course else None
        }
    
    @staticmethod
    def generate_certificate_number():
        """Generate a unique certificate number."""
        return f'CERT-{uuid.uuid4().hex[:12].upper()}'


class Review(db.Model):
    """
    Course review model for ratings and feedback.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        course_id: Foreign key to Course
        rating: Rating (1-5)
        comment: Review comment
        created_at: Review timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='reviews')
    course = db.relationship('Course', back_populates='reviews')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'course_id', name='unique_user_course_review'),
    )
    
    def __repr__(self):
        return f'<Review user={self.user_id} course={self.course_id} rating={self.rating}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'full_name': self.user.full_name,
                'avatar_url': self.user.avatar_url
            } if self.user else None
        }
    
    def validate_rating(self):
        """Ensure rating is between 1 and 5."""
        return 1 <= self.rating <= 5


# Additional utility models for analytics

class UserActivity(db.Model):
    """
    User activity log for analytics.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        activity_type: Type of activity (login, lesson_view, quiz_complete, etc.)
        details: Activity details (JSON)
        ip_address: User's IP address
        created_at: Activity timestamp
    """
    __tablename__ = 'user_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    activity_type = db.Column(db.String(50), nullable=False)
    details = db.Column(db.JSON, default=dict)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<UserActivity {self.activity_type} user={self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Achievement(db.Model):
    """
    Achievement/badge model for gamification.
    
    Attributes:
        id: Primary key
        name: Achievement name
        description: Achievement description
        icon: Icon name
        criteria: Achievement criteria (JSON)
        created_at: Creation timestamp
    """
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='star')
    criteria = db.Column(db.JSON, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user_achievements = db.relationship('UserAchievement', back_populates='achievement', lazy='dynamic')
    
    def __repr__(self):
        return f'<Achievement {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'criteria': self.criteria
        }


class UserAchievement(db.Model):
    """Many-to-many relationship between User and Achievement."""
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User')
    achievement = db.relationship('Achievement', back_populates='user_achievements')
    
    def __repr__(self):
        return f'<UserAchievement user={self.user_id} achievement={self.achievement_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'achievement_id': self.achievement_id,
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'achievement': self.achievement.to_dict() if self.achievement else None
        }