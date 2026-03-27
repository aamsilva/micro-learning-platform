"""
Tests for courses module
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, db
from src.models import User, Course, Lesson, Enrollment, Category
from src.courses import (
    create_course, get_course, list_courses, enroll_course, unenroll_course,
    create_lesson, get_lesson, mark_lesson_complete, get_user_progress,
    add_review, generate_certificate, get_user_certificates, search_courses
)
from src.auth import create_user, generate_tokens


@pytest.fixture
def test_app():
    """Create test app"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['JWT_SECRET_KEY'] = 'test-jwt-secret'
    
    with app.app_context():
        db.create_all()
    
    yield app


@pytest.fixture
def instructor(test_app):
    """Create instructor user"""
    with test_app.app_context():
        instructor = create_user(
            email='instructor@test.com',
            username='instructor',
            password='Instructor123',
            full_name='Course Instructor',
            role='instructor'
        )
        return instructor


@pytest.fixture
def student(test_app):
    """Create student user"""
    with test_app.app_context():
        student = create_user(
            email='student@test.com',
            username='student',
            password='Student123',
            full_name='Course Student',
            role='student'
        )
        return student


@pytest.fixture
def category(test_app):
    """Create category"""
    with test_app.app_context():
        cat = Category(name='Programming', description='Programming courses')
        db.session.add(cat)
        db.session.commit()
        return cat


def test_create_course(test_app, instructor, category):
    """Test course creation"""
    with test_app.app_context():
        course = create_course(
            title='Python Basics',
            description='Learn Python from scratch',
            instructor_id=instructor.id,
            category_id=category.id,
            difficulty='beginner',
            price=0.0
        )
        
        assert course is not None
        assert course.title == 'Python Basics'
        assert course.instructor_id == instructor.id
        assert course.is_published is False


def test_get_course(test_app, instructor, category):
    """Test get course"""
    with test_app.app_context():
        course = create_course(
            title='Get Course Test',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id
        )
        
        retrieved = get_course(course.id)
        assert retrieved['title'] == 'Get Course Test'


def test_list_courses(test_app, instructor, category):
    """Test listing courses"""
    with test_app.app_context():
        # Create multiple courses
        for i in range(5):
            create_course(
                title=f'Course {i}',
                description=f'Test course {i}',
                instructor_id=instructor.id,
                category_id=category.id,
                is_published=True
            )
        
        result = list_courses(page=1, per_page=10)
        
        assert result['total'] >= 5
        assert len(result['courses']) >= 5


def test_enroll_course(test_app, instructor, student, category):
    """Test course enrollment"""
    with test_app.app_context():
        course = create_course(
            title='Enroll Test',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        enrollment = enroll_course(course.id, student.id)
        
        assert enrollment is not None
        assert enrollment.user_id == student.id
        assert enrollment.course_id == course.id


def test_unenroll_course(test_app, instructor, student, category):
    """Test course unenrollment"""
    with test_app.app_context():
        course = create_course(
            title='Unenroll Test',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        # Enroll first
        enroll_course(course.id, student.id)
        
        # Unenroll
        result = unenroll_course(course.id, student.id)
        assert result is True


def test_create_lesson(test_app, instructor, category):
    """Test lesson creation"""
    with test_app.app_context():
        course = create_course(
            title='Lesson Test Course',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id
        )
        
        lesson = create_lesson(
            course_id=course.id,
            user_id=instructor.id,
            title='Lesson 1: Introduction',
            content='Welcome to the course!',
            content_type='text',
            order=1
        )
        
        assert lesson is not None
        assert lesson.title == 'Lesson 1: Introduction'
        assert lesson.course_id == course.id


def test_mark_lesson_complete(test_app, instructor, student, category):
    """Test marking lesson complete"""
    with test_app.app_context():
        course = create_course(
            title='Progress Test',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        # Enroll student
        enroll_course(course.id, student.id)
        
        # Create lesson
        lesson = create_lesson(
            course_id=course.id,
            user_id=instructor.id,
            title='Test Lesson',
            content='Test',
            order=1
        )
        
        # Mark complete
        progress = mark_lesson_complete(lesson.id, student.id, 100)
        
        assert progress is not None
        assert progress.completed is True


def test_get_user_progress(test_app, instructor, student, category):
    """Test get user progress"""
    with test_app.app_context():
        course = create_course(
            title='Progress Course',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        enroll_course(course.id, student.id)
        
        lesson = create_lesson(
            course_id=course.id,
            user_id=instructor.id,
            title='Progress Lesson',
            content='Test',
            order=1
        )
        
        mark_lesson_complete(lesson.id, student.id)
        
        progress = get_user_progress(student.id, course.id)
        
        assert progress['total_lessons'] >= 1
        assert progress['completed_lessons'] >= 1


def test_add_review(test_app, instructor, student, category):
    """Test adding review"""
    with test_app.app_context():
        course = create_course(
            title='Review Test',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        enroll_course(course.id, student.id)
        
        review = add_review(course.id, student.id, 5, 'Great course!')
        
        assert review is not None
        assert review.rating == 5
        assert review.comment == 'Great course!'


def test_generate_certificate(test_app, instructor, student, category):
    """Test certificate generation"""
    with test_app.app_context():
        course = create_course(
            title='Certificate Test',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        # Enroll and complete course
        enroll_course(course.id, student.id)
        
        lesson = create_lesson(
            course_id=course.id,
            user_id=instructor.id,
            title='Final Lesson',
            content='Test',
            order=1
        )
        
        mark_lesson_complete(lesson.id, student.id)
        
        certificates = get_user_certificates(student.id)
        
        assert len(certificates) >= 1


def test_search_courses(test_app, instructor, category):
    """Test course search"""
    with test_app.app_context():
        # Create courses
        create_course(
            title='Python Programming',
            description='Learn Python',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        create_course(
            title='JavaScript Basics',
            description='Learn JavaScript',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
        
        # Search
        result = search_courses('Python')
        
        assert result['total'] >= 1
        assert any('Python' in c['title'] for c in result['courses'])


def test_courses_endpoint(test_app, instructor, category):
    """Test courses API endpoint"""
    client = test_app.test_client()
    
    with test_app.app_context():
        create_course(
            title='API Test Course',
            description='Test',
            instructor_id=instructor.id,
            category_id=category.id,
            is_published=True
        )
    
    response = client.get('/api/courses')
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'courses' in data['data']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])