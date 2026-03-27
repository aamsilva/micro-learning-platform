"""
Micro Learning Platform - Main Application Entry Point

This module initializes and configures the Flask application,
sets up all extensions, registers blueprints, and handles
CLI commands for database management.
"""

import os
import sys
import click
from datetime import timedelta
from flask import Flask, render_template, jsonify, request
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_migrate import Migrate
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize extensions - import from src.models
from src.models import db, User, Course, Lesson, Quiz, Progress, Certificate, Review, Category, Tag

jwt = JWTManager()
migrate = Migrate()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name=None):
    """
    Application factory for creating Flask app instances.
    
    Args:
        config_name: Optional configuration name (development/testing/production)
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    configure_app(app, config_name)
    
    # Initialize extensions with app
    initialize_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register CLI commands
    register_cli_commands(app)
    
    return app


def configure_app(app, config_name):
    """
    Configure the Flask application with settings.
    
    Args:
        app: Flask application instance
        config_name: Configuration name
    """
    # Base configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    
    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        f'sqlite:///{os.path.join(basedir, "instance", "lms.db")}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = False
    
    # Cache configuration
    app.config['CACHE_TYPE'] = 'simple'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    
    # Rate limiting
    app.config['RATELIMIT_ENABLED'] = True
    app.config['RATELIMIT_DEFAULT'] = "100 per hour"
    app.config['RATELIMIT_STORAGE'] = 'memory'
    
    # Upload configuration
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
    app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp4', 'webm'}
    
    # CORS configuration
    app.config['CORS_ORIGINS'] = ['http://localhost:5000', 'http://127.0.0.1:5000']
    
    # Swagger configuration
    app.config['SWAGGER'] = {
        'title': 'Micro Learning Platform API',
        'uiversion': 3,
        'doc': 'docs'
    }


def initialize_extensions(app):
    """
    Initialize all Flask extensions with the application.
    
    Args:
        app: Flask application instance
    """
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Initialize JWT
    jwt.init_app(app)
    
    # Initialize migrations
    migrate.init_app(app, db)
    
    # Initialize cache
    cache.init_app(app)
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config['CORS_ORIGINS'],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Create upload folder if not exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def register_blueprints(app):
    """
    Register Flask blueprints for modular routing.
    
    Args:
        app: Flask application instance
    """
    from src.api import api_bp
    
    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register main routes
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/login')
    def login_page():
        return render_template('login.html')
    
    @app.route('/register')
    def register_page():
        return render_template('register.html')
    
    @app.route('/dashboard')
    def dashboard_page():
        return render_template('dashboard.html')
    
    @app.route('/courses')
    def courses_page():
        return render_template('courses.html')
    
    @app.route('/course/<int:course_id>')
    def course_detail_page(course_id):
        return render_template('course_detail.html', course_id=course_id)
    
    @app.route('/lesson/<int:lesson_id>')
    def lesson_page(lesson_id):
        return render_template('lesson.html', lesson_id=lesson_id)
    
    @app.route('/quiz/<int:quiz_id>')
    def quiz_page(quiz_id):
        return render_template('quiz.html', quiz_id=quiz_id)
    
    @app.route('/profile')
    def profile_page():
        return render_template('profile.html')
    
    @app.route('/analytics')
    def analytics_page():
        return render_template('analytics.html')


def register_error_handlers(app):
    """
    Register custom error handlers for the application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Resource not found',
                'status': 404
            }), 404
        return render_template('error.html', error='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Internal server error',
                'status': 500
            }), 500
        return render_template('error.html', error='Internal server error'), 500
    
    @app.errorhandler(400)
    def bad_request(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Bad request',
                'status': 400
            }), 400
        return render_template('error.html', error='Bad request'), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Authentication required',
                'status': 401
            }), 401
        return render_template('error.html', error='Please login to continue'), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Access forbidden',
                'status': 403
            }), 403
        return render_template('error.html', error='You do not have permission'), 403
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'success': False,
            'error': 'Token has expired',
            'code': 'token_expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Invalid token',
            'code': 'invalid_token'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'Authorization required',
            'code': 'authorization_required'
        }), 401


