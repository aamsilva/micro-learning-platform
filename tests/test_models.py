"""
Tests for database models
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, db
from src.models import User, Course, Lesson, Quiz, Progress, Certificate, Review, Category, Tag


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client


@pytest.fixture
def auth_headers(client):
    """Get authentication headers"""
    # Create a test user and get token
    with app.app_context():
        user = User(
            email='test@test.com',
            username='testuser',
            password_hash='hashed_password',
            full_name='Test User',
            role='student'
        )
        db.session.add(user)
        db.session.commit()
    
    # Login and get token
    response = client.post('/api/auth/login', json={
        'email': 'test@test.com',
        'password': 'testpassword'
    })
    
    if response.status_code == 200:
        token = response.get_json()['data']['tokens']['access_token']
        return {'Authorization': f'Bearer {token}'}
    
    return {}


def test_user_model():
    """Test User model"""
    with app.app_context():
        user = User(
            email='test@example.com',
            username='testuser',
            password_hash='hashed',
            full_name='Test User'
        )
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.email == 'test@example.com'
        assert user.username == 'testuser'
        assert user.role == 'student'
        assert user.is_active is True


def test_category_model():
    """Test Category model"""
    with app.app_context():
        category = Category(
            name='Programming',
            description='Learn programming',
            icon='code'
        )
        db.session.add(category)
        db.session.commit()
        
        assert category.id is not None
        assert category.name == 'Programming'
        assert category.courses.count() == 0


def test_course_model():
    """Test Course model"""
    with app.app_context():
        # Create user
        user = User(
            email='instructor@test.com',
            username='instructor',
            password_hash='hashed',
            full_name='Instructor',
            role='instructor'
        )
        db.session.add(user)
        
        # Create category
        category = Category(name='Test', description='Test')
        db.session.add(category)
        db.session.commit()
        
        # Create course
        course = Course(
            title='Test Course',
            description='Test description',
            instructor_id=user.id,
            category_id=category.id,
            difficulty='beginner',
            price=0.0
        )
        db.session.add(course)
        db.session.commit()
        
        assert course.id is not None
        assert course.title == 'Test Course'
        assert course.instructor_id == user.id
        assert course.is_published is False


def test_lesson_model():
    """Test Lesson model"""
    with app.app_context():
        # Create user
        user = User(
            email='instructor2@test.com',
            username='instructor2',
            password_hash='hashed',
            full_name='Instructor 2',
            role='instructor'
        )
        db.session.add(user)
        
        # Create course
        course = Course(
            title='Test Course 2',
            description='Test',
            instructor_id=user.id
        )
        db.session.add(course)
        db.session.commit()
        
        # Create lesson
        lesson = Lesson(
            course_id=course.id,
            title='Lesson 1',
            content='Test content',
            content_type='text',
            order=1
        )
        db.session.add(lesson)
        db.session.commit()
        
        assert lesson.id is not None
        assert lesson.title == 'Lesson 1'
        assert lesson.course_id == course.id
        assert lesson.order == 1


def test_quiz_model():
    """Test Quiz model"""
    with app.app_context():
        # Create user and course
        user = User(
            email='instructor3@test.com',
            username='instructor3',
            password_hash='hashed',
            full_name='Instructor 3',
            role='instructor'
        )
        db.session.add(user)
        
        course = Course(
            title='Test Course 3',
            description='Test',
            instructor_id=user.id
        )
        db.session.add(course)
        db.session.commit()
        
        # Create lesson
        lesson = Lesson(
            course_id=course.id,
            title='Lesson 1',
            content='Test',
            order=1
        )
        db.session.add(lesson)
        db.session.commit()
        
        # Create quiz
        quiz = Quiz(
            lesson_id=lesson.id,
            title='Test Quiz',
            passing_score=70,
            questions=[
                {
                    'question': 'What is 2+2?',
                    'options': ['3', '4', '5', '6'],
                    'correct': 1
                }
            ]
        )
        db.session.add(quiz)
        db.session.commit()
        
        assert quiz.id is not None
        assert quiz.title == 'Test Quiz'
        assert quiz.passing_score == 70
        assert len(quiz.questions) == 1


def test_progress_model():
    """Test Progress model"""
    with app.app_context():
        # Create user
        user = User(
            email='student@test.com',
            username='student',
            password_hash='hashed',
            full_name='Student'
        )
        db.session.add(user)
        
        # Create course
        course = Course(
            title='Progress Test Course',
            description='Test',
            instructor_id=user.id
        )
        db.session.add(course)
        
        # Create lesson
        lesson = Lesson(
            course_id=course.id,
            title='Lesson',
            content='Test',
            order=1
        )
        db.session.add(lesson)
        db.session.commit()
        
        # Create progress
        progress = Progress(
            user_id=user.id,
            course_id=course.id,
            lesson_id=lesson.id,
            completed=True
        )
        db.session.add(progress)
        db.session.commit()
        
        assert progress.id is not None
        assert progress.completed is True
        assert progress.user_id == user.id


def test_certificate_model():
    """Test Certificate model"""
    with app.app_context():
        user = User(
            email='certstudent@test.com',
            username='certstudent',
            password_hash='hashed',
            full_name='Cert Student'
        )
        db.session.add(user)
        
        course = Course(
            title='Certificate Test Course',
            description='Test',
            instructor_id=user.id
        )
        db.session.add(course)
        db.session.commit()
        
        # Create certificate
        cert = Certificate(
            user_id=user.id,
            course_id=course.id,
            certificate_number='CERT-TEST-001'
        )
        db.session.add(cert)
        db.session.commit()
        
        assert cert.id is not None
        assert cert.certificate_number == 'CERT-TEST-001'


def test_review_model():
    """Test Review model"""
    with app.app_context():
        user = User(
            email='reviewer@test.com',
            username='reviewer',
            password_hash='hashed',
            full_name='Reviewer'
        )
        db.session.add(user)
        
        course = Course(
            title='Review Test Course',
            description='Test',
            instructor_id=user.id
        )
        db.session.add(course)
        db.session.commit()
        
        # Create review
        review = Review(
            user_id=user.id,
            course_id=course.id,
            rating=5,
            comment='Great course!'
        )
        db.session.add(review)
        db.session.commit()
        
        assert review.id is not None
        assert review.rating == 5
        assert review.comment == 'Great course!'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])