#!/usr/bin/env python3
"""
Seed Data Generator - Gera dados de teste para micro-learning-platform
Executar: python seed_data.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import create_app, db
from src.models import User, Course, Lesson, Quiz, Category, Progress, Certificate, Enrollment
from src.auth import hash_password
from datetime import datetime, timedelta
import random

def generate_seed_data():
    app = create_app()
    
    with app.app_context():
        db.create_all()
        print("✅ Database created")
        
        # Categorias
        categories = [
            Category(name="Programming", description="Programming languages"),
            Category(name="Web Dev", description="Web technologies"),
            Category(name="Data Science", description="Data analysis and ML"),
            Category(name="AI", description="Artificial Intelligence"),
            Category(name="Business", description="Business skills"),
        ]
        db.session.add_all(categories)
        db.session.commit()
        print(f"✅ {len(categories)} categories")
        
        # Utilizadores
        users = []
        admin = User(username="admin", email="admin@lms.com", password_hash=hash_password("Admin123"), full_name="Admin", role="admin")
        users.append(admin)
        
        for i in range(3):
            instructor = User(username=f"instructor{i}", email=f"instructor{i}@lms.com", password_hash=hash_password("Instructor123"), full_name=f"Instructor {i}", role="instructor")
            users.append(instructor)
        
        for i in range(10):
            student = User(username=f"student{i}", email=f"student{i}@lms.com", password_hash=hash_password("Student123"), full_name=f"Student {i}", role="student")
            users.append(student)
        
        db.session.add_all(users)
        db.session.commit()
        print(f"✅ {len(users)} users")
        
        # Cursos
        courses = []
        course_data = [
            ("Python for Beginners", "Learn Python from scratch", 1, "Beginner", 40),
            ("Advanced Python", "Master advanced concepts", 1, "Advanced", 30),
            ("Web Dev with Flask", "Build web apps", 2, "Intermediate", 35),
            ("Data Science", "Data analysis and ML", 3, "Intermediate", 50),
            ("Machine Learning", "ML fundamentals", 4, "Advanced", 45),
            ("Business Comm", "Business skills", 5, "Beginner", 20),
        ]
        
        for title, desc, cat, diff, hours in course_data:
            course = Course(title=title, description=desc, instructor_id=random.randint(2, 4), category_id=cat, difficulty=diff, duration_hours=hours, is_published=True)
            courses.append(course)
        
        db.session.add_all(courses)
        db.session.commit()
        print(f"✅ {len(courses)} courses")
        
        # Lições
        lessons = []
        for course in courses:
            for i in range(6):
                lesson = Lesson(course_id=course.id, title=f"Lesson {i+1}", content=f"Content for {course.title} - Part {i+1}", content_type="text", order=i+1)
                lessons.append(lesson)
        
        db.session.add_all(lessons)
        db.session.commit()
        print(f"✅ {len(lessons)} lessons")
        
        # Quizzes (linked to lessons)
        for course in courses:
            course_lessons = Lesson.query.filter_by(course_id=course.id).all()
            for lesson in course_lessons[:2]:  # 2 quizzes per course
                quiz = Quiz(lesson_id=lesson.id, title=f"Quiz: {lesson.title}", description="Test your knowledge", passing_score=70, questions=[])
                db.session.add(quiz)
        
        db.session.commit()
        print(f"✅ Quizzes created")
        
        # Inscrições e progresso
        for student in users[4:14]:
            for course in random.sample(courses, 4):
                enroll = Enrollment(user_id=student.id, course_id=course.id)
                db.session.add(enroll)
                
                # Progresso
                course_lessons = Lesson.query.filter_by(course_id=course.id).all()
                for lesson in random.sample(course_lessons, 3):
                    progress = Progress(user_id=student.id, course_id=course.id, lesson_id=lesson.id, completed=True, completed_at=datetime.utcnow())
                    db.session.add(progress)
        
        db.session.commit()
        print(f"✅ Enrollments and progress created")
        
        # Certificados
        for student in users[4:14]:
            for course in random.sample(courses, 2):
                cert = Certificate(user_id=student.id, course_id=course.id, issued_at=datetime.utcnow())
                db.session.add(cert)
        
        db.session.commit()
        print(f"✅ Certificates created")
        
        print("\n" + "=" * 50)
        print("🎉 SEED DATA COMPLETE!")
        print("=" * 50)
        print("""
🔑 LOGIN:
  Admin:    admin@lms.com / Admin123
  Teacher:  instructor0@lms.com / Instructor123  
  Student:  student0@lms.com / Student123

🌐 URL: http://localhost:5005
""")

if __name__ == "__main__":
    generate_seed_data()