def register_cli_commands(app):
    """
    Register CLI commands for database management.
    
    Args:
        app: Flask application instance
    """
    
    @app.cli.command('init-db')
    def init_db():
        """Initialize the database with tables and default data."""
        click.echo('Initializing database...')
        
        # Import all models to ensure they're registered
        from src.models import User, Course, Lesson, Quiz, Progress, Certificate, Review, Category, Tag
        
        # Create all tables
        db.create_all()
        click.echo('Tables created successfully.')
        
        # Create default admin user
        from src.auth import create_user
        admin = create_user(
            email='admin@lms.com',
            username='admin',
            password='admin123',
            full_name='System Administrator',
            role='admin'
        )
        click.echo(f'Admin user created: {admin.email}')
        
        # Create default instructor user
        instructor = create_user(
            email='instructor@lms.com',
            username='instructor',
            password='instructor123',
            full_name='Demo Instructor',
            role='instructor'
        )
        click.echo(f'Instructor user created: {instructor.email}')
        
        # Create default student user
        student = create_user(
            email='student@lms.com',
            username='student',
            password='student123',
            full_name='Demo Student',
            role='student'
        )
        click.echo(f'Student user created: {student.email}')
        
        # Create default categories
        categories = [
            {'name': 'Programming', 'description': 'Learn programming languages', 'icon': 'code'},
            {'name': 'Web Development', 'description': 'Build websites and web apps', 'icon': 'globe'},
            {'name': 'Data Science', 'description': 'Analyze and visualize data', 'icon': 'chart'},
            {'name': 'Design', 'description': 'UI/UX and graphic design', 'icon': 'palette'},
            {'name': 'Business', 'description': 'Business and entrepreneurship', 'icon': 'briefcase'},
            {'name': 'Marketing', 'description': 'Digital marketing strategies', 'icon': 'megaphone'},
        ]
        
        for cat_data in categories:
            category = Category(**cat_data)
            db.session.add(category)
        
        db.session.commit()
        click.echo(f'Created {len(categories)} categories.')
        
        # Create sample course
        from src.courses import create_course
        course = create_course(
            title='Introduction to Python Programming',
            description='Learn Python from scratch. This comprehensive course covers Python basics, data structures, functions, object-oriented programming, and more.',
            instructor_id=instructor.id,
            category_id=1,
            difficulty='beginner',
            price=0.0
        )
        
        # Add lessons to the course
        lessons_data = [
            {'title': 'Welcome to Python', 'content': 'Welcome to Python programming! In this lesson, you will learn about Python and its features.', 'content_type': 'text', 'order': 1},
            {'title': 'Setting Up Your Environment', 'content': '# Setting Up Your Environment\n\nTo start programming in Python, you need to install Python on your computer.\n\n## Installation\n\n1. Download Python from python.org\n2. Run the installer\n3. Verify installation with `python --version`', 'content_type': 'text', 'order': 2},
            {'title': 'Your First Python Program', 'content': 'print("Hello, World!")', 'content_type': 'code', 'order': 3},
            {'title': 'Variables and Data Types', 'content': 'Learn about variables, strings, numbers, and booleans.', 'content_type': 'text', 'order': 4},
            {'title': 'Control Flow', 'content': 'Learn about if statements, loops, and control structures.', 'content_type': 'text', 'order': 5},
        ]
        
        for lesson_data in lessons_data:
            lesson = Lesson(course_id=course.id, **lesson_data)
            db.session.add(lesson)
        
        db.session.commit()
        
        # Add quiz for first lesson
        quiz = Quiz(
            lesson_id=1,
            title='Python Basics Quiz',
            passing_score=70,
            questions=[
                {
                    'question': 'What is Python?',
                    'options': ['A programming language', 'A snake', 'A tool', 'A database'],
                    'correct': 0
                },
                {
                    'question': 'What is the correct file extension for Python files?',
                    'options': ['.py', '.python', '.pyt', '.pyo'],
                    'correct': 0
                },
                {
                    'question': 'How do you print "Hello" in Python?',
                    'options': ['echo "Hello"', 'print("Hello")', 'printf("Hello")', 'console.log("Hello")'],
                    'correct': 1
                }
            ]
        )
        db.session.add(quiz)
        db.session.commit()
        
        click.echo(f'Created sample course: {course.title}')
        click.echo('Database initialization complete!')
    
    @app.cli.command('create-admin')
    def create_admin():
        """Create an admin user."""
        email = click.prompt('Email', default='admin@lms.com')
        username = click.prompt('Username', default='admin')
        password = click.prompt('Password', hide_input=True)
        full_name = click.prompt('Full Name', default='Admin User')
        
        from src.auth import create_user
        user = create_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            role='admin'
        )
        
        click.echo(f'Admin user created: {user.email}')
    
    @app.cli.command('create-course')
    def create_course_cmd():
        """Create a new course (CLI)."""
        title = click.prompt('Course Title')
        description = click.prompt('Description')
        category_id = click.prompt('Category ID', type=int)
        difficulty = click.prompt('Difficulty', default='beginner')
        price = click.prompt('Price', default=0.0, type=float)
        
        # For CLI, we'll use the first instructor found
        from src.models import User
        instructor = User.query.filter_by(role='instructor').first()
        
        if not instructor:
            click.echo('No instructor found. Please create one first.')
            return
        
        from src.courses import create_course
        course = create_course(
            title=title,
            description=description,
            instructor_id=instructor.id,
            category_id=category_id,
            difficulty=difficulty,
            price=price
        )
        
        click.echo(f'Course created: {course.title} (ID: {course.id})')


# Import models to ensure they're available
from src.models import User, Course, Lesson, Quiz, Progress, Certificate, Review, Category, Tag


# Create the application instance
app = create_app()


def run_server(host='0.0.0.0', port=5000, debug=True):
    """
    Run the Flask development server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Enable debug mode
    """
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Micro Learning Platform')
    parser.add_argument('command', nargs='?', help='Command to run (run/init-db/create-admin/create-course)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    
    args = parser.parse_args()
    
    if args.command == 'init-db':
        with app.app_context():
            db.create_all()
            click.echo('Database initialized!')
    elif args.command == 'run':
        run_server(host=args.host, port=args.port, debug=args.debug)
    else:
        # Default: run the server
        run_server(debug=args.debug if args.command == '--debug' else True)